"""
LLM-powered rule generator for SageScan.

This module provides a deterministic prompt structure for generating
data quality validation rules using large language models.
"""

import io
import re as _re
import time
import yaml
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ColumnStatistics:
    """Statistics for a single column."""
    name: str
    dtype: str
    missing_ratio: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    unique_count: int = 0
    top_values: List[Any] = None
    quartiles: Dict[str, float] = None

    def __post_init__(self):
        if self.top_values is None:
            self.top_values = []
        if self.quartiles is None:
            self.quartiles = {}


class LLMRuleGenerator:
    """
    Generator for creating validation rules using LLMs.
    
    Provides a deterministic prompt structure that ensures consistent
    and production-ready rule generation.
    """

    def __init__(self, api_key: str, model: str = "gpt-4", max_tokens: int = 2000, base_url: Optional[str] = None, temperature: float = 0.3):
        """
        Initialize the rule generator.
        
        Args:
            api_key: API key for the LLM provider
            model: Model name to use
            max_tokens: Maximum tokens for response
            base_url: Custom API base URL
            temperature: LLM generation temperature
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.base_url = base_url
        self.temperature = temperature

    # Column names whose top-values must never be sent to the LLM.
    _PII_COLUMN_PATTERNS = _re.compile(
        r"(email|phone|ssn|social.?security|credit.?card|passport|address|dob|birth|"
        r"name|password|token|secret|api.?key|ip.?addr)",
        _re.IGNORECASE,
    )
    # Maximum columns to include in a single prompt to avoid context-window overflow.
    _MAX_PROMPT_COLUMNS = 80

    def _mask_top_values(self, col_name: str, top_values: List[Any]) -> str:
        """Return a safe string for top_values, redacting PII columns."""
        if self._PII_COLUMN_PATTERNS.search(col_name):
            return "<redacted – potential PII column>"
        return ", ".join(map(str, top_values[:5]))

    def _sanitise_text(self, text: str) -> str:
        """Strip markdown-header sequences from user-supplied free text to prevent prompt injection."""
        # Remove lines that look like prompt-injection attempts (## headings, triple backticks)
        sanitised = _re.sub(r"^(#{1,6}|```)", "", text, flags=_re.MULTILINE)
        # Truncate to 2000 chars
        return sanitised[:2000]

    def _build_prompt(
        self,
        schema: Dict[str, Any],
        statistics: List[ColumnStatistics],
        business_context: Optional[str] = None,
        existing_rules: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build a deterministic prompt for rule generation.

        Args:
            schema: Dataset schema with column types and descriptions
            statistics: Column statistics
            business_context: Optional business context for rules
            existing_rules: Existing rules to avoid duplication

        Returns:
            Formatted prompt string
        """
        buf = io.StringIO()

        buf.write("""# SageScan Rule Generation Task

You are an expert data quality engineer. Generate production-ready validation rules
for a dataset based on the provided schema and statistics.

## Output Format
Return a valid YAML configuration for SageScan with a single top-level "rules" key.

## Requirements
- Avoid generic rules (e.g., "not_null" for all columns)
- Include statistical constraints where meaningful (range checks based on quartiles)
- Focus on data quality issues common in production
- Use appropriate check types for each column
- Include business context where specified

## Available Check Types
- not_null: Check for null values (use only if column must have values)
- unique: Check for duplicate values (use for IDs, primary keys)
- min_value/max_value: Range constraints (use with statistical quartiles)
- range: Both min and max constraints
- regex: Pattern validation (use for structured data like emails, phone numbers)
- null_percentage: Enforce acceptable null ratios
- z_score: Anomaly detection (use for detecting outliers)
- psi: Population Stability Index (use for drift detection)
- ks_test: Distribution comparison (use for comparing to reference)

## Example Structure
```yaml
rules:
  - column: "age"
    checks:
      - type: "not_null"
      - type: "min_value"
        value: 0
      - type: "z_score"
        value: 3.5
```
""")

        # Cap columns to avoid context-window overflow
        schema_items = list(schema.items())
        stats_list = list(statistics)
        if len(schema_items) > self._MAX_PROMPT_COLUMNS:
            logger.warning(
                "Schema has %d columns; truncating prompt to first %d to avoid "
                "context-window overflow.",
                len(schema_items), self._MAX_PROMPT_COLUMNS,
            )
            schema_items = schema_items[:self._MAX_PROMPT_COLUMNS]
            stats_list = stats_list[:self._MAX_PROMPT_COLUMNS]

        # Schema section
        buf.write("\n## Dataset Schema\n")
        for col_name, col_info in schema_items:
            buf.write(f"- {col_name}: {col_info.get('type', 'unknown')}")
            if col_info.get("description"):
                buf.write(f" - {col_info['description']}")
            buf.write("\n")

        # Statistics section
        buf.write("\n## Column Statistics\n")
        for stat in stats_list:
            buf.write(f"\n### {stat.name} ({stat.dtype})\n")
            buf.write(f"- Missing Ratio: {stat.missing_ratio:.2%}\n")
            if stat.min_value is not None:
                buf.write(f"- Min: {stat.min_value}\n")
            if stat.max_value is not None:
                buf.write(f"- Max: {stat.max_value}\n")
            if stat.mean is not None:
                buf.write(f"- Mean: {stat.mean:.2f}\n")
            if stat.std is not None:
                buf.write(f"- Std: {stat.std:.2f}\n")
            if stat.unique_count > 0:
                buf.write(f"- Unique Values: {stat.unique_count}\n")
            if stat.top_values:
                masked = self._mask_top_values(stat.name, stat.top_values)
                buf.write(f"- Top Values: {masked}\n")
            if stat.quartiles:
                buf.write(f"- Quartiles: {stat.quartiles}\n")

        # Business context (sanitised)
        if business_context:
            buf.write(f"\n## Business Context\n{self._sanitise_text(business_context)}\n")

        # Existing rules
        if existing_rules:
            buf.write("\n## Existing Rules (Avoid Duplication)\n")
            buf.write(yaml.dump(existing_rules, default_flow_style=False, sort_keys=False))

        buf.write("\n## Your Task\nGenerate validation rules for this dataset.\n")
        buf.write("Return ONLY the YAML configuration, no additional text.\n")

        return buf.getvalue()

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse the LLM response into validation rules.

        Args:
            response_text: Text response from LLM

        Returns:
            List of validation rules

        Raises:
            ValueError: If the response cannot be parsed into a non-empty rule list.
        """
        # Extract YAML content from code fences if present
        if "```yaml" in response_text:
            yaml_start = response_text.find("```yaml") + 7
            yaml_end = response_text.find("```", yaml_start)
            yaml_content = response_text[yaml_start:yaml_end].strip()
        elif "```" in response_text:
            yaml_start = response_text.find("```") + 3
            yaml_end = response_text.find("```", yaml_start)
            yaml_content = response_text[yaml_start:yaml_end].strip()
        else:
            yaml_content = response_text.strip()

        try:
            # Use safe_load_all to handle multi-document YAML (--- separators)
            documents = list(yaml.safe_load_all(yaml_content))
        except yaml.YAMLError as e:
            # Log the raw response at ERROR level so it's visible in production
            logger.error("Failed to parse YAML from LLM response: %s", e)
            logger.error("Raw LLM response:\n%s", response_text)
            raise ValueError(f"LLM returned unparseable YAML: {e}") from e

        rules: List[Dict[str, Any]] = []
        for doc in documents:
            if doc is None:
                continue
            if isinstance(doc, dict):
                rules.extend(doc.get("rules", []))
            elif isinstance(doc, list):
                rules.extend(doc)
            else:
                logger.warning("Unexpected YAML document type from LLM: %s", type(doc))

        if not rules:
            logger.error("LLM returned a parseable YAML response but it contained no rules.")
            logger.error("Raw LLM response:\n%s", response_text)
            raise ValueError(
                "LLM response parsed successfully but contained zero rules. "
                "Check the raw response logged above."
            )

        return rules

    # Maximum retries for transient OpenAI errors (429, 500, 503)
    _MAX_RETRIES = 3
    _RETRY_BASE_DELAY = 2.0  # seconds; doubled each attempt

    def _call_llm(self, prompt: str) -> str:
        """
        Call the LLM API with retry logic for transient failures.

        Retries up to _MAX_RETRIES times on RateLimitError and APIError,
        using exponential back-off.  Logs token usage and latency on every
        successful call.

        Args:
            prompt: Prompt to send to LLM

        Returns:
            Response text from LLM

        Raises:
            ImportError: If openai package is not installed.
            Exception: After all retries are exhausted.
        """
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI package is required. Install with: pip install openai")

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = openai.OpenAI(**client_kwargs)
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._MAX_RETRIES + 1):
            t0 = time.monotonic()
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a data quality validation expert."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    response_format={"type": "text"},
                )
                latency_ms = (time.monotonic() - t0) * 1000
                usage = response.usage
                logger.info(
                    "LLM call succeeded: model=%s latency_ms=%.0f "
                    "prompt_tokens=%d completion_tokens=%d total_tokens=%d",
                    self.model,
                    latency_ms,
                    usage.prompt_tokens if usage else -1,
                    usage.completion_tokens if usage else -1,
                    usage.total_tokens if usage else -1,
                )
                return response.choices[0].message.content

            except Exception as exc:
                last_exc = exc
                is_retryable = (
                    "RateLimitError" in type(exc).__name__
                    or "APIError" in type(exc).__name__
                    or "APIConnectionError" in type(exc).__name__
                    or "InternalServerError" in type(exc).__name__
                    or "ServiceUnavailableError" in type(exc).__name__
                )
                if is_retryable and attempt < self._MAX_RETRIES:
                    delay = self._RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "LLM call failed (attempt %d/%d): %s – retrying in %.1fs",
                        attempt, self._MAX_RETRIES, exc, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "LLM call failed after %d attempt(s): %s",
                        attempt, exc,
                    )
                    raise

        raise last_exc  # should be unreachable

    def generate_rules(
        self,
        schema: Dict[str, Any],
        statistics: List[ColumnStatistics],
        business_context: Optional[str] = None,
        existing_rules: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate validation rules using the LLM.
        
        Args:
            schema: Dataset schema with column types and descriptions
            statistics: Column statistics
            business_context: Optional business context
            existing_rules: Existing rules to avoid duplication
            
        Returns:
            List of validation rules in SageScan format
        """
        try:
            # Build prompt
            prompt = self._build_prompt(schema, statistics, business_context, existing_rules)
            
            # Call LLM
            response = self._call_llm(prompt)
            
            # Parse response
            rules = self._parse_response(response)
            
            logger.info(f"Generated {len(rules)} rules from LLM")
            return rules
            
        except Exception as e:
            logger.error(f"Failed to generate rules: {e}")
            raise

    def generate_full_config(
        self,
        schema: Dict[str, Any],
        statistics: List[ColumnStatistics],
        business_context: Optional[str] = None,
        existing_rules: Optional[List[Dict[str, Any]]] = None,
        source_type: str = "csv",
        source_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a full SageScan configuration with rules.
        
        Args:
            schema: Dataset schema
            statistics: Column statistics
            business_context: Optional business context
            existing_rules: Existing rules
            source_type: Type of data source
            source_path: Path to data source
            
        Returns:
            Full SageScan configuration
        """
        rules = self.generate_rules(schema, statistics, business_context, existing_rules)
        
        config = {
            "version": "1.0",
            "source": {
                "type": source_type,
                "path": source_path or "data.csv"
            },
            "rules": rules
        }
        
        if business_context:
            config["business_context"] = business_context
        
        return config


def build_statistics_from_dataframe(df: pd.DataFrame) -> List[ColumnStatistics]:
    """
    Build column statistics from a pandas DataFrame.

    Args:
        df: Input DataFrame

    Returns:
        List of ColumnStatistics objects
    """
    if df.empty:
        logger.warning("build_statistics_from_dataframe received an empty DataFrame; returning [].")
        return []

    statistics = []
    n_rows = len(df)

    for col in df.columns:
        col_data = df[col]

        dtype = str(col_data.dtype)
        # Guard against zero-row slices (already blocked above, but be safe)
        missing_ratio = float(col_data.isna().sum() / n_rows) if n_rows > 0 else 0.0

        # Numeric statistics
        numeric_stats: Dict[str, Any] = {}
        quartiles: Dict[str, float] = {}
        if pd.api.types.is_numeric_dtype(col_data):
            numeric_stats = {
                "min_value": float(col_data.min()),
                "max_value": float(col_data.max()),
                "mean": float(col_data.mean()),
                "std": float(col_data.std()),
            }
            quartiles = {
                "q1": float(col_data.quantile(0.25)),
                "q2": float(col_data.quantile(0.50)),
                "q3": float(col_data.quantile(0.75)),
            }

        # Categorical / low-cardinality top values
        top_values: List[Any] = []
        # isinstance check works for both old and new pandas
        is_cat = hasattr(col_data, "cat") or str(col_data.dtype) == "category"
        if is_cat or col_data.nunique() < 20:
            top_values = [
                v for v in col_data.value_counts().head(10).index.tolist()
            ]

        stats_obj = ColumnStatistics(
            name=col,
            dtype=dtype,
            missing_ratio=missing_ratio,
            **numeric_stats,
            unique_count=int(col_data.nunique()),
            top_values=top_values[:10],
            quartiles=quartiles,
        )

        statistics.append(stats_obj)

    return statistics