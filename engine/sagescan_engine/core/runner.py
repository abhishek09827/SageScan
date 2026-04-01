"""
Validation runner for executing rules on data.

This module provides the main entry point for validation.
"""

import logging
import logging
import os
import time

logger = logging.getLogger(__name__)

from sagescan_engine.rules.models import SageScanConfig


def run_validation(config: dict) -> dict:
    """
    Parses the configuration and dispatches the execution to the appropriate data connector and rules.
    
    Args:
        config: Configuration dictionary containing source and rules
        
    Returns:
        List of validation result dictionaries
        
    Raises:
        ValueError: If configuration is invalid or validation fails
    """
    logger.info("runner=validation status=starting")

    # Validate the raw dictionary configuration with Pydantic
    try:
        validated_config = SageScanConfig(**config)
    except Exception as e:
        logger.exception("runner=validation status=config_invalid")
        raise ValueError(f"Configuration validation failed: {e}")

    source = validated_config.source
    rules_config = validated_config.rules
    
    # Import here to avoid circular dependency
    from sagescan_engine.core.pipeline import ValidationPipeline

    # Use the ValidationPipeline for actual validation.
    # Read optional fields from the validated Pydantic object so they are
    # not silently dropped by Pydantic's extra='ignore' (see models.py fix).
    pipeline = ValidationPipeline({
        "source": {
            "type": source.type,
            "path": source.path
        },
        "rules": rules_config,
        "context": validated_config.context or "",
        "baseline": validated_config.baseline or "",
    })

    # Run the pipeline and get results
    try:
        report = pipeline.run()

        # Convert results to expected format for backward compatibility
        results = []
        for result in report.get("results", []):
            results.append({
                "column": result.get("column", ""),
                "check": result.get("check", ""),
                "check_type": result.get("check", ""),   # alias: same value, consistent key
                "passed": result.get("passed", False),
                "failed_rows": result.get("failed_rows", []),
                "message": result.get("message", "")
            })

        report["results"] = results
        logger.info(
            "runner=validation status=complete run_id=%s result=%s",
            report.get("run_id", "unknown"), report.get("status"),
        )
        return report

    except Exception as e:
        logger.exception("runner=validation status=failed")
        raise

def run_profile(config: dict) -> dict:
    from sagescan_engine.core.pipeline import ValidationPipeline
    from sagescan_engine.llm.rule_generator import build_statistics_from_dataframe
    import logging
    
    logger.info("runner=profile status=starting")
    pipeline = ValidationPipeline(config)

    try:
        df = pipeline.load_data()
        stats = build_statistics_from_dataframe(df)

        stats_dict = [
            {k: v for k, v in stat.__dict__.items()}
            for stat in stats
        ]

        logger.info("runner=profile status=complete columns=%d", len(stats))
        return {
            "status": "PASS",
            "summary": {"message": f"Successfully profiled {len(stats)} columns."},
            "results": stats_dict
        }
    except Exception as e:
        logger.exception("runner=profile status=failed")
        raise

def run_generate_rules(config: dict) -> dict:
    from sagescan_engine.core.pipeline import ValidationPipeline
    from sagescan_engine.llm.rule_generator import build_statistics_from_dataframe, LLMRuleGenerator
    import logging
    import yaml
    
    logger.info("runner=generate_rules status=starting")
    pipeline = ValidationPipeline(config)
    
    try:
        df = pipeline.load_data()
        stats = build_statistics_from_dataframe(df)
        
        schema = {col: {"type": str(df[col].dtype)} for col in df.columns}
        
        # Issue #7: never fall back to "dummy" – fail fast with a clear message.
        api_key = config.get("llm_api_key") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {
                "status": "FAIL",
                "summary": {
                    "message": (
                        "LLM API key is required for rule generation. "
                        "Set the OPENAI_API_KEY environment variable or pass "
                        "llm_api_key in your config."
                    )
                },
                "results": []
            }
        model = config.get("llm_model", "gpt-4")
        base_url = config.get("llm_base_url")
        temperature = config.get("llm_temperature", 0.3)
        
        generator = LLMRuleGenerator(api_key=api_key, model=model, base_url=base_url, temperature=temperature)
        
        try:
            full_config = generator.generate_full_config(
                schema=schema,
                statistics=stats,
                business_context=config.get("context"),
                source_type=config.get("source", {}).get("type", "csv"),
                source_path=config.get("source", {}).get("path")
            )
        except Exception as api_e:
            logger.exception("runner=generate_rules status=llm_failed")
            return {
                "status": "FAIL",
                "summary": {"message": f"LLM Generation failed: {api_e}. Ensure OPENAI_API_KEY is set."},
                "results": []
            }

        output_file = config.get("output_file")
        if output_file:
            with open(output_file, 'w') as f:
                yaml.dump(full_config, f, sort_keys=False)

        rule_count = len(full_config.get("rules", []))
        logger.info("runner=generate_rules status=complete rules_generated=%d", rule_count)
        return {
            "status": "PASS",
            "summary": {"message": f"Successfully generated {rule_count} rules."},
            "results": [{"config": full_config}]
        }
    except Exception as e:
        logger.exception("runner=generate_rules status=failed")
        raise

