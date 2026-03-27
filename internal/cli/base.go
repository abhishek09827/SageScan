package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// BaseCommand provides common functionality for all CLI commands
type BaseCommand struct {
	*cobra.Command
	context      string
	baseline     string
	outputFormat string
	timeout      time.Duration
}

// NewBaseCommand creates a new base command with common flags.
// The long description is used as-is; Cobra renders multi-line text correctly.
func NewBaseCommand(use, short, long string) *BaseCommand {
	cmd := &cobra.Command{
		Use:   use,
		Short: short,
		Long:  long, // Issue #19: do NOT collapse newlines — Cobra handles multi-line help natively.
	}

	bc := &BaseCommand{Command: cmd}

	// Common flags shared by all sub-commands.
	cmd.Flags().StringVar(&bc.context, "context", "", "Context for the validation (e.g., 'production', 'staging')")
	cmd.Flags().StringVar(&bc.baseline, "baseline", "", "Path to baseline configuration for comparison")
	// Issue #12: expose timeout as a flag with a sensible default instead of hardcoding.
	cmd.Flags().DurationVar(&bc.timeout, "timeout", 5*time.Minute, "Maximum time to wait for the engine (e.g. 30s, 5m, 1h)")

	return bc
}

// GetContext returns the validation context
func (bc *BaseCommand) GetContext() string {
	return bc.context
}

// GetBaseline returns the baseline configuration path
func (bc *BaseCommand) GetBaseline() string {
	return bc.baseline
}

// GetOutputFormat returns the desired output format
func (bc *BaseCommand) GetOutputFormat() string {
	return bc.outputFormat
}

// GetTimeout returns the configured engine execution timeout.
func (bc *BaseCommand) GetTimeout() time.Duration {
	return bc.timeout
}

// ValidateConfig ensures the config file exists and is readable
func ValidateConfig(configFile string) error {
	if configFile == "" {
		return fmt.Errorf("config file is required")
	}

	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		return fmt.Errorf("config file not found: %s", configFile)
	}

	file, err := os.Open(configFile)
	if err != nil {
		return fmt.Errorf("cannot read config file: %w", err)
	}
	file.Close()

	return nil
}

// LoadConfig loads and validates a configuration file using a local Viper instance.
func LoadConfig(configFile string) (*viper.Viper, error) {
	v := viper.New()
	v.SetConfigFile(configFile)
	v.SetConfigType("yaml")

	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	return v, nil
}

// WriteConfig writes a configuration file from Viper
func WriteConfig(v *viper.Viper, configFile string) error {
	dir := filepath.Dir(configFile)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	if err := v.SafeWriteConfigAs(configFile); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}
