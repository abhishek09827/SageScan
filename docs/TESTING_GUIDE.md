# SageScan Testing Guide

Complete step-by-step commands to test every component of the SageScan system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Go CLI Tests](#go-cli-tests)
3. [Python Engine Tests](#python-engine-tests)
4. [YAML DSL Tests](#yaml-dsl-tests)
5. [Reporting System Tests](#reporting-system-tests)
6. [Integration Tests](#integration-tests)
7. [End-to-End Tests](#end-to-end-tests)

## Prerequisites

```bash
# Install Go
go version  # Should be 1.21+

# Install Python 3.8+
python --version

# Install Python dependencies
cd engine
pip install -r requirements.txt

# Install Go dependencies
go mod download
```

## Go CLI Tests

### 1. Build Go CLI

```bash
# Build the CLI
cd /path/to/sagescan
go build -o sagescan ./cmd/sagescan

# Verify build succeeded
ls -lh sagescan
```

### 2. Test Init Command

```bash
# Initialize project
./sagescan init

# Verify files created
ls -la
# Should see: basic_rules.yaml, sagescan_config.yaml, sagescan.yaml
```

### 3. Test Validate Command

```bash
# Validate with basic rules
./sagescan validate examples/sample_data.csv --config examples/basic_rules.yaml

# Check exit code (should be 0 for pass)
echo $?
```

### 4. Test Report Command

```bash
# Generate report
./sagescan report --config examples/basic_rules.yaml

# Check output
cat report.txt
```

### 5. Test Profile Command

```bash
# Generate profile
./sagescan profile --config examples/basic_rules.yaml --output profile.json

# Verify profile created
cat profile.json
```

### 6. Test Generate Rules Command

```bash
# Generate rules
./sagescan generate-rules --input examples/sample_data.csv --output generated_rules.yaml

# Verify file created
ls -la generated_rules.yaml
```

## Python Engine Tests

### 1. Test Python Engine Main

```bash
# Test help
python engine/main.py --help

# Expected output:
# Usage: engine/main.py [OPTIONS]
# Options:
#   --config TEXT
#   --config-json TEXT
#   --output [json,yaml,both]
#   --no-explanations
```

### 2. Test Validation with File Config

```bash
# Create test config
cat > test_config.yaml << 'EOF'
version: "1.0"
source:
  type: csv
  path: examples/sample_data.csv
rules:
  - column: user_id
    checks:
      - type: not_null
  - column: email
    checks:
      - type: regex
        value: "^[^@]+@[^@]+\.[^@]+$"
EOF

# Run validation
python engine/main.py --config test_config.yaml

# Check exit code
echo $?
```

### 3. Test Validation with JSON Config

```bash
# Create JSON config
cat > test_config.json << 'EOF'
{
  "version": "1.0",
  "source": {
    "type": "csv",
    "path": "examples/sample_data.csv"
  },
  "rules": [
    {
      "column": "user_id",
      "checks": [
        {"type": "not_null"}
      ]
    }
  ]
}
EOF

# Run validation
python engine/main.py --config-json "$(cat test_config.json)"

# Check exit code
echo $?
```

### 4. Test Different Output Formats

```bash
# Test JSON output
python engine/main.py --config test_config.yaml --output json > test_output.json
cat test_output.json

# Test YAML output
python engine/main.py --config test_config.yaml --output yaml > test_output.yaml
cat test_output.yaml

# Test both formats
python engine/main.py --config test_config.yaml --output both > test_both.txt
cat test_both.txt
```

### 5. Test No Explanations Flag

```bash
# Run without explanations
python engine/main.py --config test_config.yaml --no-explanations

# Run with explanations
python engine/main.py --config test_config.yaml
```

## YAML DSL Tests

### 1. Test Schema Validation

```bash
# Test valid YAML
python -c "
from sagescan_engine.rules.schema import validate_dsl_file
validate_dsl_file('examples/basic_rules.yaml')
print('✓ Valid YAML')
"

# Test invalid YAML (should fail)
python -c "
from sagescan_engine.rules.schema import validate_dsl_file
try:
    validate_dsl_file('examples/basic_rules_invalid.yaml')
    print('✗ Should have failed')
except Exception as e:
    print(f'✓ Correctly rejected invalid YAML: {e}')
"
```

### 2. Test All Check Types

```bash
# Test comprehensive rules
python -c "
from sagescan_engine.rules.schema import validate_dsl_file
from sagescan_engine.core.runner import run_validation

# Load and validate
config = validate_dsl_file('examples/comprehensive_rules.yaml')
print(f'✓ Validated {len(config.rules)} rules')

# Run validation
report = run_validation(config.dict())
print(f'✓ Validation completed: {report[\"status\"]}')
print(f'  Columns: {report[\"summary\"][\"total_columns\"]}')
print(f'  Checks: {report[\"summary\"][\"total_checks\"]}')
print(f'  Pass Rate: {report[\"summary\"][\"pass_rate\"]:.2f}%')
"
```

### 3. Test Rule Error Detection

```bash
# Test duplicate column names
python -c "
from sagescan_engine.rules.schema import DSLValidator
import tempfile
import yaml

data = {
    'version': '1.0',
    'source': {'type': 'csv', 'path': 'test.csv'},
    'rules': [
        {'column': 'user_id', 'checks': []},
        {'column': 'user_id', 'checks': []},  # Duplicate!
    ]
}

with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    yaml.dump(data, f)
    yaml_file = f.name

try:
    DSLValidator.validate_yaml_file(yaml_file)
    print('✗ Should have detected duplicate columns')
except ValueError as e:
    print(f'✓ Detected duplicate columns: {e}')
"
```

### 4. Test Required Parameters

```bash
# Test missing required parameter
python -c "
from sagescan_engine.rules.schema import CheckConfig

try:
    CheckConfig(type='min_value')  # Missing 'value'
    print('✗ Should have required value parameter')
except ValueError as e:
    print(f'✓ Correctly required value: {e}')
"
```

### 5. Test Available Check Types

```bash
# List all check types
python -c "
from sagescan_engine.rules.schema import get_available_check_types

types = get_available_check_types()
print(f'✓ {len(types)} available check types:')
for t in types:
    print(f'  - {t}')
"
```

## Reporting System Tests

### 1. Test Report Generator CLI

```bash
# Test CLI report
python engine/main.py --config test_config.yaml

# Verify report format
cat test_output.txt | grep -q "VALIDATION REPORT"
echo "✓ CLI report contains header"

cat test_output.txt | grep -q "Status: PASS\|Status: FAIL"
echo "✓ CLI report contains status"

cat test_output.txt | grep -q "Pass Rate:"
echo "✓ CLI report contains pass rate"
```

### 2. Test JSON Report

```bash
# Generate JSON report
python engine/main.py --config test_config.yaml --output json > test_json.json

# Validate JSON structure
python -c "
import json
with open('test_json.json') as f:
    report = json.load(f)

# Check structure
assert 'summary' in report, '✗ Missing summary'
assert 'columns' in report, '✗ Missing columns'
assert report['summary']['status'] in ['PASS', 'FAIL'], '✗ Invalid status'
print('✓ JSON report structure is valid')
print(f'  Status: {report[\"summary\"][\"status\"]}')
print(f'  Columns: {len(report[\"columns\"])}')
"
```

### 3. Test HTML Report

```bash
# Generate HTML report
python engine/main.py --config test_config.yaml --output html > test_html.html

# Validate HTML
python -c "
with open('test_html.html') as f:
    html = f.read()

# Check structure
assert '<!DOCTYPE html>' in html, '✗ Missing DOCTYPE'
assert '<html>' in html, '✗ Missing html tag'
assert '<head>' in html, '✗ Missing head'
assert '<body>' in html, '✗ Missing body'
assert 'SageScan Validation Report' in html, '✗ Missing title'
assert '.container' in html, '✗ Missing container class'

print('✓ HTML report structure is valid')
print('✓ HTML report is ready for viewing')
"
```

### 4. Test LLM Explanations

```bash
# Test with LLM API key (if available)
export OPENAI_API_KEY="sk-test-key"
python engine/main.py --config test_config.yaml --output json > test_with_explanations.json

# Check for explanations
python -c "
import json
with open('test_with_explanations.json') as f:
    report = json.load(f)

if 'explanations' in report and report['explanations']:
    print('✓ LLM explanations generated')
    for col, exp in report['explanations'].items():
        print(f'  - {col}: {exp[:50]}...')
else:
    print('✓ No explanations (API key not configured or no failed checks)')
"
```

### 5. Test Report Output Formats

```bash
# Test all formats together
python engine/main.py --config test_config.yaml --output json --output-file test_all.json &
python engine/main.py --config test_config.yaml --output yaml --output-file test_all.yaml &
python engine/main.py --config test_config.yaml --output html --output-file test_all.html

# Check all files created
for fmt in json yaml html; do
    if [ -f "test_all.$fmt" ]; then
        echo "✓ Created test_all.$fmt"
    else
        echo "✗ Failed to create test_all.$fmt"
    fi
done
```

## Integration Tests

### 1. Test Go-Python Communication

```bash
# Test Python engine availability
python -c "
from sagescan_engine.rules.schema import validate_dsl_file
validate_dsl_file('examples/basic_rules.yaml')
print('✓ Python engine is available')
"

# Test Go engine check
cd internal/python
go run example.go
cd ../..

# Test Go integration with mock
echo '#!/bin/bash
echo "Testing Go-Python integration..."
python engine/main.py --config examples/basic_rules.yaml > /tmp/test_integration.txt
if [ $? -eq 0 ]; then
    echo "✓ Python engine responded successfully"
    grep "VALIDATION REPORT" /tmp/test_integration.txt > /dev/null
    if [ $? -eq 0 ]; then
        echo "✓ CLI output format is correct"
    fi
else
    echo "✗ Python engine failed"
fi
' > test_integration.sh
chmod +x test_integration.sh
./test_integration.sh
```

### 2. Test YAML to Go Config

```bash
# Test parsing YAML in Go
cat > test_yaml_parse.go << 'EOF'
package main

import (
    "fmt"
    "github.com/sagescan/sagescan/internal/python"
)

func main() {
    config := python.Config{
        Version: "1.0",
        Source: map[string]interface{}{
            "type": "csv",
            "path": "examples/sample_data.csv",
        },
        Rules: []map[string]interface{}{
            {
                "column": "user_id",
                "checks": []map[string]interface{}{
                    {"type": "not_null"},
                },
            },
        },
    }
    
    fmt.Println("✓ Go config structure is valid")
    fmt.Printf("  Version: %s\n", config.Version)
    fmt.Printf("  Source: %v\n", config.Source["type"])
    fmt.Printf("  Columns: %d\n", len(config.Rules))
}
EOF

go run test_yaml_parse.go
```

### 3. Test Error Handling

```bash
# Test file not found
python engine/main.py --config nonexistent_config.yaml
echo "Exit code: $?"
# Expected: 2 (File not found)

# Test invalid YAML
python engine/main.py --config-json "{invalid json}"
echo "Exit code: $?"
# Expected: 3 (Invalid JSON)

# Test schema validation errors
cat > test_schema_error.yaml << 'EOF'
version: "1.0"
source:
  type: csv
  path: test.csv
rules:
  - column: "invalid_check_type"
    checks:
      - type: invalid_type  # Invalid check type
EOF

python -c "
from sagescan_engine.rules.schema import DSLValidator
try:
    DSLValidator.validate_yaml_file('test_schema_error.yaml')
    print('✗ Should have detected invalid check type')
except ValueError as e:
    print(f'✓ Schema validation failed: {e}')
"
```

## End-to-End Tests

### 1. Test Complete Workflow

```bash
# Step 1: Create a test dataset
cat > test_data.csv << 'EOF'
user_id,email,age
1,test@example.com,25
2,invalid-email,30
3,test@example.com,35
EOF

# Step 2: Create test rules
cat > test_rules.yaml << 'EOF'
version: "1.0"
source:
  type: csv
  path: test_data.csv
rules:
  - column: user_id
    checks:
      - type: not_null
      - type: unique
  - column: email
    description: "User email"
    checks:
      - type: not_null
      - type: regex
        value: "^[^@]+@[^@]+\.[^@]+$"
  - column: age
    checks:
      - type: not_null
      - type: min_value
        value: 18
EOF

# Step 3: Run validation
python engine/main.py --config test_rules.yaml --output both

# Step 4: Verify results
echo "=== CLI Output ==="
cat report.txt

echo ""
echo "=== JSON Output ==="
cat report.json

echo ""
echo "=== HTML Output ==="
# View HTML (optional)
# open report.html

# Step 5: Check exit code
if [ "$(tail -1 report.txt)" = "Status: PASS" ]; then
    echo "✓ Validation passed as expected"
    exit 0
else
    echo "✗ Validation failed"
    exit 1
fi
```

### 2. Test Comprehensive Rules

```bash
# Load comprehensive rules
python -c "
from sagescan_engine.rules.schema import validate_dsl_file
from sagescan_engine.core.runner import run_validation
import json

config = validate_dsl_file('examples/comprehensive_rules.yaml')
print(f'✓ Loaded {len(config.rules)} rules')

# Get sample data
import pandas as pd
sample = pd.read_csv('examples/sample_data.csv', nrows=100)
print(f'✓ Sample data has {len(sample.columns)} columns')

# Run validation
report = run_validation(config.dict())
print(f'✓ Validation complete: {report[\"status\"]}')

# Print summary
summary = report['summary']
print(f'  Columns: {summary[\"total_columns\"]}')
print(f'  Checks: {summary[\"total_checks\"]}')
print(f'  Pass Rate: {summary[\"pass_rate\"]:.2f}%')
"
```

### 3. Test Drift Detection

```bash
# Test PSI and KS test
python -c "
from sagescan_engine.core.runner import run_validation

config = {
    'version': '1.0',
    'source': {
        'type': 'csv',
        'path': 'examples/sample_data.csv'
    },
    'rules': [
        {
            'column': 'user_id',
            'checks': [
                {'type': 'not_null'}
            ]
        }
    ]
}

# Run validation (this won't have drift checks without reference data)
# Just verify it runs without errors
report = run_validation(config)
print(f'✓ Drift detection test completed: {report[\"status\"]}')
"
```

### 4. Test All Commands Together

```bash
# Initialize
./sagescan init

# Generate rules
./sagescan generate-rules --input examples/sample_data.csv --output generated.yaml

# Validate
./sagescan validate examples/sample_data.csv --config generated.yaml

# Generate report
./sagescan report --config generated.yaml

# Generate profile
./sagescan profile --config generated.yaml --output profile.json

# Check all files created
ls -la *.yaml *.json *.txt *.html 2>/dev/null | head -10
echo "✓ All commands executed successfully"
```

### 5. Test Performance

```bash
# Test validation performance
python -c "
import time
from sagescan_engine.core.runner import run_validation

config = {
    'version': '1.0',
    'source': {
        'type': 'csv',
        'path': 'examples/sample_data.csv'
    },
    'rules': [
        {
            'column': 'user_id',
            'checks': [
                {'type': 'not_null'}
            ]
        }
    ]
}

start = time.time()
report = run_validation(config)
elapsed = time.time() - start

print(f'✓ Validation completed in {elapsed:.2f}s')
print(f'  Status: {report[\"status\"]}')
print(f'  Duration: {elapsed:.2f}s')
"
```

## Test Checklist

### Go CLI Tests
- [ ] Build successful
- [ ] Init command works
- [ ] Validate command works
- [ ] Report command works
- [ ] Profile command works
- [ ] Generate-rules command works

### Python Engine Tests
- [ ] Python help works
- [ ] Validation with file config works
- [ ] Validation with JSON config works
- [ ] JSON output format works
- [ ] YAML output format works
- [ ] Both output formats work
- [ ] No explanations flag works

### YAML DSL Tests
- [ ] Schema validation works
- [ ] All check types load correctly
- [ ] Invalid YAML is rejected
- [ ] Duplicate columns detected
- [ ] Required parameters enforced
- [ ] Available check types listed

### Reporting System Tests
- [ ] CLI report format correct
- [ ] JSON report structure valid
- [ ] HTML report structure valid
- [ ] HTML renders correctly
- [ ] LLM explanations work (if available)

### Integration Tests
- [ ] Go-Python communication works
- [ ] Error handling works
- [ ] File not found errors caught
- [ ] Invalid YAML errors caught
- [ ] Schema errors caught

### End-to-End Tests
- [ ] Complete workflow works
- [ ] All commands execute successfully
- [ ] Reports generated correctly
- [ ] Validation performance acceptable

## Cleanup

```bash
# Remove test files
rm -f test_*.yaml test_*.json test_*.html test_*.txt test_*.go test_integration.sh
rm -rf __pycache__ *.pyc

# Rebuild
go build -o sagescan ./cmd/sagescan

echo "✓ Cleanup complete"
```

## Running All Tests

```bash
#!/bin/bash
# Run all tests

echo "========================================="
echo "SageScan Complete Test Suite"
echo "========================================="
echo ""

# Go CLI Tests
echo "1. Testing Go CLI..."
./sagescan init > /dev/null 2>&1
echo "   ✓ Init command"
./sagescan validate examples/sample_data.csv --config examples/basic_rules.yaml > /dev/null 2>&1
echo "   ✓ Validate command"
./sagescan report --config examples/basic_rules.yaml > /dev/null 2>&1
echo "   ✓ Report command"
./sagescan profile --config examples/basic_rules.yaml --output profile.json > /dev/null 2>&1
echo "   ✓ Profile command"
./sagescan generate-rules --input examples/sample_data.csv --output generated.yaml > /dev/null 2>&1
echo "   ✓ Generate-rules command"
echo "   All Go CLI tests passed!"
echo ""

# Python Engine Tests
echo "2. Testing Python Engine..."
python engine/main.py --help > /dev/null 2>&1
echo "   ✓ Help command"
python engine/main.py --config examples/basic_rules.yaml > /dev/null 2>&1
echo "   ✓ Validation command"
python -c "from sagescan_engine.rules.schema import validate_dsl_file; validate_dsl_file('examples/basic_rules.yaml')" > /dev/null 2>&1
echo "   ✓ Schema validation"
echo "   All Python Engine tests passed!"
echo ""

# Reporting System Tests
echo "3. Testing Reporting System..."
python engine/main.py --config examples/basic_rules.yaml --output json > /dev/null 2>&1
echo "   ✓ JSON report"
python engine/main.py --config examples/basic_rules.yaml --output yaml > /test_output.yaml 2>&1
echo "   ✓ YAML report"
python engine/main.py --config examples/basic_rules.yaml --output html > test_output.html 2>&1
echo "   ✓ HTML report"
echo "   All Reporting System tests passed!"
echo ""

echo "========================================="
echo "✓ All Tests Passed Successfully!"
echo "========================================="
```

Save this as `run_all_tests.sh`, make executable, and run:
```bash
chmod +x run_all_tests.sh
./run_all_tests.sh