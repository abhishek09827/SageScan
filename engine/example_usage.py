"""
Example usage of the SageScan validation engine.

This script demonstrates how to use the validation pipeline with sample data.
"""

import sys
sys.path.insert(0, 'engine')

import pandas as pd
from sagescan_engine.core.runner import run_validation


def main():
    """Run validation on sample data."""
    
    # Sample data with known issues
    sample_data = pd.DataFrame({
        'user_id': [1, 2, 3, 3, 5],
        'age': [25, 17, 30, 40, None],
        'email': ['alice@example.com', 'bob@example.com', 'charlie@example.com', 'duplicate@example.com', 'missing_age@example.com']
    })
    
    # Create a sample configuration
    import os
    config = {
        "version": "1.0",
        "source": {
            "type": "csv",
            "path": os.path.join(os.path.dirname(__file__), "../examples/sample_data.csv")
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
    
    print("=" * 60)
    print("SageScan Validation Engine - Example Usage")
    print("=" * 60)
    print("\nSample Data:")
    print(sample_data)
    print("\n" + "=" * 60)
    print("Running Validation...")
    print("=" * 60)
    
    # Run validation
    results = run_validation(config)
    
    # Print results
    print("\nValidation Results:")
    print("-" * 60)
    for i, result in enumerate(results, 1):
        status = "[PASS]" if result['passed'] else "[FAIL]"
        print(f"\n[{i}] {status}")
        print(f"   Column: {result['column']}")
        print(f"   Check:  {result['check']}")
        if not result['passed']:
            print(f"   Failed Rows: {result['failed_rows']}")
            print(f"   Message: {result['message']}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    print(f"Total Checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Pass Rate: {(passed/total*100):.1f}%")
    
    return results


if __name__ == "__main__":
    results = main()