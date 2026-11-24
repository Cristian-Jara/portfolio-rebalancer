"""Unit tests for `src.exceptions`."""

import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidStockIdError,
    MissingAllocationError,
    PortfolioError,
)


class TestExceptionHierarchy(unittest.TestCase):
    def test_all_exceptions_inherit_from_portfolio_error(self) -> None:
        domain_exceptions = (
            InvalidNumericError,
            InvalidStockError,
            InvalidStockIdError,
            InvalidPriceError,
            InvalidAssetTypeError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        )
        for exc_cls in domain_exceptions:
            with self.subTest(exception=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, PortfolioError))

    def test_value_error_subclasses(self) -> None:
        value_error_exceptions = (
            InvalidNumericError,
            InvalidStockError,
            InvalidStockIdError,
            InvalidPriceError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        )
        for exc_cls in value_error_exceptions:
            with self.subTest(exception=exc_cls.__name__):
                self.assertTrue(issubclass(exc_cls, ValueError))

    def test_type_error_subclasses(self) -> None:
        self.assertTrue(issubclass(InvalidAssetTypeError, TypeError))
        self.assertFalse(issubclass(InvalidAssetTypeError, ValueError))

    def test_stock_error_subclasses(self) -> None:
        self.assertTrue(issubclass(InvalidStockIdError, InvalidStockError))
        self.assertTrue(issubclass(InvalidPriceError, InvalidStockError))

    def test_catching_via_base_portfolio_error(self) -> None:
        with self.assertRaises(PortfolioError):
            raise InvalidStockIdError(ErrorMessages.EMPTY_STOCK_ID)

        with self.assertRaises(InvalidStockError):
            raise InvalidPriceError(ErrorMessages.NON_POSITIVE_PRICE)


class TestErrorMessages(unittest.TestCase):
    def test_parameterized_templates_format_cleanly(self) -> None:
        formatted_cases = [
            (
                ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name="shares"),
                "shares cannot be a boolean.",
            ),
            (
                ErrorMessages.INVALID_NUMERIC_VALUE.format(
                    field_name="price", value="abc"
                ),
                "Invalid numeric value for price: 'abc'.",
            ),
            (
                ErrorMessages.NON_FINITE_NUMBER.format(field_name="weight"),
                "weight must be a finite number.",
            ),
            (
                ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id="META"),
                "Target weight for META cannot be negative.",
            ),
            (
                ErrorMessages.DUPLICATE_ALLOCATION_STOCK_ID.format(stock_id="AAPL"),
                "Duplicate stock Id in target allocations: AAPL.",
            ),
            (
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("0.90")),
                "Target allocation weights must sum to 1.0 (100%), got 0.90.",
            ),
        ]
        for rendered, expected in formatted_cases:
            with self.subTest(expected=expected):
                self.assertEqual(rendered, expected)

    def test_static_messages_are_non_empty_strings(self) -> None:
        static_messages = (
            ErrorMessages.EMPTY_STOCK_ID,
            ErrorMessages.NON_POSITIVE_PRICE,
            ErrorMessages.EXPECTED_STOCK_INSTANCE,
            ErrorMessages.NEGATIVE_SHARES,
            ErrorMessages.EMPTY_ALLOCATIONS,
            ErrorMessages.INVALID_ALLOCATION_KEY,
            ErrorMessages.MISSING_TARGET_ALLOCATIONS,
        )
        for msg in static_messages:
            self.assertIsInstance(msg, str)
            self.assertTrue(msg.strip())


if __name__ == "__main__":
    unittest.main()
