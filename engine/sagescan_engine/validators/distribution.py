"""
Distribution analysis and drift detection validators.

This module provides validators for analyzing data distributions and detecting
drift between reference and current datasets.
"""

import pandas as pd
import numpy as np
import scipy.stats as stats
from typing import Dict, Any, List, Optional
from .base import BaseValidator, ValidationResult, ValidationResultDetail


class ZScoreOutlierDetector(BaseValidator):
    """
    Detect outliers using z-score from current dataset distribution.
    
    This validator calculates z-scores from the current dataset and identifies
    values that are statistically unlikely given the distribution.
    """

    def __init__(self, check_config: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Initialize the z-score outlier detector.
        
        Args:
            check_config: Configuration with type and threshold parameters
            metadata: Additional metadata
        """
        super().__init__(check_config, metadata)
        self.threshold = self.check_config.get("threshold", 3.0)
        self.upper_threshold = self.check_config.get("upper_threshold", 3.0)
        self.lower_threshold = self.check_config.get("lower_threshold", 3.0)
        self.num_bins = self.check_config.get("bins", 10)

    def validate(self, series) -> ValidationResultDetail:
        """
        Detect outliers using z-scores from current distribution.
        
        Args:
            series: pandas Series to analyze
            
        Returns:
            ValidationResultDetail with outlier information
        """
        # Remove NaN for z-score calculation
        valid_values = series.dropna()
        
        if len(valid_values) == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="No valid values to analyze (all null)"
            )

        # Calculate z-scores
        mean = valid_values.mean()
        std = valid_values.std()

        if std == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="Standard deviation is 0, no outliers detected"
            )

        z_scores = (valid_values - mean) / std

        # Detect outliers
        is_upper_outlier = z_scores > self.upper_threshold
        is_lower_outlier = z_scores < -self.lower_threshold
        is_outlier = is_upper_outlier | is_lower_outlier

        # Get outlier details
        outlier_indices = valid_values[is_outlier].index.tolist()
        outlier_values = valid_values[is_outlier].tolist()
        outlier_z_scores = z_scores[is_outlier].tolist()

        passed = len(outlier_indices) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = f"Found {len(outlier_indices)} outliers (|z| > {self.threshold})"
        if outlier_indices:
            message += f"\n  Upper outliers: {len([x for x in outlier_z_scores if x > self.upper_threshold])}"
            message += f"\n  Lower outliers: {len([x for x in outlier_z_scores if x < -self.lower_threshold])}"
            message += f"\n  Sample z-scores: {outlier_z_scores[:3]}"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=outlier_indices,
            failed_values=outlier_values,
            message=message
        )


class KSTestValidator(BaseValidator):
    """
    Perform Kolmogorov-Smirnov test for distribution comparison.
    
    Compares the distribution of a column against a reference distribution.
    """

    def __init__(self, check_config: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Initialize the KS test validator.
        
        Args:
            check_config: Configuration with type and reference parameters
            metadata: Additional metadata
        """
        super().__init__(check_config, metadata)
        self.reference_type = self.check_config.get("reference_type", "file")
        self.reference_path = self.check_config.get("reference_path", "")
        self.significance_level = self.check_config.get("alpha", 0.05)
        self.min_samples = self.check_config.get("min_samples", 30)

    def validate(self, series) -> ValidationResultDetail:
        """
        Perform KS test against reference distribution.
        
        Args:
            series: pandas Series to compare
            
        Returns:
            ValidationResultDetail with KS test results
        """
        # Load reference data
        if self.reference_type == "file":
            try:
                ref_series = pd.read_csv(self.reference_path)[self.check_config["column"]]
            except Exception as e:
                return ValidationResultDetail(
                    column=self.check_config["column"],
                    check_type=self.check_type,
                    result=ValidationResult.FAIL,
                    passed=False,
                    message=f"Failed to load reference data: {e}"
                )
        else:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message=f"Reference type '{self.reference_type}' not implemented"
            )

        # Filter valid values from both series
        valid_series = series.dropna()
        valid_ref = ref_series.dropna()

        if len(valid_series) < self.min_samples or len(valid_ref) < self.min_samples:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message=f"Insufficient samples (current: {len(valid_series)}, reference: {len(valid_ref)})"
            )

        # Perform KS test
        stat, p_value = stats.ks_2samp(valid_series, valid_ref)

        # Interpret results
        passed = p_value >= self.significance_level
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = f"KS statistic: {stat:.4f}, p-value: {p_value:.4f}"
        if p_value < self.significance_level:
            message += f" (Significant difference at alpha={self.significance_level})"
        else:
            message += f" (Distributions are similar at alpha={self.significance_level})"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=[],
            failed_values=[],
            message=message
        )