def run_check_llm(config: dict) -> dict:
    """
    Verify LLM connectivity by sending a minimal test message.

    Returns a structured result with model name, response text, token usage,
    and latency so the Go CLI can print a clean summary.
    """
    api_key = config.get("llm_api_key") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {
            "status": "FAIL",
            "summary": {
                "message": (
                    "No API key found. Set OPENAI_API_KEY environment variable "
                    "or pass llm_api_key in your config."
                )
            },
            "results": [],
        }

    model = config.get("llm_model", "gpt-4o")

    try:
        import openai
    except ImportError:
        return {
            "status": "FAIL",
            "summary": {
                "message": (
                    "openai package is not installed. "
                    "Run: engine/.venv/bin/pip install openai"
                )
            },
            "results": [],
        }

    client_kwargs = {"api_key": api_key}
    base_url = config.get("llm_base_url")
    if base_url:
        client_kwargs["base_url"] = base_url
    client = openai.OpenAI(**client_kwargs)
    TEST_PROMPT = "Reply with exactly the text: SageScan LLM OK"

    logger.info("runner=check_llm model=%s status=connecting", model)
    t0 = time.monotonic()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": TEST_PROMPT}],
            max_tokens=20,
            temperature=config.get("llm_temperature", 0.0),
        )
        latency_ms = round((time.monotonic() - t0) * 1000)
        reply = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0

        logger.info(
            "runner=check_llm model=%s status=ok latency_ms=%d tokens=%d",
            model, latency_ms, tokens,
        )
        return {
            "status": "PASS",
            "summary": {
                "message":    reply,
                "model":      model,
                "tokens_used": tokens,
                "latency_ms": latency_ms,
            },
            "results": [],
        }

    except Exception as exc:
        latency_ms = round((time.monotonic() - t0) * 1000)
        logger.error("runner=check_llm model=%s status=error error=%s", model, exc)
        return {
            "status": "ERROR",
            "error": str(exc),
            "summary": {
                "message":    str(exc),
                "model":      model,
                "latency_ms": latency_ms,
            },
            "results": [],
        }

def run_report(config: dict) -> dict:
    """
    Generate a report from validation results.
    
    Args:
        config: Configuration dictionary containing source and rules
        
    Returns:
        Dictionary containing report data
    """
    from sagescan_engine.core.report import ReportGenerator, ValidationSummary
    from datetime import datetime
    import logging
    
    logger.info("runner=report status=starting")
    try:
        val_report = run_validation(config)

        summary = ValidationSummary(
            status=val_report.get("status", "FAIL"),
            context=config.get("context", ""),
            total_columns=0,
            total_checks=val_report.get("summary", {}).get("total", 0),
            passed_checks=val_report.get("summary", {}).get("passed", 0),
            failed_checks=val_report.get("summary", {}).get("failed", 0),
            pass_rate=val_report.get("summary", {}).get("pass_rate", 0.0),
            duration_seconds=0.0,
            start_time=datetime.now(),
            end_time=datetime.now()
        )
        generator = ReportGenerator(summary)
        cli_report = generator.generate_cli()

        logger.info("runner=report status=complete")
        return {
            "status": "PASS",
            "summary": {"message": f"Report generated:\n\n{cli_report}"},
            "results": []
        }
    except Exception as e:
        logger.exception("runner=report status=failed")
        raise
