package cli

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/sagescan/sagescan/internal/python"
	"github.com/spf13/cobra"
)

// GenerateRulesCommand implements the sagescan generate-rules command
type GenerateRulesCommand struct {
	*BaseCommand
	inputFile  string
	outputFile string
	llmAPIKey      string
	llmModel       string
	llmBaseURL     string
	llmTemperature float32
}

// NewGenerateRulesCommand creates a new generate-rules command
func NewGenerateRulesCommand() *GenerateRulesCommand {
	cmd := NewBaseCommand(
		"generate-rules",
		"Generate validation rules from a dataset using AI",
		`Generates validation rules from a dataset automatically using an LLM.

The command analyses the dataset structure and generates appropriate validation
rules for each column based on data types, statistics, and common patterns.

Requires an OpenAI-compatible API key:
  - Set the OPENAI_API_KEY environment variable, OR
  - Pass --llm-api-key directly (not recommended for CI pipelines)

Examples:
  sagescan generate-rules --input data.csv --output rules.yaml
  sagescan generate-rules --input data.csv --output rules.yaml --context production
  sagescan generate-rules -i data.csv -o rules.yaml --llm-model gpt-4o --timeout 10m
`,
	)

	grc := &GenerateRulesCommand{BaseCommand: cmd}

	cmd.Flags().StringVarP(&grc.inputFile, "input", "i", "", "Input dataset file path (required)")
	cmd.Flags().StringVarP(&grc.outputFile, "output", "o", "", "Output rules file path (required)")
	cmd.Flags().StringVar(&grc.llmAPIKey, "llm-api-key", "", "OpenAI-compatible API key (overrides OPENAI_API_KEY env var)")
	cmd.Flags().StringVar(&grc.llmModel, "llm-model", "gpt-4o", "LLM model to use for rule generation")
	cmd.Flags().StringVar(&grc.llmBaseURL, "llm-base-url", "", "Custom API base URL for self-hosted or local LLMs")
	cmd.Flags().Float32Var(&grc.llmTemperature, "llm-temperature", 0.3, "Temperature setting for LLM generation")

	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return grc.Run(cmd, args)
	}

	return grc
}

// Run executes the generate-rules command
func (grc *GenerateRulesCommand) Run(cmd *cobra.Command, args []string) error {
	if grc.inputFile == "" {
		return fmt.Errorf("input file is required (--input or -i flag)")
	}

	if grc.outputFile == "" {
		return fmt.Errorf("output file is required (--output or -o flag)")
	}

	// Resolve LLM API key: flag → env var
	apiKey := grc.llmAPIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}
	if apiKey == "" {
		return fmt.Errorf(
			"LLM API key is required for rule generation.\n" +
				"  Set OPENAI_API_KEY environment variable, or pass --llm-api-key",
		)
	}

	fmt.Printf("🤖 Generating validation rules from: %s\n", grc.inputFile)
	fmt.Printf("🔧 Context: %s\n", strings.ToUpper(grc.GetContext()))
	fmt.Printf("📁 Output:  %s\n", grc.outputFile)
	fmt.Printf("🧠 Model:   %s\n", grc.llmModel)
	fmt.Println(strings.Repeat("─", 60))

	sourceType := "csv"
	if strings.HasSuffix(grc.inputFile, ".parquet") {
		sourceType = "parquet"
	}

	cfg := map[string]interface{}{
		"source": map[string]interface{}{
			"type": sourceType,
			"path": grc.inputFile,
		},
		"output_file": grc.outputFile,
		"context":     grc.GetContext(),
		"llm_api_key":     apiKey,
		"llm_model":       grc.llmModel,
		"llm_temperature": grc.llmTemperature,
	}
	if grc.llmBaseURL != "" {
		cfg["llm_base_url"] = grc.llmBaseURL
	}

	// Use SAGESCAN_PYTHON env var if set, otherwise default to "python"
	pythonPath := os.Getenv("SAGESCAN_PYTHON")
	if pythonPath == "" {
		pythonPath = "python"
	}
	engine := python.NewEngine(pythonPath, "")
	ctx, cancel := context.WithTimeout(context.Background(), grc.GetTimeout())
	defer cancel()

	result, err := engine.RunCommand(ctx, "generate_rules", cfg)
	if err != nil {
		return fmt.Errorf("rule generation failed: %w", err)
	}

	if result.Status == "ERROR" {
		return fmt.Errorf("engine reported error: %s", result.Error)
	}

	fmt.Println("✓ Rules generation completed")
	fmt.Printf("  - Input file:  %s\n", grc.inputFile)
	fmt.Printf("  - Output file: %s\n", grc.outputFile)
	fmt.Printf("  - Context:     %s\n", grc.GetContext())

	if summaryMsg, ok := result.Summary["message"]; ok {
		fmt.Printf("✅ %s\n", summaryMsg)
	}

	return nil
}
