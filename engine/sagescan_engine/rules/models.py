from typing import List, Literal, Optional, Any
from pydantic import BaseModel, ConfigDict


class DataSource(BaseModel):
    type: Literal["csv", "parquet", "postgres", "snowflake"]
    path: Optional[str] = None   # For CSV and Parquet
    uri: Optional[str] = None    # For databases (postgres, snowflake)


class ValidationCheck(BaseModel):
    # Flexible check definition, e.g., type="not_null", type="min_value", value=18
    model_config = ConfigDict(extra='allow')
    type: str


class ColumnRuleConfig(BaseModel):
    column: str
    checks: List[ValidationCheck]


class SageScanConfig(BaseModel):
    """
    Top-level configuration model.

    All optional fields must be declared here; Pydantic v2 silently drops keys
    not present on the model (extra='ignore'), so every optional runtime field
    needs an explicit declaration with a default.
    """
    model_config = ConfigDict(extra='ignore')

    version: str
    source: DataSource
    rules: List[ColumnRuleConfig]

    # Optional runtime fields
    context: Optional[str] = None
    baseline: Optional[str] = None
    output_file: Optional[str] = None

    # LLM integration fields
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    llm_max_tokens: Optional[int] = None
    llm_base_url: Optional[str] = None
    llm_temperature: Optional[float] = None

