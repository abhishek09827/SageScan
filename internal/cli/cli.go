package cli

import (
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:     "sagescan",
	Short:   "SageScan is a polyglot data quality validation tool",
	Long:    `A fast, flexible, and production-ready tool to validate data quality rules locally or in CI/CD pipelines using a Python data engine.`,
	Version: "1.0.0",
}

// Register all commands
func init() {
	InitLogger()

	rootCmd.AddCommand(NewValidateCommand().Command)
	rootCmd.AddCommand(NewReportCommand().Command)
	rootCmd.AddCommand(NewProfileCommand().Command)
	rootCmd.AddCommand(NewGenerateRulesCommand().Command)
	rootCmd.AddCommand(NewInitCommand().Command)
	rootCmd.AddCommand(NewCheckLLMCommand().Command)
}

// Execute triggers the CLI
func Execute() error {
	return rootCmd.Execute()
}
