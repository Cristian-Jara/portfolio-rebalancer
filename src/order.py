"""Order-related data structures for the portfolio rebalancer."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class TradeAction(StrEnum):
    """Supported trade directives emitted by the rebalancing engine."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class RebalanceOrder:
    """
    Immutable trade instruction for a single stock.

    Attributes:
        stock_id: Stock identifier or symbol (e.g., 'META', 'AAPL').
        action: BUY, SELL, or HOLD directive.
        shares: Non-negative quantity of shares to buy or sell (0 for HOLD).
        amount: Non-negative monetary value of the trade (0 for HOLD).
        current_weight: Asset's weight in the portfolio prior to rebalancing.
        target_weight: Asset's desired weight in the portfolio.
    """

    stock_id: str
    action: TradeAction
    shares: Decimal
    amount: Decimal
    current_weight: Decimal
    target_weight: Decimal
