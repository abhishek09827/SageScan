package cli

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/sagescan/sagescan/internal/python"
	"github.com/spf13/cobra"
)

// ProfileCommand implements the sagescan profile command
type ProfileCommand struct {
	*BaseCommand
	configFile string
}

// NewProfileCommand creates a new profile command
func NewProfileCommand() *ProfileCommand {
	cmd := NewBaseCommand(
		"profile",
		"Generate a data profile from a configuration file",
		`Generates a data profile from a configuration file.

The command reads a configuration file and generates statistical profiles
including distribution analysis, value counts, and data quality metrics.

Examples:
  sagescan profile dq.yml
  sagescan profile dq.yml --context production
  sagescan profile dq.yml --output profile.json
  sagescan profile dq.yml --timeout 15m
`,
	)

	pc := &ProfileCommand{BaseCommand: cmd}

	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return pc.Run(cmd, args)
	}

	return pc
}

// Run executes the profile command
func (pc *ProfileCommand) Run(cmd *cobra.Command, args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("config file is required")
	}
	configFile := args[0]

	if err := ValidateConfig(configFile); err != nil {
		return fmt.Errorf("config validation failed: %w", err)
	}

	fmt.Printf("📊 Generating profile from: %s\n", configFile)
	fmt.Printf("🔧 Context: %s\n", strings.ToUpper(pc.GetContext()))
	fmt.Printf("📋 Output: %s\n", strings.ToUpper(pc.GetOutputFormat()))
	fmt.Println(strings.Repeat("─", 60))

	v, err := LoadConfig(configFile)
	if err != nil {
		return fmt.Errorf("failed to load config: %w", err)
	}

	cfg := v.AllSettings()
	if pc.GetContext() != "" {
		cfg["context"] = pc.GetContext()
	}

	// Use SAGESCAN_PYTHON env var if set, otherwise default to "python"
	pythonPath := os.Getenv("SAGESCAN_PYTHON")
	if pythonPath == "" {
		pythonPath = "python"
	}
	engine := python.NewEngine(pythonPath, "")
	ctx, cancel := context.WithTimeout(context.Background(), pc.GetTimeout())
	defer cancel()

	result, err := engine.RunCommand(ctx, "profile", cfg)
	if err != nil {
		return fmt.Errorf("profile generation failed: %w", err)
	}

	if result.Status == "ERROR" {
		return fmt.Errorf("engine reported error: %s", result.Error)
	}

	fmt.Println("✓ Profile generation completed")
	fmt.Printf("  - Configuration loaded: %s\n", configFile)
	fmt.Printf("  - Context: %s\n", pc.GetContext())
	fmt.Printf("  - Analysis type: data profiling\n\n")

	if summaryMsg, ok := result.Summary["message"]; ok {
		fmt.Printf("✅ %s\n", summaryMsg)
	}

	return nil
}
