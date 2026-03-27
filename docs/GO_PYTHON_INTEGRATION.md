# Go-Python Subprocess Communication

This document explains how the Go CLI and Python engine communicate using subprocess calls.

## Overview

SageScan uses a hybrid architecture:
- **Go CLI**: Provides fast, native command-line interface
- **Python Engine**: Implements complex validation logic and AI features

Communication happens via subprocess calls with JSON-based messaging.

## Architecture

```
┌─────────────┐
│  Go CLI     │
│  (Cobra)    │
└──────┬──────┘
       │ subprocess call
       │
       ▼
┌─────────────┐
│  Python     │
│  Engine     │
│  (main.py)  │
└──────┬──────┘
       │ subprocess call
       │
       ▼
┌─────────────┐
│  Data       │
│  Processing │
│  & Validation│
└─────────────┘
```

## File Structure

```
sagescan/
├── engine/
│   ├── main.py                 # Python CLI entrypoint
│   └── sagescan_engine/
│       ├── core/
│       │   ├── runner.py       # Validation runner
│       │   └── pipeline.py     # Pipeline orchestration
│       ├── validators/
│       │   ├── base.py         # Base validator class
│       │   ├── implementations.py
│       │   └── distribution.py # Distribution validators
│       └── llm/
│           ├── rule_generator.py
│           └── explanation_generator.py
├── internal/
│   ├── python/
│   │   └── engine.go           # Go subprocess client
│   └── cli/
│       └── *.go                # Cobra commands
└── examples/
    └── python_integration.go   # Usage example
```

## Python CLI Entrypoint (`engine/main.py`)

### Features

1. **Configuration Loading**: Accepts config from file or JSON string
2. **Validation Execution**: Calls Python validation engine
3. **Explanation Generation**: Optional AI-powered explanations
4. **Output Formatting**: JSON and YAML output options
5. **Error Handling**: Structured error messages

### Command-Line Interface

```bash
python engine/main.py --config config.json
python engine/main.py --config-json '{"version":"1.0","source":{"type":"csv","path":"data.csv"},...}'
python engine/main.py --config config.json --output json --no-explanations
```

### Key Functions

- `save_config_to_file()`: Creates temporary JSON config
- `run_validation()`: Main validation logic
- Generates explanations if requested
- Outputs results in specified format
- Returns appropriate exit code (0=PASS, 1=FAIL)

## Go Subprocess Client (`internal/python/engine.go`)

### Key Components

#### 1. **Engine Struct**

```go
type Engine struct {
    pythonPath string
    enginePath string
}
```

#### 2. **Config Struct**

```go
type Config struct {
    Version      string
    Source       map[string]interface{}
    Rules        []map[string]interface{}
    Context      string
    Baseline     string
    LLMAPIKey    string
    LLMModel     string
    LLMMaxTokens int
}
```

#### 3. **Result Struct**

```go
type Result struct {
    Status  string
    Summary map[string]interface{}
    Results []map[string]interface{}
    Error   string
}
```

### Key Methods

#### `RunValidation(config Config) (*Result, error)`

Executes validation using subprocess:

```go
config := python.Config{
    Version: "1.0",
    Source: map[string]interface{}{
        "type": "csv",
        "path": "data.csv",
    },
    Rules: []map[string]interface{}{
        {
            "column": "email",
            "checks": []map[string]interface{}{
                {"type": "regex", "value": "^[^@]+@[^@]+\\.[^@]+$"},
            },
        },
    },
}

result, err := engine.RunValidation(config)
```

#### `createTempConfig(config Config) (string, error)`

Creates temporary JSON config file for subprocess.

#### `buildCommand(configPath string) *exec.Cmd`

Builds subprocess command:
- Sets PYTHONUNBUFFERED=1 for real-time output
- Uses Python to run `engine/main.py`

#### `parseOutput(output []byte) (*Result, error)`

Parses JSON output from Python engine.

#### `CheckEngineAvailability() error`

Verifies Python and engine are installed.

## Example Usage

### Full Integration Example (`examples/python_integration.go`)

```go
package main

import (
    "fmt"
    "os"
    "github.com/sagescan/sagescan/internal/python"
)

func main() {
    // Initialize engine
    engine := python.NewEngine("python", "")
    
    // Check availability
    if err := engine.CheckEngineAvailability(); err != nil {
        log.Fatalf("Engine not available: %v", err)
    }
    
    // Create configuration
    config := python.Config{
        Version: "1.0",
        Source: map[string]interface{}{
            "type": "csv",
            "path": "data.csv",
        },
        Rules: []map[string]interface{}{
            {
                "column": "email",
                "checks": []map[string]interface{}{
                    {"type": "regex", "value": "^[^@]+@[^@]+\\.[^@]+$"},
                },
            },
        },
        Context: "production",
    }
    
    // Run validation
    result, err := engine.RunValidation(config)
    if err != nil {
        log.Fatalf("Validation failed: %v", err)
    }
    
    // Process results
    fmt.Printf("Status: %s\n", result.Status)
    fmt.Printf("Pass Rate: %.1f%%\n", result.Summary["pass_rate"])
    
    if result.Status == "FAIL" {
        os.Exit(1)
    }
}
```

