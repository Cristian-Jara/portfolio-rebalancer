"""Unit tests for `src.validation`."""

import math
import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    PortfolioError,
)
from src.validation import to_decimal


class TestToDecimal(unittest.TestCase):
    def test_valid_integers(self) -> None:
        self.assertEqual(to_decimal(0, "amount"), Decimal("0"))
        self.assertEqual(to_decimal(42, "shares"), Decimal("42"))
        self.assertEqual(to_decimal(-10, "delta"), Decimal("-10"))

    def test_valid_floats_avoid_binary_artifacts(self) -> None:
        self.assertEqual(to_decimal(0.1, "weight"), Decimal("0.1"))
        self.assertEqual(to_decimal(0.2, "weight"), Decimal("0.2"))
        self.assertEqual(to_decimal(500.25, "price"), Decimal("500.25"))

    def test_valid_strings(self) -> None:
        self.assertEqual(to_decimal("100", "price"), Decimal("100"))
        self.assertEqual(to_decimal("215.50", "price"), Decimal("215.50"))
        self.assertEqual(to_decimal("  12.34  ", "price"), Decimal("12.34"))
        self.assertEqual(to_decimal("1e-6", "tolerance"), Decimal("1e-6"))

    def test_valid_decimal_passthrough(self) -> None:
        value = Decimal("123.456")
        self.assertIs(to_decimal(value, "price"), value)

    def test_booleans_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name="shares")
        )
        for invalid_bool in (True, False):
            with (
                self.subTest(value=invalid_bool),
                self.assertRaisesRegex(InvalidNumericError, expected_msg),
            ):
                to_decimal(invalid_bool, "shares")

    def test_non_numeric_inputs_raise_invalid_numeric_error(self) -> None:
        invalid_values = ["", "   ", "abc", None, [1], {"a": 1}, object()]
        for invalid in invalid_values:
            expected_msg = re.escape(
                ErrorMessages.INVALID_NUMERIC_VALUE.format(
                    field_name="price", value=invalid
                )
            )
            with (
                self.subTest(value=invalid),
                self.assertRaisesRegex(InvalidNumericError, expected_msg),
            ):
                to_decimal(invalid, "price")

    def test_non_finite_numbers_raise_invalid_numeric_error(self) -> None:
        expected_msg = re.escape(
            ErrorMessages.NON_FINITE_NUMBER.format(field_name="price")
        )
        non_finite_values = [
            float("nan"),
            float("inf"),
            float("-inf"),
            math.nan,
            math.inf,
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            "NaN",
            "Infinity",
            "-Infinity",
        ]
        for invalid in non_finite_values:
            with (
                self.subTest(value=invalid),
                self.assertRaisesRegex(InvalidNumericError, expected_msg),
            ):
                to_decimal(invalid, "price")

    def test_exception_inheritance(self) -> None:
        self.assertTrue(issubclass(InvalidNumericError, PortfolioError))
        self.assertTrue(issubclass(InvalidNumericError, ValueError))


if __name__ == "__main__":
    unittest.main()
