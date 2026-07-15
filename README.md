# SageScan

SageScan is a CLI for validating tabular data with YAML rules and a Python validation engine.
It is designed for local files, CI pipelines, and repeatable data quality checks on CSV and Parquet inputs.
[![Hashnode]]( https://ab-blog.hashnode.dev/i-built-a-cli-data-quality-tool-that-goes-beyond-schema-checks-here-s-what-i-learned) 
![SageScan Terminal Demo](demo.gif)
## What it does

- Validates schema and data quality rules from a single config file
- Runs statistical checks such as z-score, KS test, and PSI
- Supports chunked CSV reads for larger files
- Produces text and JSON output for automation
- Includes an optional AI-assisted rule generator

## Project Layout

- `cmd/sagescan/` - CLI entrypoint
- `internal/` - Go command wiring, config loading, and Python bridge
- `engine/` - Python validation engine
- `examples/` - Sample data and sample configs
- `benchmarks/` - Benchmark harness and documentation
- `results/` - Generated benchmark outputs

## Installation

### From source

```bash
git clone https://github.com/abhishek09827/SageScan.git
cd SageScan
make setup-python
make build
```

### From Python package

```bash
pip install sagescan-data[all]
```

## Quick Start

Create a config file with the dataset path and rules:

```yaml
version: "1.0"

source:
  type: csv
  path: examples/sample_data.csv

rules:
  - column: user_id
    checks:
      - type: not_null
      - type: unique

  - column: email
    checks:
      - type: regex
        value: "^[^@]+@[^@]+\\.[^@]+$"

  - column: age
    checks:
      - type: range
        min: 18
        max: 120
```

Run validation:

```bash
sagescan validate examples/basic_rules.yaml
```

Get JSON output:

```bash
sagescan validate examples/basic_rules.yaml --output json
```

## CLI Commands

- `sagescan validate <config.yaml>` - run data quality checks
- `sagescan profile <config.yaml>` - profile the dataset
- `sagescan report <config.yaml>` - run validation and format the result
- `sagescan init --output rules.yaml` - create a starter config
- `sagescan generate-rules -i data.csv -o rules.yaml` - generate rules from a dataset

## Configuration Format

SageScan expects a full config file, not a bare rules file.

```yaml
version: "1.0"

source:
  type: csv
  path: data/users.csv

rules:
  - column: status
    checks:
      - type: not_null
      - type: allowed_values
        values: [active, inactive]
```

## Validator Types

The engine currently supports these checks:

- `not_null`
- `unique`
- `min_value`
- `max_value`
- `range`
- `regex`
- `pattern`
- `null_percentage`
- `min_length`
- `max_length`
- `allowed_values`
- `mean_check`
- `std_check`
- `z_score`
- `z_score_outlier`
- `ks_test`
- `psi`

## Environment Variables

- `SAGESCAN_ENGINE_PATH` - override the Python engine path
- `SAGESCAN_VERBOSE` - enable verbose logging
- `SAGESCAN_LOG_LEVEL` - set the engine log level
- `OPENAI_API_KEY` - optional key for AI features

## Benchmarks

Benchmark docs and outputs live in [`benchmarks/`](benchmarks/):

- [`benchmarks/README_benchmarks.md`](benchmarks/README_benchmarks.md)
- [`results/benchmark_report.md`](results/benchmark_report.md)
- [`results/benchmark_raw.json`](results/benchmark_raw.json)

## Testing

```bash
make test
make test-go
make test-python
```

## Contributing

- Keep changes aligned with the actual CLI contract and engine behavior
- Add tests for new validators or command behavior
- Make sure generated outputs are reproducible when possible

