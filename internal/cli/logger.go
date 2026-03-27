package cli

import (
	"log/slog"
	"os"
)

// InitLogger configures the global slog logger.
// In verbose mode (SAGESCAN_VERBOSE=true) it emits DEBUG-level JSON to stderr.
// Otherwise only WARN+ is emitted as text to stderr so normal stdout stays clean.
func InitLogger() {
	var handler slog.Handler
	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		handler = slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{
			Level: slog.LevelDebug,
		})
	} else {
		handler = slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
			Level: slog.LevelWarn,
		})
	}
	slog.SetDefault(slog.New(handler))
}

