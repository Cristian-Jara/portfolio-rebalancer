"""Unit tests for `src.stock`."""

import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidNumericError,
    InvalidPriceError,
    InvalidStockError,
    InvalidStockIdError,
    PortfolioError,
)
from src.stock import Stock


class TestStock(unittest.TestCase):
    def test_stock_initialization_normalizes_id_and_sets_price(self) -> None:
        meta = Stock("  meta  ", 500.25)
        self.assertEqual(meta.stock_id, "META")
        self.assertEqual(meta.current_price(), Decimal("500.25"))

    def test_update_price(self) -> None:
        aapl = Stock("AAPL", 200)
        aapl.update_price("215.50")
        self.assertEqual(aapl.current_price(), Decimal("215.50"))

    def test_equality_and_hashing_by_stock_id(self) -> None:
        s1 = Stock("aapl", 200)
        s2 = Stock("AAPL", 210)
        s3 = Stock("META", 500)

        self.assertEqual(s1, s2)
        self.assertEqual(hash(s1), hash(s2))
        self.assertNotEqual(s1, s3)
        self.assertNotEqual(s1, "AAPL")

    def test_repr_contains_stock_id_and_price(self) -> None:
        meta = Stock("META", "500.25")
        self.assertEqual(repr(meta), "Stock(stock_id='META', current_price=500.25)")

    def test_invalid_stock_id_raises_invalid_stock_id_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.EMPTY_STOCK_ID)
        invalid_ids = ["", "   ", "\t\n", None, 123]
        for bad_id in invalid_ids:
            with (
                self.subTest(stock_id=bad_id),
                self.assertRaisesRegex(InvalidStockIdError, expected_msg),
            ):
                Stock(bad_id, 100)

    def test_non_positive_price_raises_invalid_price_error(self) -> None:
        expected_msg = re.escape(ErrorMessages.NON_POSITIVE_PRICE)
        for bad_price in (0, -50, "-0.01"):
            with (
                self.subTest(price=bad_price),
                self.assertRaisesRegex(InvalidPriceError, expected_msg),
            ):
                Stock("AAPL", bad_price)

        aapl = Stock("AAPL", 100)
        with self.assertRaisesRegex(InvalidPriceError, expected_msg):
            aapl.update_price(0)

    def test_invalid_numeric_price_raises_invalid_numeric_error(self) -> None:
        for bad_price in (True, False, "not-a-number", float("nan"), float("inf")):
            with self.subTest(price=bad_price), self.assertRaises(InvalidNumericError):
                Stock("AAPL", bad_price)

    def test_exception_hierarchy(self) -> None:
        self.assertTrue(issubclass(InvalidStockIdError, InvalidStockError))
        self.assertTrue(issubclass(InvalidPriceError, InvalidStockError))
        self.assertTrue(issubclass(InvalidStockError, PortfolioError))
        self.assertTrue(issubclass(InvalidStockError, ValueError))


if __name__ == "__main__":
    unittest.main()
