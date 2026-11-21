"""Arithmetic and button-state regression tests; no GUI or audio is needed."""

import unittest
from decimal import Decimal, getcontext

from calculator_core import CalculationError, CalculatorModel, evaluate_tokens


class CalculatorTests(unittest.TestCase):
    def setUp(self):
        self.model = CalculatorModel()

    def keys(self, *keys):
        for key in keys:
            self.model.press(key)
        return self.model.display

    def text(self, text):
        return self.keys(*text)

    def test_original_addition_regression(self):
        self.assertEqual(self.text("1+2="), "3")
        self.assertEqual(self.model.expression, "1 + 2 =")
        self.assertEqual(self.model.history, ["1 + 2 = 3"])

    def test_all_basic_operations(self):
        for expression, result in (("9-12=", "-3"), ("7*8=", "56"), ("8/4=", "2"), ("0+0=", "0")):
            with self.subTest(expression=expression):
                self.model.clear()
                self.assertEqual(self.text(expression), result)

    def test_precedence_and_left_associative_division(self):
        self.assertEqual(self.text("2+3*4="), "14")
        self.assertEqual(self.text("C24/4/2="), "3")
        self.assertEqual(self.text("C20-6/2+1="), "18")

    def test_decimal_arithmetic_is_not_binary_float(self):
        self.assertEqual(self.text("0.1+0.2="), "0.3")

    def test_leading_and_duplicate_decimal_points(self):
        self.assertEqual(self.text(".5+.2="), "0.7")
        self.assertEqual(self.text("C1..2="), "1.2")

    def test_leading_zeros_are_normalized(self):
        self.assertEqual(self.text("00012="), "12")

    def test_operator_replacement(self):
        self.assertEqual(self.text("9+-*2="), "18")

    def test_negative_operand_and_signed_zero_entry(self):
        self.assertEqual(self.keys("±", "5", "+", "3", "="), "-2")
        self.assertEqual(self.keys("C", "2", "*", "±", "3", "="), "-6")
        self.assertEqual(self.keys("C", "±", ".", "5", "="), "-0.5")

    def test_sign_changes_only_current_operand(self):
        self.assertEqual(self.keys("9", "+", "2", "±", "="), "7")

    def test_percent_is_current_operand_divided_by_100(self):
        self.assertEqual(self.keys("2", "0", "0", "+", "1", "0", "%", "="), "200.1")
        self.assertEqual(self.keys("C", "5", "0", "%", "="), "0.5")

    def test_square_root_is_current_operand(self):
        self.assertEqual(self.keys("1", "+", "9", "√", "="), "4")
        self.assertEqual(self.keys("C", "0", "√", "="), "0")

    def test_square_root_negative_error_and_recovery(self):
        self.keys("9", "±", "√")
        self.assertIsNotNone(self.model.error)
        self.assertEqual(self.model.display, "错误")
        self.assertEqual(self.text("2+3="), "5")

    def test_division_by_zero_then_clear_recovery(self):
        self.text("1/0=")
        self.assertIsNotNone(self.model.error)
        self.assertEqual(self.text("C6/2="), "3")

    def test_zero_divided_by_zero_is_an_error(self):
        self.text("0/0=")
        self.assertIsNotNone(self.model.error)

    def test_error_ignores_operators_but_allows_new_numeric_input(self):
        self.text("1/0=")
        self.text("+*=")
        self.assertIsNotNone(self.model.error)
        self.assertEqual(self.text(".5+1="), "1.5")

    def test_result_then_operator_continues(self):
        self.assertEqual(self.text("1+2=*4="), "12")

    def test_result_then_number_starts_new_calculation(self):
        self.assertEqual(self.text("1+2=4+5="), "9")

    def test_repeated_equal_does_not_repeat_operation_or_history(self):
        self.assertEqual(self.text("1+2==="), "3")
        self.assertEqual(len(self.model.history), 1)

    def test_initial_equal_is_noop(self):
        self.assertEqual(self.text("="), "0")
        self.assertEqual(self.model.history, [])

    def test_missing_final_operand_has_clear_error(self):
        self.text("1+=")
        self.assertIsNotNone(self.model.error)

    def test_backspace_edits_current_operand_only(self):
        self.text("12+34")
        self.assertEqual(self.keys("Backspace", "="), "15")
        self.keys("C", "1", "+", "Backspace", "2", "=")
        self.assertEqual(self.model.display, "3")

    def test_backspace_result_and_error_start_over(self):
        self.text("2+3=")
        self.assertEqual(self.keys("Backspace"), "0")
        self.text("1/0=")
        self.assertEqual(self.keys("Backspace"), "0")
        self.assertIsNone(self.model.error)

    def test_unary_result_next_digit_replaces_current_operand(self):
        self.assertEqual(self.keys("1", "+", "9", "√", "4", "="), "5")

    def test_history_retains_last_ten_and_clear_preserves_it(self):
        for number in range(12):
            self.text("C" + str(number) + "+1=")
        self.assertEqual(len(self.model.history), 10)
        self.assertEqual(self.model.history[0], "2 + 1 = 3")
        self.model.press("C")
        self.assertEqual(len(self.model.history), 10)
        self.assertEqual(self.model.display, "0")

    def test_unsupported_inputs_are_ignored(self):
        for key in ("", "a", "__import__", "12", None):
            self.model.press(key)
        self.assertEqual(self.model.display, "0")

    def test_digit_limit_and_recovery(self):
        self.text("1" * 24)
        self.assertIsNone(self.model.error)
        self.model.press("2")
        self.assertIsNotNone(self.model.error)
        self.assertEqual(self.text("3="), "3")

    def test_expression_length_limit(self):
        self.text("1+" * 32)
        self.assertIsNotNone(self.model.error)
        self.assertEqual(self.text("C2="), "2")

    def test_large_result_is_bounded(self):
        for _ in range(5):
            self.text("9" * 24)
            self.model.press("*")
        self.text("1=")
        self.assertIsNotNone(self.model.error)

    def test_scientific_display_retains_internal_precision(self):
        self.text("1/3=")
        self.assertLessEqual(len(self.model.display), 24)
        self.assertIn("E", self.model.display)
        self.text("*3=")
        # The internal result is not the shortened 16-digit display.
        self.assertEqual(Decimal(self.model._current), Decimal("0.9999999999999999999999999999"))

    def test_decimal_context_is_not_modified(self):
        old = getcontext().prec
        try:
            getcontext().prec = 6
            self.text("1/7=")
            self.assertEqual(getcontext().prec, 6)
            self.assertEqual(Decimal(self.model._current), Decimal("0.1428571428571428571428571429"))
        finally:
            getcontext().prec = old

    def test_token_evaluator_rejects_unsupported_expressions(self):
        for tokens in (["1", "**", "2"], ["__import__('os')"], ["NaN"], ["Infinity"], ["1", "+"]):
            with self.subTest(tokens=tokens), self.assertRaises(CalculationError):
                evaluate_tokens(tokens)


if __name__ == "__main__":
    unittest.main()
