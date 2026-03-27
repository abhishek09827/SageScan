"""
Python CLI entrypoint for SageScan validation engine.

This module provides a simple command-line interface that can be called
from the Go CLI using subprocess.
"""

import sys
import os
import json
import logging
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Route ALL logging to stderr so it never contaminates the JSON on stdout.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s",
)

# Allow SAGESCAN_LOG_LEVEL to override default level
_log_level = os.environ.get("SAGESCAN_LOG_LEVEL", "WARNING").upper()
logging.getLogger().setLevel(getattr(logging, _log_level, logging.WARNING))

# Add engine directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sagescan_engine.core.runner import (
    run_validation,
    run_profile,
    run_generate_rules,
    run_report,
    run_check_llm,
)

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Command routing table  (command name → function)
# ---------------------------------------------------------------------------
_COMMANDS = {
    "validate":       run_validation,
    "report":         run_report,
    "profile":        run_profile,
    "generate_rules": run_generate_rules,
    "generate-rules": run_generate_rules,   # hyphen variant
    "check_llm":      run_check_llm,
    "check-llm":      run_check_llm,        # hyphen variant
}


def _load_config_from_args(args) -> tuple:
    """
    Load the config dict from --config, --config-json, or stdin.

    Returns:
        (config_dict, config_file_dir)
    """
    config_file_dir = os.getcwd()

    if args.config_json:
        return json.loads(args.config_json), config_file_dir

    if args.config:
        with open(args.config, "r") as f:
            config = json.load(f)
        config_file_dir = os.path.dirname(os.path.abspath(args.config))
        return config, config_file_dir

    # Try stdin
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            return json.loads(raw), config_file_dir

    raise ValueError(
        "No configuration provided. "
        "Use --config, --config-json, or supply JSON via stdin."
    )


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="SageScan Data Quality Validation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (JSON format)",
        required=False,
    )
    parser.add_argument(
        "--config-json",
        type=str,
        help="Configuration as JSON string (overrides --config)",
        required=False,
    )
    parser.add_argument(
        "--output",
        type=str,
        choices=["json", "yaml", "both"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--no-explanations",
        action="store_true",
        help="Skip AI explanation generation",
    )

    args = parser.parse_args()

    try:
        # -----------------------------------------------------------------------
        # Load configuration
        # -----------------------------------------------------------------------
        config, config_file_dir = _load_config_from_args(args)

        # -----------------------------------------------------------------------
        # Unpack Go orchestrator envelope if present
        # -----------------------------------------------------------------------
        command_name = "validate"
        if isinstance(config, dict) and "command" in config and "config" in config:
            command_name = config["command"]
            config = config["config"]

        # -----------------------------------------------------------------------
        # Resolve relative source path to config file's own directory
        # -----------------------------------------------------------------------
        if (
            isinstance(config, dict)
            and "source" in config
            and isinstance(config["source"], dict)
            and config["source"].get("path")
            and not os.path.isabs(config["source"]["path"])
        ):
            config["source"]["path"] = os.path.normpath(
                os.path.join(config_file_dir, config["source"]["path"])
            )

        # -----------------------------------------------------------------------
        # Dispatch to the right runner
        # -----------------------------------------------------------------------
        runner_fn = _COMMANDS.get(command_name)
        if runner_fn is None:
            # Unknown command — fall back to validate with a warning
            _log.warning(
                "Unknown command %r — falling back to 'validate'", command_name
            )
            runner_fn = run_validation

        report = runner_fn(config)

        # -----------------------------------------------------------------------
        # Generate AI explanations (optional, only on validate)
        # -----------------------------------------------------------------------
        if (
            not args.no_explanations
            and command_name in ("validate",)
            and config.get("rules")
            and config.get("llm_api_key")
        ):
            try:
                from sagescan_engine.llm.explanation_generator import (
                    ExplanationGenerator,
                    create_column_contexts,
                    parse_failed_checks_from_report,
                    format_validation_report_with_explanations,
                )

                df = None
                source_path = config.get("source", {}).get("path")
                if source_path and os.path.exists(source_path):
                    try:
                        import pandas as pd
                        src_type = config.get("source", {}).get("type", "csv").lower()
                        if src_type == "parquet":
                            df = pd.read_parquet(source_path)
                        else:
                            df = pd.read_csv(source_path)
                    except Exception:
                        pass

                if df is not None:
                    column_contexts = create_column_contexts(df)
                    failed_checks = parse_failed_checks_from_report(report)
                    explanations = {}

                    if failed_checks:
                        generator = ExplanationGenerator(
                            api_key=config.get("llm_api_key", ""),
                            model=config.get("llm_model", "gpt-4o"),
                            max_tokens=config.get("llm_max_tokens", 1000),
                        )
                        explanations = generator.explain_validation_report(
                            failed_checks, column_contexts
                        )

                    report = format_validation_report_with_explanations(
                        report, explanations
                    )
            except Exception as e:
                _log.warning("Could not generate explanations: %s", e)

        # -----------------------------------------------------------------------
        # Output results — ONLY to stdout so Go can parse it
        # -----------------------------------------------------------------------
        if args.output in ("json", "both"):
            print(json.dumps(report, indent=2, default=str))

        if args.output in ("yaml", "both"):
            try:
                import yaml
                # yaml output to stdout only when output='yaml', otherwise stderr
                # to avoid corrupting Go's JSON parsing.
                dest = sys.stdout if args.output == "yaml" else sys.stderr
                print(yaml.dump(report, default_flow_style=False), file=dest)
            except ImportError:
                _log.warning("PyYAML not installed, skipping YAML output")

        # Exit 1 on FAIL so CI pipelines can detect failures without parsing JSON.
        sys.exit(1 if report.get("status") == "FAIL" else 0)

    except FileNotFoundError as e:
        print(json.dumps({"status": "ERROR", "error": "File not found", "message": str(e)}, indent=2))
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "ERROR", "error": "Invalid JSON", "message": str(e)}, indent=2))
        sys.exit(3)
    except ValueError as e:
        print(json.dumps({"status": "ERROR", "error": "Validation error", "message": str(e)}, indent=2))
        sys.exit(4)
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({"status": "ERROR", "error": str(e), "type": type(e).__name__}, indent=2))
        sys.exit(5)


if __name__ == "__main__":
    main()