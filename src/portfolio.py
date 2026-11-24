"""
Portfolio management and rebalancing engine.

Architectural Notes & Assumptions:
- Separates current holdings (`_holdings`) from target policy (`_allocations`)
  while maintaining a `_stocks` registry so `.current_price()` is always
  available for both held and newly allocated positions.
- Computes trades across the set union (`held_stock_ids | target_stock_ids`) so
  orphan holdings are fully liquidated and unheld targets are initiated.
- Runs in O(n) time and O(n) space for `n` distinct stocks.
- Fractional shares are supported (exact dollar-to-share alignment).
- Rebalancing is self-financing (total BUY value == total SELL value).
- Target allocation weights must sum to 1.0 (100%) within `WEIGHT_TOLERANCE`.
"""

from decimal import Decimal

from src.exceptions import (
    ErrorMessages,
    InvalidAllocationError,
    InvalidAssetTypeError,
    InvalidHoldingError,
    MissingAllocationError,
)
from src.order import RebalanceOrder, TradeAction
from src.stock import Stock
from src.validation import Number, to_decimal


class Portfolio:
    """Manages current stock holdings, target allocation weights, and rebalancing."""

    WEIGHT_TOLERANCE = Decimal("1e-6")
    SHARE_TOLERANCE = Decimal("1e-9")

    def __init__(self) -> None:
        self._stocks: dict[str, Stock] = {}
        self._holdings: dict[str, Decimal] = {}
        self._allocations: dict[str, Decimal] = {}

    def add_holding(self, stock: Stock, shares: Number) -> None:
        """
        Add shares of a Stock to the portfolio's current holdings.
        Calling this multiple times for the same stock_id accumulates shares.
        """
        if not isinstance(stock, Stock):
            raise InvalidAssetTypeError(ErrorMessages.EXPECTED_STOCK_INSTANCE)
        qty = to_decimal(shares, "shares")
        if qty < Decimal("0"):
            raise InvalidHoldingError(ErrorMessages.NEGATIVE_SHARES)

        self._stocks[stock.stock_id] = stock
        self._holdings[stock.stock_id] = (
            self._holdings.get(stock.stock_id, Decimal("0")) + qty
        )

    def set_target_allocations(self, allocations: dict[Stock, Number]) -> None:
        """
        Define the desired portfolio distribution (e.g., {meta: 0.40, aapl: 0.60}).

        Validates that all weights are non-negative and sum to 1.0 (100%).
        Replaces any previously configured target allocation.
        """
        if not allocations:
            raise InvalidAllocationError(ErrorMessages.EMPTY_ALLOCATIONS)

        normalized_allocations: dict[str, Decimal] = {}
        registered_stocks: dict[str, Stock] = {}
        total_weight = Decimal("0")

        for stock, raw_weight in allocations.items():
            if not isinstance(stock, Stock):
                raise InvalidAssetTypeError(ErrorMessages.INVALID_ALLOCATION_KEY)
            weight = to_decimal(raw_weight, f"weight for {stock.stock_id}")
            if weight < Decimal("0"):
                raise InvalidAllocationError(
                    ErrorMessages.NEGATIVE_TARGET_WEIGHT.format(stock_id=stock.stock_id)
                )
            if stock.stock_id in normalized_allocations:
                raise InvalidAllocationError(
                    ErrorMessages.DUPLICATE_ALLOCATION_STOCK_ID.format(
                        stock_id=stock.stock_id
                    )
                )

            normalized_allocations[stock.stock_id] = weight
            registered_stocks[stock.stock_id] = stock
            total_weight += weight

        if abs(total_weight - Decimal("1")) > self.WEIGHT_TOLERANCE:
            raise InvalidAllocationError(
                ErrorMessages.WEIGHT_SUM_MISMATCH.format(total_weight=total_weight)
            )

        self._stocks.update(registered_stocks)
        self._allocations = normalized_allocations

    def total_value(self) -> Decimal:
        """Calculate total market value of all current holdings: sum(N_i * P_i)."""
        total = Decimal("0")
        for stock_id, shares in self._holdings.items():
            price = self._stocks[stock_id].current_price()
            total += shares * price
        return total

    def current_weights(self) -> dict[str, Decimal]:
        """Return actual portfolio weight (w_i = V_i / V_total) for each stock."""
        total = self.total_value()
        if total == Decimal("0"):
            return {}
        return {
            stock_id: (shares * self._stocks[stock_id].current_price()) / total
            for stock_id, shares in self._holdings.items()
            if shares > Decimal("0")
        }

    def rebalance(self) -> list[RebalanceOrder]:
        """
        Compute BUY, SELL, and HOLD instructions to align holdings with targets.

        Equations applied per asset `i` in (held_stock_ids | target_stock_ids):
            V_total = sum(N_i * P_i)
            V_i     = N_i * P_i
            V_i*    = w_i* * V_total
            dV_i    = V_i* - V_i
            dN_i    = dV_i / P_i

        Returns:
            A deterministic list of `RebalanceOrder` objects sorted by stock_id.
            Returns an empty list if the portfolio has zero total value.
        """
        if not self._allocations:
            raise MissingAllocationError(ErrorMessages.MISSING_TARGET_ALLOCATIONS)

        total = self.total_value()
        if total == Decimal("0"):
            return []

        orders: list[RebalanceOrder] = []
        universe = sorted(set(self._holdings.keys()) | set(self._allocations.keys()))

        for stock_id in universe:
            stock = self._stocks[stock_id]
            price = stock.current_price()

            current_shares = self._holdings.get(stock_id, Decimal("0"))
            current_value = current_shares * price
            current_weight = current_value / total

            target_weight = self._allocations.get(stock_id, Decimal("0"))
            target_value = target_weight * total

            delta_value = target_value - current_value
            delta_shares = delta_value / price

            if abs(delta_shares) <= self.SHARE_TOLERANCE:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.HOLD,
                        shares=Decimal("0"),
                        amount=Decimal("0"),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            elif delta_shares > Decimal("0"):
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.BUY,
                        shares=delta_shares,
                        amount=delta_value,
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )
            else:
                orders.append(
                    RebalanceOrder(
                        stock_id=stock_id,
                        action=TradeAction.SELL,
                        shares=abs(delta_shares),
                        amount=abs(delta_value),
                        current_weight=current_weight,
                        target_weight=target_weight,
                    )
                )

        return orders
