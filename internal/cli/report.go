package cli

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/sagescan/sagescan/internal/python"
	"github.com/spf13/cobra"
)

// ReportCommand implements the sagescan report command
type ReportCommand struct {
	*BaseCommand
	configFile string
}

// NewReportCommand creates a new report command
func NewReportCommand() *ReportCommand {
	cmd := NewBaseCommand(
		"report",
		"Generate a report from a configuration file",
		`Generates a detailed report from validation results.

The command reads a configuration file and generates a human-readable report
showing validation results, pass/fail statistics, and detailed information.

Examples:
  sagescan report dq.yml
  sagescan report dq.yml --context production
  sagescan report dq.yml --output report.txt
  sagescan report dq.yml --timeout 10m
`,
	)

	rc := &ReportCommand{BaseCommand: cmd}

	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return rc.Run(cmd, args)
	}

	return rc
}

// Run executes the report command
func (rc *ReportCommand) Run(cmd *cobra.Command, args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("config file is required")
	}
	configFile := args[0]

	if err := ValidateConfig(configFile); err != nil {
		return fmt.Errorf("config validation failed: %w", err)
	}

	fmt.Printf("📄 Generating report from: %s\n", configFile)
	fmt.Printf("🔧 Context: %s\n", strings.ToUpper(rc.GetContext()))
	fmt.Println(strings.Repeat("─", 60))

	v, err := LoadConfig(configFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	cfg := v.AllSettings()
	if rc.GetContext() != "" {
		cfg["context"] = rc.GetContext()
	}

	// Use SAGESCAN_PYTHON env var if set, otherwise default to "python"
	pythonPath := os.Getenv("SAGESCAN_PYTHON")
	if pythonPath == "" {
		pythonPath = "python"
	}
	engine := python.NewEngine(pythonPath, "")
	ctx, cancel := context.WithTimeout(context.Background(), rc.GetTimeout())
	defer cancel()

	result, err := engine.RunCommand(ctx, "report", cfg)
	if err != nil {
		return fmt.Errorf("report generation failed: %w", err)
	}

	if result.Status == "ERROR" {
		return fmt.Errorf("engine reported error: %s", result.Error)
	}

	fmt.Println("✓ Report generation completed")
	fmt.Printf("  - Configuration loaded: %s\n", configFile)
	fmt.Printf("  - Context: %s\n", rc.GetContext())
	fmt.Printf("  - Output format: text\n\n")

	if summaryMsg, ok := result.Summary["message"]; ok {
		fmt.Printf("✅ %s\n", summaryMsg)
	}

	return nil
}
