# SageScan Reporting System

Complete documentation for SageScan's reporting system with CLI, JSON, and HTML outputs.

## Overview

The reporting system provides three complementary output formats for validation results:
- **CLI Summary**: Human-readable, formatted for terminal output
- **JSON Report**: Machine-readable, perfect for automation and parsing
- **HTML Report**: Professional, styled for stakeholders and web viewing

## Architecture

```
┌──────────────────┐
│  Validation      │
│  Results Data    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  ReportGenerator │
│  (Python)        │
└────────┬─────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    │         │          │          │
    ▼         ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│   CLI   │ │  JSON  │ │  HTML  │ │Custom  │
│ Format  │ │ Format │ │ Format │ │ Format │
└─────────┘ └────────┘ └────────┘ └────────┘
```

## Core Components

### 1. Data Structures

#### `ValidationResult`
Represents a single validation check result.

```python
@dataclass
class ValidationResult:
    column: str
    check_type: str
    passed: bool
    message: str
    details: Dict[str, Any] = None
    timestamp: str = None
```

**Example:**
```python
ValidationResult(
    column="email",
    check_type="regex",
    passed=False,
    message="Invalid email format: 'invalid-email'",
    details={"invalid_value": "invalid-email", "pattern": "^[^@]+@[^@]+\\.[^@]+$"},
    timestamp="2026-03-25T22:30:16.345678"
)
```

#### `ColumnResult`
Represents validation results for a single column.

```python
@dataclass
class ColumnResult:
    column: str
    description: Optional[str] = None
    tags: List[str] = None
    passed: bool = True
    total_checks: int = 0
    failed_checks: int = 0
    results: List[ValidationResult] = None
```

#### `ValidationSummary`
Complete summary of validation results.

```python
@dataclass
class ValidationSummary:
    status: str
    context: str
    total_columns: int
    total_checks: int
    passed_checks: int
    failed_checks: int
    pass_rate: float
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    columns: List[ColumnResult] = None
    errors: List[str] = None
    llm_explanations: Dict[str, str] = None
```

### 2. ReportGenerator Class

Main class for generating reports in various formats.

```python
from sagescan_engine.core.report import ReportGenerator, ReportFormat

generator = ReportGenerator(validation_summary)
```

## Report Formats

### CLI Format

**Purpose**: Quick, human-readable summary for terminal.

**Characteristics:**
- Formatted with separators and spacing
- Color-coded status indicators
- Grouped by column
- Shows only failed checks

**Output:**
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

amount: ✗ FAIL
  Description: Transaction amount in currency
  Tags: monetary, validity
  Checks: 3 total, 1 failed

  Failed checks:
    - max_value: Value 1500000 exceeds maximum allowed value 1000000

================================================================================
```

### JSON Format

**Purpose**: Machine-readable, for automation and parsing.

**Characteristics:**
- Structured JSON with clear sections
- Detailed check results
- Timestamps for all results
- LLM explanations (if available)
- Errors section (if errors occur)

**Output Structure:**
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
  "columns": [...],
  "explanations": {...},
  "errors": [...]
}
```

**Use Cases:**
- CI/CD integration
- Data quality dashboards
- Automated alerts
- API endpoints
- Database storage

### HTML Format

**Purpose**: Professional, stakeholder-friendly presentation.

**Characteristics:**
- Responsive, modern design
- Color-coded pass/fail status
- Interactive sections
- Print-friendly
- Mobile-friendly

**Features:**
- Summary statistics grid
- Column-by-column breakdowns
- Check-level details
- AI explanations
- Error sections
- Timestamps

**View in Browser:**
```bash
sagescan validate --config rules.yaml --output html data.csv --output-file report.html
open report.html  # macOS
start report.html # Windows
xdg-open report.html # Linux
```

## Integration with CLI

### Python Implementation

```python
# engine/main.py
from sagescan_engine.core.report import ReportGenerator, ReportFormat

def main():
    # Run validation
    config = load_config(args)
    report = run_validation(config)
    
    # Generate report based on format
    generator = ReportGenerator(report)
    
    if args.format == ReportFormat.CLI:
        print(generator.generate(ReportFormat.CLI))
    elif args.format == ReportFormat.JSON:
        json_report = generator.generate(ReportFormat.JSON)
        print(json_report)
    elif args.format == ReportFormat.HTML:
        html_report = generator.generate(ReportFormat.HTML)
        with open(args.output_file, 'w') as f:
            f.write(html_report)
    
    # Exit with appropriate code
    if report['status'] == 'FAIL':
        sys.exit(1)
    else:
        sys.exit(0)
```

