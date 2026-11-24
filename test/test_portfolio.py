"""Unit tests for `src.portfolio` and rebalancing logic."""

import re
import unittest
from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
    PortfolioError,
)
from src.order import TradeAction
from src.portfolio import Portfolio
from src.stock import Stock


class TestPortfolioValidation(unittest.TestCase):
    def test_invalid_stock_type_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        ):
            portfolio.add_holding("META", 10)

        with self.assertRaisesRegex(
            InvalidAssetTypeError, re.escape(ErrorMessages.INVALID_ALLOCATION_KEY)
        ):
            portfolio.set_target_allocations({"META": Decimal("1.0")})

    def test_negative_shares_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        with self.assertRaisesRegex(
            InvalidHoldingError, re.escape(ErrorMessages.NEGATIVE_SHARES)
        ):
            portfolio.add_holding(meta, -1)

    def test_accumulating_holdings_sums_shares(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        portfolio.add_holding(meta, 4)
        portfolio.add_holding(meta, 6)
        self.assertEqual(portfolio.total_value(), Decimal("5000"))

    def test_empty_allocations_rejected(self) -> None:
        portfolio = Portfolio()
        with self.assertRaisesRegex(
            InvalidAllocationError, re.escape(ErrorMessages.EMPTY_ALLOCATIONS)
        ):
            portfolio.set_target_allocations({})

    def test_target_allocations_must_sum_to_one(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("0.90"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.40"), aapl: Decimal("0.50")}
            )

        with self.assertRaisesRegex(
            InvalidAllocationError,
            re.escape(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=Decimal("1.20"))
            ),
        ):
            portfolio.set_target_allocations(
                {meta: Decimal("0.60"), aapl: Decimal("0.60")}
            )

    def test_negative_target_weight_rejected(self) -> None:
        portfolio = Portfolio()
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        expected_msg = re.escape(
            ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id="META")
        )
        with self.assertRaisesRegex(InvalidAllocationError, expected_msg):
            portfolio.set_target_allocations(
                {meta: Decimal("-0.20"), aapl: Decimal("1.20")}
            )

    def test_rebalance_without_allocations_raises_missing_allocation_error(
        self,
    ) -> None:
        portfolio = Portfolio()
        portfolio.add_holding(Stock("META", 500), 10)
        with self.assertRaisesRegex(
            MissingAllocationError,
            re.escape(ErrorMessages.MISSING_TARGET_ALLOCATIONS),
        ):
            portfolio.rebalance()

    def test_all_domain_exceptions_inherit_from_portfolio_error(self) -> None:
        for exc_cls in (
            InvalidAssetTypeError,
            InvalidHoldingError,
            InvalidAllocationError,
            MissingAllocationError,
        ):
            self.assertTrue(issubclass(exc_cls, PortfolioError))


