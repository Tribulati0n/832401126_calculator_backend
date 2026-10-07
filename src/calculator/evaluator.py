"""AST evaluator for calculator expressions.

This module walks the AST produced by :class:`~src.calculator.parser.Parser`
and computes the numeric result.  All mathematical rules — operator
precedence, unary operators, domain restrictions and division by zero —
are enforced here, on the back end.
"""

from __future__ import annotations

import math

from .exceptions import DivisionByZeroError, MathDomainError, NumberOverflowError

# Python floats can hold roughly up to 1.8e308; we reject anything beyond
# a safe margin so overflow never silently becomes ``inf``.
_MAX_ABS_VALUE = 1.0e308

_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}

# Trigonometric functions are evaluated in degrees, which matches the
# convention most students expect from a hand-held scientific calculator.
_DEG_TO_RAD = math.pi / 180.0


def _check_overflow(value: float) -> float:
    """Raise if ``value`` is not a finite, in-range number."""
    if not math.isfinite(value) or abs(value) > _MAX_ABS_VALUE:
        raise NumberOverflowError("Result is too large to represent")
    return value


def _binary(op: str, left: float, right: float) -> float:
    """Apply a binary operator with explicit error handling."""
    if op == "+":
        return _check_overflow(left + right)
    if op == "-":
        return _check_overflow(left - right)
    if op == "*":
        return _check_overflow(left * right)
    if op == "/":
        if right == 0:
            raise DivisionByZeroError("Division by zero")
        return _check_overflow(left / right)
    if op == "%":
        if right == 0:
            raise DivisionByZeroError("Modulo by zero")
        return _check_overflow(math.fmod(left, right))
    if op == "^":
        if left < 0 and not float(right).is_integer():
            raise MathDomainError(
                "Negative base with a non-integer exponent is undefined"
            )
        try:
            return _check_overflow(math.pow(left, right))
        except OverflowError as exc:
            raise NumberOverflowError("Result is too large to represent") from exc
    raise ValueError(f"Unknown operator {op!r}")  # pragma: no cover


def _apply_function(name: str, args: list[float]) -> float:
    """Evaluate a named function with domain validation."""
    (x,) = args
    try:
        if name == "sqrt":
            if x < 0:
                raise MathDomainError("sqrt of a negative number is undefined")
            return _check_overflow(math.sqrt(x))
        if name == "cbrt":
            return _check_overflow(math.copysign(abs(x) ** (1.0 / 3.0), x))
        if name == "abs":
            return _check_overflow(abs(x))
        if name == "ln":
            if x <= 0:
                raise MathDomainError("ln is only defined for x > 0")
            return _check_overflow(math.log(x))
        if name == "log" or name == "log10":
            if x <= 0:
                raise MathDomainError("log is only defined for x > 0")
            return _check_overflow(math.log10(x))
        if name == "log2":
            if x <= 0:
                raise MathDomainError("log2 is only defined for x > 0")
            return _check_overflow(math.log2(x))
        if name == "exp":
            return _check_overflow(math.exp(x))
        if name == "sin":
            return _check_overflow(math.sin(x * _DEG_TO_RAD))
        if name == "cos":
            return _check_overflow(math.cos(x * _DEG_TO_RAD))
        if name == "tan":
            cosine = math.cos(x * _DEG_TO_RAD)
            if cosine == 0:
                raise MathDomainError("tan is undefined at this angle")
            return _check_overflow(math.tan(x * _DEG_TO_RAD))
        if name == "asin":
            if not -1 <= x <= 1:
                raise MathDomainError("asin is only defined for -1 <= x <= 1")
            return _check_overflow(math.degrees(math.asin(x)))
        if name == "acos":
            if not -1 <= x <= 1:
                raise MathDomainError("acos is only defined for -1 <= x <= 1")
            return _check_overflow(math.degrees(math.acos(x)))
        if name == "atan":
            return _check_overflow(math.degrees(math.atan(x)))
        if name == "sinh":
            return _check_overflow(math.sinh(x))
        if name == "cosh":
            return _check_overflow(math.cosh(x))
        if name == "tanh":
            return _check_overflow(math.tanh(x))
        if name == "floor":
            return _check_overflow(float(math.floor(x)))
        if name == "ceil":
            return _check_overflow(float(math.ceil(x)))
        if name == "sign":
            if x > 0:
                return 1.0
            if x < 0:
                return -1.0
            return 0.0
        if name == "round":
            return _check_overflow(float(round(x)))
        if name == "fact":
            if x < 0 or not float(x).is_integer():
                raise MathDomainError("factorial is only defined for "
                                      "non-negative integers")
            n = int(x)
            if n > 170:  # 171! already exceeds float range
                raise NumberOverflowError("Factorial is too large to represent")
            return _check_overflow(float(math.factorial(n)))
    except (OverflowError, ValueError) as exc:
        raise NumberOverflowError("Result is too large to represent") from exc
    raise ValueError(f"Unknown function {name!r}")  # pragma: no cover


def evaluate(node: tuple) -> float:
    """Evaluate an AST node and return a float result."""
    kind = node[0]

    if kind == "num":
        return _check_overflow(node[1])

    if kind == "const":
        return _check_overflow(_CONSTANTS[node[1]])

    if kind == "neg":
        return _check_overflow(-evaluate(node[1]))

    if kind == "fact":
        # Postfix factorial: 5! == fact(5)
        return _apply_function("fact", [evaluate(node[1])])

    if kind == "binop":
        return _binary(node[1], evaluate(node[2]), evaluate(node[3]))

    if kind == "func":
        name, arg_nodes = node[1], node[2]
        args = [evaluate(arg) for arg in arg_nodes]
        return _apply_function(name, args)

    raise ValueError(f"Unknown AST node {kind!r}")  # pragma: no cover


def format_result(value: float) -> str:
    """Format a float for storage and display.

    Integers print without a decimal point; other values are rounded to
    12 significant digits to hide float-representation noise such as
    ``0.30000000000000004`` for ``0.1 + 0.2``.
    """
    if value == 0:
        return "0"
    if float(value).is_integer() and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.12g}"