### Go Implementation

```go
// cmd/sagescan/main.go
import (
    "github.com/sagescan/sagescan/internal/python"
    "github.com/sagescan/sagescan/internal/report"
)

func runValidation(config python.Config) (*python.Result, error) {
    engine := python.NewEngine("python", "")
    return engine.RunValidation(config)
}

func main() {
    // Parse arguments
    config := parseConfig(args)
    
    // Run validation
    result, err := runValidation(config)
    if err != nil {
        log.Fatalf("Validation failed: %v", err)
    }
    
    // Generate report
    generator := report.NewGenerator(result)
    
    // Output based on format
    switch args.format {
    case "cli":
        fmt.Println(generator.GenerateCLI())
    case "json":
        fmt.Println(generator.GenerateJSON())
    case "html":
        html := generator.GenerateHTML()
        if err := os.WriteFile(args.outputFile, []byte(html), 0644); err != nil {
            log.Fatalf("Failed to write HTML report: %v", err)
        }
    }
    
    // Exit code
    if result.Status == "FAIL" {
        os.Exit(1)
    }
}
```

## Using Reports

### Command-Line Usage

```bash
# Default: CLI format
sagescan validate --config rules.yaml data.csv

# JSON format
sagescan validate --config rules.yaml --output json data.csv --output-file report.json

# HTML format
sagescan validate --config rules.yaml --output html data.csv --output-file report.html

# View HTML in browser
sagescan validate --config rules.yaml --output html data.csv --output-file report.html && open report.html
```

### Programmatic Usage

```python
from sagescan_engine.core.report import ReportGenerator, ReportFormat
from sagescan_engine.core.runner import run_validation

# Run validation
report = run_validation(config)

# Generate all formats
generator = ReportGenerator(report)

# CLI
cli_output = generator.generate(ReportFormat.CLI)
print(cli_output)

# JSON
json_output = generator.generate(ReportFormat.JSON)
with open('report.json', 'w') as f:
    f.write(json_output)

# HTML
html_output = generator.generate(ReportFormat.HTML)
with open('report.html', 'w') as f:
    f.write(html_output)

# Handle exit code
if report['status'] == 'FAIL':
    sys.exit(1)
```

## Report Features

### 1. Summary Section

**CLI:**
- Overall status (PASS/FAIL)
- Duration and timestamps
- Statistics (columns, checks, pass rate)

**JSON:**
- All summary fields
- Timestamps in ISO format

**HTML:**
- Professional dashboard
- Color-coded status
- Responsive grid

### 2. Column Details

**Information Shown:**
- Column name
- Status (PASS/FAIL)
- Description
- Tags
- Check count and failures

**Failed Column Breakdown:**
- Individual check results
- Detailed error messages
- Additional details (if available)

### 3. Check Results

**Fields:**
- `check_type`: Type of validation check
- `passed`: Boolean result
- `message`: Human-readable message
- `details`: Additional context (dict)
- `timestamp`: ISO timestamp

**Example Check Result:**
```python
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
```

### 4. AI Explanations (Optional)

**When Available:**
- LLM-generated explanations for failed checks
- Provides context and guidance
- Helps understand why checks failed

**Example:**
```json
{
  "explanations": {
    "amount": "The amount value of 1,500,000 significantly exceeds the maximum allowed value of 1,000,000. This could indicate data entry errors, currency conversion issues, or fraudulent transactions. Review data sources and validation rules."
  }
}
```

### 5. Errors Section

**CLI:**
- List of all errors
- Warning messages

**JSON:**
- Array of error messages

**HTML:**
- Dedicated error section
- Color-coded (red background)

## Report Customization

### Custom CLI Format

```python
def generate_custom_cli(self) -> str:
    """Generate custom CLI format."""
    lines = []
    
    # Custom header
    lines.append("=== Custom Report ===")
    lines.append(f"Context: {self.summary.context}")
    lines.append()
    
    # Custom summary
    for col in self.summary.columns:
        status = "✓" if col.passed else "✗"
        lines.append(f"{col.column}: {status}")
    
    # Custom footer
    lines.append()
    lines.append("=== End Report ===")
    
    return "\n".join(lines)
```

### Custom HTML Styling

