# SageScan — Deep Code Audit Report
**Reviewer:** Senior Backend Engineer  
**Date:** March 26, 2026  
**Codebase:** SageScan v1.0.0 (Go CLI + Python Engine, polyglot)

---

## Critical Issues (Must Fix)

---

### 1. `CombinedOutput()` Merges stderr Into JSON — IPC Contract Broken

**File:** `internal/python/engine.go` — `RunCommand()` and `RunValidation()`

```go
output, err := cmd.CombinedOutput()
```

`CombinedOutput()` merges both `stdout` and `stderr` into a single byte slice. The Go side then tries to parse this as JSON. Any Python `print(..., file=sys.stderr)`, logging output, or library warning written to stderr will prepend or interleave non-JSON content, causing a guaranteed JSON parse failure in `parseOutput()`.

**Evidence:** `engine/main.py` line 109:
```python
print(f"Running validation with config: {config_path}", file=sys.stderr)
```
This `stderr` line is captured by `CombinedOutput()`, prepended to the JSON, and then `parseOutput()` fails because the output doesn't start with `{`.

**Fix:** Use separate `stdout` and `stderr` pipes:
```go
var stdout, stderr bytes.Buffer
cmd.Stdout = &stdout
cmd.Stderr = &stderr
if err := cmd.Run(); err != nil {
    return nil, fmt.Errorf("engine error: %w\nstderr: %s", err, stderr.String())
}
output = stdout.Bytes()
```
The `directRun()` method already does this correctly — `RunCommand()` must be brought in line.

---

### 2. Engine Path Resolution Is Broken in All Deployments

**File:** `internal/python/engine.go` — `RunCommand()`

```go
enginePath = filepath.Join(filepath.Dir(filepath.Clean(e.pythonPath)), "engine", "main.py")
```

`e.pythonPath` is always `"python"` (a bare executable name, not an absolute path). `filepath.Dir("python")` returns `"."`, so `enginePath` resolves to `"./engine/main.py"`. This only works if the binary is run from the project root. In any CI, Docker, or installed context, the engine will fail to find `main.py` — silently producing a `python: can't open file './engine/main.py'` error surfaced only in the stderr that is already discarded.

**Fix:** Use an absolute path or embed the engine path as a build-time variable / env override:
```go
// Resolution priority: explicit > env var > relative to binary
if enginePath == "" {
    if ep := os.Getenv("SAGESCAN_ENGINE_PATH"); ep != "" {
        enginePath = ep
    } else {
        // Resolve relative to the running binary
        exe, _ := os.Executable()
        enginePath = filepath.Join(filepath.Dir(exe), "engine", "main.py")
    }
}
```

---

### 3. `RunValidationString()` Creates an Empty Temp Config Then Ignores the Input String

**File:** `internal/python/engine.go` — `RunValidationString()`

```go
func (e *Engine) RunValidationString(configJSON string) (*Result, error) {
    configPath, err := e.createTempConfig(Config{})   // <-- creates EMPTY config
    ...
    // configJSON is never written to the temp file or passed to the process
```

The `configJSON` parameter is never used. The function writes an empty `Config{}` struct to a temp file, calls the engine with it, and discards the actual JSON string passed in. This is a silent data-loss bug: callers believe their config is being used but it is not.

**Fix:** Either unmarshal `configJSON` into `Config` before calling `createTempConfig`, or write the raw string directly to the temp file, or remove this dead-code method entirely.

---

### 4. Python Logging Is Unguarded and Pollutes stdout at Runtime

**File:** `engine/main.py`, `engine/sagescan_engine/core/runner.py`, `engine/sagescan_engine/core/pipeline.py`

```python
logger = logging.getLogger(__name__)
logger.info("Executing validation runner...")
```

No logging configuration is set anywhere in the Python engine. The default Python logging level is `WARNING`, so `logger.info()` calls are silent by default — but this is fragile and developer-hostile. More critically, if any dependency (e.g., pandas, scipy) or any top-level code configures the root logger (which is common), all `INFO`/`DEBUG` logs will be written to `stdout`, immediately breaking the JSON contract with Go.

**Fix:** At the top of `main.py`, explicitly redirect all logging to stderr:
```python
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s"
)
```

---

### 5. `parseOutput()` — Fragile JSON Detection with Silent Truncation

**File:** `internal/python/engine.go`

```go
if !strings.HasPrefix(outputStr, "{") {
    return &Result{Status: "ERROR", Error: "Invalid output format: not JSON"}, ...
}
```

