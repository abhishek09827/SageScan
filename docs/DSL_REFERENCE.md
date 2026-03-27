# SageScan YAML DSL Reference

Complete reference for the SageScan YAML-based Domain Specific Language (DSL) for data quality validation.

## Table of Contents

1. [Overview](#overview)
2. [Schema Reference](#schema-reference)
3. [Check Types](#check-types)
4. [Examples](#examples)
5. [Best Practices](#best-practices)
6. [Advanced Features](#advanced-features)
7. [Extensibility](#extensibility)

## Overview

SageScan's DSL provides a human-readable, intuitive way to define data quality rules using YAML. The DSL is designed for data engineers and follows a declarative style where you specify what you want to validate rather than how to do it.

### Key Features

- **Declarative**: Specify what you want to validate
- **Intuitive**: Easy to read and understand for data engineers
- **Type-safe**: Comprehensive validation with clear error messages
- **Extensible**: Easy to add new check types
- **Structured**: Organized by columns with clear separation of concerns
- **Advanced**: Supports statistical checks and drift detection

### File Structure

```yaml
version: "1.0"                    # Configuration version
context: "Context description"    # Optional: Validation context
baseline: "path/to/reference.csv" # Optional: Reference data for drift detection

source:
  type: csv                      # Data source type
  path: "data.csv"               # Path to data file
  sample_size: 10000             # Optional: Sample size limit

rules:
  - column: "user_id"            # Column to validate
    description: "Description"    # Optional: Column purpose
    tags: ["tag1", "tag2"]        # Optional: Organizing tags
    checks:                       # Validation checks
      - type: "not_null"
        # ... check parameters
```

## Schema Reference

### Root Level

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Version identifier (e.g., "1.0") |
| `context` | string | No | Context or description of validation |
| `baseline` | string | No | Path to reference/baseline data |
| `source` | object | Yes | Data source configuration |
| `rules` | array | Yes | Validation rules |

### Data Source

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Data source type (csv, database) |
| `path` | string | Conditional | Path to CSV file |
| `connection_string` | string | Conditional | Database connection string |
| `query` | string | Conditional | SQL query for databases |
| `sample_size` | integer | No | Max rows to sample (default: 10000) |

### Rules

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `column` | string | Yes | Column name to validate |
| `checks` | array | Yes | List of validation checks |
| `description` | string | No | Description of column's purpose |
| `tags` | array | No | Organizing tags |

### Checks

Each check has a `type` field that defines the validation logic. Required parameters vary by type.

## Check Types

### 1. Basic Validation Checks

#### `not_null`

Validates that a column contains no null or NaN values.

```yaml
checks:
  - type: not_null
```

**Result:** Fails if any null values are found

**Parameters:** None

**Use Case:** Ensure required fields are always populated

---

#### `min_value`

Validates that all values are greater than or equal to a minimum.

```yaml
checks:
  - type: min_value
    value: 0
```

**Result:** Fails if any value is below the minimum

**Parameters:**
- `value`: Minimum allowed value (required)

**Use Case:** Price validation, age limits, counts

---

#### `max_value`

Validates that all values are less than or equal to a maximum.

```yaml
checks:
  - type: max_value
    value: 100
```

**Result:** Fails if any value exceeds the maximum

**Parameters:**
- `value`: Maximum allowed value (required)

**Use Case:** Score limits, quotas, dates

---

#### `range`

Validates that values fall within a specified range.

```yaml
checks:
  - type: range
    value: [0, 100]  # or [0, 100] as list
```

**Result:** Fails if any value is outside the range

**Parameters:**
- `value`: Minimum and maximum values (required, tuple or list)

**Use Case:** Validating numeric ranges, percentages

---

#### `regex`

Validates that values match a regular expression pattern.

```yaml
checks:
  - type: regex
    value: "^[^@]+@[^@]+\\.[^@]+$"
```

**Result:** Fails if pattern doesn't match

**Parameters:**
- `value`: Regular expression pattern (required)

**Use Case:** Email validation, phone number format, IDs

**Note:** Escape special characters with `\\`

---

#### `unique`

Validates that all values in a column are unique.

```yaml
checks:
  - type: unique
    value: true  # or false
```

**Result:** Fails if duplicate values exist

**Parameters:**
- `value`: `true` or `false` (required, boolean)

**Use Case:** Primary keys, user IDs

---

#### `null_percentage`

Enforces an acceptable ratio of null values.

```yaml
checks:
  - type: null_percentage
    value: 0.0  # 0% nulls (required)
    max_percentage: 0.01  # Allow up to 1% (optional)
```

**Result:** Fails if null percentage exceeds max_percentage

**Parameters:**
- `value`: Target null percentage (0.0-1.0, required)
- `max_percentage`: Maximum allowed percentage (0.0-1.0, optional)

**Use Case:** Allow occasional missing values while preventing data loss

---

### 2. Statistical Checks

#### `z_score`

Detects statistical anomalies using z-scores.

```yaml
checks:
  - type: z_score
    threshold: 3.0
    upper_threshold: 3.0
    lower_threshold: 3.0
```

**Result:** Fails if any value exceeds the z-score threshold

**Parameters:**
- `threshold`: Z-score threshold (default: 3.0)
- `upper_threshold`: Upper threshold (default: 3.0)
- `lower_threshold`: Lower threshold (default: 3.0)

**Use Case:** Outlier detection, anomaly scoring

---

#### `z_score_outlier`

Detects outliers using z-score analysis.

```yaml
checks:
  - type: z_score_outlier
    threshold: 3.0
```

**Result:** Fails if any outlier is detected

**Parameters:**
- `threshold`: Z-score threshold (default: 3.0)

**Use Case:** Fraud detection, extreme value detection

---

### 3. Categorical Validation

#### `in_set`

Validates that values are from a predefined set.

```yaml
checks:
  - type: in_set
    value: ["pending", "processing", "shipped", "delivered", "cancelled"]
```

**Result:** Fails if value is not in the set

**Parameters:**
- `value`: Array of allowed values (required)

**Use Case:** Status codes, categories, enum-like fields

---

### 4. Distribution Analysis (Drift Detection)

#### `psi` (Population Stability Index)

Detects distribution shifts between current and reference data.

```yaml
checks:
  - type: psi
    reference_type: file
    reference_path: "reference_data/distribution.csv"
    warning_threshold: 0.1
    drift_threshold: 0.2
```

**Result:** Fails if PSI exceeds drift_threshold, warns if exceeds warning_threshold

**Parameters:**
- `reference_type`: "file" or "csv" (default: "file")
- `reference_path`: Path to reference data (required)
- `warning_threshold`: PSI warning level (0-1, default: 0.1)
- `drift_threshold`: PSI fail level (0-1, default: 0.2)

**Use Case:** Model drift detection, population stability monitoring

**Note:** PSI values close to 0 indicate no drift; values > 0.2 indicate significant drift

---

#### `ks_test` (Kolmogorov-Smirnov Test)

Statistical test to compare distributions.

```yaml
checks:
  - type: ks_test
    reference_type: file
    reference_path: "reference_data/distribution.csv"
    alpha: 0.05
```

**Result:** Fails if p-value < alpha (default: 0.05)

**Parameters:**
- `reference_type`: "file" or "csv" (default: "file")
- `reference_path`: Path to reference data (required)
- `alpha`: Significance level (0.01-0.1, default: 0.05)

**Use Case:** Distribution comparison, feature drift detection

---

## Examples

### Simple Example: Email Validation

```yaml
version: "1.0"
source:
  type: csv
  path: "users.csv"

rules:
  - column: email
    description: "User email address"
    checks:
      - type: not_null
      - type: regex
        value: "^[^@]+@[^@]+\\.[^@]+$"
```

### Complex Example: Transaction Validation

```yaml
version: "1.0"
context: "E-commerce Transactions"
source:
  type: csv
  path: "transactions.csv"

rules:
  - column: user_id
    tags: ["identity", "critical"]
    checks:
      - type: not_null
      - type: unique
  
  - column: amount
    tags: ["monetary", "validity"]
    checks:
      - type: not_null
      - type: min_value
        value: 0.01
      - type: max_value
        value: 1000000
  
  - column: age
    tags: ["statistical", "drift"]
    checks:
      - type: not_null
      - type: z_score_outlier
        threshold: 3.0
  
  - column: age
    tags: ["distribution", "drift"]
    checks:
      - type: psi
        reference_type: file
        reference_path: "reference_data/user_age.csv"
        warning_threshold: 0.1
        drift_threshold: 0.2
```

### All Check Types Example

See `examples/comprehensive_rules.yaml` for a complete example demonstrating all available check types.

## Best Practices

### 1. Organize by Business Domain

Group related columns together:

```yaml
rules:
  - column: user_id
    description: "User identifier"
    tags: ["identity"]
    checks: [...]
  
  - column: email
    description: "Contact information"
    tags: ["contact"]
    checks: [...]
  
  - column: transaction_id
    description: "Transaction identifier"
    tags: ["identity"]
    checks: [...]
```

### 2. Use Descriptions and Tags

Add context to make rules self-documenting:

```yaml
- column: amount
  description: "Transaction amount in USD"
  tags: ["monetary", "financial", "critical"]
  checks:
    - type: not_null
    - type: min_value
      value: 0.01
```

### 3. Apply Tags for Organization

Use tags to categorize rules:

```yaml
tags:
  - critical
  - financial
  - statistical
```

### 4. Start Simple, Add Complexity Gradually

```yaml
# Simple
- column: email
  checks:
    - type: not_null
    - type: regex
      value: "^[^@]+@[^@]+\\.[^@]+$"

# Advanced (add statistical checks later)
- column: amount
  checks:
    - type: not_null
    - type: min_value
      value: 0.01
    - type: max_value
      value: 1000000
    - type: z_score_outlier
      threshold: 4.0
```

### 5. Use Appropriate Thresholds

- **Z-score**: Use 3.0 for standard outlier detection, 4.0 for strict checks
- **PSI**: Use 0.1 for warning, 0.2 for fail
- **KS test**: Use 0.05 for standard, 0.01 for strict

### 6. Handle Edge Cases

Allow small percentages for nullable fields:

```yaml
- column: middle_name
  checks:
    - type: null_percentage
      value: 0.0
      max_percentage: 0.05  # Allow up to 5% nulls
```

## Advanced Features

### Multiple Checks Per Column

Combine multiple checks for comprehensive validation:

```yaml
- column: age
  checks:
    - type: not_null
    - type: min_value
      value: 18
    - type: max_value
      value: 120
    - type: z_score_outlier
      threshold: 3.0
```

### Reference Data for Drift Detection

Use baseline/reference data for statistical analysis:

```yaml
- column: amount
  checks:
    - type: psi
      reference_type: file
      reference_path: "baseline/amount_distribution.csv"
      warning_threshold: 0.1
      drift_threshold: 0.2
```

### Data Sampling for Large Datasets

Limit sample size for performance:

```yaml
source:
  type: csv
  path: "large_dataset.csv"
  sample_size: 10000  # Only validate first 10,000 rows
```

## Extensibility

### Adding New Check Types

1. Add to `CheckType` enum in `schema.py`:
```python
class CheckType(str, Enum):
    # ... existing types
    CUSTOM = "custom"
```

2. Create validator in `validators/implementations.py`:
```python
def validate_custom(check_config: CheckConfig, column_data: pd.Series) -> bool:
    """Implement custom validation logic"""
    # Your logic here
    return result
```

3. Register in validator registry:
```python
validator_registry.register("custom", validate_custom)
```

4. Add documentation in schema.py:
```python
def get_check_type_description(check_type: str) -> str:
    descriptions = {
        # ... existing descriptions
        CheckType.CUSTOM.value: "Your custom validation logic"
    }
```

### Custom Validators

You can extend the DSL by creating custom validators that integrate with your specific business rules.

## Validation

The DSL includes automatic validation:

- **Schema validation**: Validates YAML structure
- **Type validation**: Ensures parameters are correct
- **Consistency checks**: Detects duplicate column names, missing checks

### Validating Your DSL File

```python
from sagescan_engine.rules.schema import validate_dsl_file

try:
    validate_dsl_file("my_rules.yaml")
    print("✓ DSL is valid")
except Exception as e:
    print(f"✗ DSL validation failed: {e}")
```

### Common Validation Errors

**Error: Invalid check type**
```yaml
checks:
  - type: invalid_type  # Not in CheckType enum
```

**Error: Missing required parameter**
```yaml
checks:
  - type: min_value  # Missing 'value' parameter
```

**Error: Duplicate column names**
```yaml
rules:
  - column: user_id  # First occurrence
    checks: [...]
  - column: user_id  # Duplicate!
    checks: [...]
```

**Error: Invalid threshold**
```yaml
checks:
  - type: psi
    warning_threshold: 2.0  # Must be between 0 and 1
```

## Migration Guide

### From Simple Rules to DSL

**Before (Python code):**
```python
def validate_email(value):
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", value))

results = []
for row in data:
    if not validate_email(row['email']):
        results.append(f"Invalid email: {row['email']}")
```

**After (DSL):**
```yaml
rules:
  - column: email
    checks:
      - type: not_null
      - type: regex
        value: "^[^@]+@[^@]+\.[^@]+$"
```

### Versioning

Always include version in your DSL files:
```yaml
version: "1.0"
```

When adding new checks, bump the version:
```yaml
version: "1.1"
```

## Support and Feedback

For issues, questions, or feature requests:
- GitHub Issues: https://github.com/abhishek09827/SageScan/issues
- Documentation: https://github.com/abhishek09827/SageScan/docs

## License

See LICENSE file for details.