"""
Validation pipeline for executing rules on data.

This module provides the main pipeline that loads data, parses rules,
executes validators, and generates reports.
"""

import uuid
import pandas as pd
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from ..validators.registry import registry

logger = logging.getLogger(__name__)

# Hard limits to prevent OOM on large files
_CSV_MAX_BYTES = 2 * 1024 ** 3          # 2 GB
_FAILED_ROWS_CAP = 1_000               # max failed rows stored per check


class ValidationPipeline:
    """
    Main validation pipeline that orchestrates the entire validation process.
    
    This class handles:
    1. Loading data from various sources
    2. Parsing rule configurations
    3. Executing validators
    4. Generating reports
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the validation pipeline.

        Args:
            config: Configuration dictionary containing source and rules
        """
        self.config = config
        self.data = None
        self.validators = []
        self.results = []
        self.run_id = str(uuid.uuid4())

    def load_data(self) -> pd.DataFrame:
        """
        Load data from the configured source.
        
        Supports CSV, PostgreSQL, and Snowflake (future).
        
        Returns:
            pandas DataFrame
        """
        source = self.config.get("source", {})
        source_type = source.get("type", "csv")
        source_path = source.get("path")

        if not source_path:
            raise ValueError("Source path must be specified")

        logger.info(
            "Loading data: run_id=%s source_type=%s source_path=%s",
            self.run_id, source_type, source_path,
        )

        if source_type == "csv":
            self.data = self._load_csv(source_path)
        elif source_type == "parquet":
            self.data = self._load_parquet(source_path)
        else:
            raise NotImplementedError(
                f"Data source type '{source_type}' is not yet implemented. "
                "Supported types: csv, parquet"
            )

        return self.data

    def _load_csv(self, path: str) -> pd.DataFrame:
        """
        Load CSV file with a pre-flight size guard.

        Args:
            path: Path to CSV file

        Returns:
            pandas DataFrame

        Raises:
            ValueError: If file size exceeds _CSV_MAX_BYTES.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        file_size = file_path.stat().st_size
        if file_size > _CSV_MAX_BYTES:
            raise ValueError(
                f"CSV file '{path}' is {file_size / 1024**3:.2f} GB, which exceeds the "
                f"{_CSV_MAX_BYTES / 1024**3:.0f} GB safety limit. Use chunked processing "
                "or a database connector for large files."
            )

        df = pd.read_csv(path)
        logger.info(
            "CSV loaded: run_id=%s path=%s rows=%d columns=%d size_bytes=%d",
            self.run_id, path, len(df), len(df.columns), file_size,
        )
        return df

    def _load_parquet(self, path: str) -> pd.DataFrame:
        """
        Load Parquet file.

        Args:
            path: Path to Parquet file

        Returns:
            pandas DataFrame
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Parquet file not found: {path}")

        try:
            df = pd.read_parquet(path)
        except ImportError:
            raise ImportError(
                "pyarrow or fastparquet is required to read Parquet files. "
                "Install with: pip install pyarrow"
            )

        logger.info(
            "Parquet loaded: run_id=%s path=%s rows=%d columns=%d",
            self.run_id, path, len(df), len(df.columns),
        )
        return df

    def parse_rules(self) -> List[Dict[str, Any]]:
        """
        Parse rule configurations.
        
        Returns:
            List of rule dictionaries
        """
        raw_rules = self.config.get("rules", [])
        
        # Convert raw rules to standardized format
        parsed_rules = []
        for i, raw_rule in enumerate(raw_rules):
            # Handle both Pydantic models and dictionaries
            if hasattr(raw_rule, 'column'):
                column = raw_rule.column
                checks = raw_rule.checks
            else:
                column = raw_rule.get("column", f"column_{i}")
                checks = raw_rule.get("checks", [])
            
            for check in checks:
                # Handle both Pydantic models and dictionaries
                if hasattr(check, 'type'):
                    check_type = check.type
                    parameters = {k: v for k, v in check.__dict__.items() if k != "type"}
                else:
                    check_type = check.get("type")
                    parameters = {k: v for k, v in check.items() if k != "type"}
                
                parsed_rule = {
                    "column": column,
                    "check_type": check_type,
                    "parameters": parameters
                }
                parsed_rules.append(parsed_rule)
        
        return parsed_rules

    def execute_validators(self):
        """Execute all validators on the data."""
        if self.data is None or self.data.empty:
            logger.warning("run_id=%s No data to validate", self.run_id)
            return

        rules = self.parse_rules()
        self.results = []

        for rule in rules:
            column_name = rule["column"]
            check_type = rule["check_type"]
            parameters = rule["parameters"]

            if column_name not in self.data.columns:
                logger.warning(
                    "run_id=%s column=%s check=%s message='column not found, skipping'",
                    self.run_id, column_name, check_type,
                )
                continue

            logger.info(
                "run_id=%s column=%s check=%s status=running",
                self.run_id, column_name, check_type,
            )

            check_config = {
                "column": column_name,
                "type": check_type,
                **parameters,
            }

            try:
                validator = registry.get_validator(check_config)
                series = self.data[column_name]
                result = validator.validate(series)

                # Cap failed_rows / failed_values to avoid OOM on large datasets
                if len(result.failed_rows) > _FAILED_ROWS_CAP:
                    logger.warning(
                        "run_id=%s column=%s check=%s failed_rows=%d truncating_to=%d",
                        self.run_id, column_name, check_type,
                        len(result.failed_rows), _FAILED_ROWS_CAP,
                    )
                    result.failed_rows = result.failed_rows[:_FAILED_ROWS_CAP]
                    result.failed_values = result.failed_values[:_FAILED_ROWS_CAP]

                # Ensure index values are plain Python ints for JSON serialisation
                result.failed_rows = [int(i) for i in result.failed_rows]

                self.results.append(result)
                logger.info(
                    "run_id=%s column=%s check=%s status=%s",
                    self.run_id, column_name, check_type,
                    "PASS" if result.passed else "FAIL",
                )

            except Exception as e:
                logger.exception(
                    "run_id=%s column=%s check=%s status=ERROR",
                    self.run_id, column_name, check_type,
                )
                from ..validators.base import ValidationResult, ValidationResultDetail
                self.results.append(ValidationResultDetail(
                    column=column_name,
                    check_type=check_type,
                    result=ValidationResult.FAIL,
                    passed=False,
                    failed_rows=[],
                    failed_values=[],
                    message=f"Validation error: {str(e)}",
                ))

    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a validation report.
        
        Returns:
            Dictionary containing validation results and statistics
        """
        total_checks = len(self.results)
        passed_checks = sum(1 for r in self.results if r.passed)
        failed_checks = total_checks - passed_checks

        # Build summary
        summary = {
            "total": total_checks,
            "passed": passed_checks,
            "failed": failed_checks,
            "pass_rate": (passed_checks / total_checks * 100) if total_checks > 0 else 0
        }

        # Build results list
        results_list = []
        for r in self.results:
            results_list.append({
                "column": r.column,
                "check": r.check_type,
                "passed": r.passed,
                "failed_rows": r.failed_rows,
                "failed_values": r.failed_values,
                "message": r.message,
                "result": r.result.value
            })

        # Create report
        report = {
            "run_id": self.run_id,
            "status": "PASS" if failed_checks == 0 else "FAIL",
            "summary": summary,
            "results": results_list,
            "timestamp": str(pd.Timestamp.now()),
            "context": self.config.get("context", ""),
            "baseline": self.config.get("baseline", ""),
        }

        return report

    def run(self) -> Dict[str, Any]:
        """
        Run the complete validation pipeline.

        Returns:
            Validation report dictionary
        """
        logger.info("run_id=%s status=starting", self.run_id)

        try:
            self.load_data()
            self.execute_validators()
            report = self.generate_report()
            logger.info(
                "run_id=%s status=complete result=%s total=%d passed=%d failed=%d",
                self.run_id, report["status"],
                report["summary"]["total"],
                report["summary"]["passed"],
                report["summary"]["failed"],
            )
            return report

        except Exception as e:
            logger.exception("run_id=%s status=failed", self.run_id)
            raise

    def to_json(self, indent: int = 2) -> str:
        """
        Convert report to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON string representation of the report
        """
        return json.dumps(self.run(), indent=indent, default=str)