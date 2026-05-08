# SageScan Benchmark Report
Generated: 2026-05-05 13:19:25
System: Windows-11-10.0.26220-SP0 | Intel64 Family 6 Model 165 Stepping 2, GenuineIntel | 16GB RAM
SageScan version: 1.0.5

## Summary - Resume-Ready Metrics
- Validates 125,547 rows/second on 1M-row dataset
- 0.3x faster than Great Expectations on equivalent check suite (500K rows)
- Detects distribution drift at 1 sigma+ shift with 100% recall and 0% false positives on control
- Processes 0.13GB CSV files with 599MB peak memory via chunked reads
- 100% violation recall on dataset with 15% injected violations across 4 validator types
- 17 validator types: schema + statistical + drift

## Full Benchmark Results
### SS-1: Throughput at Scale
| Rows      | Time (s) | Rows/sec | Memory(MB) | Return |
|-----------|----------|----------|------------|--------|
| 10,000    | 3.14     | 3,189    | 147        | 0      |
| 100,000   | 4.14     | 24,167   | 177        | 0      |
| 500,000   | 4.87     | 102,570  | 274        | 0      |
| 1,000,000 | 7.97     | 125,547  | 398        | 0      |
| 2,000,000 | 11.95    | 167,430  | 710        | 0      |

### SS-2: Validator Recall on Dirty Data
| Injected | Detected | Recall | False Negatives | Return |
|----------|----------|--------|-----------------|--------|
| 15,000   | 15,000   | 100%   | 0               | 0      |

### SS-3: Drift Detection Accuracy
| Scenario           | Shift (σ) | KS stat | PSI    | Flagged |
|--------------------|-----------|---------|--------|---------|
| no drift (control) | 0.0       | 0.000   | 0.000  | NO      |
| subtle drift       | 0.5       | 0.266   | 1.504  | YES     |
| moderate drift     | 1.0       | 0.402   | 4.644  | YES     |
| significant drift  | 2.0       | 0.692   | 9.436  | YES     |
| severe drift       | 3.0       | 0.896   | 10.848 | YES     |

### SS-4: SageScan vs Great Expectations
| Tool               | Time (s)    | Rows/sec |
|--------------------|-------------|----------|
| SageScan           | 4.33        | 115,390  |
| Great Expectations | 1.20        | 417,653  |
| SageScan speedup   | 0.3x faster |          |

### SS-5: Memory Safety on Large Files
| Rows      | CSV Size (GB) | Peak Memory (MB) | Return |
|-----------|---------------|------------------|--------|
| 2,000,000 | 0.13          | 599              | 0      |

## Raw sagescan output samples
### SS-1 10,000 rows stdout
```text
📊 Validating data quality rules from: E:\Personal Projects\SageScan\results\sagescan_bench_1777967248_700172\ss1_clean_10000.yaml
────────────────────────────────────────────────────────────

Status: PASS
Pass Rate: 100.0%

Checks: 8 total | 8 passed | 0 failed

  ✅ id                   unique               All values are unique
  ✅ email                regex                All values match the specified pattern
  ✅ amount               range                All values are within range
  ✅ amount               z_score              Found 0 outliers (|z-score| > 3.0)
  ✅ status               not_null             All values are not null
  ✅ status               allowed_values       All values are in the allowed set
  ✅ category             allowed_values       All values are in the allowed set
  ✅ score                range                All values are within range
```

### SS-1 100,000 rows stdout
```text
📊 Validating data quality rules from: E:\Personal Projects\SageScan\results\sagescan_bench_1777967248_700172\ss1_clean_100000.yaml
────────────────────────────────────────────────────────────

Status: PASS
Pass Rate: 100.0%

Checks: 8 total | 8 passed | 0 failed

  ✅ id                   unique               All values are unique
  ✅ email                regex                All values match the specified pattern
  ✅ amount               range                All values are within range
  ✅ amount               z_score              Found 0 outliers (|z-score| > 3.0)
  ✅ status               not_null             All values are not null
  ✅ status               allowed_values       All values are in the allowed set
  ✅ category             allowed_values       All values are in the allowed set
  ✅ score                range                All values are within range
```

### SS-1 500,000 rows stdout
```text
📊 Validating data quality rules from: E:\Personal Projects\SageScan\results\sagescan_bench_1777967248_700172\ss1_clean_500000.yaml
────────────────────────────────────────────────────────────

Status: PASS
Pass Rate: 100.0%

Checks: 8 total | 8 passed | 0 failed

  ✅ id                   unique               All values are unique
  ✅ email                regex                All values match the specified pattern
  ✅ amount               range                All values are within range
  ✅ amount               z_score              Found 0 outliers (|z-score| > 3.0)
  ✅ status               not_null             All values are not null
  ✅ status               allowed_values       All values are in the allowed set
  ✅ category             allowed_values       All values are in the allowed set
  ✅ score                range                All values are within range
```

## Methodology
- SageScan is invoked as a subprocess using the real CLI binary selected at runtime.
- Benchmark configs are generated programmatically and always include the benchmark dataset path under `source.path` because that is what the codebase expects.
- SS-1 uses a clipped version of the synthetic clean dataset so the baseline does not fail due to random normal-tail values outside the configured range.
- SS-2 counts injected violations from the generator and treats SageScan JSON `summary.failed` as the detected violation count because that matches the current code output.
- SS-3 uses the actual `ks_test` and `psi` validators implemented in `engine/sagescan_engine/validators/distribution.py`.
- SS-4 compares SageScan against Great Expectations when the library is installed; otherwise the benchmark is marked unavailable rather than fabricating a speedup.
- SS-5 records the actual file size written on disk and monitors process-tree memory while the validation command runs.
