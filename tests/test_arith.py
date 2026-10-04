"""Tests for the safe arithmetic evaluator (arith.py)."""

import pytest

from arith import evaluate


class TestBasicArithmetic:
    def test_addition(self):
        assert evaluate("5+3") == 8

    def test_subtraction(self):
        assert evaluate("10-4") == 6

    def test_multiplication(self):
        assert evaluate("7*6") == 42

    def test_division_returns_int_when_exact(self):
        assert evaluate("9/3") == 3

    def test_division_returns_float_when_inexact(self):
        assert evaluate("10/4") == 2.5

    def test_floor_division(self):
        assert evaluate("10//3") == 3

    def test_modulo(self):
        assert evaluate("10%3") == 1

    def test_power(self):
        assert evaluate("2**10") == 1024

    def test_parentheses(self):
        assert evaluate("(2+3)*4") == 20

    def test_unary_minus(self):
        assert evaluate("-5+2") == -3

    def test_unary_plus(self):
        assert evaluate("+5") == 5

    def test_operator_precedence(self):
        assert evaluate("2+3*4") == 14

    def test_decimals(self):
        assert evaluate("1.5*2") == 3

    def test_whitespace_tolerated(self):
        assert evaluate(" 5 + 3 ") == 8


class TestRejectsCodeExecution:
    """The whole point: eval() is gone, code must not run."""

    def test_import_statement_rejected(self):
        with pytest.raises(ValueError):
            evaluate("__import__('os')")

    def test_import_literal_rejected(self):
        with pytest.raises(ValueError):
            evaluate("__import__('os').system('id')")

    def test_call_rejected(self):
        with pytest.raises(ValueError):
            evaluate("os.system('id')")

    def test_attribute_access_rejected(self):
        with pytest.raises(ValueError):
            evaluate("().__class__")

    def test_name_rejected(self):
        with pytest.raises(ValueError):
            evaluate("evil")

    def test_string_literal_rejected(self):
        with pytest.raises(ValueError):
            evaluate("'hello'")

    def test_semicolon_sequence_rejected(self):
        with pytest.raises(ValueError):
            evaluate("1;2")

    def test_comparison_rejected(self):
        with pytest.raises(ValueError):
            evaluate("1 < 2")

    def test_assignment_rejected(self):
        with pytest.raises(ValueError):
            evaluate("a=1")


class TestErrorHandling:
    def test_empty_string(self):
        with pytest.raises(ValueError):
            evaluate("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            evaluate("   ")

    def test_none(self):
        with pytest.raises(ValueError):
            evaluate(None)

    def test_non_string(self):
        with pytest.raises(ValueError):
            evaluate(42)

    def test_division_by_zero(self):
        with pytest.raises(ValueError):
            evaluate("1/0")

    def test_floor_div_by_zero(self):
        with pytest.raises(ValueError):
            evaluate("1//0")

    def test_mod_by_zero(self):
        with pytest.raises(ValueError):
            evaluate("1%0")

    def test_garbage(self):
        with pytest.raises(ValueError):
            evaluate("hello world")

    def test_oversized_expression(self):
        with pytest.raises(ValueError):
            evaluate("1" * 300)