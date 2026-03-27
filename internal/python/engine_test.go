package python

import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"
	"time"
)

// ---------------------------------------------------------------------------
// parseOutput tests
// ---------------------------------------------------------------------------

func TestParseOutput_ValidJSON(t *testing.T) {
	e := NewEngine("python", "")
	input := `{"status":"PASS","summary":{"pass_rate":100},"results":[]}`
	result, err := e.parseOutput([]byte(input))
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if result.Status != "PASS" {
		t.Errorf("expected status PASS, got %q", result.Status)
	}
}

func TestParseOutput_LeadingWhitespace(t *testing.T) {
	e := NewEngine("python", "")
	input := "\n  \t" + `{"status":"FAIL","summary":{},"results":[]}`
	result, err := e.parseOutput([]byte(input))
	if err != nil {
		t.Fatalf("expected no error after trimming whitespace, got: %v", err)
	}
	if result.Status != "FAIL" {
		t.Errorf("expected status FAIL, got %q", result.Status)
	}
}

func TestParseOutput_BOM(t *testing.T) {
	e := NewEngine("python", "")
	// UTF-8 BOM prefix
	input := "\xef\xbb\xbf" + `{"status":"PASS","summary":{},"results":[]}`
	result, err := e.parseOutput([]byte(input))
	if err != nil {
		t.Fatalf("expected no error when stripping BOM, got: %v", err)
	}
	if result.Status != "PASS" {
		t.Errorf("expected PASS, got %q", result.Status)
	}
}

func TestParseOutput_EmptyOutput(t *testing.T) {
	e := NewEngine("python", "")
	_, err := e.parseOutput([]byte(""))
	if err == nil {
		t.Fatal("expected error for empty output, got nil")
	}
	if !strings.Contains(err.Error(), "no output") {
		t.Errorf("expected 'no output' in error, got: %v", err)
	}
}

func TestParseOutput_InvalidJSON_SurfacesRaw(t *testing.T) {
	e := NewEngine("python", "")
	garbage := "Traceback (most recent call last):\n  File ...\nValueError: bad config"
	_, err := e.parseOutput([]byte(garbage))
	if err == nil {
		t.Fatal("expected error for invalid JSON, got nil")
	}
	// The raw output must appear in the error so the operator can diagnose it.
	if !strings.Contains(err.Error(), "Traceback") {
		t.Errorf("expected raw output in error message, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// resolveEnginePath tests
// ---------------------------------------------------------------------------

func TestResolveEnginePath_ExplicitPath(t *testing.T) {
	e := NewEngine("python", "/opt/sagescan/engine/main.py")
	got := e.resolveEnginePath()
	if got != "/opt/sagescan/engine/main.py" {
		t.Errorf("expected explicit path, got %q", got)
	}
}

func TestResolveEnginePath_EnvVar(t *testing.T) {
	t.Setenv("SAGESCAN_ENGINE_PATH", "/custom/engine/main.py")
	e := NewEngine("python", "")
	got := e.resolveEnginePath()
	if got != "/custom/engine/main.py" {
		t.Errorf("expected env-var path, got %q", got)
	}
}

// ---------------------------------------------------------------------------
// createTempConfig tests
// ---------------------------------------------------------------------------

func TestCreateTempConfig_RestrictedPermissions(t *testing.T) {
	e := NewEngine("python", "")
	cfg := Config{Version: "1.0"}
	path, err := e.createTempConfig(cfg)
	if err != nil {
		t.Fatalf("createTempConfig failed: %v", err)
	}
	defer os.Remove(path)

	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat failed: %v", err)
	}
	perm := info.Mode().Perm()
	if perm != 0600 {
		t.Errorf("expected file permissions 0600, got %04o", perm)
	}
}

func TestCreateTempConfig_ValidJSON(t *testing.T) {
	e := NewEngine("python", "")
	cfg := Config{
		Version: "1.0",
		Context: "test",
		Source:  map[string]interface{}{"type": "csv", "path": "data.csv"},
	}
	path, err := e.createTempConfig(cfg)
	if err != nil {
		t.Fatalf("createTempConfig failed: %v", err)
	}
	defer os.Remove(path)

	data, _ := os.ReadFile(path)
	var out Config
	if err := json.Unmarshal(data, &out); err != nil {
		t.Errorf("temp file contains invalid JSON: %v", err)
	}
	if out.Version != "1.0" {
		t.Errorf("expected version 1.0, got %q", out.Version)
	}
}

// ---------------------------------------------------------------------------
// RunCommand timeout test (requires no Python — just context cancellation)
// ---------------------------------------------------------------------------

func TestRunCommand_ContextCancel(t *testing.T) {
	e := NewEngine("python", "nonexistent_engine_path_for_test.py")

	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()

	// Sleep to let the context expire, then call — it should return a context error.
	time.Sleep(5 * time.Millisecond)
	_, err := e.RunCommand(ctx, "validate", map[string]interface{}{})
	if err == nil {
		t.Fatal("expected an error when context is already expired, got nil")
	}
}

