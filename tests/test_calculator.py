"""Unit and API tests for the calculator backend.

Run with::

    python -m unittest discover -s tests -v

or::

    pytest tests -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.calculator.calculator import safe_calculate
from src.calculator.exceptions import (
    DivisionByZeroError,
    InvalidExpressionError,
    MathDomainError,
    NumberOverflowError,
)
from src.config import Config
from src.model.database import Database


class EngineTestCase(unittest.TestCase):
    """Tests for the expression engine (no HTTP involved)."""

    def assert_result(self, expression: str, expected: float):
        self.assertAlmostEqual(safe_calculate(expression), expected, places=10)

    # -- basic arithmetic ------------------------------------------------

    def test_addition(self):
        self.assert_result("12+8", 20)

    def test_subtraction(self):
        self.assert_result("12-8", 4)

    def test_multiplication(self):
        self.assert_result("5*8", 40)

    def test_division(self):
        self.assert_result("10/2", 5)

    # -- precedence and parentheses --------------------------------------

    def test_operator_precedence(self):
        self.assert_result("1+2*3", 7)
        self.assert_result("8-3*2", 2)
        self.assert_result("10/2+7", 12)

    def test_parentheses(self):
        self.assert_result("(1+2)*3", 9)
        self.assert_result("(2+3)*(4+1)", 25)
        self.assert_result("((2+3))*2", 10)

    def test_power_right_associative(self):
        self.assert_result("2^3^2", 512)
        self.assert_result("2^10", 1024)

    def test_postfix_factorial(self):
        self.assert_result("5!", 120)
        self.assert_result("(2+3)!", 120)
        self.assert_result("3!*2", 12)

    # -- unary plus/minus ------------------------------------------------

    def test_unary_minus_at_start(self):
        self.assert_result("-5+8", 3)

    def test_unary_minus_after_operator(self):
        self.assert_result("3*-2", -6)

    def test_unary_minus_and_power(self):
        self.assert_result("-2^2", -4)  # -(2^2), per mathematical convention
        self.assert_result("2^-2", 0.25)

    def test_unary_plus(self):
        self.assert_result("+5+3", 8)

    def test_double_negation(self):
        self.assert_result("--5", 5)

    # -- decimals --------------------------------------------------------

    def test_decimals(self):
        self.assert_result("1.5*2", 3)
        self.assert_result("0.1+0.2", 0.3)
        self.assert_result(".5+.25", 0.75)

    def test_scientific_notation(self):
        self.assert_result("1e3+1", 1001)

    # -- scientific functions and constants ------------------------------

    def test_sqrt(self):
        self.assert_result("sqrt(9)", 3)

    def test_sin_degrees(self):
        self.assertAlmostEqual(safe_calculate("sin(30)"), 0.5, places=10)

    def test_log10(self):
        self.assert_result("log10(1000)", 3)

    def test_ln_e(self):
        self.assertAlmostEqual(safe_calculate("ln(e)"), 1.0, places=10)

    def test_factorial(self):
        self.assert_result("fact(5)", 120)

    def test_pi_constant(self):
        self.assertAlmostEqual(safe_calculate("pi"), 3.141592653589793, places=10)

    def test_expression_with_functions(self):
        self.assertAlmostEqual(
            safe_calculate("sqrt(2^2+3^2)"), 3.605551275463989, places=10
        )

    # -- invalid expressions ---------------------------------------------

    def test_empty(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("")

    def test_unbalanced_parentheses(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("(1+2")
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1+2)")

    def test_dangling_operator(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1+")
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("*3")

    def test_illegal_characters(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1+2;3")
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1 == 2")
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("import os")

    def test_code_injection_blocked(self):
        # The classic eval-based attack must not work.
        with self.assertRaises(InvalidExpressionError):
            safe_calculate('__import__("os").system("ls")')
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1 and 2")

    def test_unknown_name(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("foo(1)")

    def test_wrong_arity(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("sqrt(1,2)")

    def test_too_long(self):
        with self.assertRaises(InvalidExpressionError):
            safe_calculate("1" * 300)

    # -- division by zero ------------------------------------------------

    def test_division_by_zero(self):
        with self.assertRaises(DivisionByZeroError):
            safe_calculate("1/0")
        with self.assertRaises(DivisionByZeroError):
            safe_calculate("10/(5-5)")

    # -- domain and overflow ---------------------------------------------

    def test_sqrt_negative(self):
        with self.assertRaises(MathDomainError):
            safe_calculate("sqrt(-1)")

    def test_negative_base_fractional_exponent(self):
        with self.assertRaises(MathDomainError):
            safe_calculate("(-8)^0.5")

    def test_overflow(self):
        with self.assertRaises(NumberOverflowError):
            safe_calculate("9^9^9")

    # -- symbol normalization --------------------------------------------

    def test_unicode_symbols_normalized(self):
        self.assert_result("12×8", 96)
        self.assert_result("10÷2", 5)
        self.assert_result("6−2", 4)
        self.assert_result("√(9)", 3)


class ApiTestCase(unittest.TestCase):
    """End-to-end tests against the real Flask application."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.temp_dir.name) / "test.db")

        class TestConfig(Config):
            DATABASE_PATH = cls.db_path

        from app import create_app

        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def _calculate(self, expression: str):
        return self.client.post(
            "/api/calculate", json={"expression": expression}
        )

    def test_calculate_success(self):
        response = self._calculate("(1+2)*3")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["expression"], "(1+2)*3")
        self.assertEqual(body["result"], "9")
        self.assertIn("id", body)
        self.assertIn("created_at", body)

    def test_calculate_error_returns_400(self):
        response = self._calculate("1/0")
        self.assertEqual(response.status_code, 400)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertIn("message", body)

    def test_calculate_invalid_json(self):
        response = self.client.post(
            "/api/calculate", data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_calculate_missing_expression(self):
        response = self.client.post("/api/calculate", json={})
        self.assertEqual(response.status_code, 400)

    def test_history_is_persisted(self):
        self._calculate("5*8")
        response = self.client.get("/api/history")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertGreaterEqual(body["total"], 1)
        self.assertEqual(body["data"][0]["expression"], "5*8")
        self.assertEqual(body["data"][0]["result"], "40")

    def test_history_search(self):
        self._calculate("77+11")
        response = self.client.get("/api/history?q=77")
        body = response.get_json()
        self.assertTrue(any("77" in item["expression"] for item in body["data"]))

    def test_history_pagination(self):
        self.client.delete("/api/history")  # isolate from other tests
        for i in range(5):
            self._calculate(f"{i}+{i}")
        response = self.client.get("/api/history?limit=2&offset=0")
        body = response.get_json()
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["total"], 5)

    def test_delete_history_record(self):
        record = self._calculate("3*3").get_json()
        response = self.client.delete(f"/api/history/{record['id']}")
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(f"/api/history/{record['id']}")
        self.assertEqual(response.status_code, 404)

    def test_clear_history(self):
        self._calculate("1+1")
        response = self.client.delete("/api/history")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertGreaterEqual(body["deleted"], 1)

        response = self.client.get("/api/history")
        self.assertEqual(response.get_json()["total"], 0)

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
