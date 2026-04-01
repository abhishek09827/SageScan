package cli

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/sagescan/sagescan/internal/python"
	"github.com/spf13/cobra"
)

// CheckLLMCommand implements the sagescan check-llm command
type CheckLLMCommand struct {
	*BaseCommand
	llmAPIKey      string
	llmModel       string
	llmBaseURL     string
	llmTemperature float32
}

// NewCheckLLMCommand creates the check-llm command
func NewCheckLLMCommand() *CheckLLMCommand {
	cmd := NewBaseCommand(
		"check-llm",
		"Verify LLM connectivity and API key",
		`Tests that SageScan can reach the LLM API and that the key is valid.

Sends a single minimal test message to the model and prints the response.
No dataset or config file is required.

Examples:
  sagescan check-llm
  sagescan check-llm --llm-model gpt-3.5-turbo
  sagescan check-llm --llm-api-key sk-...
`,
	)

	clc := &CheckLLMCommand{BaseCommand: cmd}

	cmd.Flags().StringVar(&clc.llmAPIKey, "llm-api-key", "", "OpenAI-compatible API key (overrides OPENAI_API_KEY env var)")
	cmd.Flags().StringVar(&clc.llmModel, "llm-model", "gpt-4o", "LLM model to test against")
	cmd.Flags().StringVar(&clc.llmBaseURL, "llm-base-url", "", "Custom API base URL for self-hosted or local LLMs")
	cmd.Flags().Float32Var(&clc.llmTemperature, "llm-temperature", 0.0, "Temperature setting for LLM request")

	cmd.RunE = func(cmd *cobra.Command, args []string) error {
		return clc.Run(cmd, args)
	}

	return clc
}

// Run executes the check-llm command
func (clc *CheckLLMCommand) Run(cmd *cobra.Command, args []string) error {
	// Resolve API key: flag → env var
	apiKey := clc.llmAPIKey
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}
	if apiKey == "" {
		return fmt.Errorf(
			"no API key found.\n" +
				"  Set OPENAI_API_KEY environment variable, or pass --llm-api-key",
		)
	}

	// Mask the key for display: show first 8 chars + "..."
	masked := apiKey
	if len(apiKey) > 8 {
		masked = apiKey[:8] + strings.Repeat("*", len(apiKey)-8)
	}

	fmt.Println("🔍 SageScan LLM Connectivity Check")
	fmt.Println(strings.Repeat("─", 50))
	fmt.Printf("  Model   : %s\n", clc.llmModel)
	fmt.Printf("  API Key : %s\n", masked)
	fmt.Println(strings.Repeat("─", 50))

	cfg := map[string]interface{}{
		// Minimal source — not used by check_llm command, but required by envelope
		"source":      map[string]interface{}{"type": "csv", "path": ""},
		"llm_api_key":     apiKey,
		"llm_model":       clc.llmModel,
		"llm_temperature": clc.llmTemperature,
	}
	if clc.llmBaseURL != "" {
		cfg["llm_base_url"] = clc.llmBaseURL
	}

	// Use SAGESCAN_PYTHON env var if set, otherwise default to "python"
	pythonPath := os.Getenv("SAGESCAN_PYTHON")
	if pythonPath == "" {
		pythonPath = "python"
	}
	engine := python.NewEngine(pythonPath, "")
	ctx, cancel := context.WithTimeout(context.Background(), clc.GetTimeout())
	defer cancel()

	result, err := engine.RunCommand(ctx, "check_llm", cfg)
	if err != nil {
		return fmt.Errorf("LLM check failed: %w", err)
	}

	if result.Status == "ERROR" {
		fmt.Printf("\n❌  LLM check FAILED\n")
		fmt.Printf("    Error: %s\n", result.Error)
		return fmt.Errorf("LLM connectivity check failed")
	}

	// Print result details from summary
	fmt.Printf("\n✅  LLM check PASSED\n")
	if msg, ok := result.Summary["message"]; ok {
		fmt.Printf("    Response : %v\n", msg)
	}
	if model, ok := result.Summary["model"]; ok {
		fmt.Printf("    Model    : %v\n", model)
	}
	if tokens, ok := result.Summary["tokens_used"]; ok {
		fmt.Printf("    Tokens   : %v\n", tokens)
	}
	if latency, ok := result.Summary["latency_ms"]; ok {
		fmt.Printf("    Latency  : %vms\n", latency)
	}
	fmt.Println()

	return nil
}
