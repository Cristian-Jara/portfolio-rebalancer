"""Validation utilities for numeric inputs."""

from decimal import Decimal, InvalidOperation

from src.exceptions import ErrorMessages, InvalidNumericError

Number = int | float | str | Decimal


def to_decimal(value: Number, field_name: str) -> Decimal:
    """Safely convert numeric inputs into finite Decimal values."""
    if isinstance(value, bool):
        raise InvalidNumericError(
            ErrorMessages.BOOLEAN_NOT_ALLOWED.format(field_name=field_name)
        )
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise InvalidNumericError(
            ErrorMessages.INVALID_NUMERIC_VALUE.format(
                field_name=field_name, value=value
            )
        ) from exc

    if not result.is_finite():
        raise InvalidNumericError(
            ErrorMessages.NON_FINITE_NUMBER.format(field_name=field_name)
        )
    return result
