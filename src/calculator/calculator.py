"""Public facade for the calculation engine.

``safe_calculate`` is the single entry point used by the service layer.
It normalizes the user input, applies limits, tokenizes, parses and
evaluates the expression, and returns a ready-to-display result string.
No ``eval`` / ``exec`` is used anywhere in the pipeline.
"""

from __future__ import annotations

from .evaluator import evaluate, format_result
from .exceptions import InvalidExpressionError
from .lexer import tokenize
from .parser import parse

# Guard against pathological payloads (DoS protection).
MAX_EXPRESSION_LENGTH = 200

# Accept the friendly symbols some front ends send and normalize them to
# the ASCII form the lexer understands.
_TRANSLATION = str.maketrans({
    "×": "*",
    "÷": "/",
    "−": "-",
    "＋": "+",
    "π": "pi",
    "√": "sqrt",
})


def normalize_expression(expression: str) -> str:
    """Strip whitespace and normalize unicode symbols."""
    return expression.strip().translate(_TRANSLATION)


def safe_calculate(expression: str) -> float:
    """Evaluate ``expression`` and return the numeric result."""
    if not expression:
        raise InvalidExpressionError("Expression is empty")

    text = normalize_expression(expression)
    if len(text) > MAX_EXPRESSION_LENGTH:
        raise InvalidExpressionError(
            f"Expression exceeds the maximum length of "
            f"{MAX_EXPRESSION_LENGTH} characters"
        )

    tokens = tokenize(text)
    ast = parse(tokens)
    return evaluate(ast)
