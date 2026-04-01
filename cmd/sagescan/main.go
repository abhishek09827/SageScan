package main

import (
	"fmt"
	"os"

	"github.com/sagescan/sagescan/internal/cli"
)

func main() {
	// Debug output for environment variable
	if os.Getenv("SAGESCAN_VERBOSE") == "true" {
		fmt.Fprintf(os.Stderr, "Main: SAGESCAN_PYTHON=%q\n", os.Getenv("SAGESCAN_PYTHON"))
	}

	if err := cli.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
