"""Recursive-descent parser for calculator expressions.

Grammar (in order of increasing precedence)::

    expression := term (('+' | '-') term)*
    term       := factor (('*' | '/' | '%') factor)*
    factor     := ('+' | '-') factor | power
    power      := primary ('^' factor)?        # right associative
    primary    := NUMBER
                | CONSTANT                    # pi, e
                | NAME '(' expression (',' expression)* ')'
                | '(' expression ')'
                followed by any number of postfix '!' factorial operators

The output is an AST made of tuples::

    ("num", value)
    ("const", name)
    ("neg", node)
    ("binop", op, left, right)
    ("func", name, [arg1, arg2, ...])

Because we build an AST and then evaluate it ourselves, the user's input is
never executed as code.
"""

from __future__ import annotations

from .exceptions import InvalidExpressionError
from .lexer import Token, TokenType

# Name -> arity mapping; the evaluator additionally validates the name.
KNOWN_FUNCTIONS = {
    "sqrt": 1, "cbrt": 1, "abs": 1, "ln": 1, "log": 1, "log2": 1,
    "log10": 1, "exp": 1, "sin": 1, "cos": 1, "tan": 1,
    "asin": 1, "acos": 1, "atan": 1, "sinh": 1, "cosh": 1, "tanh": 1,
    "fact": 1, "floor": 1, "ceil": 1, "sign": 1, "round": 1,
}

KNOWN_CONSTANTS = {"pi", "e"}


class Parser:
    """Turn a token list into an AST."""

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._index = 0

    # -- token stream helpers -------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._index]

    def _advance(self) -> Token:
        token = self._tokens[self._index]
        self._index += 1
        return token

    def _expect(self, token_type: str, what: str) -> Token:
        token = self._peek()
        if token.type != token_type:
            raise InvalidExpressionError(
                f"Expected {what} but found {token.value!r} "
                f"at position {token.position}"
            )
        return self._advance()

    def _expect_operator(self, op: str) -> Token:
        token = self._peek()
        if token.type != TokenType.OPERATOR or token.value != op:
            raise InvalidExpressionError(
                f"Expected {op!r} but found {token.value!r} "
                f"at position {token.position}"
            )
        return self._advance()

    # -- grammar rules --------------------------------------------------

    def parse(self) -> tuple:
        """Parse the whole token stream into an AST."""
        if self._peek().type == TokenType.END:
            raise InvalidExpressionError("Expression is empty")
        node = self._expression()
        token = self._peek()
        if token.type != TokenType.END:
            raise InvalidExpressionError(
                f"Unexpected token {token.value!r} at position {token.position}"
            )
        return node

    def _expression(self) -> tuple:
        node = self._term()
        while True:
            token = self._peek()
            if token.type == TokenType.OPERATOR and token.value in ("+", "-"):
                self._advance()
                node = ("binop", token.value, node, self._term())
            else:
                return node

    def _term(self) -> tuple:
        node = self._factor()
        while True:
            token = self._peek()
            if token.type == TokenType.OPERATOR and token.value in ("*", "/", "%"):
                self._advance()
                node = ("binop", token.value, node, self._factor())
            else:
                return node

    def _factor(self) -> tuple:
        token = self._peek()
        if token.type == TokenType.OPERATOR and token.value in ("+", "-"):
            self._advance()
            inner = self._factor()
            # "+x" is just x; "-x" becomes a unary negation node.
            return inner if token.value == "+" else ("neg", inner)
        return self._power()

    def _power(self) -> tuple:
        node = self._primary()
        token = self._peek()
        if token.type == TokenType.OPERATOR and token.value == "^":
            self._advance()
            # Right associative: 2^3^2 == 2^(3^2)
            exponent = self._factor()
            node = ("binop", "^", node, exponent)
        return node

    def _postfix_factorial(self, node: tuple) -> tuple:
        """Wrap ``node`` in factorial nodes for each trailing ``!``."""
        while (self._peek().type == TokenType.OPERATOR
               and self._peek().value == "!"):
            self._advance()
            node = ("fact", node)
        return node

    def _primary(self) -> tuple:
        token = self._peek()

        if token.type == TokenType.END:
            raise InvalidExpressionError(
                f"Expression ended unexpectedly at position {token.position}"
            )

        if token.type == TokenType.NUMBER:
            self._advance()
            return self._postfix_factorial(("num", float(token.value)))

        if token.type == TokenType.LPAREN:
            self._advance()
            node = self._expression()
            self._expect(TokenType.RPAREN, "')'")
            return self._postfix_factorial(node)

        if token.type == TokenType.NAME:
            self._advance()
            if self._peek().type == TokenType.LPAREN:
                return self._function_call(token)
            if token.value in KNOWN_CONSTANTS:
                return self._postfix_factorial(("const", token.value))
            raise InvalidExpressionError(
                f"Unknown name {token.value!r} at position {token.position}"
            )

        raise InvalidExpressionError(
            f"Unexpected token {token.value!r} at position {token.position}"
        )

    def _function_call(self, name_token: Token) -> tuple:
        """Parse ``name ( arg, arg, ... )`` and validate the arity."""
        if name_token.value not in KNOWN_FUNCTIONS:
            raise InvalidExpressionError(
                f"Unknown function {name_token.value!r} "
                f"at position {name_token.position}"
            )
        self._expect(TokenType.LPAREN, "'('")
        args: list[tuple] = []
        if self._peek().type != TokenType.RPAREN:
            args.append(self._expression())
            while self._peek().type == TokenType.COMMA:
                self._advance()
                args.append(self._expression())
        self._expect(TokenType.RPAREN, "')'")
        expected = KNOWN_FUNCTIONS[name_token.value]
        if len(args) != expected:
            raise InvalidExpressionError(
                f"Function {name_token.value!r} expects {expected} argument(s) "
                f"but got {len(args)}"
            )
        return ("func", name_token.value, args)


def parse(tokens: list[Token]) -> tuple:
    """Convenience wrapper around :class:`Parser`."""
    return Parser(tokens).parse()
