"""Domain exception centralized error message templates."""


class ErrorMessages:
    """Centralized error message templates for the portfolio_manager package."""

    # Numeric & Validation
    BOOLEAN_NOT_ALLOWED = "{field_name} cannot be a boolean."
    INVALID_NUMERIC_VALUE = "Invalid numeric value for {field_name}: {value!r}."
    NON_FINITE_NUMBER = "{field_name} must be a finite number."

    # Stock
    EMPTY_STOCK_ID = "Stock Id (Ticker) must be a non-empty string."
    NON_POSITIVE_PRICE = "Stock price must be strictly greater than zero."

    # Portfolio & Holdings
    EXPECTED_STOCK_INSTANCE = "Expected a Stock instance."
    NEGATIVE_SHARES = "Share quantity cannot be negative."

    # Allocations & Rebalancing
    EMPTY_ALLOCATIONS = "Target allocations cannot be empty."
    INVALID_ALLOCATION_KEY = "Allocation keys must be Stock instances."
    NEGATIVE_TARGET_WEIGHT = "Target weight for {stock_id} cannot be negative."
    DUPLICATE_ALLOCATION_STOCK_ID = (
        "Duplicate stock Id in target allocations: {stock_id}."
    )
    WEIGHT_SUM_MISMATCH = (
        "Target allocation weights must sum to 1.0 (100%), got {total_weight}."
    )
    MISSING_TARGET_ALLOCATIONS = "Target allocations must be set before rebalancing."


class PortfolioError(Exception):
    """Base exception for all errors raised by the portfolio_manager package."""


class InvalidNumericError(PortfolioError, ValueError):
    """Raised when a numeric input is a boolean, unparseable, or non-finite."""


class InvalidStockError(PortfolioError, ValueError):
    """Base exception for invalid Stock attributes."""


class InvalidStockIdError(InvalidStockError):
    """Raised when a stock Id (ticker symbol) is missing or blank."""


class InvalidPriceError(InvalidStockError):
    """Raised when a stock price is zero, negative, or invalid."""


class InvalidAssetTypeError(PortfolioError, TypeError):
    """Raised when an object other than a Stock instance is provided."""


class InvalidHoldingError(PortfolioError, ValueError):
    """Raised when a portfolio holding operation receives invalid parameters."""


class InvalidAllocationError(PortfolioError, ValueError):
    """Raised when target allocation weights or keys violate domain invariants."""


class MissingAllocationError(PortfolioError, ValueError):
    """Raised when rebalancing is attempted before target allocations are set."""
