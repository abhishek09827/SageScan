"""
AI-based explanation module for SageScan data quality validation.

This module provides contextual, human-readable explanations for data anomalies
using LLMs with detailed context about data behavior and statistics.
"""

import yaml
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FailedCheck:
    """A single failed validation check."""
    column: str
    check_type: str
    passed: bool
    failed_rows: List[int]
    failed_values: List[Any]
    message: str
    parameters: Dict[str, Any]


@dataclass
class ColumnContext:
    """Context about a column including statistics."""
    name: str
    dtype: str
    missing_ratio: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    quartiles: Dict[str, float] = None
    top_values: List[Any] = None
    unique_count: int = 0


class ExplanationGenerator:
    """
    Generates contextual explanations for data quality issues.
    
    Provides human-readable, data-specific explanations rather than
    generic messages, tied to actual data behavior and statistics.
    """

    def __init__(self, api_key: str, model: str = "gpt-4", max_tokens: int = 1000, base_url: Optional[str] = None, temperature: float = 0.5):
        """
        Initialize the explanation generator.
        
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

    def _build_explanation_prompt(
        self,
        failed_check: FailedCheck,
        column_context: ColumnContext
    ) -> str:
        """
        Build a deterministic prompt for generating explanations.
        
        Args:
            failed_check: The failed validation check
            column_context: Statistics and context about the column
            
        Returns:
            Formatted prompt string
        """
        prompt = """# SageScan Anomaly Explanation Task

You are a data quality expert. Provide a clear, contextual explanation for a data quality issue.

## Your Task
Explain WHY the validation failed and WHAT this means for the data. Avoid generic explanations like "data contains invalid values". Instead, tie your explanation to the actual data behavior and business implications.

## Required Components

1. **What Happened**: Briefly describe the issue (2-3 sentences)
2. **Data Context**: Connect to the column statistics and data behavior
3. **Business Impact**: What does this mean for users/business?
4. **Recommended Action**: What should be fixed and how?

## Input Information

