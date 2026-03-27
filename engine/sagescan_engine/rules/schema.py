"""
Schema definition for SageScan YAML-based DSL.

This module defines the structure and validation rules for the DSL.
"""

from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class CheckType(str, Enum):
    """Available validation check types."""
    NOT_NULL = "not_null"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    RANGE = "range"
    REGEX = "regex"
    NULL_PERCENTAGE = "null_percentage"
    Z_SCORE = "z_score"
    Z_SCORE_OUTLIER = "z_score_outlier"
    UNIQUE = "unique"
    KS_TEST = "ks_test"
    PSI = "psi"


class CheckConfig(BaseModel):
    """Configuration for a single validation check."""
    type: CheckType = Field(..., description="Type of validation check")
    value: Optional[Any] = Field(None, description="Required value for the check")
    upper_threshold: Optional[float] = Field(None, description="Upper threshold for z_score")
    lower_threshold: Optional[float] = Field(None, description="Lower threshold for z_score")
    warning_threshold: Optional[float] = Field(None, description="Warning threshold for PSI")
    drift_threshold: Optional[float] = Field(None, description="Drift threshold for PSI")
    alpha: Optional[float] = Field(None, description="Significance level for KS test")
    reference_type: Optional[str] = Field(None, description="Type of reference data (file/csv) for distribution checks")
    reference_path: Optional[str] = Field(None, description="Path to reference data")
    max_percentage: Optional[float] = Field(None, description="Maximum allowed percentage")

    # Issue #22: use Pydantic v2 @field_validator instead of deprecated @validator.
    # Issue #16: UNIQUE is removed from the list of checks that require 'value' —
    #            the UniqueValidator takes no parameters.

    @field_validator('value', mode='before')
    @classmethod
    def validate_value_for_type(cls, v, info):
        """Validate that required fields are provided based on check type."""
        check_type = info.data.get('type')

        if check_type == CheckType.NOT_NULL and v is not None:
            raise ValueError("not_null check does not require a 'value' parameter")

        # Issue #16: UNIQUE intentionally omitted — it takes no value parameter.
        if check_type in [CheckType.MIN_VALUE, CheckType.MAX_VALUE] and v is None:
            raise ValueError(f"{check_type.value} check requires a 'value' parameter")

        if check_type == CheckType.Z_SCORE and v is None:
            raise ValueError("z_score check requires a 'value' (threshold) parameter")

        if check_type == CheckType.NULL_PERCENTAGE and v is None:
            raise ValueError("null_percentage check requires a 'value' parameter (percentage 0–100)")

        return v

    @field_validator('upper_threshold', 'lower_threshold', 'alpha', mode='before')
    @classmethod
    def validate_threshold(cls, v, info):
        """Validate threshold parameters are within sensible bounds."""
        check_type = info.data.get('type')

        if check_type == CheckType.Z_SCORE:
            if v is not None and not (-10 <= v <= 10):
                raise ValueError("z_score threshold should be between -10 and 10")

        if check_type == CheckType.PSI:
            if v is not None and not (0 <= v <= 1):
                raise ValueError("PSI threshold should be between 0 and 1")

        if check_type == CheckType.KS_TEST and v is not None:
            if not (0.01 <= v <= 0.1):
                raise ValueError("KS test alpha should be between 0.01 and 0.1")

        return v


class ColumnRules(BaseModel):
    """Validation rules for a single column."""
    column: str = Field(..., description="Column name")
    checks: List[CheckConfig] = Field(..., description="List of validation checks")
    description: Optional[str] = Field(None, description="Optional description of the column's purpose")
    tags: List[str] = Field(default_factory=list, description="Optional tags for organization")

    @field_validator('column', mode='before')
    @classmethod
    def validate_column_name(cls, v):
        """Validate column name is not empty."""
        if not v or not str(v).strip():
            raise ValueError("Column name cannot be empty")
        return str(v).strip()


class DataSource(BaseModel):
    """Configuration for data source."""
    type: str = Field(..., description="Type of data source (csv, database, etc.)")
    path: Optional[str] = Field(None, description="Path to data file")
    connection_string: Optional[str] = Field(None, description="Connection string for database")
    query: Optional[str] = Field(None, description="SQL query for database")
    sample_size: Optional[int] = Field(default=10000, description="Maximum rows to sample for large datasets")