```python
def generate_html(self) -> str:
    """Generate HTML with custom styling."""
    custom_css = """
    .my-custom-theme {
        --primary-color: #your-color;
        --success-color: #your-success-color;
        --error-color: #your-error-color;
    }
    
    .custom-header {
        font-size: 32px;
        font-weight: bold;
        color: var(--primary-color);
    }
    
    .custom-column {
        background: var(--card-background);
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    """
    
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <style>
            {custom_css}
            {{}} /main.css{{ }}/* Your existing styles */
        </style>
    </head>
    <body class="my-custom-theme">
        ...
    </body>
    </html>
    """
    return html
```

### Custom HTML Layout

```python
def generate_html(self) -> str:
    """Generate HTML with custom layout."""
    html = f"""<!DOCTYPE html>
    <html>
    <head>
        <style>
            /* Layout styles */
            .report-container {{
                display: flex;
                flex-direction: column;
                gap: 30px;
            }}
            
            .sidebar {{
                width: 250px;
                position: fixed;
            }}
            
            .main-content {{
                margin-left: 270px;
            }}
        </style>
    </head>
    <body>
        <div class="report-container">
            <div class="sidebar">
                {{/* Sidebar content */}}
            </div>
            <div class="main-content">
                {{/* Main content */}}
            </div>
        </div>
    </body>
    </html>
    """
    return html
```

## Best Practices

### 1. Exit Codes

Always return appropriate exit codes:
```python
if report['status'] == 'FAIL':
    sys.exit(1)  # Error
else:
    sys.exit(0)  # Success
```

### 2. File Naming

Use timestamps for audit trails:
```python
from datetime import datetime

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'report_{timestamp}.json'
```

### 3. Format Selection

- **CLI**: Quick validation, debugging
- **JSON**: CI/CD, automation, parsing
- **HTML**: Stakeholders, web viewing, presentations

### 4. Error Handling

Check status before processing:
```python
if report['status'] == 'FAIL':
    # Handle errors, log details
    for error in report['errors']:
        log.error(error)
    sys.exit(1)
```

### 5. Performance

For large reports:
- Consider pagination in HTML
- Limit detailed output
- Use streaming for JSON (if needed)

## Examples

### Example 1: Complete Report Flow

```python
#!/usr/bin/env python3
import sys
from sagescan_engine.core.report import ReportGenerator, ReportFormat
from sagescan_engine.core.runner import run_validation

def generate_all_reports(report):
    """Generate reports in all formats."""
    generator = ReportGenerator(report)
    
    # CLI
    cli = generator.generate(ReportFormat.CLI)
    
    # JSON
    json_report = generator.generate(ReportFormat.JSON)
    
    # HTML
    html_report = generator.generate(ReportFormat.HTML)
    
    return cli, json_report, html_report

def main():
    # Load config
    config = load_config()
    
    # Run validation
    report = run_validation(config)
    
    # Generate reports
    cli, json_report, html_report = generate_all_reports(report)
    
    # Output reports
    print(cli)  # CLI to stdout
    
    # Save files
    with open('report.json', 'w') as f:
        f.write(json_report)
    
    with open('report.html', 'w') as f:
        f.write(html_report)
    
    # Exit code
    sys.exit(0 if report['status'] == 'PASS' else 1)

if __name__ == "__main__":
    main()
```

### Example 2: JSON Parsing for CI/CD

```python
#!/usr/bin/env python3
import json
import sys
from sagescan_engine.core.report import ReportFormat

def check_validation_report(json_report):
    """Parse and check JSON report."""
    report = json.loads(json_report)
    
    if report['summary']['status'] == 'FAIL':
        print("Validation failed!")
        print(f"Pass Rate: {report['summary']['pass_rate']:.2f}%")
        
        # Show failed columns
        for column in report['columns']:
            if not column['passed']:
                print(f"  - {column['column']}: {column['failed_checks']} checks failed")
        
        return False
    
    return True

def main():
    # Read JSON report
    with open('report.json') as f:
        json_report = f.read()
    
    # Check report
    if not check_validation_report(json_report):
        sys.exit(1)
    
    print("Validation passed!")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### Example 3: HTML Report Generation

```python
#!/usr/bin/env python3
from sagescan_engine.core.report import ReportGenerator, ReportFormat
from sagescan_engine.core.runner import run_validation

