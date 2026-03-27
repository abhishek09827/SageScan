/*
Example usage of the Python engine communication layer

This file demonstrates how to integrate the Go Python engine client
into a Go application using subprocess calls.
*/

package main

import (
	"fmt"
	"log"
	"os"

	"github.com/sagescan/sagescan/internal/python"
)

// Example shows how to use the Python engine from Go
func Example() {
	// Initialize the Python engine
	engine := python.NewEngine("python", "")

	// Check if engine is available
	if err := engine.CheckEngineAvailability(); err != nil {
		log.Fatalf("Engine not available: %v", err)
	}

	// Create validation configuration
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
			{
				"column": "age",
				"checks": []map[string]interface{}{
					{"type": "not_null"},
					{"type": "min_value", "value": 18},
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

	// Print results
	fmt.Printf("Status: %s\n", result.Status)
	fmt.Printf("Pass Rate: %.1f%%\n", result.Summary["pass_rate"])

	// Check for failures
	for _, r := range result.Results {
		if !r["passed"].(bool) {
			fmt.Printf("  - %s: %s\n", r["column"], r["message"])
		}
	}

	// Exit with appropriate code
	if result.Status == "FAIL" {
		os.Exit(1)
	}
}

// RunExample is a self-contained example that can be tested
func RunExample() {
	fmt.Println("=== Python Engine Integration Example ===")
	fmt.Println()

	// Initialize the Python engine
	engine := python.NewEngine("python", "")
	fmt.Println("✓ Engine initialized")

	// Check if engine is available
	if err := engine.CheckEngineAvailability(); err != nil {
		fmt.Printf("✗ Engine not available: %v\n", err)
		fmt.Println("\nTo run this example:")
		fmt.Println("1. Install Python: https://www.python.org/downloads/")
		fmt.Println("2. Install dependencies: pip install pandas scipy openai pyyaml")
		fmt.Println("3. Run from project root: go run examples/python_integration.go")
		return
	}

	// Create validation configuration
	config := python.Config{
		Version: "1.0",
		Source: map[string]interface{}{
			"type": "csv",
			"path": "../examples/sample_data.csv",
		},
		Rules: []map[string]interface{}{
			{
				"column": "user_id",
				"checks": []map[string]interface{}{
					{"type": "not_null"},
					{"type": "unique"},
				},
			},
			{
				"column": "age",
				"checks": []map[string]interface{}{
					{"type": "not_null"},
					{"type": "min_value", "value": 18},
				},
			},
		},
		Context: "production",
	}

	fmt.Println("✓ Configuration created")
	fmt.Println()

	// Run validation
	fmt.Println("Running validation...")
	result, err := engine.RunValidation(config)
	if err != nil {
		fmt.Printf("✗ Validation failed: %v\n", err)
		return
	}

	fmt.Println("✓ Validation complete")
	fmt.Println()

	// Print results
	fmt.Printf("Status: %s\n", result.Status)
	fmt.Printf("Pass Rate: %.1f%%\n", result.Summary["pass_rate"])
	fmt.Println()

	// Check for failures
	failedCount := 0
	for _, r := range result.Results {
		if !r["passed"].(bool) {
			failedCount++
			fmt.Printf("✗ %s: %s\n", r["column"], r["message"])
		}
	}

	if failedCount == 0 {
		fmt.Println("All checks passed! ✓")
		os.Exit(0)
	} else {
		fmt.Printf("\n%d validation(s) failed\n", failedCount)
		os.Exit(1)
	}
}

func main() {
	RunExample()
}