### Running the Example

```bash
cd /path/to/sagescan
go run examples/python_integration.go
```

## Execution Flow

### 1. Go CLI Receives Request

```go
// From internal/cli/validate.go
config := parseConfig(args)
result, err := pythonEngine.RunValidation(config)
```

### 2. Go Creates Temp Config

```go
// internal/python/engine.go
configPath := createTempConfig(config)
// /tmp/sagescan/config_1234567890.json
```

### 3. Go Launches Python Process

```bash
python engine/main.py --config /tmp/sagescan/config_1234567890.json
```

### 4. Python Loads and Validates

```python
# engine/main.py
with open(config_path) as f:
    config = json.load(f)
    
report = run_validation(config)
```

### 5. Python Returns JSON

```json
{
  "status": "PASS",
  "summary": {"pass_rate": 100.0, ...},
  "results": [...]
}
```

### 6. Go Parses and Returns Result

```go
result := parseOutput(output)
return result, nil
```

## Error Handling

### Python Side

- File not found → JSON error with exit code 2
- Invalid JSON → JSON parse error with exit code 3
- Validation error → JSON error with exit code 4

### Go Side

```go
result, err := engine.RunValidation(config)
if err != nil {
    // Handle subprocess error
    log.Fatalf("Validation failed: %v", err)
}

if result.Status == "FAIL" {
    os.Exit(1)
}
```

## Best Practices

### 1. **Absolute Paths**

Convert relative paths to absolute in Go:

```go
if not os.IsAbs(config['source']['path']) {
    config['source']['path'] = os.path.abspath(config['source']['path'])
}
```

### 2. **Cleanup**

Always remove temp files:

```go
defer os.Remove(configPath)
```

### 3. **Error Messages**

Python returns structured JSON errors:

```json
{
  "error": "File not found",
  "message": "/path/to/file.csv: No such file or directory"
}
```

### 4. **Output Buffering**

Set `PYTHONUNBUFFERED=1` for real-time output:

```go
cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
```

## Configuration Examples

### Simple Validation

```go
config := python.Config{
    Version: "1.0",
    Source: map[string]interface{}{
        "type": "csv",
        "path": "data.csv",
    },
    Rules: []map[string]interface{}{
        {
            "column": "email",
            "checks": []map[string]interface{}{
                {"type": "regex", "value": "^[^@]+@[^@]+\\.[^@]+$"},
            },
        },
    },
}
```

### Distribution Analysis

```go
config := python.Config{
    Version: "1.0",
    Source: map[string]interface{}{
        "type": "csv",
        "path": "current_data.csv",
    },
    Rules: []map[string]interface{}{
        {
            "column": "feature_a",
            "checks": []map[string]interface{}{
                {"type": "z_score_outlier", "threshold": 3.0},
                {"type": "psi", "reference_path": "reference_data.csv"},
            },
        },
    },
}
```

### With AI Explanations

Python automatically generates explanations if LLM config is provided:

```go
config := python.Config{
    Version: "1.0",
    Source: map[string]interface{}{
        "type": "csv",
        "path": "data.csv",
    },
    Rules: [...],
    LLMAPIKey: "sk-...",
    LLMModel: "gpt-4",
    LLMMaxTokens: 1000,
}
```

## Testing

### Test Python Engine

```bash
# Test help
python engine/main.py --help

# Test with config file
python engine/main.py --config examples/basic_rules.yaml

# Test with JSON
python engine/main.py --config-json '{"version":"1.0","source":{"type":"csv","path":"examples/sample_data.csv"}}'
```

### Test Go Integration

```bash
# Run example
go run examples/python_integration.go

# Run all tests
go test ./...
```

## Performance Considerations

1. **Subprocess Overhead**: Each validation creates a new Python process
2. **Cold Start**: First call may be slower due to Python import time
3. **Temp File Creation**: Creates temp files on disk

### Optimization Tips

- Cache Python executable path
- Use direct call fallback for development
- Enable verbose logging for debugging

## Troubleshooting

### Common Issues

**1. Python not found**

```
Python not found at: python
```

Solution: Specify full path
```go
engine := python.NewEngine("C:\\Python312\\python.exe", "")
```

**2. Engine not found**

```
Engine not found at: engine/main.py
```

Solution: Verify directory structure or set engine path

**3. Module not found**

```
ModuleNotFoundError: No module named 'sagescan_engine'
```

Solution: Ensure engine directory is in Python path

**4. JSON parse error**

```
Failed to unmarshal JSON: invalid character...
```

Solution: Verify config structure matches Python expectations

## Future Enhancements

- [ ] Add connection pooling for multiple validations
- [ ] Implement streaming output for large datasets
- [ ] Add timeout handling
- [ ] Support for Unix sockets
- [ ] Batch validation for multiple files