class ValidationConfig(BaseModel):
    """Complete validation configuration."""
    version: str = Field(..., description="Configuration version")
    source: DataSource = Field(..., description="Data source configuration")
    rules: List[ColumnRules] = Field(..., description="Validation rules")
    context: Optional[str] = Field(None, description="Optional context for the validation")
    baseline: Optional[str] = Field(None, description="Optional baseline/reference data path")
    output_format: str = Field(default="json", description="Output format (json, yaml)")
    llm_api_key: Optional[str] = Field(None, description="Optional LLM API key for explanations")
    llm_model: Optional[str] = Field(default="gpt-4", description="Default LLM model for explanations")
    llm_max_tokens: Optional[int] = Field(default=1000, description="Max tokens for LLM responses")



class DSLValidator:
    """Validates YAML-based DSL files."""
    
    @staticmethod
    def validate_yaml_file(yaml_path: str) -> ValidationConfig:
        """
        Validate a YAML file containing SageScan DSL.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            Parsed ValidationConfig object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            ValueError: If schema validation fails
        """
        try:
            with open(yaml_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML: {e}")
        
        return DSLValidator.validate_yaml_data(data)
    
    @staticmethod
    def validate_yaml_data(data: Any) -> ValidationConfig:
        """
        Validate YAML data directly.
        
        Args:
            data: Parsed YAML data
            
        Returns:
            Parsed ValidationConfig object
            
        Raises:
            ValueError: If schema validation fails
        """
        try:
            config = ValidationConfig(**data)
            DSLValidator._validate_rules(config)
            return config
        except Exception as e:
            raise ValueError(f"Schema validation failed: {e}")
    
    @staticmethod
    def _validate_rules(config: ValidationConfig):
        """Validate rules for completeness and consistency."""
        # Check for duplicate column names
        column_names = [rule.column for rule in config.rules]
        if len(column_names) != len(set(column_names)):
            duplicates = [name for name in column_names if column_names.count(name) > 1]
            raise ValueError(f"Duplicate column names found: {set(duplicates)}")
        
        # Check for empty check lists
        for rule in config.rules:
            if not rule.checks:
                raise ValueError(f"Column '{rule.column}' has no validation checks defined")
            
            # Check for duplicate check types in same column
            check_types = [check.type.value for check in rule.checks]
            if len(check_types) != len(set(check_types)):
                raise ValueError(f"Duplicate check types found in column '{rule.column}'")
    
    @staticmethod
    def validate_check_config(check: CheckConfig) -> bool:
        """
        Validate a single check configuration.
        
        Args:
            check: CheckConfig object
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        try:
            CheckConfig(**check.dict())
            return True
        except Exception as e:
            raise ValueError(f"Invalid check configuration: {e}")


def validate_dsl_file(yaml_path: str) -> bool:
    """
    Convenience function to validate a YAML DSL file.
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        True if valid
        
    Raises:
        Any exceptions from DSLValidator
    """
    DSLValidator.validate_yaml_file(yaml_path)
    return True


def get_available_check_types() -> List[str]:
    """Get list of all available check types."""
    return [ct.value for ct in CheckType]


def get_check_type_description(check_type: str) -> str:
    """Get description for a check type."""
    descriptions = {
        CheckType.NOT_NULL.value: "Check for null/NaN values",
        CheckType.MIN_VALUE.value: "Validate minimum value",
        CheckType.MAX_VALUE.value: "Validate maximum value",
        CheckType.RANGE.value: "Validate value is within a range",
        CheckType.REGEX.value: "Validate pattern matching",
        CheckType.NULL_PERCENTAGE.value: "Enforce acceptable null ratios",
        CheckType.Z_SCORE.value: "Statistical anomaly detection",
        CheckType.Z_SCORE_OUTLIER.value: "Outlier detection using z-scores",
        CheckType.UNIQUE.value: "Check for duplicate values",
        CheckType.KS_TEST.value: "Distribution comparison using KS test",
        CheckType.PSI.value: "Population Stability Index for drift detection",
    }
    return descriptions.get(check_type, "No description available")