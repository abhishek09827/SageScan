# SageScan Report Output Examples

This document shows example outputs for all three report formats: CLI, JSON, and HTML.

## CLI Report

### Successful Validation

```
================================================================================
 VALIDATION REPORT: E-commerce Transactions
================================================================================
 Status: PASS
 Duration: 2.34s
 Start: 2026-03-25 22:30:15
 End: 2026-03-25 22:30:17

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------
  Columns: 12/12
  Total Checks: 45
  Passed: 42
  Failed: 3
  Pass Rate: 93.33%

--------------------------------------------------------------------------------
COLUMN DETAILS
--------------------------------------------------------------------------------

user_id: ✓ PASS
  Description: Unique identifier for each user
  Tags: identity, critical
  Checks: 2 total, 0 failed

email: ✓ PASS
  Description: User email address for communication
  Tags: contact, formatting
  Checks: 3 total, 0 failed

age: ✓ PASS
  Description: User age in years
  Tags: validity, business
  Checks: 3 total, 0 failed

transaction_id: ✓ PASS
  Description: Unique transaction identifier
  Tags: identity, critical
  Checks: 2 total, 0 failed

amount: ✓ FAIL
  Description: Transaction amount in currency
  Tags: monetary, validity
  Checks: 3 total, 1 failed

  Failed checks:
    - max_value: Value 1500000 exceeds maximum allowed value 1000000

currency: ✓ PASS
  Description: Transaction currency code
  Tags: monetary, validity
  Checks: 2 total, 0 failed

transaction_date: ✓ PASS
  Description: Timestamp of transaction
  Tags: temporal, validity
  Checks: 2 total, 0 failed

category: ✓ PASS
  Description: Product category
  Tags: categorical, reference
  Checks: 2 total, 0 failed

================================================================================
```

### Failed Validation

```
================================================================================
 VALIDATION REPORT: User Data Validation
================================================================================
 Status: FAIL
 Duration: 1.87s
 Start: 2026-03-25 22:35:20
 End: 2026-03-25 22:35:22

--------------------------------------------------------------------------------
SUMMARY
--------------------------------------------------------------------------------
  Columns: 8/8
  Total Checks: 35
  Passed: 23
  Failed: 12
  Pass Rate: 65.71%

--------------------------------------------------------------------------------
COLUMN DETAILS
--------------------------------------------------------------------------------

user_id: ✓ PASS
  Description: Unique user identifier
  Tags: identity
  Checks: 2 total, 0 failed

email: ✗ FAIL
  Description: User email address
  Tags: contact, formatting
  Checks: 3 total, 2 failed

  Failed checks:
    - regex: Invalid email format: "invalid-email"

    - regex: Invalid email format: "missing-at-sign"

username: ✓ PASS
  Description: User username
  Tags: identity
  Checks: 2 total, 0 failed

age: ✗ FAIL
  Description: User age
  Tags: validity
  Checks: 2 total, 1 failed

  Failed checks:
    - min_value: Value -5 is below minimum allowed value 18

phone: ✓ PASS
  Description: Phone number
  Tags: contact
  Checks: 2 total, 0 failed

--------------------------------------------------------------------------------
ERRORS
--------------------------------------------------------------------------------
  • Failed: 5 validations did not pass
  • Warnings: 7 validations passed with warnings

================================================================================
```

## JSON Report

### Successful Validation

