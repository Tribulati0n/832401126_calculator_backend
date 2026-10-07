"""Tokenizer for calculator expressions.

The lexer turns the raw expression string into a flat list of
:class:`Token` objects.  It is the first line of defence against
arbitrary code execution: only a strict whitelist of characters is
accepted, so constructs such as ``__import__("os")`` or ``1;2`` can
never even reach the parser.
"""

from __future__ import annotations

import re

from .exceptions import InvalidExpressionError

# Characters allowed anywhere in an expression.  Note that quotes,
# semicolons, equals signs and other "programming" characters are
# deliberately missing.
_ALLOWED_CHARS = re.compile(r"^[0-9+\-*/^%().,\sA-Za-z_!]+$")

# A number may be an integer, a decimal, or scientific notation.
_NUMBER_RE = re.compile(
    r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?"
)
# Identifiers are used for function names (sqrt, sin, ...) and constants.
_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Operators supported by the grammar, in their canonical form.
_OPERATORS = {"+", "-", "*", "/", "%", "^", "!"}


class TokenType:
    """Constants for the token kinds produced by the lexer."""

    NUMBER = "NUMBER"
    OPERATOR = "OPERATOR"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    NAME = "NAME"
    END = "END"


class Token:
    """A single lexical token with its source position (for messages)."""

    __slots__ = ("type", "value", "position")

    def __init__(self, token_type: str, value: object, position: int) -> None:
        self.type = token_type
        self.value = value
        self.position = position

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.type}, {self.value!r}, pos={self.position})"


def tokenize(text: str) -> list[Token]:
    """Convert ``text`` into a token list terminated by an END token."""
    if not _ALLOWED_CHARS.match(text):
        raise InvalidExpressionError("Expression contains illegal characters")

    tokens: list[Token] = []
    index = 0
    length = len(text)

    while index < length:
        char = text[index]

        if char.isspace():
            index += 1
            continue

        if char.isdigit() or (char == "." and index + 1 < length
                              and text[index + 1].isdigit()):
            match = _NUMBER_RE.match(text, index)
            assert match is not None
            raw = match.group(0)
            tokens.append(Token(TokenType.NUMBER, raw, index))
            index = match.end()
            continue

        if char in _OPERATORS:
            tokens.append(Token(TokenType.OPERATOR, char, index))
            index += 1
            continue

        if char == "(":
            tokens.append(Token(TokenType.LPAREN, char, index))
            index += 1
            continue

        if char == ")":
            tokens.append(Token(TokenType.RPAREN, char, index))
            index += 1
            continue

        if char == ",":
            tokens.append(Token(TokenType.COMMA, char, index))
            index += 1
            continue

        if char.isalpha() or char == "_":
            match = _NAME_RE.match(text, index)
            assert match is not None
            name = match.group(0)
            tokens.append(Token(TokenType.NAME, name, index))
            index = match.end()
            continue

        # Unreachable for any string that passed the whitelist, kept as a
        # safety net.
        raise InvalidExpressionError(
            f"Unexpected character {char!r} at position {index}"
        )

    tokens.append(Token(TokenType.END, None, length))
    return tokens
