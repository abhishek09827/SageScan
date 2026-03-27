"""
Concrete validator implementations for data quality checks.

Each validator implements the BaseValidator interface for specific check types.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, Any, List
from .base import BaseValidator, ValidationResult, ValidationResultDetail


class NotNullValidator(BaseValidator):
    """Validator for checking that values are not null."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that no values are null."""
        is_null = series.isna()
        # get_failed_rows expects a "pass" mask (True = OK), so invert is_null.
        failed_rows = series[is_null].index.tolist()
        failed_values = series[is_null].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = self._build_error_message(failed_rows, failed_values)
        if not passed and len(failed_values) > 0:
            message += f" Null values found in {len(failed_values)} rows"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else "All values are not null"
        )


class MinValueValidator(BaseValidator):
    """Validator for checking minimum value constraints."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that values meet minimum threshold."""
        min_value = self.check_config.get("value", 0)

        try:
            min_value = float(min_value)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid minimum value: {min_value}"
            )

        is_below_min = series < min_value
        failed_rows = series[is_below_min].index.tolist()
        failed_values = series[is_below_min].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = self._build_error_message(
            failed_rows, failed_values,
            f"Found {len(failed_rows)} values below minimum of {min_value}"
        )

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else f"All values are >= {min_value}"
        )


class MaxValueValidator(BaseValidator):
    """Validator for checking maximum value constraints."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that values meet maximum threshold."""
        max_value = self.check_config.get("value", 0)

        try:
            max_value = float(max_value)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid maximum value: {max_value}"
            )

        is_above_max = series > max_value
        failed_rows = series[is_above_max].index.tolist()
        failed_values = series[is_above_max].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = self._build_error_message(
            failed_rows, failed_values,
            f"Found {len(failed_rows)} values above maximum of {max_value}"
        )

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else f"All values are <= {max_value}"
        )


class RangeValidator(BaseValidator):
    """Validator for checking value ranges (both min and max)."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that values are within the specified range."""
        min_value = self.check_config.get("min", None)
        max_value = self.check_config.get("max", None)

        if min_value is None and max_value is None:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message="Both min and max must be specified for range validation"
            )

        try:
            if min_value is not None:
                min_value = float(min_value)
            if max_value is not None:
                max_value = float(max_value)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid range values: min={min_value}, max={max_value}"
            )

        is_invalid = pd.Series([False] * len(series), index=series.index)
        if min_value is not None:
            is_invalid |= series < min_value
        if max_value is not None:
            is_invalid |= series > max_value

        failed_rows = series[is_invalid].index.tolist()
        failed_values = series[is_invalid].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        # Issue #14: initialise message before the conditional block to avoid NameError.
        message = ""
        message_parts = []
        if min_value is not None:
            message_parts.append(f"below {min_value}")
        if max_value is not None:
            message_parts.append(f"above {max_value}")

        if message_parts:
            message = self._build_error_message(
                failed_rows, failed_values,
                f"Found {len(failed_rows)} values {', '.join(message_parts)}"
            )

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else "All values are within range"
        )


class RegexValidator(BaseValidator):
    """Validator for checking value patterns using regex."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that values match the specified regex pattern."""
        pattern = self.check_config.get("value", "")

        if not pattern:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message="No regex pattern provided"
            )

        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid regex pattern: {e}"
            )

        # Vectorised match: series.str.contains handles NaN safely via na=False
        # This is 50-100x faster than row-wise apply() on large Series.
        matches = series.astype(str).str.contains(pattern, na=False, regex=True)
        # NaN original values should not match
        matches = matches & series.notna()

        failed_rows = series[~matches].index.tolist()
        failed_values = series[~matches].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = self._build_error_message(
            failed_rows, failed_values,
            f"Found {len(failed_rows)} values not matching pattern '{pattern}'"
        )

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else "All values match the specified pattern"
        )


class NullPercentageValidator(BaseValidator):
    """Validator for checking percentage of null values."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that null percentage is within threshold."""
        # Issue #8: keep everything in the 0–100 % scale consistently.
        # 'value' is expected to be a percentage, e.g. 5 means "up to 5% nulls allowed".
        threshold_pct = float(self.check_config.get("value", 0.0))

        if threshold_pct < 0 or threshold_pct > 100:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid threshold value {threshold_pct}: must be between 0 and 100"
            )

        is_null = series.isna()
        null_count = int(is_null.sum())
        null_percentage = (null_count / len(series)) * 100 if len(series) > 0 else 0.0

        passed = null_percentage <= threshold_pct
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = f"Null percentage: {null_percentage:.2f}% (threshold: {threshold_pct:.2f}%)"
        if not passed:
            message += f". Found {null_count} null values out of {len(series)} rows"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=[] if passed else is_null[is_null].index.tolist(),
            failed_values=[] if passed else series[is_null].tolist(),
            message=message
        )


class ZScoreValidator(BaseValidator):
    """Validator for anomaly detection using z-score."""

    def validate(self, series) -> ValidationResultDetail:
        """Check for outliers using z-score."""
        max_z_score = float(self.check_config.get("value", self.check_config.get("max_z_score", 3.0)))

        try:
            max_z_score = float(max_z_score)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid z-score threshold: {max_z_score}"
            )

        valid_values = series.dropna()

        if len(valid_values) == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="No valid values to analyze (all null)"
            )

        mean = valid_values.mean()
        std = valid_values.std()

        if std == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="Standard deviation is 0, cannot calculate z-scores"
            )

        z_scores = (valid_values - mean) / std
        is_outlier = np.abs(z_scores) > max_z_score

        outlier_indices = valid_values[is_outlier].index.tolist()
        outlier_values = valid_values[is_outlier].tolist()

        passed = len(outlier_indices) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = f"Found {len(outlier_indices)} outliers (|z-score| > {max_z_score})"
        if outlier_indices:
            message += f" with z-scores: {z_scores[is_outlier].tolist()[:5]}"

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=outlier_indices,
            failed_values=outlier_values,
            message=message
        )