def generate_html_report(output_path, context):
    """Generate and save HTML report."""
    # Run validation
    report = run_validation(config)
    
    # Generate HTML
    generator = ReportGenerator(report)
    html = generator.generate(ReportFormat.HTML)
    
    # Add custom header
    html = html.replace(
        '<title>SageScan Validation Report</title>',
        f'<title>Validation Report - {context}</title>'
    )
    
    # Add custom footer
    html = html.replace(
        '<div class="footer">',
        f'''<div class="footer">
            <p>Generated for: {context}</p>
            <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>'''
    )
    
    # Save to file
    with open(output_path, 'w') as f:
        f.write(html)
    
    return html

if __name__ == "__main__":
    html = generate_html_report('report.html', 'Production Data')
    print(f"HTML report generated: report.html")
```

## Testing Reports

### CLI Format Test

```python
def test_cli_format():
    """Test CLI report generation."""
    from sagescan_engine.core.report import ReportGenerator
    
    # Create sample summary
    summary = ValidationSummary(
        status="PASS",
        context="Test Validation",
        total_columns=3,
        total_checks=10,
        passed_checks=8,
        failed_checks=2,
        pass_rate=80.0,
        duration_seconds=1.23,
        start_time=datetime.now(),
        end_time=datetime.now(),
        columns=[
            ColumnResult(
                column="user_id",
                passed=True,
                total_checks=2,
                failed_checks=0,
                results=[
                    ValidationResult(column="user_id", check_type="not_null", passed=True, message="All not null")
                ]
            )
        ]
    )
    
    generator = ReportGenerator(summary)
    cli_output = generator.generate(ReportFormat.CLI)
    
    # Verify format
    assert "VALIDATION REPORT" in cli_output
    assert "Status: PASS" in cli_output
    assert "user_id" in cli_output
    print("✓ CLI format test passed")
```

### JSON Format Test

```python
def test_json_format():
    """Test JSON report generation."""
    from sagescan_engine.core.report import ReportGenerator
    
    summary = create_test_summary()
    generator = ReportGenerator(summary)
    json_output = generator.generate(ReportFormat.JSON)
    
    # Parse JSON
    report = json.loads(json_output)
    
    # Verify structure
    assert "summary" in report
    assert "columns" in report
    assert report["summary"]["status"] == "PASS"
    
    # Verify column structure
    column = report["columns"][0]
    assert column["column"] == "user_id"
    assert "results" in column
    
    print("✓ JSON format test passed")
```

### HTML Format Test

```python
def test_html_format():
    """Test HTML report generation."""
    from sagescan_engine.core.report import ReportGenerator
    
    summary = create_test_summary()
    generator = ReportGenerator(summary)
    html_output = generator.generate(ReportFormat.HTML)
    
    # Verify HTML structure
    assert "<!DOCTYPE html>" in html_output
    assert "<html>" in html_output
    assert "<head>" in html_output
    assert "<body>" in html output
    
    # Verify CSS
    assert ".container" in html_output
    assert ".column" in html_output
    
    # Verify content
    assert "SageScan Validation Report" in html_output
    
    # Write to file for visual testing
    with open('test_report.html', 'w') as f:
        f.write(html_output)
    
    print("✓ HTML format test passed")
    print("  View test_report.html in browser")
```

## Performance Considerations

### Large Reports

For datasets with many columns:
1. **CLI**: Shows summary only by default
2. **JSON**: Full detail - consider pagination
3. **HTML**: Consider pagination or lazy loading

### Memory Usage

```python
# For very large reports, generate incrementally
def generate_large_html(generator):
    """Generate HTML with progressive rendering."""
    html_parts = []
    
    html_parts.append("<html><body><div class='container'>")
    
    # Summary
    summary_html = generator._generate_summary_html()
    html_parts.append(summary_html)
    
    # Columns (one at a time)
    for column in generator.summary.columns:
        html_parts.append(generator._generate_column_html(column))
    
    html_parts.append("</div></body></html>")
    
    return "\n".join(html_parts)
```

## Troubleshooting

### Common Issues

**1. Empty Reports**
```python
# Check if columns exist
if not summary.columns:
    print("Warning: No columns in summary")
    return ""
```

**2. Missing Timestamps**
```python
# Ensure timestamps are set
if not result.timestamp:
    result.timestamp = datetime.now().isoformat()
```

**3. HTML Not Displaying**
- Check for unclosed tags
- Verify CSS is properly embedded
- Test in multiple browsers

## Conclusion

The reporting system provides:
- **Three complementary formats** for different use cases
- **Consistent structure** across all formats
- **Easy integration** with CLI
- **Extensible design** for custom formats
- **Production-ready** features and documentation

For more examples, see `examples/report_outputs.md`.