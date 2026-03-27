"""
Unit tests for Pydantic models.

Run with: python -m pytest engine/sagescan_engine/rules/test_models.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pytest
from pydantic import ValidationError

from sagescan_engine.rules.models import SageScanConfig, DataSource, ColumnRuleConfig, ValidationCheck


# ---------------------------------------------------------------------------
# SageScanConfig — issue #6 regression: optional fields must not be silently dropped
# ---------------------------------------------------------------------------

BASE_CONFIG = {
    "version": "1.0",
    "source": {"type": "csv", "path": "data.csv"},
    "rules": [
        {"column": "id", "checks": [{"type": "not_null"}]}
    ],
}


class TestSageScanConfig:
    def test_minimal_valid(self):
        cfg = SageScanConfig(**BASE_CONFIG)
        assert cfg.version == "1.0"
        assert cfg.source.type == "csv"

    def test_context_preserved(self):
        """Regression for #6: context must not be silently dropped."""
        cfg = SageScanConfig(**{**BASE_CONFIG, "context": "production"})
        assert cfg.context == "production"

    def test_baseline_preserved(self):
        """Regression for #6: baseline must not be silently dropped."""
        cfg = SageScanConfig(**{**BASE_CONFIG, "baseline": "baseline.csv"})
        assert cfg.baseline == "baseline.csv"

    def test_llm_fields_preserved(self):
        """Regression for #6: LLM fields must not be silently dropped."""
        cfg = SageScanConfig(**{
            **BASE_CONFIG,
            "llm_api_key": "sk-test",
            "llm_model": "gpt-4",
            "llm_max_tokens": 500,
        })
        assert cfg.llm_api_key == "sk-test"
        assert cfg.llm_model == "gpt-4"
        assert cfg.llm_max_tokens == 500

    def test_output_file_preserved(self):
        """Regression for #6: output_file must not be silently dropped."""
        cfg = SageScanConfig(**{**BASE_CONFIG, "output_file": "out.yaml"})
        assert cfg.output_file == "out.yaml"

    def test_missing_version_raises(self):
        bad = {k: v for k, v in BASE_CONFIG.items() if k != "version"}
        with pytest.raises(ValidationError):
            SageScanConfig(**bad)

    def test_missing_source_raises(self):
        bad = {k: v for k, v in BASE_CONFIG.items() if k != "source"}
        with pytest.raises(ValidationError):
            SageScanConfig(**bad)

    def test_unknown_source_type_raises(self):
        with pytest.raises(ValidationError):
            SageScanConfig(**{**BASE_CONFIG, "source": {"type": "mongodb"}})

    def test_context_defaults_to_none(self):
        cfg = SageScanConfig(**BASE_CONFIG)
        assert cfg.context is None

    def test_multiple_rules(self):
        data = {
            **BASE_CONFIG,
            "rules": [
                {"column": "id", "checks": [{"type": "not_null"}, {"type": "unique"}]},
                {"column": "age", "checks": [{"type": "min_value", "value": 0}]},
            ]
        }
        cfg = SageScanConfig(**data)
        assert len(cfg.rules) == 2
        assert len(cfg.rules[0].checks) == 2


# ---------------------------------------------------------------------------
# DataSource
# ---------------------------------------------------------------------------

class TestDataSource:
    def test_csv_with_path(self):
        ds = DataSource(type="csv", path="/data/file.csv")
        assert ds.path == "/data/file.csv"

    def test_postgres_with_uri(self):
        ds = DataSource(type="postgres", uri="postgresql://localhost/db")
        assert ds.uri == "postgresql://localhost/db"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            DataSource(type="redis")


# ---------------------------------------------------------------------------
# ValidationCheck — extra fields via model_config extra='allow'
# ---------------------------------------------------------------------------

class TestValidationCheck:
    def test_basic_check(self):
        check = ValidationCheck(type="not_null")
        assert check.type == "not_null"

    def test_check_with_value(self):
        check = ValidationCheck(type="min_value", value=18)
        assert check.type == "min_value"
        # extra fields are accessible via model_extra
        assert check.value == 18

    def test_missing_type_raises(self):
        with pytest.raises(ValidationError):
            ValidationCheck()

