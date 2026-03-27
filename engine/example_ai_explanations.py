"""
Example usage of the AI explanation module.

This script demonstrates how to generate contextual, human-readable
explanations for data quality issues.
"""

import sys
import os
sys.path.insert(0, 'engine')

import pandas as pd
from sagescan_engine.llm.explanation_generator import (
    ExplanationGenerator,
    create_column_contexts,
    parse_failed_checks_from_report,
    format_validation_report_with_explanations
)
from sagescan_engine.core.runner import run_validation


def main():
    """Demonstrate AI explanation generation."""
    
    # Load sample data
    df = pd.read_csv('../examples/sample_data.csv')
    
    # Run validation
    config = {
        "version": "1.0",
        "source": {
            "type": "csv",
            "path": "../examples/sample_data.csv"
        },
        "rules": [
            {
                "column": "user_id",
                "checks": [
                    {"type": "not_null"},
                    {"type": "unique"}
                ]
            },
            {
                "column": "age",
                "checks": [
                    {"type": "not_null"},
                    {"type": "min_value", "value": 18}
                ]
            },
            {
                "column": "email",
                "checks": [
                    {"type": "not_null"}
                ]
            }
        ],
        "context": "production",
        "baseline": ""
    }
    
    print("=" * 80)
    print("SageScan AI Explanation Generator - Example Usage")
    print("=" * 80)
    
    print("\n## Running Validation...")
    print("-" * 80)
    
    # Run validation to get report
    results = run_validation(config)
    
    # Create report structure
    report = {
        "status": "FAIL",
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.get("passed", False)),
            "failed": len(results) - sum(1 for r in results if r.get("passed", False)),
            "pass_rate": (sum(1 for r in results if r.get("passed", False)) / len(results) * 100)
        },
        "results": results
    }
    
    print(f"\nValidation Complete: {report['status']}")
    print(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
    
    # Parse failed checks
    failed_checks = parse_failed_checks_from_report(report)
    
    print(f"\n## Failed Checks: {len(failed_checks)}")
    print("-" * 80)
    
    for check in failed_checks:
        print(f"\n[FAILED] {check.check_type} on {check.column}")
        print(f"  Failed Rows: {len(check.failed_rows)}")
        print(f"  Message: {check.message}")
    
    # Create column contexts
    print("\n\n## Creating Column Contexts...")
    print("-" * 80)
    
    column_contexts = create_column_contexts(df)
    
    for col, context in column_contexts.items():
        print(f"\n{context.name} ({context.dtype}):")
        print(f"  Missing Ratio: {context.missing_ratio:.2%}")
        print(f"  Unique Values: {context.unique_count}")
        if context.mean is not None:
            print(f"  Mean: {context.mean:.2f}")
        if context.quartiles:
            print(f"  Quartiles: {context.quartiles}")
    
    # Generate explanations
    print("\n\n## Generating AI Explanations...")
    print("-" * 80)
    
    generator = ExplanationGenerator(
        api_key="dummy",
        model="gpt-4",
        max_tokens=1000
    )
    
    explanations = generator.explain_validation_report(
        failed_checks,
        column_contexts
    )
    
    # Display explanations
    print("\n## Generated Explanations")
    print("=" * 80)
    
    for col, explanation in explanations.items():
        print(f"\n### {col}")
        print(explanation)
        print("\n" + "-" * 80)
    
    # Format report with explanations
    print("\n\n## Formatted Report with Explanations")
    print("=" * 80)
    
    formatted_report = format_validation_report_with_explanations(report, explanations)
    
    # Display formatted report
    print(f"\nStatus: {formatted_report['status']}")
    print(f"Summary: {formatted_report['summary']}")
    
    for result in formatted_report.get("results", []):
        if not result.get("passed", False):
            print(f"\n✗ {result['column']} - {result['check']}")
            print(f"  {result['message']}")
            if "explanation" in result:
                print(f"\n  📖 Explanation:")
                print(f"  {result['explanation']}")
    
    print("\n\n## Prompt Structure Example")
    print("=" * 80)
    
    # Show what the prompt looks like
    from sagescan_engine.llm.explanation_generator import FailedCheck, ColumnContext
    
    # Create a sample failed check
    sample_check = FailedCheck(
        column="age",
        check_type="not_null",
        passed=False,
        failed_rows=[0, 4],
        failed_values=[None, None],
        message="Found 2 failing rows Sample values: None",
        parameters={}
    )
    
    sample_context = ColumnContext(
        name="age",
        dtype="float64",
        missing_ratio=0.2,
        min_value=17.0,
        max_value=40.0,
        mean=27.2,
        std=8.9,
        quartiles={"q1": 20.0, "q2": 27.0, "q3": 32.0},
        unique_count=20,
        top_values=[25.0, 30.0, 27.0, 22.0, 35.0]
    )
    
    # Build prompt
    prompt = generator._build_explanation_prompt(sample_check, sample_context)
    
    print("Deterministic Prompt Structure:")
    print(prompt[:500] + "...")
    
    print("\n\n## Integration Point")
    print("=" * 80)
    
    integration_code = """
# Integration with validation pipeline

from sagescan_engine.core.runner import run_validation
from sagescan_engine.llm.explanation_generator import (
    ExplanationGenerator,
    create_column_contexts,
    parse_failed_checks_from_report,
    format_validation_report_with_explanations
)

# 1. Run validation
results = run_validation(config)

# 2. Build report and parse failed checks
report = {...}  # Create from results
failed_checks = parse_failed_checks_from_report(report)

# 3. Get column contexts from data
df = pd.read_csv(config['source']['path'])
column_contexts = create_column_contexts(df)

# 4. Generate explanations
generator = ExplanationGenerator(api_key="...", model="gpt-4")
explanations = generator.explain_validation_report(failed_checks, column_contexts)

# 5. Format report with explanations
formatted_report = format_validation_report_with_explanations(report, explanations)

# 6. Output (save to file or display)
import json
with open('report_with_explanations.json', 'w') as f:
    json.dump(formatted_report, f, indent=2)
"""
    
    print(integration_code)
    
    print("\n\n## Key Features")
    print("=" * 80)
    
    features = [
        "Context-aware explanations tied to actual data behavior",
        "Statistical context (quartiles, distributions, min/max)",
        "Business impact assessment",
        "Actionable recommendations",
        "Concise, data-driven explanations",
        "Markdown-formatted output",
        "Reusable integration with validation pipeline"
    ]
    
    for feature in features:
        print(f"  ✓ {feature}")
    
    return generator


if __name__ == "__main__":
    generator = main()