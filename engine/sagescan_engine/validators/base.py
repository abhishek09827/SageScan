"""
Base validator class for data quality checks.

All validators inherit from this base class and implement the validate method.
"""

from typing import Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """Validation result enumeration."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


@dataclass
class ValidationResultDetail:
    """Detailed result of a validation check."""
    column: str
    check_type: str
    result: ValidationResult
    passed: bool
    failed_rows: List[int] = None
    failed_values: List[Any] = None
    message: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.failed_rows is None:
            self.failed_rows = []
        if self.failed_values is None:
            self.failed_values = []
        if self.metadata is None:
            self.metadata = {}


class BaseValidator:
    """
    Base class for all data quality validators.
    
    Validators are responsible for validating a single column against
    a specific check type.
    """

    def __init__(self, check_config: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Initialize the validator.
        
        Args:
            check_config: Configuration for this check
            metadata: Additional metadata for the validator
        """
        self.check_config = check_config
        self.check_type = check_config.get("type", "")
        self.metadata = metadata or {}

    def validate(self, series) -> ValidationResultDetail:
        """
        Validate a pandas Series against the check configuration.
        
        Args:
            series: pandas Series to validate
            
        Returns:
            ValidationResultDetail containing the validation results
        """
        raise NotImplementedError("Subclasses must implement validate method")

    def get_failed_rows(self, series, condition) -> List[int]:
        """
        Get indices of rows that fail a condition.
        
        Args:
            series: pandas Series to check
            condition: Boolean condition to evaluate
            
        Returns:
            List of failed row indices
        """
        return series[~condition].index.tolist()

    def get_failed_values(self, series, condition) -> List[Any]:
        """
        Get values of rows that fail a condition.
        
        Args:
            series: pandas Series to check
            condition: Boolean condition to evaluate
            
        Returns:
            List of failed values
        """
        return series[~condition].tolist()

    def _build_error_message(self, failed_rows: List[int], failed_values: List[Any], 
                           message_template: str = "Found {n} failing rows") -> str:
        """
        Build an error message from failed rows and values.
        
        Args:
            failed_rows: List of failed row indices
            failed_values: List of failed values
            message_template: Template for the error message
            
        Returns:
            Formatted error message
        """
        if not failed_rows:
            return ""

        n = len(failed_rows)
        message = message_template.replace("{n}", str(n))
        
        # Add sample values if available
        if failed_values and len(failed_values) > 0:
            sample_values = str(failed_values[:5])  # Limit to 5 samples
            message += f" Sample values: {sample_values}"
        
        return message

    @property
    def name(self) -> str:
        """Return the name of the validator."""
        return self.check_type

    def get_parameters(self) -> Dict[str, Any]:
        """Return the parameters of this validator."""
        return {k: v for k, v in self.check_config.items() if k != "type"}