class TestPortfolioRebalance(unittest.TestCase):
    def test_standard_rebalance_meta_and_aapl(self) -> None:
        """
        Hold 10 META @ $500 ($5,000 -> 50%) and 25 AAPL @ $200 ($5,000 -> 50%).
        Total = $10,000. Target: 40% META ($4,000), 60% AAPL ($6,000).
        Expected: SELL 2 META ($1,000), BUY 5 AAPL ($1,000).
        """
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        orders = {order.stock_id: order for order in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].shares, Decimal("2"))
        self.assertEqual(orders["META"].amount, Decimal("1000.00"))
        self.assertEqual(orders["META"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["META"].target_weight, Decimal("0.40"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("5"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))
        self.assertEqual(orders["AAPL"].current_weight, Decimal("0.5"))
        self.assertEqual(orders["AAPL"].target_weight, Decimal("0.60"))

    def test_rebalance_after_market_price_drift(self) -> None:
        """Portfolio starts balanced (40/60), then price drift triggers rebalance."""
        meta = Stock("META", 400)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 30)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        initial_orders = portfolio.rebalance()
        self.assertTrue(all(o.action == TradeAction.HOLD for o in initial_orders))

        # META surges to $700, AAPL stays $200 -> Total = $13,000
        meta.update_price(700)
        orders = {o.stock_id: o for o in portfolio.rebalance()}

        self.assertEqual(orders["META"].action, TradeAction.SELL)
        self.assertEqual(orders["META"].amount, Decimal("1800.00"))
        self.assertEqual(orders["META"].shares, Decimal("1800") / Decimal("700"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].amount, Decimal("1800.00"))
        self.assertEqual(orders["AAPL"].shares, Decimal("9"))

    def test_orphan_holding_liquidated_and_unheld_target_bought(self) -> None:
        """
        Held stock omitted from target allocations is sold completely;
        target stock with 0 held shares is bought from scratch.
        """
        goog = Stock("GOOG", 200)
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 250)

        portfolio = Portfolio()
        portfolio.add_holding(goog, 5)
        portfolio.add_holding(meta, 2)
        portfolio.set_target_allocations({meta: Decimal("0.50"), aapl: Decimal("0.50")})

        orders = {o.stock_id: o for o in portfolio.rebalance()}

        self.assertEqual(orders["GOOG"].action, TradeAction.SELL)
        self.assertEqual(orders["GOOG"].shares, Decimal("5"))
        self.assertEqual(orders["GOOG"].amount, Decimal("1000.00"))

        self.assertEqual(orders["META"].action, TradeAction.HOLD)
        self.assertEqual(orders["META"].shares, Decimal("0"))

        self.assertEqual(orders["AAPL"].action, TradeAction.BUY)
        self.assertEqual(orders["AAPL"].shares, Decimal("4"))
        self.assertEqual(orders["AAPL"].amount, Decimal("1000.00"))

    def test_self_financing_conservation_of_value(self) -> None:
        """Sum of BUY amounts must always equal sum of SELL amounts."""
        stocks = [
            Stock("META", 512.35),
            Stock("AAPL", 227.80),
            Stock("MSFT", 418.10),
            Stock("NVDA", 135.45),
        ]
        portfolio = Portfolio()
        portfolio.add_holding(stocks[0], 7)
        portfolio.add_holding(stocks[1], 19)
        portfolio.add_holding(stocks[2], 3)

        portfolio.set_target_allocations(
            {
                stocks[0]: Decimal("0.25"),
                stocks[1]: Decimal("0.35"),
                stocks[2]: Decimal("0.15"),
                stocks[3]: Decimal("0.25"),
            }
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertEqual(total_buy, total_sell)

    def test_empty_portfolio_returns_no_orders(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        self.assertEqual(portfolio.total_value(), Decimal("0"))
        self.assertEqual(portfolio.current_weights(), {})
        self.assertEqual(portfolio.rebalance(), [])

    def test_rebalance_does_not_mutate_holdings(self) -> None:
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)
        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations({meta: Decimal("0.40"), aapl: Decimal("0.60")})

        before_weights = portfolio.current_weights()
        _ = portfolio.rebalance()
        after_weights = portfolio.current_weights()

        self.assertEqual(before_weights, after_weights)

    def test_near_unit_weights_are_normalized_to_preserve_self_financing(
        self,
    ) -> None:
        """Weights within WEIGHT_TOLERANCE normalize to 1.0 so BUY == SELL."""
        meta = Stock("META", 500)
        aapl = Stock("AAPL", 200)

        portfolio = Portfolio()
        portfolio.add_holding(meta, 10)
        portfolio.add_holding(aapl, 25)
        portfolio.set_target_allocations(
            {meta: Decimal("0.400001"), aapl: Decimal("0.60")}
        )

        orders = portfolio.rebalance()
        total_buy = sum(o.amount for o in orders if o.action == TradeAction.BUY)
        total_sell = sum(o.amount for o in orders if o.action == TradeAction.SELL)

        self.assertEqual(total_buy, total_sell)

    def test_high_price_disparity_preserves_funding_leg(self) -> None:
        """Tiny monetary shifts on high-priced stocks still emit matching SELL/BUY."""
        brk = Stock("BRK.A", 600000)
        penny = Stock("PENNY", 1)

        portfolio = Portfolio()
        portfolio.add_holding(brk, 1)
        portfolio.set_target_allocations(
            {brk: Decimal("0.999999999"), penny: Decimal("0.000000001")}
        )

        orders = {o.stock_id: o for o in portfolio.rebalance()}

        self.assertEqual(orders["BRK.A"].action, TradeAction.SELL)
        self.assertEqual(orders["BRK.A"].amount, Decimal("0.000600000"))
        self.assertEqual(orders["PENNY"].action, TradeAction.BUY)
        self.assertEqual(orders["PENNY"].amount, Decimal("0.000600000"))


if __name__ == "__main__":
    unittest.main()
