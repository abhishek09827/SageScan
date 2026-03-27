"""
Example usage of drift detection and distribution analysis.

This script demonstrates how to use the new distribution validators:
- Z-score outlier detection
- KS test for distribution comparison
- PSI (Population Stability Index)
"""

import sys
import os
sys.path.insert(0, 'engine')

import pandas as pd
import numpy as np
from sagescan_engine.core.runner import run_validation


def main():
    """Run drift detection validation."""
    
    # Generate reference data
    reference_data = pd.DataFrame({
        'feature_a': np.random.normal(100, 15, 1000),
        'feature_b': np.random.exponential(50, 1000)
    })
    
    # Generate current data with slight drift
    current_data = pd.DataFrame({
        'feature_a': np.random.normal(105, 15, 1000),
        'feature_b': np.random.exponential(55, 1000)
    })
    
    # Save reference data to examples directory
    examples_dir = os.path.join(os.path.dirname(__file__), '../examples')
    os.makedirs(examples_dir, exist_ok=True)
    
    reference_path = os.path.join(examples_dir, 'reference_data.csv')
    current_path = os.path.join(examples_dir, 'current_data.csv')
    
    reference_data.to_csv(reference_path, index=False)
    current_data.to_csv(current_path, index=False)
    
    # Create a sample configuration with distribution validators
    config = {
        "version": "1.0",
        "source": {
            "type": "csv",
            "path": current_path
        },
        "rules": [
            {
                "column": "feature_a",
                "checks": [
                    {
                        "type": "z_score",
                        "threshold": 3.0,
                        "upper_threshold": 3.0,
                        "lower_threshold": 3.0
                    }
                ]
            },
            {
                "column": "feature_a",
                "checks": [
                    {
                        "type": "ks_test",
                        "reference_type": "file",
                        "reference_path": reference_path,
                        "alpha": 0.05
                    }
                ]
            },
            {
                "column": "feature_a",
                "checks": [
                    {
                        "type": "psi",
                        "reference_type": "file",
                        "reference_path": reference_path,
                        "warning_threshold": 0.1,
                        "drift_threshold": 0.2
                    }
                ]
            },
            {
                "column": "feature_b",
                "checks": [
                    {
                        "type": "z_score",
                        "threshold": 3.0
                    }
                ]
            },
            {
                "column": "feature_b",
                "checks": [
                    {
                        "type": "psi",
                        "reference_type": "file",
                        "reference_path": reference_path,
                        "warning_threshold": 0.1,
                        "drift_threshold": 0.2
                    }
                ]
            }
        ],
        "context": "production-drift-detection",
        "baseline": ""
    }
    
    print("=" * 70)
    print("SageScan Drift Detection Example")
    print("=" * 70)
    print("\nReference Data Shape:", reference_data.shape)
    print("Current Data Shape:", current_data.shape)
    print("\nReference Data Sample:")
    print(reference_data.head())
    print("\nCurrent Data Sample:")
    print(current_data.head())
    print("\n" + "=" * 70)
    print("Running Distribution Analysis...")
    print("=" * 70)
    
    # Run validation
    results = run_validation(config)
    
    # Print results
    print("\nDistribution Analysis Results:")
    print("-" * 70)
    for i, result in enumerate(results, 1):
        status = "[PASS]" if result['passed'] else "[FAIL]"
        check_type = result['check']
        
        print(f"\n[{i}] {status} - {check_type}")
        print(f"   Column: {result['column']}")
        
        # Print detailed information based on check type
        if 'z_score' in check_type.lower():
            print(f"   Result: Outliers detected: {not result['passed']}")
        elif 'ks_test' in check_type.lower():
            print(f"   KS Statistic: {result.get('message', '').split('KS statistic:')[1].split(',')[0].strip()}")
            print(f"   P-value: {result.get('message', '').split('p-value:')[1].split(')')[0].strip()}")
        elif 'psi' in check_type.lower():
            psi_value = result.get('message', '').split('PSI:')[1].split('(')[0].strip()
            print(f"   PSI: {psi_value}")
        
        if not result['passed']:
            print(f"   Message: {result['message']}")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    print(f"Total Checks: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Pass Rate: {(passed/total*100):.1f}%")
    
    # Print PSI interpretation guide
    print("\n" + "=" * 70)
    print("PSI Interpretation Guide:")
    print("=" * 70)
    print("  PSI < 0.1:    Good - No significant drift")
    print("  0.1 <= PSI < 0.2: Moderate - Some drift detected")
    print("  PSI >= 0.2:   High Drift - Significant population shift")
    
    return results


if __name__ == "__main__":
    results = main()