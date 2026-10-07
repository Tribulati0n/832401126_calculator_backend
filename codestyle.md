# Code Standard — 832401126_calculator_backend

## Standard source

This project follows **PEP 8 — Style Guide for Python Code**
(https://peps.python.org/pep-0008/), supplemented by the **Google Python
Style Guide** (https://google.github.io/styleguide/pyguide.html) where PEP 8
leaves room for interpretation.

Key references:

- PEP 8: https://peps.python.org/pep-0008/
- Google Python Style Guide: https://google.github.io/styleguide/pyguide.html
- PEP 257 (docstrings): https://peps.python.org/pep-0257/
- PEP 484 (type hints): https://peps.python.org/pep-0484/

## Conventions applied in this repository

### 1. Formatting

- 4-space indentation, no tabs. Max line length **88 characters**
  (Google style allows up to 80; 88 is used for readability with modern
  tooling).
- Single quotes preferred for short strings; double quotes only when the
  string contains a single quote.
- Imports grouped in the order: standard library → third-party → local,
  each group separated by a blank line, sorted alphabetically inside a
  group.
- `from __future__ import annotations` is placed at the top of every module
  that uses modern type syntax, so the code runs on Python 3.10+.

### 2. Naming

- `snake_case` for functions, methods and variables.
- `PascalCase` for classes (`Token`, `Parser`, `Database`, ...).
- `UPPER_SNAKE_CASE` for module-level constants (`_MAX_ABS_VALUE`,
  `MAX_EXPRESSION_LENGTH`).
- Private helpers start with a single underscore (`_binary`, `_factor`).
- `__slots__` is used on the hot-path `Token` class to reduce memory and
  attribute lookups.

### 3. Comments and docstrings

- Every module has a module docstring explaining its responsibility.
- Public functions and classes carry a one-line docstring; where the
  behavior is non-trivial (e.g. `parse`), the grammar is documented
  directly in the docstring.
- Comments explain *why*, not *what*; inline comments clarify non-obvious
  rules such as operator associativity or the overflow guard.

### 4. Type hints

- All function signatures use type hints (PEP 484), e.g.
  `def tokenize(text: str) -> list[Token]:`.
- Union types use the modern `X | None` syntax.

### 5. Error handling

- Domain errors are modeled as an exception hierarchy rooted at
  `CalculatorError` (`InvalidExpressionError`, `DivisionByZeroError`,
  `MathDomainError`, `NumberOverflowError`).
- The API layer catches only `CalculatorError` and translates it to HTTP
  400; unexpected exceptions fall through to the Flask 500 handler.
- Guards (`_check_overflow`) centralize numeric safety checks instead of
  sprinkling `try/except` through the evaluator.

### 6. Security

- **Never use `eval`/`exec`/`compile` on user input** (assignment rule).
- Input is validated by a strict character whitelist before tokenization.
- SQL is always parameterized (`?` placeholders); string concatenation is
  used only for validated identifiers (table/column names are constants in
  the code, never user input).

### 7. Structure

- Layered architecture: `controller` (HTTP) → `service` (business flow) →
  `model` (data) and a self-contained `calculator` package (pure engine).
- The engine package has no Flask dependency, so it is unit-testable in
  isolation.
- Configuration is centralized in `src/config.py` and env-var driven.

## Verification

```bash
python -m unittest discover -s tests -v   # 45 tests, all green
```
