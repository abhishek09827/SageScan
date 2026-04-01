# SageScan

> **Production-grade, CLI-first data quality validation for modern data pipelines.**

[![Go Version](https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go)](https://go.dev)
[![Python Version](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SageScan combines a **Go CLI** for fast, scriptable orchestration with a **Python engine** for rich statistical validation — connected via a clean JSON bridge over stdin/stdout.

---

## Table of Contents

1. [Why SageScan?](#why-sagescan)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Quick Start](#quick-start)
5. [CLI Reference](#cli-reference)
6. [Configuration Reference](#configuration-reference)
7. [Validator Types](#validator-types)
8. [Example Dataset & Output](#example-dataset--output)
9. [Big-Data Readiness](#big-data-readiness)
10. [AI Layer (Optional)](#ai-layer-optional)
11. [Testing](#testing)
12. [Roadmap](#roadmap)
13. [Contributing](#contributing)

---

## Why SageScan?

Data pipelines fail **silently** more often than they break loudly.  
SageScan helps you catch those failures before they reach production.

| Feature | SageScan |
|---------|----------|
| CLI-first design | ✅ — pipe-friendly, CI-ready |
| Declarative rules | ✅ — YAML-based, version-controlled |
| Statistical checks | ✅ — z-score, mean, std, PSI, KS |
| Drift detection | ✅ — KS test + Population Stability Index |
| AI rule generation | ✅ — optional, GPT-4 compatible |
| Big-data support | ✅ — CSV chunked reads, Parquet |
| Zero external DB | ✅ — runs on local files |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Go CLI (Cobra)                    │
│   validate │ profile │ report │ generate-rules │ init│
└─────────────────────┬───────────────────────────────┘
                      │  JSON via stdin/stdout
┌─────────────────────▼───────────────────────────────┐
│              Python Engine (main.py)                 │
│   Command router → runner → pipeline → validators   │
└──────────────────────────────────────────────────────┘
         │                              │
   Pydantic v2                   Validator Registry
   (strict schema)          (not_null │ regex │ z_score
                             min_length │ allowed_values …)
```

**Key Design Decisions:**

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| CLI | Go + Cobra + Viper | Fast startup, single binary, no runtime needed |
| Validation Engine | Python + pandas | Rich ecosystem for data science |
| Schema Validation | Pydantic v2 | Strict, fast, Pythonic |
| Communication | JSON stdin/stdout | Simple, debuggable, language-agnostic |
| Config | YAML | Human-readable, version-control friendly |

---

## Installation

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Go | 1.22 |
| Python | 3.9 |
| make | any |

---

### Step 1 — Clone the repo

```bash
git clone https://github.com/sagescan/sagescan.git
cd sagescan
```

### Step 2 — Set up the Python engine

```bash
make setup-python
```

This creates `engine/.venv` and installs all dependencies (pandas, pydantic, scipy, pyarrow …).

### Step 3 — Build the CLI binary

```bash
make build
```

This produces a `./sagescan` binary in the project root.

### Step 4 — (Optional) Install globally

```bash
make install
```

Installs the binary to `~/.local/bin/sagescan`.  
Add `~/.local/bin` to your PATH if not already there:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### Step 5 — Point SageScan at the Python engine

When running outside the project directory, set this environment variable:

```bash
export SAGESCAN_ENGINE_PATH=/path/to/sagescan/engine/main.py
```

Or always run from the project root.

---

## Quick Start

```bash
# 1. Create a sample data file
cat > data/sample.csv << 'EOF'
user_id,age,email,status
1,25,alice@example.com,active
2,17,bob@example.com,inactive
3,30,charlie@example.com,active
EOF

# 2. Initialise a config
./sagescan init --output rules.yaml

# 3. Edit rules.yaml to match your columns, then run:
./sagescan validate rules.yaml

# 4. Get JSON output (great for CI / downstream processing)
./sagescan validate rules.yaml --output json

# 5. Fail CI pipeline on any violation
./sagescan validate rules.yaml --fail-fast
```

---

## CLI Reference

```
Usage:
  sagescan [command]

Available Commands:
  validate        Run data quality validation on a config file
  profile         Generate a statistical profile of a dataset
  report          Generate a formatted validation report
  generate-rules  Auto-generate validation rules using AI (requires API key)
  init            Create a new SageScan config file with defaults

Flags:
  --timeout duration   Max wait time for engine (default: 5m)
  --context string     Validation context tag (e.g. production, staging)
  --baseline string    Path to baseline config for comparison
  -h, --help           Help for any command
  -v, --version        Show version
```

### `validate`

```bash
sagescan validate <config.yaml> [flags]

Flags:
  -o, --output string    Output format: text (default) or json
      --fail-fast        Exit 1 on any validation failure (for CI)
      --timeout 10m      Override engine timeout
      --context string   Tag the run (e.g. production)
```

### `profile`

```bash
sagescan profile <config.yaml> [flags]
```

Profiles the dataset: row count, column types, null %, min/max/mean/std for numeric columns.

### `report`

```bash
sagescan report <config.yaml> [flags]
```

Runs validation and outputs a rich formatted report.

### `generate-rules`

```bash
sagescan generate-rules -i data.csv -o rules.yaml [flags]

Flags:
  -i, --input string             Input CSV file (required)
  -o, --output string            Output YAML rules file (required)
      --llm-model string         LLM model (default: gpt-4o)
      --llm-api-key string       OpenAI API key (or set OPENAI_API_KEY env var)
      --llm-base-url string      Custom API base URL for self-hosted or local LLMs
      --llm-temperature float32  Temperature setting for LLM generation (default: 0.3)
```

### `init`

```bash
sagescan init --output my_rules.yaml
```

Generates a ready-to-use config file with sensible defaults.

---

## Configuration Reference

```yaml
version: "1.0"

source:
  type: csv              # csv | parquet
  path: data/users.csv   # relative to the config file, or absolute

rules:
  - column: user_id
    checks:
      - type: not_null
      - type: unique

  - column: age
    checks:
      - type: range
        min: 18
        max: 120
      - type: z_score
        value: 3.0         # flag |z| > 3 as outlier

  - column: email
    checks:
      - type: not_null
      - type: regex
        value: "^[^@]+@[^@]+\\.[^@]+$"
      - type: max_length
        value: 254

  - column: status
    checks:
      - type: allowed_values
        values: [active, inactive, pending, banned]

# Optional — needed only for generate-rules and explain features
# llm_api_key: sk-...   (prefer OPENAI_API_KEY env var)
# llm_model: gpt-4o
# llm_max_tokens: 2000
# llm_base_url: http://localhost:11434/v1
# llm_temperature: 0.3
```

---

## Validator Types

| Check type | Config keys | Description |
|-----------|-------------|-------------|
| `not_null` | — | No null values allowed |
| `unique` | — | All values must be distinct |
| `min_value` | `value` | All values ≥ value |
| `max_value` | `value` | All values ≤ value |
| `range` | `min`, `max` | All values in [min, max] |
| `regex` | `value` | Values match regex pattern |
| `pattern` | `value` | Alias for `regex` |
| `null_percentage` | `value` | % of nulls ≤ value (0–100) |
| `min_length` | `value` | String length ≥ value |
| `max_length` | `value` | String length ≤ value |
| `allowed_values` | `values: [...]` | Value must be in the list |
| `mean_check` | `min`, `max` | Column mean in [min, max] |
| `std_check` | `min`, `max` | Column std in [min, max] |
| `z_score` | `value` | Flag rows where \|z\| > value |
| `z_score_outlier` | `threshold`, `upper_threshold`, `lower_threshold` | Separate upper/lower bounds |
| `ks_test` | `reference_path`, `alpha` | Kolmogorov–Smirnov distribution test |
| `psi` | `reference_path`, `threshold`, `bins` | Population Stability Index |

---

## Example Dataset & Output

**`examples/sample_data.csv`**

```
user_id,age,email,status
1,25,alice@example.com,active
2,17,bob@example.com,inactive
3,30,charlie@example.com,active
3,40,duplicate@example.com,pending
5,,missing_age@example.com,active
```

**Run:**

```bash
./sagescan validate examples/basic_rules.yaml
```

**Output:**

```
📊 Validating data quality rules from: examples/basic_rules.yaml
────────────────────────────────────────────────────────────

Status: FAIL
Pass Rate: 60.0%

Checks: 5 total | 3 passed | 2 failed

  ✅ user_id              not_null             All values are not null
  ❌ user_id              unique               Found 1 duplicate values
  ❌ age                  not_null              Null values found in 1 rows
  ✅ age                  range                All values are within range
  ✅ email                regex                All values match the specified pattern
```

**JSON output mode:**

```bash
./sagescan validate examples/basic_rules.yaml --output json
```

```json
{
  "status": "FAIL",
  "summary": {
    "total": 5,
    "passed": 3,
    "failed": 2,
    "pass_rate": 60.0
  },
  "results": [
    {
      "column": "user_id",
      "check_type": "not_null",
      "passed": true,
      "message": "All values are not null"
    },
    ...
  ]
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SAGESCAN_ENGINE_PATH` | `<binary_dir>/engine/main.py` | Override Python engine path |
| `SAGESCAN_VERBOSE` | `false` | Set `true` for debug timing info |
| `SAGESCAN_LOG_LEVEL` | `WARNING` | Python log level (DEBUG/INFO/WARNING/ERROR) |
| `OPENAI_API_KEY` | — | API key for AI features |

---

## Big-Data Readiness

| Scenario | Current Behaviour |
|----------|------------------|
| CSV < 50 MB | Full in-memory load |
| CSV 50 MB – 2 GB | Chunked `pd.read_csv(chunksize=100_000)` |
| CSV > 2 GB | Rejected with clear error message |
| Parquet | `pd.read_parquet` via pyarrow (up to 4 GB) |
| Failed rows | Capped at 1,000 per check to prevent OOM |

**Planned improvements:**

- Polars backend (10–50× faster than pandas for large files)
- Streaming validation (per-chunk without materialising full DataFrame)
- DuckDB connector for in-process SQL-based validation
- S3 / GCS URI support for cloud-native use

---

## AI Layer (Optional)

### Generate rules from a dataset

```bash
export OPENAI_API_KEY=sk-...
./sagescan generate-rules -i data/users.csv -o rules/users.yaml --context "user registration data"
```

To use a custom local model like Ollama instead of OpenAI, provide your custom base URL and temperature:
```bash
./sagescan generate-rules -i data/users.csv -o rules/users.yaml --llm-model="llama3" --llm-base-url="http://localhost:11434/v1" --llm-temperature=0.8 --llm-api-key="dummy"
```

SageScan sends column statistics (not raw data) to the LLM to generate rules — no PII leaves your machine.

### Explain validation failures

Add `llm_api_key` to your config. On the next `validate` run, failed checks automatically get plain-English explanations appended to the JSON output.

**AI is always optional.** Core validation is fully deterministic and works without any API key.

---

## Testing

```bash
# Run all tests
make test

# Go tests only
make test-go

# Python tests only
make test-python

# With coverage
cd engine && python -m pytest --cov=sagescan_engine --cov-report=term-missing
```

**Test coverage:**
- `engine/sagescan_engine/validators/test_implementations.py` — all 17 validator types
- `engine/sagescan_engine/rules/test_models.py` — Pydantic schema validation
- `internal/cli/base_test.go` — CLI config loading
- `internal/python/engine_test.go` — subprocess communication

---

## Project Structure

```
sagescan/
├── cmd/sagescan/
│   └── main.go                  # CLI entrypoint
├── internal/
│   ├── cli/                     # Cobra command definitions
│   │   ├── cli.go               # Root command + init
│   │   ├── validate.go          # sagescan validate
│   │   ├── profile.go           # sagescan profile
│   │   ├── report.go            # sagescan report
│   │   ├── generate_rules.go    # sagescan generate-rules
│   │   ├── init.go              # sagescan init
│   │   ├── base.go              # Shared flags/helpers
│   │   └── logger.go            # Structured logging setup
│   ├── python/
│   │   └── engine.go            # Go ↔ Python subprocess bridge
│   └── config/
│       └── config.go            # Config loading utilities
├── engine/
│   ├── main.py                  # Python engine entrypoint
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── sagescan_engine/
│       ├── core/
│       │   ├── pipeline.py      # Data loading + validator orchestration
│       │   ├── runner.py        # Command dispatch (validate/profile/…)
│       │   └── report.py        # Report formatting (CLI / JSON / HTML)
│       ├── rules/
│       │   ├── models.py        # Pydantic config models
│       │   └── schema.py        # JSON schema
│       ├── validators/
│       │   ├── base.py          # BaseValidator + ValidationResult
│       │   ├── implementations.py  # All 17 validator types
│       │   ├── distribution.py  # KS test, PSI, z-score outlier
│       │   └── registry.py      # Validator factory
│       └── llm/
│           ├── rule_generator.py     # AI rule generation
│           └── explanation_generator.py  # AI failure explanation
├── examples/
│   ├── sample_data.csv
│   ├── basic_rules.yaml
│   └── comprehensive_rules.yaml
├── Makefile
├── go.mod
└── README.md
```

---

## Roadmap

### v1.1 (Next)

- [ ] Polars backend (opt-in via `--engine polars`)
- [ ] DuckDB connector for SQL-based validation
- [ ] HTML report generation
- [ ] `--watch` mode for streaming pipelines
- [ ] GitHub Actions example workflow

### v1.2

- [ ] PostgreSQL connector
- [ ] Snowflake connector
- [ ] S3/GCS URI support
- [ ] Webhook notifications (Slack, PagerDuty)
- [ ] Rule inheritance / rule templates

### v2.0

- [ ] Web UI dashboard
- [ ] Drift alerting + historical trending
- [ ] dbt integration
- [ ] Great Expectations compatibility layer

---

## Contributing

Contributions are welcome!

```bash
# Fork the repo, then:
git checkout -b feat/my-improvement

# Make your changes, then test:
make test

# Open a pull request
```

**Guidelines:**

- All new validators must have tests in `test_implementations.py`
- Go changes must pass `go vet ./...`
- Python changes must pass `python -m py_compile`
- Keep `engine/main.py` stdout clean — only JSON, nothing else
- Document new check types in this README

---

## License

MIT © SageScan Contributors
