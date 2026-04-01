/*
Package python provides communication between Go CLI and Python engine
using subprocess calls.
*/

package python

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Config represents the validation configuration
type Config struct {
	Version      string                   `json:"version"`
	Source       map[string]interface{}   `json:"source"`
	Rules        []map[string]interface{} `json:"rules"`
	Context      string                   `json:"context,omitempty"`
	Baseline     string                   `json:"baseline,omitempty"`
	LLMAPIKey      string                   `json:"llm_api_key,omitempty"`
	LLMModel       string                   `json:"llm_model,omitempty"`
	LLMMaxTokens   int                      `json:"llm_max_tokens,omitempty"`
	LLMBaseURL     string                   `json:"llm_base_url,omitempty"`
	LLMTemperature float32                  `json:"llm_temperature,omitempty"`
}

// Result represents the validation result
type Result struct {
	Status  string                   `json:"status"`
	Summary map[string]interface{}   `json:"summary"`
	Results []map[string]interface{} `json:"results"`
	Error   string                   `json:"error,omitempty"`
}

// Engine handles communication with Python engine
type Engine struct {
	pythonPath string
	enginePath string
}

// NewEngine creates a new Python engine client
func NewEngine(pythonPath string, enginePath string) *Engine {
	return &Engine{
		pythonPath: pythonPath,
		enginePath: enginePath,
	}
}

// resolveEnginePath returns the absolute path to engine/main.py.
// Priority: explicit enginePath > SAGESCAN_ENGINE_PATH env var > relative to running binary.
func (e *Engine) resolveEnginePath() string {
	if e.enginePath != "" {
		return e.enginePath
	}
	if ep := os.Getenv("SAGESCAN_ENGINE_PATH"); ep != "" {
		return ep
	}
	// Resolve relative to the running binary so the tool works outside the project root.
	exe, err := os.Executable()
	if err == nil {
		return filepath.Join(filepath.Dir(exe), "engine", "main.py")
	}
	// Last-resort fallback: relative to CWD (only works from project root).
	return filepath.Join("engine", "main.py")
}

// RunValidation runs validation using the Python engine (file-based config path).
func (e *Engine) RunValidation(config Config) (*Result, error) {
	configPath, err := e.createTempConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create config: %w", err)
	}
	defer os.Remove(configPath)

	cmd := e.buildCommand(configPath)

	startTime := time.Now()
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	duration := time.Duration(0)

	runErr := cmd.Run()
	duration = time.Since(startTime)

	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		fmt.Fprintf(os.Stderr, "Python engine executed in %v\n", duration)
	}

	if runErr != nil {
		// If it's an ExitError, the script ran but returned non-zero.
		// It might have still produced valid JSON output (e.g. status FAIL).
		if _, isExitErr := runErr.(*exec.ExitError); isExitErr && stdout.Len() > 0 {
			if result, parseErr := e.parseOutput(stdout.Bytes()); parseErr == nil {
				return result, nil // Return the parsed result despite exit status 1
			}
		}

		return &Result{
			Status: "ERROR",
			Error:  fmt.Sprintf("execution failed (%v): %s", runErr, stderr.String()),
		}, runErr
	}

	result, err := e.parseOutput(stdout.Bytes())
	if err != nil {
		return &Result{Status: "ERROR", Error: err.Error()}, err
	}
	return result, nil
}

// RunCommand executes a command on the Python engine via stdin using a context wrapper.
func (e *Engine) RunCommand(ctx context.Context, commandName string, payload interface{}) (*Result, error) {
	request := map[string]interface{}{
		"command": commandName,
		"config":  payload,
	}

	payloadBytes, err := json.MarshalIndent(request, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("failed to marshal payload: %w", err)
	}

	enginePath := e.resolveEnginePath()

	// Resolve relative python path to absolute path only if it looks like a path
	pythonPath := e.pythonPath
	if !filepath.IsAbs(pythonPath) && (strings.Contains(pythonPath, string(filepath.Separator)) || strings.Contains(pythonPath, "/")) {
		if absPath, err := filepath.Abs(pythonPath); err == nil {
			pythonPath = absPath
		}
	}

	// Debug output if verbose
	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		fmt.Fprintf(os.Stderr, "Python path: %s\n", pythonPath)
		fmt.Fprintf(os.Stderr, "Engine path: %s\n", enginePath)
	}

	cmd := exec.CommandContext(ctx, pythonPath, enginePath)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	cmd.Stdin = bytes.NewReader(payloadBytes)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	startTime := time.Now()
	runErr := cmd.Run()
	duration := time.Since(startTime)

	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		fmt.Fprintf(os.Stderr, "Python engine executed in %v\n", duration)
	}

	if runErr != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return nil, fmt.Errorf("python engine execution timed out after %v\nstderr: %s", duration, stderr.String())
		}
		if ctx.Err() == context.Canceled {
			return nil, fmt.Errorf("python engine execution canceled\nstderr: %s", stderr.String())
		}

		// Check if it's an ExitError and we have stdout to parse
		if _, isExitErr := runErr.(*exec.ExitError); isExitErr && stdout.Len() > 0 {
			if result, parseErr := e.parseOutput(stdout.Bytes()); parseErr == nil {
				return result, nil // Python engine exited non-zero but gave valid JSON
			}
		}

		return &Result{
			Status: "ERROR",
			Error:  fmt.Sprintf("execution failed (%v)\nstderr: %s", runErr, stderr.String()),
		}, runErr
	}

	result, err := e.parseOutput(stdout.Bytes())
	if err != nil {
		return &Result{Status: "ERROR", Error: err.Error()}, err
	}
	return result, nil
}