class PSIValidator(BaseValidator):
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures the difference in distributions between a reference population
    and a current population. Values > 0.2 indicate significant drift.
    """

    def __init__(self, check_config: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Initialize the PSI validator.
        
        Args:
            check_config: Configuration with type and reference parameters
            metadata: Additional metadata
        """
        super().__init__(check_config, metadata)
        self.reference_type = self.check_config.get("reference_type", "file")
        self.reference_path = self.check_config.get("reference_path", "")
        self.num_bins = self.check_config.get("bins", 10)
        self.warning_threshold = self.check_config.get("warning_threshold", 0.1)
        self.drift_threshold = self.check_config.get("drift_threshold", 0.2)

    def calculate_psi(self, actual_values, expected_values, num_bins=10) -> float:
        """
        Calculate Population Stability Index.
        
        Args:
            actual_values: Actual population values
            expected_values: Expected population values
            num_bins: Number of bins to use for binning
            
        Returns:
            PSI value
        """
        # Combine values to get min and max
        min_val = min(actual_values.min() if len(actual_values) > 0 else 0,
                      expected_values.min() if len(expected_values) > 0 else 0)
        max_val = max(actual_values.max() if len(actual_values) > 0 else 0,
                      expected_values.max() if len(expected_values) > 0 else 0)

        # Handle constant values
        if max_val == min_val:
            bins = [min_val - 0.5, min_val + 0.5]
            expected_count = len(expected_values)
            actual_count = len(actual_values)
        else:
            bins = np.linspace(min_val, max_val, num_bins + 1)
            expected_count = len(expected_values)
            actual_count = len(actual_values)

        # Calculate percentage in each bin
        expected_percents = np.zeros(num_bins)
        actual_percents = np.zeros(num_bins)

        for i in range(num_bins):
            expected_percents[i] = np.sum((expected_values >= bins[i]) & (expected_values < bins[i + 1])) / expected_count
            actual_percents[i] = np.sum((actual_values >= bins[i]) & (actual_values < bins[i + 1])) / actual_count

        # Avoid division by zero
        expected_percents = np.maximum(expected_percents, 1e-6)
        actual_percents = np.maximum(actual_percents, 1e-6)

        # Calculate PSI
        psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
        return psi

    def validate(self, series) -> ValidationResultDetail:
        """
        Calculate PSI between current and reference distributions.
        
        Args:
            series: pandas Series to compare
            
        Returns:
            ValidationResultDetail with PSI results
        """
        # Load reference data
        if self.reference_type == "file":
            try:
                ref_series = pd.read_csv(self.reference_path)[self.check_config["column"]]
            except Exception as e:
                return ValidationResultDetail(
                    column=self.check_config["column"],
                    check_type=self.check_type,
                    result=ValidationResult.FAIL,
                    passed=False,
                    message=f"Failed to load reference data: {e}"
                )
        else:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message=f"Reference type '{self.reference_type}' not implemented"
            )

        # Filter valid values
        valid_series = series.dropna()
        valid_ref = ref_series.dropna()

        if len(valid_series) == 0 or len(valid_ref) == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="Cannot calculate PSI with empty data"
            )

        # Calculate PSI
        psi = self.calculate_psi(valid_series, valid_ref, self.num_bins)

        # Interpret results
        if psi < self.warning_threshold:
            status = "Good"
        elif psi < self.drift_threshold:
            status = "Moderate"
        else:
            status = "High Drift"

        passed = psi < self.drift_threshold
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = f"PSI: {psi:.4f} ({status})"
        if psi >= self.drift_threshold:
            message += f" (Threshold: {self.drift_threshold}, Warning: {self.warning_threshold})"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=[],
            failed_values=[],
            message=message
        )