```json
{
  "summary": {
    "status": "PASS",
    "context": "E-commerce Transactions",
    "total_columns": 12,
    "total_checks": 45,
    "passed_checks": 42,
    "failed_checks": 3,
    "pass_rate": 93.33,
    "duration_seconds": 2.34,
    "start_time": "2026-03-25T22:30:15.123456",
    "end_time": "2026-03-25T22:30:17.123456"
  },
  "columns": [
    {
      "column": "user_id",
      "description": "Unique identifier for each user",
      "tags": [
        "identity",
        "critical"
      ],
      "passed": true,
      "total_checks": 2,
      "failed_checks": 0,
      "results": [
        {
          "check_type": "not_null",
          "passed": true,
          "message": "All values are not null",
          "details": {},
          "timestamp": "2026-03-25T22:30:16.234567"
        },
        {
          "check_type": "unique",
          "passed": true,
          "message": "All values are unique",
          "details": {},
          "timestamp": "2026-03-25T22:30:16.345678"
        }
      ]
    },
    {
      "column": "amount",
      "description": "Transaction amount in currency",
      "tags": [
        "monetary",
        "validity"
      ],
      "passed": false,
      "total_checks": 3,
      "failed_checks": 1,
      "results": [
        {
          "check_type": "not_null",
          "passed": true,
          "message": "All values are not null",
          "details": {},
          "timestamp": "2026-03-25T22:30:16.456789"
        },
        {
          "check_type": "min_value",
          "passed": true,
          "message": "All values are >= 0.01",
          "details": {},
          "timestamp": "2026-03-25T22:30:16.567890"
        },
        {
          "check_type": "max_value",
          "passed": false,
          "message": "Value 1500000 exceeds maximum allowed value 1000000",
          "details": {
            "invalid_value": 1500000,
            "max_value": 1000000
          },
          "timestamp": "2026-03-25T22:30:16.678901"
        }
      ]
    }
  ],
  "explanations": {
    "amount": "The amount value of 1,500,000 significantly exceeds the maximum allowed value of 1,000,000. This could indicate data entry errors, currency conversion issues, or fraudulent transactions. Review data sources and validation rules."
  }
}
```

### Failed Validation

```json
{
  "summary": {
    "status": "FAIL",
    "context": "User Data Validation",
    "total_columns": 8,
    "total_checks": 35,
    "passed_checks": 23,
    "failed_checks": 12,
    "pass_rate": 65.71,
    "duration_seconds": 1.87,
    "start_time": "2026-03-25T22:35:20.123456",
    "end_time": "2026-03-25T22:35:22.123456"
  },
  "columns": [
    {
      "column": "email",
      "description": "User email address",
      "tags": [
        "contact",
        "formatting"
      ],
      "passed": false,
      "total_checks": 3,
      "failed_checks": 2,
      "results": [
        {
          "check_type": "not_null",
          "passed": true,
          "message": "All values are not null",
          "details": {},
          "timestamp": "2026-03-25T22:35:21.234567"
        },
        {
          "check_type": "regex",
          "passed": false,
          "message": "Invalid email format: 'invalid-email'",
          "details": {
            "invalid_value": "invalid-email",
            "pattern": "^[^@]+@[^@]+\\.[^@]+$"
          },
          "timestamp": "2026-03-25T22:35:21.345678"
        },
        {
          "check_type": "regex",
          "passed": false,
          "message": "Invalid email format: 'missing-at-sign'",
          "details": {
            "invalid_value": "missing-at-sign",
            "pattern": "^[^@]+@[^@]+\\.[^@]+$"
          },
          "timestamp": "2026-03-25T22:35:21.456789"
        }
      ]
    },
    {
      "column": "age",
      "description": "User age",
      "tags": [
        "validity"
      ],
      "passed": false,
      "total_checks": 2,
      "failed_checks": 1,
      "results": [
        {
          "check_type": "not_null",
          "passed": true,
          "message": "All values are not null",
          "details": {},
          "timestamp": "2026-03-25T22:35:21.567890"
        },
        {
          "check_type": "min_value",
          "passed": false,
          "message": "Value -5 is below minimum allowed value 18",
          "details": {
            "invalid_value": -5,
            "min_value": 18
          },
          "timestamp": "2026-03-25T22:35:21.678901"
        }
      ]
    }
  ],
  "errors": [
    "5 validations did not pass",
    "7 validations passed with warnings"
  ]
}
```

## HTML Report

The HTML report includes:
- **Professional design** with clean layout
- **Summary statistics** in a responsive grid
- **Column-by-column breakdown** with visual status indicators
- **Color-coded** pass/fail status
- **Detailed check results** with messages
- **AI explanations** (when available)
- **Error section** (when errors occur)