"""
        
        # Add column context
        prompt += f"### Column: {column_context.name} ({column_context.dtype})\n"
        prompt += f"- Missing Ratio: {column_context.missing_ratio:.2%}\n"
        if column_context.min_value is not None:
            prompt += f"- Min: {column_context.min_value:.2f}\n"
        if column_context.max_value is not None:
            prompt += f"- Max: {column_context.max_value:.2f}\n"
        if column_context.mean is not None:
            prompt += f"- Mean: {column_context.mean:.2f}\n"
        if column_context.std is not None:
            prompt += f"- Std: {column_context.std:.2f}\n"
        if column_context.unique_count > 0:
            prompt += f"- Unique Values: {column_context.unique_count}\n"
        if column_context.top_values:
            prompt += f"- Top Values: {', '.join(map(str, column_context.top_values[:5]))}\n"
        if column_context.quartiles:
            prompt += f"- Quartiles: {column_context.quartiles}\n"
        
        # Add failed check details
        prompt += f"\n### Validation Check: {failed_check.check_type}\n"
        prompt += f"- Failed Rows: {len(failed_check.failed_rows)}\n"
        if failed_check.failed_values:
            prompt += f"- Sample Failed Values: {failed_check.failed_values[:3]}\n"
        prompt += f"- Message: {failed_check.message}\n"
        prompt += f"- Parameters: {failed_check.parameters}\n"
        
        prompt += "\n## Explanation Requirements\n"
        prompt += "- Be specific and data-driven (avoid generic statements)\n"
        prompt += "- Use business language when appropriate\n"
        prompt += "- Explain the root cause, not just the symptom\n"
        prompt += "- Provide actionable recommendations\n"
        prompt += "- Keep it concise (2-4 paragraphs)\n"
        prompt += "- Output in Markdown format\n"
        
        return prompt

    def _generate_explanation(self, prompt: str) -> str:
        """
        Generate explanation using LLM.
        
        Args:
            prompt: Prompt to send to LLM
            
        Returns:
            Explanation text from LLM
        """
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI package is required. Install with: pip install openai")
        
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = openai.OpenAI(**client_kwargs)
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data quality explanation expert. Provide clear, contextual explanations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature  # Moderate temperature for balanced explanations
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            raise

    def explain_failed_check(
        self,
        failed_check: FailedCheck,
        column_context: ColumnContext
    ) -> str:
        """
        Generate a contextual explanation for a failed check.
        
        Args:
            failed_check: The failed validation check
            column_context: Statistics and context about the column
            
        Returns:
            Human-readable explanation
        """
        try:
            # Build prompt
            prompt = self._build_explanation_prompt(failed_check, column_context)
            
            # Generate explanation
            explanation = self._generate_explanation(prompt)
            
            logger.info(f"Generated explanation for {failed_check.column} - {failed_check.check_type}")
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            return f"Unable to generate explanation for {failed_check.check_type} on column {failed_check.column}"

    def explain_validation_report(
        self,
        failed_checks: List[FailedCheck],
        column_contexts: Dict[str, ColumnContext]
    ) -> Dict[str, str]:
        """
        Generate explanations for all failed checks in a validation report.
        
        Args:
            failed_checks: List of failed validation checks
            column_contexts: Dictionary of column contexts
            
        Returns:
            Dictionary mapping check identifiers to explanations
        """
        explanations = {}
        
        for check in failed_checks:
            # Find column context
            column_context = column_contexts.get(check.column)
            if not column_context:
                column_context = ColumnContext(
                    name=check.column,
                    dtype="unknown",
                    missing_ratio=0.0
                )
            
            # Generate explanation
            explanation = self.explain_failed_check(check, column_context)
            explanations[check.column] = explanation
        
        return explanations


def format_validation_report_with_explanations(
    report: Dict[str, Any],
    explanations: Dict[str, str]
) -> Dict[str, Any]:
    """
    Format a validation report with AI-generated explanations.
    
    Args:
        report: Original validation report
        explanations: Dictionary of explanations for failed checks
        
    Returns:
        Formatted report with explanations
    """
    formatted_report = report.copy()
    
    # Add explanations to results
    for result in formatted_report.get("results", []):
        if not result.get("passed", False):
            column = result.get("column", "")
            explanation = explanations.get(column, "No explanation available.")
            result["explanation"] = explanation
    
    return formatted_report


def create_column_contexts(df: pd.DataFrame) -> Dict[str, ColumnContext]:
    """
    Build column contexts from a DataFrame.
    
    Args:
        df: Input DataFrame
        
    Returns:
        Dictionary of ColumnContext objects
    """
    contexts = {}
    
    for col in df.columns:
        col_data = df[col]
        
        # Basic statistics
        dtype = str(col_data.dtype)
        missing_ratio = col_data.isna().sum() / len(col_data)
        
        # Numeric statistics
        numeric_stats = None
        if pd.api.types.is_numeric_dtype(col_data):
            numeric_stats = {
                "min_value": float(col_data.min()),
                "max_value": float(col_data.max()),
                "mean": float(col_data.mean()),
                "std": float(col_data.std())
            }
        
        # Categorical statistics
        top_values = []
        if pd.api.types.is_categorical_dtype(col_data):
            top_values = col_data.value_counts().head(10).index.tolist()
        elif col_data.nunique() < 20:
            top_values = col_data.value_counts().head(10).index.tolist()
        
        # Quartiles for numeric data
        quartiles = {}
        if numeric_stats:
            quartiles = {
                "q1": float(col_data.quantile(0.25)),
                "q2": float(col_data.quantile(0.50)),
                "q3": float(col_data.quantile(0.75))
            }
        
        context = ColumnContext(
            name=col,
            dtype=dtype,
            missing_ratio=missing_ratio,
            **numeric_stats if numeric_stats else {},
            unique_count=col_data.nunique(),
            top_values=top_values[:10],
            quartiles=quartiles
        )
        
        contexts[col] = context
    
    return contexts


def parse_failed_checks_from_report(report: Dict[str, Any]) -> List[FailedCheck]:
    """
    Parse failed checks from a validation report.
    
    Args:
        report: Validation report dictionary
        
    Returns:
        List of FailedCheck objects
    """
    failed_checks = []
    
    for result in report.get("results", []):
        if not result.get("passed", False):
            failed_check = FailedCheck(
                column=result.get("column", ""),
                check_type=result.get("check", ""),
                passed=result.get("passed", False),
                failed_rows=result.get("failed_rows", []),
                failed_values=result.get("failed_values", []),
                message=result.get("message", ""),
                parameters=result.get("parameters", {})
            )
            failed_checks.append(failed_check)
    
    return failed_checks