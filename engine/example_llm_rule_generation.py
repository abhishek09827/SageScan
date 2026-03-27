"""
Example usage of the LLM rule generator.

This script demonstrates the deterministic prompt structure and shows
what input/output would be generated.
"""

import sys
import os
sys.path.insert(0, 'engine')

import pandas as pd
from sagescan_engine.llm.rule_generator import LLMRuleGenerator, build_statistics_from_dataframe


def main():
    """Demonstrate LLM rule generation."""
    
    # Load sample data
    df = pd.read_csv('../examples/sample_data.csv')
    
    # Build schema (simplified)
    schema = {
        'user_id': {'type': 'integer', 'description': 'Unique user identifier'},
        'age': {'type': 'integer', 'description': 'User age in years'},
        'email': {'type': 'string', 'description': 'User email address'}
    }
    
    # Build statistics
    statistics = build_statistics_from_dataframe(df)
    
    # Business context for specific rules
    business_context = """
This is a user registration system. User data must be:
- Complete (no missing values)
- Valid (proper email format)
- Consistent (valid age ranges)
- Unique (no duplicate user IDs)
"""
    
    print("=" * 80)
    print("SageScan LLM Rule Generator - Example Usage")
    print("=" * 80)
    
    print("\n## Input Information")
    print("-" * 80)
    print("\n### Dataset Schema")
    for col, info in schema.items():
        print(f"- {col}: {info['type']}")
        if info.get('description'):
            print(f"  Description: {info['description']}")
    
    print("\n### Sample Statistics")
    for stats in statistics:
        print(f"\n{stats.name} ({stats.dtype}):")
        print(f"  Missing Ratio: {stats.missing_ratio:.2%}")
        print(f"  Unique Values: {stats.unique_count}")
        if stats.top_values:
            print(f"  Top Values: {stats.top_values[:5]}")
    
    print("\n### Business Context")
    print(business_context)
    
    print("\n" + "=" * 80)
    print("## Deterministic Prompt Structure")
    print("=" * 80)
    
    # Build prompt to show structure
    generator = LLMRuleGenerator(api_key="dummy", model="gpt-4")
    prompt = generator._build_prompt(
        schema=schema,
        statistics=statistics,
        business_context=business_context,
        existing_rules=None
    )
    
    print(prompt)
    
    print("=" * 80)
    print("## Expected Output Format (YAML)")
    print("=" * 80)
    
    # Show expected output format
    expected_output = """version: "1.0"
source:
  type: csv
  path: data.csv
rules:
  - column: user_id
    checks:
      - type: not_null
      - type: unique
  - column: age
    checks:
      - type: not_null
      - type: min_value
        value: 18
      - type: max_value
        value: 120
  - column: email
    checks:
      - type: not_null
      - type: regex
        value: "^[^@]+@[^@]+\\.[^@]+$"
      - type: null_percentage
        value: 0.0
        max_percentage: 1.0
"""
    
    print(expected_output)
    
    print("=" * 80)
    print("## Example: Calling the Generator")
    print("=" * 80)
    
    print("""
The generator can be called with:

    generator = LLMRuleGenerator(
        api_key="your-openai-api-key",
        model="gpt-4",
        max_tokens=2000
    )
    
    rules = generator.generate_rules(
        schema=schema,
        statistics=statistics,
        business_context=business_context
    )
    
    config = generator.generate_full_config(
        schema=schema,
        statistics=statistics,
        business_context=business_context,
        source_type="csv",
        source_path="data.csv"
    )
    
    # Save as YAML
    import yaml
    with open('generated_rules.yaml', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
""")
    
    print("=" * 80)
    print("## Key Features")
    print("=" * 80)
    
    features = [
        "Deterministic prompt structure for consistent outputs",
        "Statistical constraints based on quartiles and distributions",
        "Business context integration for domain-specific rules",
        "Avoids generic rules (e.g., doesn't suggest not_null for all columns)",
        "Supports all SageScan validator types",
        "Output in valid YAML format",
        "Extensible to other LLM providers",
    ]
    
    for feature in features:
        print(f"  ✓ {feature}")
    
    print("\n## Implementation Notes")
    print("=" * 80)
    
    notes = """
1. **Deterministic Prompts**: The prompt structure is fixed and includes
   specific instructions about check types and their appropriate use cases.

2. **Statistical Awareness**: The generator receives actual statistics
   (quartiles, distributions) to create meaningful constraints rather
   than arbitrary thresholds.

3. **Business Context**: Rules are tailored to the specific business
   requirements, not generic data quality checks.

4. **Extensible Design**: Can easily add support for other LLM providers
   by modifying the _call_llm method.

5. **Error Handling**: Robust YAML parsing with fallback for malformed responses.

6. **Production-Ready**: Includes logging, type safety, and comprehensive
   error handling.
"""
    
    print(notes)
    
    return generator


if __name__ == "__main__":
    generator = main()