This check is both too strict and too lenient:
- **Too strict:** A BOM (`\xEF\xBB\xBF`), whitespace, or a warning line before the JSON object breaks detection.
- **Too lenient:** It only checks the first character. A response like `{"error": ...}\nsome garbage` will pass this check but `json.Unmarshal` will fail on the trailing data.

The error message `"Invalid output format: not JSON"` gives the operator no diagnostic information about what was actually received. If the Python engine crashes with a traceback, the Go caller sees only `"Invalid output format: not JSON"` with no traceback.

**Fix:**
```go
// Trim BOM and whitespace
outputStr = strings.TrimSpace(strings.TrimPrefix(outputStr, "\xef\xbb\xbf"))
// On parse failure, surface the raw output for debugging
if err := json.Unmarshal([]byte(outputStr), &result); err != nil {
    return nil, fmt.Errorf("failed to parse engine output: %w\nraw output (first 500 chars): %.500s", err, outputStr)
}
```

---

### 6. `SageScanConfig` Pydantic Model Silently Drops Extra Fields That Other Code Reads

**File:** `engine/sagescan_engine/rules/models.py`

```python
class SageScanConfig(BaseModel):
    version: str
    source: DataSource
    rules: List[ColumnRuleConfig]
```

`SageScanConfig` does not declare `context`, `baseline`, `llm_api_key`, `llm_model`, `llm_max_tokens`, or `output_file` as fields. Pydantic v2's default behavior is `extra='ignore'`, so those fields are silently dropped when the model is instantiated. `runner.py` then accesses them via `config.get("context", "")` — but `config` at that point is the validated Pydantic object, not the original dict. This means context and baseline fields are never passed through the pipeline.

**Fix:** Add all expected fields to the model, even if optional:
```python
class SageScanConfig(BaseModel):
    model_config = ConfigDict(extra='ignore')
    version: str
    source: DataSource
    rules: List[ColumnRuleConfig]
    context: Optional[str] = None
    baseline: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_max_tokens: Optional[int] = None
    output_file: Optional[str] = None
```

---

### 7. `generate-rules` Hardcodes `api_key="dummy"` — LLM Calls Always Fail Without Clear Error

**File:** `engine/sagescan_engine/core/runner.py`

```python
api_key = config.get("llm_api_key", "dummy")
```

When the user does not pass an API key, the engine will call the OpenAI SDK with `api_key="dummy"`, receive a `401 AuthenticationError`, and return:
```json
{"status": "FAIL", "summary": {"message": "LLM Generation failed: ..."}}
```
The user has no actionable guidance — they do not know they need to set `OPENAI_API_KEY` or pass `--llm-api-key`.

**Fix:** Validate the key is non-empty before calling the LLM, and check `os.environ.get("OPENAI_API_KEY")` as a fallback:
```python
api_key = config.get("llm_api_key") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    return {"status": "FAIL", "summary": {"message": "LLM API key is required. Set OPENAI_API_KEY or pass --llm-api-key."}, "results": []}
```

---

### 8. `NullPercentageValidator` Converts Threshold Twice, Always Uses 0 as Effective Limit

**File:** `engine/sagescan_engine/validators/implementations.py`

```python
threshold = self.check_config.get("value", 0.0) / 100  # e.g., 5 → 0.05
...
passed = null_percentage <= threshold  # null_percentage is 0–100 scale, threshold is 0–1 scale
```

`null_percentage` is computed as a `0–100` value (`(null_count / len(series)) * 100`), but `threshold` is divided by 100 and stored as a `0–1` decimal. The comparison `null_percentage <= threshold` will almost always be `False` because `null_percentage` is on the wrong scale. For example, a 5% null rate with `value: 10` gives `null_percentage=5.0` vs `threshold=0.1`, resulting in a false failure.

**Fix:** Pick one scale and be consistent:
```python
threshold_pct = self.check_config.get("value", 0.0)  # keep as 0–100
null_percentage = (null_count / len(series)) * 100
passed = null_percentage <= threshold_pct
```

---

### 9. `UniqueValidator` Uses Inverted Condition — Reports Non-Duplicates as Failures

**File:** `engine/sagescan_engine/validators/implementations.py`

```python
is_duplicate = series.duplicated()
failed_rows = self.get_failed_rows(series, is_duplicate)
```

`BaseValidator.get_failed_rows` is:
```python
def get_failed_rows(self, series, condition) -> List[int]:
    return series[~condition].index.tolist()  # <-- inverts condition
```

