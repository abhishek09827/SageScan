package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"github.com/sagescan/sagescan/internal/python"
	"github.com/spf13/cobra"
)

// ValidateCommand implements the sagescan validate command
type ValidateCommand struct {
	*BaseCommand
	configFile   string
	outputFormat string
	failFast     bool
}

// NewValidateCommand creates a new validate command
func NewValidateCommand() *ValidateCommand {
	cmd := NewBaseCommand(
		"validate",
		"Run data quality validation on a configuration file",
		`Validates data quality rules specified in a configuration file.

The command executes validation rules defined in the config file and reports
passing/failing checks. Supports CSV and Parquet sources.

Examples:
  sagescan validate dq.yml
  sagescan validate dq.yml --context production
  sagescan validate dq.yml --output json
  sagescan validate dq.yml --timeout 10m
`,
	)

	vc := &ValidateCommand{BaseCommand: cmd}

	cmd.Flags().StringVarP(&vc.outputFormat, "output", "o", "text", "Output format: text or json")
	cmd.Flags().BoolVar(&vc.failFast, "fail-fast", false, "Exit with code 1 on any validation failure (useful for CI)")

	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return vc.Run(cmd, args)
	}

	return vc
}

// Run executes the validate command
func (vc *ValidateCommand) Run(cmd *cobra.Command, args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("config file is required\n\nUsage: sagescan validate <config.yaml>")
	}
	configFile := args[0]

	if err := ValidateConfig(configFile); err != nil {
		return fmt.Errorf("config validation failed: %w", err)
	}

	if vc.outputFormat != "json" {
		fmt.Printf("📊 Validating data quality rules from: %s\n", configFile)
		if ctx := vc.GetContext(); ctx != "" {
			fmt.Printf("🔧 Context: %s\n", strings.ToUpper(ctx))
		}
		if baseline := vc.GetBaseline(); baseline != "" {
			fmt.Printf("⚖️  Baseline: %s\n", baseline)
		}
		fmt.Println(strings.Repeat("─", 60))
	}

	v, err := LoadConfig(configFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	cfg := v.AllSettings()
	if vc.GetContext() != "" {
		cfg["context"] = vc.GetContext()
	}
	if vc.GetBaseline() != "" {
		cfg["baseline"] = vc.GetBaseline()
	}

	// Use SAGESCAN_PYTHON env var if set, otherwise default to "python"
	pythonPath := os.Getenv("SAGESCAN_PYTHON")
	if pythonPath == "" {
		pythonPath = "python"
	}

	// Debug output
	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		fmt.Fprintf(os.Stderr, "SAGESCAN_PYTHON env var: %q\n", os.Getenv("SAGESCAN_PYTHON"))
		fmt.Fprintf(os.Stderr, "Using python path: %q\n", pythonPath)
	}

	engine := python.NewEngine(pythonPath, "")

	ctx, cancel := context.WithTimeout(context.Background(), vc.GetTimeout())
	defer cancel()

	result, err := engine.RunCommand(ctx, "validate", cfg)
	if err != nil {
		return fmt.Errorf("validation execution failed: %w", err)
	}

	if result.Status == "ERROR" {
		return fmt.Errorf("engine reported error: %s", result.Error)
	}

	// ── JSON output mode ──────────────────────────────────────────────────
	if vc.outputFormat == "json" {
		enc := json.NewEncoder(cmd.OutOrStdout())
		enc.SetIndent("", "  ")
		return enc.Encode(map[string]interface{}{
			"status":  result.Status,
			"summary": result.Summary,
			"results": result.Results,
		})
	}

	// ── Text output mode ──────────────────────────────────────────────────
	fmt.Printf("\nStatus: %s\n", result.Status)
	if pr, ok := result.Summary["pass_rate"]; ok {
		fmt.Printf("Pass Rate: %.1f%%\n\n", pr)
	}
	if total, ok := result.Summary["total"]; ok {
		passed, _ := result.Summary["passed"]
		failed, _ := result.Summary["failed"]
		fmt.Printf("Checks: %v total | %v passed | %v failed\n\n", total, passed, failed)
	}

	for _, r := range result.Results {
		isPassed := false
		if val, ok := r["passed"].(bool); ok && val {
			isPassed = true
		}
		checkType := r["check_type"]
		if checkType == nil {
			checkType = r["check"]
		}
		if isPassed {
			fmt.Printf("  ✅ %-20v %-20v %v\n", r["column"], checkType, r["message"])
		} else {
			fmt.Printf("  ❌ %-20v %-20v %v\n", r["column"], checkType, r["message"])
		}
	}

	fmt.Println()

	if vc.failFast && result.Status == "FAIL" {
		return fmt.Errorf("validation failed (use --fail-fast=false to suppress this error)")
	}

	return nil
}
