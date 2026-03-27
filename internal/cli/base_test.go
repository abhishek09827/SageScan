package cli

import (
	"os"
	"testing"
	"time"
)

func TestValidateConfig_MissingFile(t *testing.T) {
	err := ValidateConfig("/nonexistent/path/config.yaml")
	if err == nil {
		t.Fatal("expected error for missing config file, got nil")
	}
}

func TestValidateConfig_EmptyPath(t *testing.T) {
	err := ValidateConfig("")
	if err == nil {
		t.Fatal("expected error for empty config path, got nil")
	}
}

func TestValidateConfig_ValidFile(t *testing.T) {
	f, err := os.CreateTemp("", "sagescan_test_*.yaml")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	f.WriteString("version: \"1.0\"\n")
	f.Close()
	defer os.Remove(f.Name())

	if err := ValidateConfig(f.Name()); err != nil {
		t.Errorf("expected no error for valid file, got: %v", err)
	}
}

func TestLoadConfig_ValidYAML(t *testing.T) {
	f, err := os.CreateTemp("", "sagescan_test_*.yaml")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	f.WriteString("version: \"1.0\"\ncontext: production\n")
	f.Close()
	defer os.Remove(f.Name())

	v, err := LoadConfig(f.Name())
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}
	if v.GetString("version") != "1.0" {
		t.Errorf("expected version 1.0, got %q", v.GetString("version"))
	}
	if v.GetString("context") != "production" {
		t.Errorf("expected context production, got %q", v.GetString("context"))
	}
}

func TestLoadConfig_InvalidYAML(t *testing.T) {
	f, err := os.CreateTemp("", "sagescan_test_*.yaml")
	if err != nil {
		t.Fatalf("failed to create temp file: %v", err)
	}
	f.WriteString(":\tinvalid: yaml: [\n")
	f.Close()
	defer os.Remove(f.Name())

	_, err = LoadConfig(f.Name())
	if err == nil {
		t.Fatal("expected error for invalid YAML, got nil")
	}
}

func TestBaseCommand_DefaultTimeout(t *testing.T) {
	bc := NewBaseCommand("test", "short", "long")
	if bc.GetTimeout() != 5*time.Minute {
		t.Errorf("expected default timeout of 5m, got %v", bc.GetTimeout())
	}
}

func TestBaseCommand_GetContext(t *testing.T) {
	bc := NewBaseCommand("test", "short", "long")
	if bc.GetContext() != "" {
		t.Errorf("expected empty context by default, got %q", bc.GetContext())
	}
}


