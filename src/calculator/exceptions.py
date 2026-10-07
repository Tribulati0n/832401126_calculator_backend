"""Custom exceptions for the calculator domain.

All calculator failures are represented by :class:`CalculatorError`
subclasses so that the API layer can translate them into clean
HTTP 400 responses without leaking Python internals to the client.
"""


class CalculatorError(Exception):
    """Base class for every error raised by the calculation engine."""


class InvalidExpressionError(CalculatorError):
    """The expression is syntactically invalid or contains unsafe input."""


class DivisionByZeroError(CalculatorError):
    """The expression attempts to divide (or take modulo) by zero."""


class MathDomainError(CalculatorError):
    """A function was called outside its domain, e.g. sqrt(-1)."""


class NumberOverflowError(CalculatorError):
    """An intermediate or final value exceeds the supported numeric range."""
