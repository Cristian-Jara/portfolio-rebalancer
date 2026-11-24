"""Stock domain entity representing a tradable equity."""

from decimal import Decimal

from src.exceptions import ErrorMessages, InvalidPriceError, InvalidStockIdError
from src.validation import Number, to_decimal


class Stock:
    """Represents a tradable equity with a stock_id and last available price."""

    def __init__(self, stock_id: str, last_price: Number) -> None:
        if not isinstance(stock_id, str) or not stock_id.strip():
            raise InvalidStockIdError(ErrorMessages.EMPTY_STOCK_ID)
        self.stock_id: str = stock_id.strip().upper()
        self._last_price: Decimal = self._validate_price(last_price)

    @staticmethod
    def _validate_price(price: Number) -> Decimal:
        decimal_price = to_decimal(price, "price")
        if decimal_price <= Decimal("0"):
            raise InvalidPriceError(ErrorMessages.NON_POSITIVE_PRICE)
        return decimal_price

    def current_price(self) -> Decimal:
        """Return the last available market price for this stock."""
        return self._last_price

    def update_price(self, new_price: Number) -> None:
        """Update the stock's last available market price."""
        self._last_price = self._validate_price(new_price)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented
        return self.stock_id == other.stock_id

    def __hash__(self) -> int:
        return hash(self.stock_id)

    def __repr__(self) -> str:
        return f"Stock(stock_id={self.stock_id!r}, current_price={self._last_price})"
