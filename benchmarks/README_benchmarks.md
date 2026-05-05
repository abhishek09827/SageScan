# SageScan Benchmarks

This folder contains the benchmark harness used to measure SageScan on real datasets generated at runtime.

## Files

- `benchmark_sagescan.py` runs every benchmark and writes the outputs into `results/`.
- `benchmark_rules.yaml` stores the validation rules shared across the benchmark suite.
- `requirements_bench.txt` lists the Python packages expected by the benchmark runner.

## Important implementation notes

- SageScan does not accept `validate <rules.yaml> --file <csv>`.
- The actual CLI expects a full config file with `source.path` and `rules` together.
- The benchmark runner therefore wraps `benchmark_rules.yaml` inside a generated config before calling SageScan.
- The "clean" generator clips `amount` to the rule bounds so SS-1 really measures a passing baseline instead of random normal-tail failures.
- The drift benchmarks use `ks_test` and `psi`, which are the actual distribution validators implemented in SageScan.

## How to run

1. Install the benchmark dependencies.

   ```powershell
   python -m pip install -r benchmarks/requirements_bench.txt
   ```

2. Run the benchmark suite.

   ```powershell
   python benchmarks/benchmark_sagescan.py
   ```

3. Review the generated artifacts.

   - `results/benchmark_report.md`
   - `results/benchmark_raw.json`

## What each benchmark does

### SS-1: Throughput at Scale

Validates clean data at increasing row counts and measures wall-clock time, rows per second, and peak RSS memory while capturing the real SageScan stdout for each run.

### SS-2: Validator Recall on Dirty Data

Injects known violations into a synthetic dataset and compares injected violations against SageScan's detected failures.

### SS-3: Drift Detection Accuracy

Compares a baseline sample against drifted samples using SageScan's `ks_test` and `psi` validators, then records whether each scenario is flagged.

### SS-4: SageScan vs Great Expectations

Compares SageScan against Great Expectations on equivalent checks over the same 500k-row dataset and reports relative speed.

### SS-5: Memory Safety on Large Files

Creates a large CSV in chunks, validates it, and records the peak memory seen during validation.

## Output format

The generated report is written in markdown so it can be pasted directly into a README, wiki, or resume draft.
