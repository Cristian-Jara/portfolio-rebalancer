"""Unit tests for `src.order`."""

import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal

from src.order import RebalanceOrder, TradeAction


class TestTradeAction(unittest.TestCase):
    def test_enum_values_and_string_behavior(self) -> None:
        self.assertEqual(TradeAction.BUY, "BUY")
        self.assertEqual(TradeAction.SELL, "SELL")
        self.assertEqual(TradeAction.HOLD, "HOLD")
        self.assertIsInstance(TradeAction.BUY, str)

    def test_enum_lookup_from_string(self) -> None:
        self.assertIs(TradeAction("BUY"), TradeAction.BUY)
        self.assertIs(TradeAction("SELL"), TradeAction.SELL)
        self.assertIs(TradeAction("HOLD"), TradeAction.HOLD)

    def test_invalid_action_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            TradeAction("SHORT")


class TestRebalanceOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.order = RebalanceOrder(
            stock_id="META",
            action=TradeAction.SELL,
            shares=Decimal("2"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.40"),
        )

    def test_order_attributes(self) -> None:
        self.assertEqual(self.order.stock_id, "META")
        self.assertEqual(self.order.action, TradeAction.SELL)
        self.assertEqual(self.order.shares, Decimal("2"))
        self.assertEqual(self.order.amount, Decimal("1000.00"))
        self.assertEqual(self.order.current_weight, Decimal("0.50"))
        self.assertEqual(self.order.target_weight, Decimal("0.40"))

    def test_order_is_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.order.shares = Decimal("5")

        with self.assertRaises(FrozenInstanceError):
            self.order.action = TradeAction.BUY

    def test_order_equality_and_hashing(self) -> None:
        duplicate = RebalanceOrder(
            stock_id="META",
            action=TradeAction.SELL,
            shares=Decimal("2"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.40"),
        )
        different = RebalanceOrder(
            stock_id="AAPL",
            action=TradeAction.BUY,
            shares=Decimal("5"),
            amount=Decimal("1000.00"),
            current_weight=Decimal("0.50"),
            target_weight=Decimal("0.60"),
        )

        self.assertEqual(self.order, duplicate)
        self.assertEqual(hash(self.order), hash(duplicate))
        self.assertNotEqual(self.order, different)
        self.assertEqual(len({self.order, duplicate, different}), 2)


if __name__ == "__main__":
    unittest.main()
