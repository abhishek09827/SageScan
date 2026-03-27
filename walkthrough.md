# SageScan IPC Fixes Walkthrough

I successfully resolved the critical Inter-Process Communication (IPC) and integration issues causing the `sagescan validate` command to crash. The changes ensure flawless data passing between the Go CLI wrapper and the inner Python data engine.

## Overview of Fixes

### 1. Python Engine CLI Entrypoint
The Python [main.py](file:///e:/Personal%20Projects/SageScan/engine/main.py) was completely ignoring `stdin`, but the Go orchestrator sends configuration JSON over pipes. Furthermore, when taking raw string inputs, Python used an unsafe and incompatible mechanism (`ast.literal_eval`) leading to JSON parsing failures.

- **Changes made**:
  - Implemented `sys.stdin.read()` fallback in [engine/main.py](file:///e:/Personal%20Projects/SageScan/engine/main.py) to allow silent config pipelining from Go.
  - Implemented an envelope unwrapper for Go's `{"command": "validate", "config": {...}}` payload format so Python validators don't mistakenly look for inner config keys at the root level.
  - Replaced the failing `ast.literal_eval` with standard `json.loads` parsing.

### 2. Dict vs List Return Mismatch
The `runner.run_validation` was incorrectly extracting and returning just the inner `results` list, which broke [main.py](file:///e:/Personal%20Projects/SageScan/engine/main.py) when it attempted to execute dictionary methods (`report.get('status')`).

- **Changes made**:
  - Rewrote the [run_validation()](file:///e:/Personal%20Projects/SageScan/engine/sagescan_engine/core/runner.py#15-76) return logic to supply the entire formatted [report](file:///e:/Personal%20Projects/SageScan/engine/sagescan_engine/core/pipeline.py#174-217) dictionary, allowing [main.py](file:///e:/Personal%20Projects/SageScan/engine/main.py) to properly evaluate the exit `status`.

### 3. Go Orchestrator Status Checks
The orchestrator in Go was hardcoded to check for `response.Status != "success"`. The Python library actually returns `"PASS"` or `"FAIL"`. This misalignment caused Go to suppress valid test failures and falsely claim the Python engine crashed.

- **Changes made**:
  - Replaced the string evaluation in [internal/orchestrator/orchestrator.go](file:///e:/Personal%20Projects/SageScan/internal/orchestrator/orchestrator.go) to explicitly check for engine crashes via `response.Status == "ERROR"`, successfully distinguishing an engine crash from a rule validation failure.

### 4. CLI Argument Passing 
CLI arguments like `--context` were being parsed by Cobra but successfully ignored before passing to Python.

- **Changes made**:
  - Modified [internal/cli/validate.go](file:///e:/Personal%20Projects/SageScan/internal/cli/validate.go) to explicitly populate Python's JSON config map (`v.AllSettings()`) with the evaluated `context` and `baseline` flags.

## Validation Results

The Go execution pipeline `go run cmd/sagescan/main.go validate` now cleanly runs Python and maps the CLI context securely entirely end-to-end.