### HTML Report Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SageScan Validation Report</title>
    <style>
        /* Professional CSS styling for reports */
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        /* Summary grid */
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .summary-item {
            background: white;
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }
        .summary-item .value.pass {
            color: #27ae60;
        }
        .summary-item .value.fail {
            color: #c0392b;
        }
        /* Column cards */
        .column {
            margin-bottom: 30px;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            overflow: hidden;
        }
        .column-passed .column-header {
            background: #27ae60;
        }
        .column-failed .column-header {
            background: #c0392b;
        }
        /* Check results */
        .check.passed {
            border-left-color: #27ae60;
            background: #f0fff4;
        }
        .check.failed {
            border-left-color: #c0392b;
            background: #fff5f5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SageScan Validation Report</h1>
            <div class="meta">
                <p>Context: E-commerce Transactions</p>
                <p>Status: <span class="badge pass">PASS</span></p>
                <p>Duration: 2.34s</p>
                <p>Start: 2026-03-25 22:30:15</p>
                <p>End: 2026-03-25 22:30:17</p>
            </div>
        </div>

        <div class="summary">
            <h2>Summary</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="label">Total Columns</div>
                    <div class="value">12</div>
                </div>
                <div class="summary-item">
                    <div class="label">Total Checks</div>
                    <div class="value">45</div>
                </div>
                <div class="summary-item">
                    <div class="label">Passed</div>
                    <div class="value pass">42</div>
                </div>
                <div class="summary-item">
                    <div class="label">Failed</div>
                    <div class="value fail">3</div>
                </div>
                <div class="summary-item">
                    <div class="label">Pass Rate</div>
                    <div class="value pass">93.33%</div>
                </div>
            </div>
        </div>

        <!-- Column details with pass/fail status -->
        <div class="column column-passed">
            <div class="column-header">
                <div class="column-name">amount</div>
                <div class="status">PASS</div>
            </div>
            <div class="column-body">
                <div class="column-info">
                    <p><strong>Description:</strong> Transaction amount in currency</p>
                    <p><strong>Tags:</strong> monetary, validity</p>
                    <p><strong>Checks:</strong> 3 total, 1 failed</p>
                </div>
                <ul class="checks-list">
                    <li class="check passed">
                        <div class="check-type">not_null</div>
                        <div class="check-message">All values are not null</div>
                    </li>
                    <li class="check passed">
                        <div class="check-type">min_value</div>
                        <div class="check-message">All values are >= 0.01</div>
                    </li>
                    <li class="check failed">
                        <div class="check-type">max_value</div>
                        <div class="check-message">Value 1500000 exceeds maximum allowed value 1000000</div>
                        <div class="check-details">
                            {
                              "invalid_value": 1500000,
                              "max_value": 1000000
                            }
                        </div>
                    </li>
                </ul>
            </div>
        </div>

        <!-- AI Explanations Section -->
        <div class="explanations">
            <h3>AI Explanation</h3>
            <div class="explanation">
                <div class="explanation-type">amount</div>
                <div class="explanation-text">The amount value of 1,500,000 significantly exceeds the maximum allowed value of 1,000,000. This could indicate data entry errors, currency conversion issues, or fraudulent transactions. Review data sources and validation rules.</div>
            </div>
        </div>
    </div>
</body>
</html>
```

## Report Integration with CLI

### Python CLI Integration

```python
# In engine/main.py
from sagescan_engine.core.report import ReportGenerator, ReportFormat

def main():
    # Run validation
    report = run_validation(config)
    
    # Generate report in desired format
    generator = ReportGenerator(report)
    
    # CLI output (default)
    print(generator.generate(ReportFormat.CLI))
    
    # JSON output
    json_report = generator.generate(ReportFormat.JSON)
    with open('report.json', 'w') as f:
        f.write(json_report)
    
    # HTML output
    html_report = generator.generate(ReportFormat.HTML)
    with open('report.html', 'w') as f:
        f.write(html_report)
    
    # Return appropriate exit code
    if report['status'] == 'FAIL':
        sys.exit(1)
    else:
        sys.exit(0)
```

### Go CLI Integration

```go
// In cmd/sagescan/main.go
import (
    "github.com/sagescan/sagescan/internal/python"
)

func runValidation(config python.Config) (*python.Result, error) {
    engine := python.NewEngine("python", "")
    return engine.RunValidation(config)
}

func main() {
    // Parse CLI arguments
    config := parseConfig(args)
    
    // Run validation
    result, err := runValidation(config)
    if err != nil {
        log.Fatalf("Validation failed: %v", err)
    }
    
    // Generate report based on output format
    generator := report.NewGenerator(result)
    
    switch args.format {
    case "cli":
        fmt.Println(generator.GenerateCLI())
    case "json":
        fmt.Println(generator.GenerateJSON())
    case "html":
        html := generator.GenerateHTML()
        err := os.WriteFile("report.html", []byte(html), 0644)
        if err != nil {
            log.Fatalf("Failed to write HTML report: %v", err)
        }
    }
    
    // Exit with appropriate code
    if result.Status == "FAIL" {
        os.Exit(1)
    }
}
```

## Using Reports

### 1. CLI (Default)

```bash
# Runs validation and shows CLI summary
sagescan validate --config rules.yaml data.csv

# Shows help
sagescan validate --help
```

### 2. JSON

```bash
# Save JSON report to file
sagescan validate --config rules.yaml --output json data.csv --output-file report.json

# Or redirect to file
sagescan validate --config rules.yaml --output json data.csv > report.json
```

### 3. HTML

```bash
# Generate HTML report
sagescan validate --config rules.yaml --output html data.csv --output-file report.html

# View in browser
open report.html  # macOS
start report.html # Windows
xdg-open report.html # Linux
```

## Report Features

### 1. **Summary Section**
- Overall status (PASS/FAIL)
- Duration and timestamps
- Statistics (columns, checks, pass rate)

### 2. **Column Details**
- Column name with status
- Description and tags
- Number of checks and failures
- Individual check results

### 3. **Check Results**
- Check type
- Pass/fail status
- Detailed error message
- Additional details (if available)
- Timestamp

### 4. **AI Explanations** (Optional)
- LLM-generated explanations for failed checks
- Provides context and guidance

### 5. **Errors Section**
- List of all errors
- Warnings (if any)
- Stack traces (if errors occur)

## Report Customization

### Custom CLI Format

```python
def generate_custom_cli(self) -> str:
    """Generate custom CLI format."""
    lines = []
    # Your custom format here
    return "\n".join(lines)
```

### Custom HTML Styling

```python
def generate_html(self) -> str:
    """Generate HTML with custom styling."""
    custom_css = """
    .my-custom-style {
        color: #your-color;
        font-size: 18px;
    }
    """
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <style>
            {custom_css}
        </style>
    </head>
    <body>
        ...
    </body>
    </html>
    """
    return html
```

## Best Practices

1. **Always check status before processing**
   ```python
   if report['status'] == 'FAIL':
       log_errors(report)
       sys.exit(1)
   ```

2. **Save reports for audit trails**
   ```python
   timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
   json_report = generator.generate_json()
   with open(f'report_{timestamp}.json', 'w') as f:
       f.write(json_report)
   ```

3. **Use HTML reports for stakeholders**
   - Easy to view in browser
   - Professional appearance
   - Color-coded status

4. **Use JSON reports for automation**
   - Easy to parse programmatically
   - Great for CI/CD pipelines
   - Can be converted to other formats

5. **Use CLI reports for quick validation**
   - Fast to see results
   - Minimal output
   - Good for debugging

## Conclusion

The reporting system provides three complementary formats:
- **CLI**: Quick, human-readable summaries
- **JSON**: Machine-readable, for automation
- **HTML**: Professional, for stakeholders

All reports include:
- Clear summary statistics
- Detailed column results
- Check-by-check breakdowns
- Error reporting
- AI explanations (when available)