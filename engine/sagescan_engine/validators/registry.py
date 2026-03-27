"""
Validator registry for creating validator instances dynamically.

This module provides a centralized registry for all validators,
making it easy to add new validators without modifying existing code.
"""

from typing import Dict, Type
from .base import BaseValidator
from .implementations import (
    NotNullValidator,
    MinValueValidator,
    MaxValueValidator,
    RangeValidator,
    RegexValidator,
    NullPercentageValidator,
    ZScoreValidator,
    UniqueValidator,
    MinLengthValidator,
    MaxLengthValidator,
    PatternValidator,
    MeanCheckValidator,
    StdCheckValidator,
    AllowedValuesValidator,
)
from .distribution import ZScoreOutlierDetector, KSTestValidator, PSIValidator


class ValidatorRegistry:
    """
    Registry for creating validator instances based on check type.
    
    This singleton class maintains a mapping from check types to validator classes.
    """

    _instance = None
    _validators: Dict[str, Type[BaseValidator]] = {}

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super(ValidatorRegistry, cls).__new__(cls)
            cls._instance._initialize_validators()
        return cls._instance

    def _initialize_validators(self):
        """Initialize the registry with built-in validators."""
        self.register("not_null", NotNullValidator)
        self.register("min_value", MinValueValidator)
        self.register("max_value", MaxValueValidator)
        self.register("range", RangeValidator)
        self.register("regex", RegexValidator)
        self.register("null_percentage", NullPercentageValidator)
        self.register("z_score", ZScoreValidator)
        self.register("unique", UniqueValidator)
        self.register("z_score_outlier", ZScoreOutlierDetector)
        self.register("ks_test", KSTestValidator)
        self.register("psi", PSIValidator)
        # New validators
        self.register("min_length", MinLengthValidator)
        self.register("max_length", MaxLengthValidator)
        self.register("pattern", PatternValidator)       # alias for regex (full-string anchored)
        self.register("mean_check", MeanCheckValidator)
        self.register("std_check", StdCheckValidator)
        self.register("allowed_values", AllowedValuesValidator)

    def register(self, check_type: str, validator_class: Type[BaseValidator]):
        """
        Register a validator class for a check type.
        
        Args:
            check_type: The type of check (e.g., "not_null", "regex")
            validator_class: The validator class to register
        """
        self._validators[check_type] = validator_class

    def get_validator(self, check_config: dict) -> BaseValidator:
        """
        Get a validator instance for the given check configuration.
        
        Args:
            check_config: Configuration dictionary with "type" field
            
        Returns:
            Validator instance
            
        Raises:
            ValueError: If validator type is not registered
        """
        check_type = check_config.get("type")
        
        if check_type not in self._validators:
            available_types = ", ".join(sorted(self._validators.keys()))
            raise ValueError(
                f"Unknown validator type: '{check_type}'. "
                f"Available types: {available_types}"
            )

        validator_class = self._validators[check_type]
        return validator_class(check_config)

    def get_available_types(self) -> list:
        """
        Get list of available validator types.
        
        Returns:
            List of validator type names
        """
        return sorted(self._validators.keys())


# Global registry instance
registry = ValidatorRegistry()