`is_duplicate` is `True` for duplicates. `~is_duplicate` is `True` for unique values. So `get_failed_rows` returns the **unique** rows, not the duplicate rows. The validator passes only when there are no unique values (i.e., when all rows are duplicates), which is the exact opposite of the intended behavior.

**Fix:** Either pass the inverted mask or use a direct index:
```python
failed_rows = series[is_duplicate].index.tolist()
failed_values = series[is_duplicate].tolist()
```

---

### 10. `RegexValidator` Inverts Match Logic — Passes Non-Matching Values

**File:** `engine/sagescan_engine/validators/implementations.py`

```python
is_no_match = series.apply(lambda x: bool(regex.search(str(x))) ...) == False
failed_rows = self.get_failed_rows(series, is_no_match)
```

`is_no_match` is `True` where the regex does **not** match. `get_failed_rows` then returns `series[~is_no_match]` — i.e., rows **where the regex matches**. The validator therefore reports matching rows as failures and non-matching rows as passing.

**Fix:** Remove the `== False` inversion and stop using `get_failed_rows` with a pre-inverted mask:
```python
matches = series.apply(lambda x: bool(regex.search(str(x))) if pd.notna(x) else False)
failed_rows = series[~matches].index.tolist()
failed_values = series[~matches].tolist()
```

---

## Important Improvements

---

### 11. Global `viper` Instance in `config/config.go` — Thread-Unsafe and Blows State Between Commands

**File:** `internal/config/config.go`

```go
viper.SetConfigFile(path)
if err := viper.ReadInConfig(); err != nil { ... }
return viper.AllSettings(), nil
```

This uses the global Viper singleton. `internal/cli/base.go` correctly creates a local `viper.New()` instance, but `config.go` mutates global state. If two commands run in the same process or if tests run in parallel, they race on the global Viper config. The global config package is also a dead code path — it's never called by any command because `base.go`'s `LoadConfig` shadows it.

**Fix:** Remove `config/config.go` or rewrite it using `viper.New()` consistently. Centralise `LoadConfig` in one place only.

---

### 12. `validate.go` Timeout Is 30 Minutes — No Reason Given, Masks Hangs

**File:** `internal/cli/validate.go`

```go
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Minute)
```

A 30-minute timeout for a validation command will silently hang for 30 minutes before reporting a timeout. Different commands use different arbitrary timeouts (5 min, 10 min, 15 min, 30 min) with no documentation. There's no progress output to indicate the tool is running.

**Fix:** Default to a configurable, short timeout (e.g., 5 minutes) with a `--timeout` flag. Add a periodic heartbeat spinner or progress line to stdout so users know the engine is working.

---

### 13. `save_config_to_file()` in `main.py` Creates a Temp Dir But Only Cleans the File

**File:** `engine/main.py`

```python
temp_dir = tempfile.mkdtemp(prefix="sagescan_")
config_path = os.path.join(temp_dir, "config.json")
...
try:
    os.remove(config_path)  # Only removes the file, not the directory
except:
    pass
```

Every run leaks a `sagescan_XXXXXXXX` temp directory in `/tmp`. On long-running systems or CI runners, this accumulates indefinitely.

**Fix:** Use `shutil.rmtree(temp_dir)` or Python's `tempfile.TemporaryDirectory` context manager:
```python
with tempfile.TemporaryDirectory(prefix="sagescan_") as temp_dir:
    config_path = os.path.join(temp_dir, "config.json")
    ...
```

---

### 14. `RangeValidator` References Undeclared Variable `message` on PASS Path

**File:** `engine/sagescan_engine/validators/implementations.py`

```python
if message_parts:
    message = self._build_error_message(...)   # only assigned inside this if-block

return ValidationResultDetail(
    ...
    message=message if message else f"All values are within range"  # NameError if message_parts is empty
)
```

