package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

// InitCommand implements the dq init command
type InitCommand struct {
	*BaseCommand
	outputFile string
	template   string
}

// NewInitCommand creates a new init command
func NewInitCommand() *InitCommand {
	cmd := NewBaseCommand(
		"init",
		"Initialize a new SageScan configuration",
		`Creates a new SageScan configuration file with sensible defaults.

Generates a configuration file with:
- Default dataset source (CSV)
- Common validation rules
- Metadata and context
- Ready for immediate use or customization

Examples:
  sagescan init
  sagescan init --output my_rules.yaml
  sagescan init --template basic --output ./rules/
`,
	)

	ic := &InitCommand{BaseCommand: cmd}

	// Add output file flag (optional)
	cmd.Flags().StringVarP(&ic.outputFile, "output", "o", "", "Output file path (defaults to sagescan_config.yaml)")

	// Set the RunE method to handle command execution
	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return ic.Run(cmd, args)
	}

	return ic
}

// Run executes the init command
func (ic *InitCommand) Run(cmd *cobra.Command, args []string) error {
	fmt.Printf("🚀 Initializing SageScan configuration\n")
	fmt.Printf("🔧 Context: %s\n", strings.ToUpper(ic.GetContext()))

	// Create default configuration
	config := ic.createDefaultConfig()

	// Add context if provided
	if ic.GetContext() != "" {
		config["context"] = ic.GetContext()
	}

	// Create parent directory if it doesn't exist
	if ic.outputFile != "" {
		dir := filepath.Dir(ic.outputFile)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create output directory: %w", err)
		}
	} else {
		// Use default filename
		ic.outputFile = "sagescan_config.yaml"
	}

	// Write to file using viper
	v := viper.New()
	for k, value := range config {
		v.Set(k, value)
	}

	if err := WriteConfig(v, ic.outputFile); err != nil {
		return fmt.Errorf("failed to write config: %w", err)
	}

	// Read and display the created config
	configData, err := os.ReadFile(ic.outputFile)
	if err != nil {
		return fmt.Errorf("failed to read created config: %w", err)
	}

	fmt.Printf("\n✅ Configuration created: %s\n", ic.outputFile)
	fmt.Println("\n--- Configuration Preview ---")
	fmt.Print(string(configData))
	fmt.Println("─────────────────────────────")
	fmt.Println("\n💡 Next steps:")
	fmt.Println("  1. Customize the rules in the configuration file")
	fmt.Println("  2. Run: sagescan validate " + ic.outputFile)
	fmt.Println("  3. Review results and adjust as needed")

	return nil
}

// createDefaultConfig creates a default SageScan configuration
func (ic *InitCommand) createDefaultConfig() map[string]interface{} {
	config := map[string]interface{}{
		"version": "1.0",
		"context": ic.GetContext(),
		"source": map[string]interface{}{
			"type": "csv",
			"path": "data/sample.csv",
		},
		"rules": []interface{}{
			map[string]interface{}{
				"column": "id",
				"checks": []interface{}{
					map[string]interface{}{"type": "not_null"},
					map[string]interface{}{"type": "unique"},
				},
			},
			map[string]interface{}{
				"column": "name",
				"checks": []interface{}{
					map[string]interface{}{"type": "not_null"},
					map[string]interface{}{"type": "min_length", "value": 1},
				},
			},
			map[string]interface{}{
				"column": "email",
				"checks": []interface{}{
					map[string]interface{}{"type": "not_null"},
					map[string]interface{}{"type": "regex", "value": `^[^@]+@[^@]+\.[^@]+$`},
				},
			},
			map[string]interface{}{
				"column": "age",
				"checks": []interface{}{
					map[string]interface{}{"type": "not_null"},
					map[string]interface{}{"type": "range", "min": 0, "max": 120},
				},
			},
		},
		"metadata": map[string]interface{}{
			"description": "Default SageScan configuration",
			"created_at":  time.Now().Format("2006-01-02"),
			"author":      "SageScan",
		},
	}

	return config
}

