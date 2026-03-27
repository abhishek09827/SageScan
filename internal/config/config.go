// Package config provides configuration loading utilities.
// All loading uses a local viper.Viper instance to avoid mutating the global
// singleton, which is thread-unsafe and bleeds state between commands/tests.
// Callers should prefer internal/cli.LoadConfig; this package exists for any
// non-CLI code that needs direct config access.
package config

import (
	"fmt"
	"os"

	"github.com/spf13/viper"
)

// RequestPayload represents the final JSON sent to the Python engine
type RequestPayload struct {
	Command string      `json:"command"`
	Config  interface{} `json:"config"`
}

// LoadConfig reads the YAML config file and returns it as a generic map.
// It uses a local viper instance (not the global singleton) to avoid state
// pollution across concurrent calls or tests.
// Full schema validation is deferred to the Python side (Pydantic) for DRYness.
func LoadConfig(path string) (interface{}, error) {
	if _, err := os.Stat(path); os.IsNotExist(err) {
		return nil, fmt.Errorf("config file %s does not exist", path)
	}

	v := viper.New()
	v.SetConfigFile(path)
	if err := v.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("error parsing yaml: %w", err)
	}

	return v.AllSettings(), nil
}