If `message_parts` is empty (which can't happen in the current logic given the prior `None` check, but is one refactor away from being reachable), `message` will be undefined and a `NameError` will crash the validator.

**Fix:** Initialize `message = ""` before the `if message_parts:` block.

---

### 15. `main.py` Unpacks Go Envelope Before Modifying `source.path`, Then Re-Runs Path Resolution on a Stale Reference

**File:** `engine/main.py`

```python
if isinstance(config, dict) and "command" in config and "config" in config:
    config = config["config"]   # config is now the inner dict

config_path = save_config_to_file(config)  # saves inner dict correctly

# But then:
if 'source' in config and 'path' in config['source']:
    source_path = config['source']['path']
    if not os.path.isabs(source_path):
        config['source']['path'] = os.path.abspath(source_path)
```

The path absolutization modifies `config` in-memory **after** `config_path` was already written. The `run_validation(config)` call receives the updated in-memory dict correctly, but `save_config_to_file` saved the old relative path. If the runner ever re-reads from `config_path` (or future code re-uses the temp file), it will get the stale relative path. Additionally, `os.path.abspath` resolves relative to the CWD of the Python process (which is the CWD of the Go subprocess), not the config file's location — so a relative path in the YAML like `data/sample.csv` resolves to wherever Go was invoked from, which may differ from where the config file lives.

**Fix:** Resolve paths relative to the config file's directory:
```python
# Before saving
config_dir = os.path.dirname(os.path.abspath(args.config)) if args.config else os.getcwd()
if 'source' in config and 'path' in config['source']:
    src = config['source']['path']
    if not os.path.isabs(src):
        config['source']['path'] = os.path.normpath(os.path.join(config_dir, src))
# Save AFTER resolution
config_path = save_config_to_file(config)
```

---

### 16. `schema.py` Validator for `unique` Incorrectly Requires a `value` Parameter

**File:** `engine/sagescan_engine/rules/schema.py`

```python
if check_type in [CheckType.MIN_VALUE, CheckType.MAX_VALUE, CheckType.UNIQUE] and v is None:
    raise ValueError(f"{check_type.value} check requires a 'value' parameter")
```

The `UniqueValidator` doesn't use a `value` parameter — it just checks that all values in a column are distinct. Adding `UNIQUE` to this list means any user who writes `- type: unique` without a value will get a Pydantic validation error before any data is touched. The schema and implementation are out of sync.

**Fix:** Remove `CheckType.UNIQUE` from that validator list.

---

### 17. `requirements.txt` Declares `polars` But All Code Uses `pandas` — Dead Dependency

**File:** `engine/requirements.txt`

```
polars>=0.20.0
```

No file in `engine/sagescan_engine/` imports `polars`. All data operations use `pandas`. `polars` is a large native-extension library (~50MB) that adds unnecessary installation time and potential platform compatibility issues (especially in constrained environments).

**Fix:** Remove `polars` from `requirements.txt`. If polars is part of a future roadmap, document it separately. Add `pandas>=2.0.0`, `numpy>=1.26.0`, and `scipy>=1.11.0` which are actually required but missing.

---

### 18. `Makefile` `build` Target Uses `.exe` Extension — Mac/Linux Produces Wrong Binary Name

**File:** `Makefile`

```makefile
build:
	go build -o sagescan.exe ./cmd/sagescan/main.go
```

The `.exe` extension is Windows-specific. On macOS/Linux this creates a file named `sagescan.exe` (which works but is unconventional and breaks shell completion conventions). The `run-example` target references `./sagescan.exe` which reinforces this.

**Fix:**
```makefile
BINARY := sagescan
ifeq ($(OS),Windows_NT)
    BINARY := sagescan.exe
endif

build:
	go build -o $(BINARY) ./cmd/sagescan/main.go
```

---

### 19. Cobra Command `Long` Description Is Mangled — Newlines Collapsed Into Spaces

**File:** `internal/cli/base.go`

```go
cmd := &cobra.Command{
    Long: strings.ReplaceAll(long, "\n", " "),
```

All multi-line help text passed to `NewBaseCommand` has every newline replaced with a space, turning structured help text into a single run-on line. This makes `--help` output illegible for all commands.

**Fix:** Remove the `strings.ReplaceAll` call. Cobra handles multi-line `Long` descriptions natively.

---

### 20. `engine.go` `buildCommand()` Ignores Its Own `enginePath` Variable

**File:** `internal/python/engine.go`

```go
func (e *Engine) buildCommand(configPath string) *exec.Cmd {
    enginePath := e.enginePath
    if enginePath == "" {
        enginePath = filepath.Join(filepath.Dir(filepath.Clean(e.pythonPath)), "engine", "main.py")
    }
    // enginePath is correctly computed above, but then:
    cmd := exec.Command(e.pythonPath, "engine/main.py", "--config", configPath) // hardcoded!
```

The computed `enginePath` variable is assigned but never used. The hardcoded `"engine/main.py"` string is used instead. This method is only called by `RunValidation()` (the older path), but the inconsistency shows the code was written without testing the resolution path.

---

## Minor Suggestions

---

### 21. `init.go` — `created_at` Is Hardcoded to `"2024-01-01"`
`createDefaultConfig()` sets `"created_at": "2024-01-01"`. It should use `time.Now().Format("2006-01-02")` to reflect the actual creation date.

---

### 22. `schema.py` Uses Deprecated Pydantic v1 `@validator` in a Pydantic v2 Model
`schema.py` uses `from pydantic import validator` which is deprecated in Pydantic v2 (the version declared in `requirements.txt`). Replace with `@field_validator` and `model_validator` from Pydantic v2 to avoid deprecation warnings and future breakage.

---

### 23. `pipeline.py` — `generate_report()` Calls `r.passed` on a Mixed-Type `self.results`
`execute_validators()` appends both `ValidationResultDetail` objects (from successful validators) and raw `dict` objects (from the `except` branch). `generate_report()` then calls `r.passed` which works on `ValidationResultDetail` but raises `AttributeError` on `dict`. The `except` branch should also produce a `ValidationResultDetail` object.

---

### 24. No Structured Logging Strategy — `fmt.Fprintf(os.Stderr, ...)` Is Not Structured
The Go layer uses `fmt.Fprintf(os.Stderr, ...)` for verbose output. As the tool grows, this makes log correlation in CI impossible. Consider `log/slog` (stdlib in Go 1.21+) with a JSON handler for machine-readable structured logs.

---

### 25. `generate-rules` Command Does Not Validate That `--input` File Exists Before Sending to Python
Unlike `validate` which calls `ValidateConfig()`, `generate-rules` sends the input file path to Python without checking if it exists first. The Python engine will fail with an obscure pandas `FileNotFoundError` rather than a clean CLI error.

---

### 26. API Key Passed in JSON Payload Over stdin — Appears in Process Arguments and System Logs
`llm_api_key` is placed in the `cfg` map and serialized to JSON written to stdin. On most systems, stdin content doesn't appear in process listings (`ps aux`), which is safe. However, it also ends up in temp files written to `/tmp/sagescan_*/config.json` with mode `0666` (default `os.Create`). Temp files with secrets should use `0600`:
```go
file, err := os.OpenFile(configPath, os.O_CREATE|os.O_WRONLY, 0600)
```

---

### 27. `BaseCommand.Execute()` in Every Command Subtype Is Dead Code
Every command type (`ValidateCommand`, `ReportCommand`, etc.) defines its own `Execute()` method that just delegates to `BaseCommand.Execute()`. This adds noise without value since no external code calls `command.Execute()` — only `rootCmd.Execute()` is called from `main.go`.

---

### 28. No Tests — Neither Unit nor Integration
`go test ./...` is in the Makefile but there are zero `*_test.go` files and zero Python `test_*.py` files in the project. The validators, pipeline, and IPC bridge have no test coverage whatsoever. This is the most significant barrier to production readiness.

---

## Overall Assessment

### Code Quality: 4 / 10

The architecture intent is sound — a clean Go CLI → stdin/stdout JSON → Python engine design is well-suited to this problem. However, the implementation has multiple correctness bugs (inverted logic in `UniqueValidator`, `RegexValidator`, `NullPercentageValidator`, broken `RunValidationString`) that would produce wrong validation results silently. The IPC layer (`CombinedOutput`, engine path resolution) is broken in non-development environments.

### Production Readiness: 2 / 10

- Zero tests of any kind
- IPC contract is broken by stderr capture
- Engine path resolution fails outside project root
- Critical validators produce inverted results
- Temp file leaks on every run
- Secrets written to world-readable temp files
- No structured logging or observability
- Windows-only `Makefile` build target
- `polars` in requirements but not used; `pandas`, `numpy`, `scipy` missing

### Biggest Risk in Current Design

**The `CombinedOutput()` + `parseOutput()` combination.** The entire value of this tool depends on the Go ↔ Python IPC working correctly. Right now, any `stderr` output from Python (logging, warnings, deprecation notices from pandas/scipy, the explicit `print(..., file=sys.stderr)` in `main.py`) will cause `parseOutput()` to return `"Invalid output format: not JSON"` — giving the user a completely opaque error with no debugging information. This means the tool fails silently in any realistic environment and provides no path to diagnosis. Fixing this single issue (`stdout`/`stderr` separation) would dramatically increase reliability before any other change.