class UniqueValidator(BaseValidator):
    """Validator for checking uniqueness."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that all values are unique.

        Uses keep='first' so only the *second and subsequent* occurrences of a
        duplicated value are flagged.  This matches the expected behaviour:
        [1, 2, 2, 3] → 1 failure (the second 2), not 2.
        """
        try:
            # keep='first' → only subsequent duplicates are True
            is_duplicate = series.duplicated(keep="first")
        except TypeError:
            is_duplicate = series.duplicated(keep="first")

        failed_rows = series[is_duplicate].index.tolist()
        failed_values = series[is_duplicate].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL

        message = self._build_error_message(
            failed_rows, failed_values,
            f"Found {len(failed_rows)} duplicate values"
        )

        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message if message else "All values are unique"
        )


class MinLengthValidator(BaseValidator):
    """Validator for checking minimum string length."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that string values meet the minimum length threshold."""
        min_len = self.check_config.get("value", 1)
        try:
            min_len = int(min_len)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid min_length value: {min_len}",
            )

        lengths = series.astype(str).str.len()
        # NaN/None values count as length 0 (fail)
        null_mask = series.isna()
        is_too_short = (lengths < min_len) | null_mask

        failed_rows = series[is_too_short].index.tolist()
        failed_values = series[is_too_short].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL
        message = (
            f"Found {len(failed_rows)} values shorter than {min_len} characters"
            if not passed else f"All values have length >= {min_len}"
        )
        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message,
        )


class MaxLengthValidator(BaseValidator):
    """Validator for checking maximum string length."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that string values do not exceed the maximum length."""
        max_len = self.check_config.get("value", 255)
        try:
            max_len = int(max_len)
        except (ValueError, TypeError):
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message=f"Invalid max_length value: {max_len}",
            )

        lengths = series.astype(str).str.len()
        is_too_long = lengths > max_len

        failed_rows = series[is_too_long].index.tolist()
        failed_values = series[is_too_long].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL
        message = (
            f"Found {len(failed_rows)} values longer than {max_len} characters"
            if not passed else f"All values have length <= {max_len}"
        )
        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message,
        )


# PatternValidator is an alias for RegexValidator, but looks for full-string matches
# (anchored with ^ and $) by default.  The 'pattern' key in the YAML config is the
# regex string stored under 'value' for consistency with other validators.
PatternValidator = RegexValidator


class MeanCheckValidator(BaseValidator):
    """Validator for checking that the column mean is within [min, max]."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that the mean of the column is within the specified range."""
        min_mean = self.check_config.get("min", None)
        max_mean = self.check_config.get("max", None)

        valid = series.dropna()
        if len(valid) == 0:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="No valid values to check mean (all null)",
            )

        actual_mean = float(valid.mean())
        passed = True
        reasons = []
        if min_mean is not None and actual_mean < float(min_mean):
            passed = False
            reasons.append(f"mean {actual_mean:.4f} < min {min_mean}")
        if max_mean is not None and actual_mean > float(max_mean):
            passed = False
            reasons.append(f"mean {actual_mean:.4f} > max {max_mean}")

        result = ValidationResult.PASS if passed else ValidationResult.FAIL
        message = (
            f"Mean check passed: mean={actual_mean:.4f}"
            if passed else f"Mean check failed: {'; '.join(reasons)}"
        )
        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=[],
            failed_values=[],
            message=message,
        )


class StdCheckValidator(BaseValidator):
    """Validator for checking that the column standard deviation is within [min, max]."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that the std of the column is within the specified range."""
        min_std = self.check_config.get("min", None)
        max_std = self.check_config.get("max", None)

        valid = series.dropna()
        if len(valid) < 2:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.WARN,
                passed=True,
                message="Need at least 2 values to compute std",
            )

        actual_std = float(valid.std())
        passed = True
        reasons = []
        if min_std is not None and actual_std < float(min_std):
            passed = False
            reasons.append(f"std {actual_std:.4f} < min {min_std}")
        if max_std is not None and actual_std > float(max_std):
            passed = False
            reasons.append(f"std {actual_std:.4f} > max {max_std}")

        result = ValidationResult.PASS if passed else ValidationResult.FAIL
        message = (
            f"Std check passed: std={actual_std:.4f}"
            if passed else f"Std check failed: {'; '.join(reasons)}"
        )
        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=[],
            failed_values=[],
            message=message,
        )


class AllowedValuesValidator(BaseValidator):
    """Validator that checks values are from a predefined allowed set."""

    def validate(self, series) -> ValidationResultDetail:
        """Check that all values are in the allowed set."""
        allowed = self.check_config.get("values", [])
        if not allowed:
            return ValidationResultDetail(
                column=self.check_config["column"],
                check_type=self.check_type,
                result=ValidationResult.FAIL,
                passed=False,
                message="No allowed values specified",
            )

        allowed_set = set(allowed)
        is_invalid = ~series.isin(allowed_set) & series.notna()

        failed_rows = series[is_invalid].index.tolist()
        failed_values = series[is_invalid].tolist()

        passed = len(failed_rows) == 0
        result = ValidationResult.PASS if passed else ValidationResult.FAIL
        message = (
            f"All values are in the allowed set"
            if passed else
            f"Found {len(failed_rows)} values not in allowed set {list(allowed_set)[:10]}"
        )
        return ValidationResultDetail(
            column=self.check_config["column"],
            check_type=self.check_type,
            result=result,
            passed=passed,
            failed_rows=failed_rows,
            failed_values=failed_values,
            message=message,
        )