// createTempConfig creates a temporary JSON config file with restricted permissions (0600).
func (e *Engine) createTempConfig(config Config) (string, error) {
	tempDir := filepath.Join(os.TempDir(), "sagescan")
	if err := os.MkdirAll(tempDir, 0700); err != nil {
		return "", fmt.Errorf("failed to create temp dir: %w", err)
	}

	configPath := filepath.Join(tempDir, fmt.Sprintf("config_%d.json", time.Now().UnixNano()))
	// Use 0600 so secrets (LLM API keys) are not world-readable.
	file, err := os.OpenFile(configPath, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0600)
	if err != nil {
		return "", fmt.Errorf("failed to create config file: %w", err)
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(config); err != nil {
		return "", fmt.Errorf("failed to encode config: %w", err)
	}

	return configPath, nil
}

// buildCommand builds the file-based subprocess command using the resolved engine path.
func (e *Engine) buildCommand(configPath string) *exec.Cmd {
	enginePath := e.resolveEnginePath()
	cmd := exec.Command(e.pythonPath, enginePath, "--config", configPath)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")
	return cmd
}

// parseOutput parses the subprocess stdout into a Result.
// It trims BOM/whitespace, and on failure surfaces the raw output for debugging.
func (e *Engine) parseOutput(output []byte) (*Result, error) {
	outputStr := strings.TrimSpace(string(output))
	// Strip UTF-8 BOM if present.
	outputStr = strings.TrimPrefix(outputStr, "\xef\xbb\xbf")
	outputStr = strings.TrimSpace(outputStr)

	if outputStr == "" {
		return nil, fmt.Errorf("python engine produced no output (check stderr with SAGESCAN_VERBOSE=true)")
	}

	var result Result
	if err := json.Unmarshal([]byte(outputStr), &result); err != nil {
		// Surface up to 500 chars of raw output to help with diagnosis.
		preview := outputStr
		if len(preview) > 500 {
			preview = preview[:500] + "…"
		}
		return nil, fmt.Errorf("failed to parse engine JSON output: %w\nraw output: %s", err, preview)
	}

	return &result, nil
}

// RunValidationWithFallback runs validation with fallback to direct Python call.
func (e *Engine) RunValidationWithFallback(config Config, fallbackEnabled bool) (*Result, error) {
	result, err := e.RunValidation(config)
	if err == nil {
		return result, nil
	}

	if !fallbackEnabled {
		return nil, fmt.Errorf("Python engine failed: %w", err)
	}

	fmt.Fprintln(os.Stderr, "Falling back to direct Python call...")
	return e.directRun(config)
}

// directRun runs validation by calling Python directly (fallback method).
func (e *Engine) directRun(config Config) (*Result, error) {
	configPath, err := e.createTempConfig(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create config: %w", err)
	}
	defer os.Remove(configPath)

	enginePath := e.resolveEnginePath()
	args := []string{enginePath, "--config", configPath}
	if config.LLMModel != "" {
		args = append(args, "--config-json", fmt.Sprintf(
			`{"llm_model":%q,"llm_api_key":%q,"llm_max_tokens":%d,"llm_base_url":%q,"llm_temperature":%f}`,
			config.LLMModel, config.LLMAPIKey, config.LLMMaxTokens, config.LLMBaseURL, config.LLMTemperature,
		))
	}

	cmd := exec.Command(e.pythonPath, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return &Result{
			Status: "ERROR",
			Error:  fmt.Sprintf("%s (stderr: %s)", err, stderr.String()),
		}, err
	}

	return e.parseOutput(stdout.Bytes())
}

// RunValidationString runs validation with configuration provided as a raw JSON string.
func (e *Engine) RunValidationString(configJSON string) (*Result, error) {
	enginePath := e.resolveEnginePath()

	cmd := exec.Command(e.pythonPath, enginePath, "--config-json", configJSON)
	cmd.Env = append(os.Environ(), "PYTHONUNBUFFERED=1")

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return &Result{
			Status: "ERROR",
			Error:  fmt.Sprintf("%s (stderr: %s)", err, stderr.String()),
		}, err
	}

	return e.parseOutput(stdout.Bytes())
}

// CheckEngineAvailability checks if the Python engine script exists.
func (e *Engine) CheckEngineAvailability() error {
	enginePath := e.resolveEnginePath()
	if _, err := os.Stat(enginePath); os.IsNotExist(err) {
		return fmt.Errorf("engine not found at %s (set SAGESCAN_ENGINE_PATH to override)", enginePath)
	}
	return nil
}

// GetHelp returns the Python engine help output
func (e *Engine) GetHelp() (string, error) {
	// Build command
	enginePath := e.enginePath
	if enginePath == "" {
		enginePath = filepath.Join(filepath.Dir(filepath.Clean(e.pythonPath)), "engine", "main.py")
	}

	// Create command
	cmd := exec.Command(e.pythonPath, enginePath, "--help")

	// Execute
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", err
	}

	return string(output), nil
}
