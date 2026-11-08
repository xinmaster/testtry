#!/usr/bin/env python3
"""Run the compiled calculator as a user would, using only Python's standard library."""

import argparse
import math
from pathlib import Path
import re
import subprocess
import unittest


RESULT = re.compile(
    r"计算结果：\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(V|A|Ω)"
)


class CalculatorTests(unittest.TestCase):
    executable = Path(__file__).resolve().parents[1] / "circuit_calculator"

    def run_calculator(self, input_text):
        completed = subprocess.run(
            [str(self.executable)],
            input=input_text,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=False,
        )
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        return output

    def assert_results(self, output, expected):
        actual = [(float(number), unit) for number, unit in RESULT.findall(output)]
        self.assertEqual(len(actual), len(expected), output)
        for (number, unit), (expected_number, expected_unit) in zip(actual, expected):
            self.assertEqual(unit, expected_unit, output)
            self.assertTrue(
                math.isclose(number, expected_number, rel_tol=1e-9, abs_tol=0.0),
                f"{number!r} != {expected_number!r}\n{output}",
            )

    def assert_input_error(self, output):
        self.assertIn("输入错误", output)

    def test_voltage(self):
        self.assert_results(self.run_calculator("1\n2\n10\n0\n"), [(20, "V")])

    def test_current(self):
        self.assert_results(self.run_calculator("2\n12\n4\n0\n"), [(3, "A")])

    def test_resistance(self):
        self.assert_results(self.run_calculator("3\n12\n0.5\n0\n"), [(24, "Ω")])

    def test_series(self):
        self.assert_results(
            self.run_calculator("4\n3\n10\n20\n30\n0\n"), [(60, "Ω")]
        )

    def test_parallel(self):
        self.assert_results(
            self.run_calculator("5\n3\n100\n200\n300\n0\n"),
            [(600 / 11, "Ω")],
        )

    def test_multiple_calculations_in_one_session(self):
        output = self.run_calculator(
            "1\n2\n10\n2\n12\n4\n3\n12\n0.5\n"
            "4\n2\n10\n20\n5\n2\n6\n3\n0\n"
        )
        self.assert_results(
            output, [(20, "V"), (3, "A"), (24, "Ω"), (30, "Ω"), (2, "Ω")]
        )

    def test_quit(self):
        output = self.run_calculator("0\n")
        self.assert_results(output, [])
        self.assertNotIn("错误", output)

    def test_quit_ignores_following_input(self):
        self.assert_results(self.run_calculator("0\n1\n2\n10\n"), [])

    def test_eof_at_menu(self):
        output = self.run_calculator("")
        self.assert_results(output, [])
        self.assertNotIn("错误", output)

    def test_eof_during_each_calculation(self):
        for input_text in ("1\n", "1\n2\n", "2\n12\n", "3\n12\n", "4\n", "5\n"):
            with self.subTest(input_text=input_text):
                self.assert_results(self.run_calculator(input_text), [])

    def test_eof_midway_through_resistor_list(self):
        for operation in (4, 5):
            with self.subTest(operation=operation):
                self.assert_results(self.run_calculator(f"{operation}\n3\n10\n"), [])

    def test_last_line_without_newline(self):
        self.assert_results(self.run_calculator("1\n2\n10"), [(20, "V")])

    def test_invalid_final_line_without_newline(self):
        output = self.run_calculator("1\nabc")
        self.assert_input_error(output)
        self.assert_results(output, [])

    def test_invalid_menu_choices_recover(self):
        for invalid in ("", "abc", "6", "-1", "1.5", "1 2", "0oops", "999999999999999999999999999"):
            with self.subTest(invalid=invalid):
                output = self.run_calculator(f"{invalid}\n1\n2\n10\n0\n")
                self.assert_input_error(output)
                self.assert_results(output, [(20, "V")])

    def test_invalid_numeric_inputs_recover(self):
        for invalid in (
            "", " ", "hello", "2amps", "1 2", "--1", "-2", "nan", "NaN",
            "inf", "-inf", "Infinity", "1e9999", "1e-9999",
        ):
            with self.subTest(invalid=invalid):
                output = self.run_calculator(f"1\n{invalid}\n2\n10\n0\n")
                self.assert_input_error(output)
                self.assert_results(output, [(20, "V")])

    def test_whitespace_decimal_and_scientific_notation(self):
        self.assert_results(
            self.run_calculator(" 1 \n\t2e-3 \n 1.5e3\t\n 0 \n"), [(3, "V")]
        )

    def test_zero_current_for_voltage(self):
        self.assert_results(self.run_calculator("1\n0\n10\n0\n"), [(0, "V")])

    def test_zero_resistance_for_voltage(self):
        self.assert_results(self.run_calculator("1\n2\n0\n0\n"), [(0, "V")])

    def test_zero_voltage_for_current_and_resistance(self):
        self.assert_results(
            self.run_calculator("2\n0\n10\n3\n0\n2\n0\n"),
            [(0, "A"), (0, "Ω")],
        )

    def test_division_by_zero_reprompts(self):
        for operation, numerator, denominator, expected_unit in (
            (2, 12, 4, "A"), (3, 12, 4, "Ω")
        ):
            with self.subTest(operation=operation):
                output = self.run_calculator(
                    f"{operation}\n{numerator}\n0\n{denominator}\n0\n"
                )
                self.assert_input_error(output)
                self.assert_results(output, [(3, expected_unit)])

    def test_invalid_resistor_counts_recover(self):
        for operation in (4, 5):
            for invalid in ("0", "-1", "1001", "2.5", "abc", "1 2", "999999999999999999999"):
                with self.subTest(operation=operation, invalid=invalid):
                    output = self.run_calculator(f"{operation}\n{invalid}\n1\n10\n0\n")
                    self.assert_input_error(output)
                    self.assert_results(output, [(10, "Ω")])

    def test_single_resistor(self):
        for operation in (4, 5):
            with self.subTest(operation=operation):
                self.assert_results(
                    self.run_calculator(f"{operation}\n1\n123.45\n0\n"), [(123.45, "Ω")]
                )

    def test_maximum_resistor_count(self):
        for operation, expected in ((4, 1000), (5, 0.001)):
            with self.subTest(operation=operation):
                self.assert_results(
                    self.run_calculator(f"{operation}\n1000\n" + "1\n" * 1000 + "0\n"),
                    [(expected, "Ω")],
                )

    def test_series_with_zero_resistors(self):
        self.assert_results(
            self.run_calculator("4\n3\n0\n10\n0\n0\n"), [(10, "Ω")]
        )

    def test_parallel_short_circuit(self):
        for resistors in ((0, 10, 20), (10, 0, 20), (10, 20, 0), (0, 0, 0)):
            with self.subTest(resistors=resistors):
                input_text = "5\n3\n" + "".join(f"{r}\n" for r in resistors) + "0\n"
                self.assert_results(self.run_calculator(input_text), [(0, "Ω")])

    def test_negative_resistor_recovers(self):
        for operation in (4, 5):
            with self.subTest(operation=operation):
                output = self.run_calculator(f"{operation}\n2\n10\n-3\n10\n0\n")
                self.assert_input_error(output)
                self.assert_results(output, [(20 if operation == 4 else 5, "Ω")])

    def test_long_menu_line_is_drained(self):
        output = self.run_calculator("1" * 600 + "\n1\n2\n10\n0\n")
        self.assert_input_error(output)
        self.assert_results(output, [(20, "V")])

    def test_long_numeric_line_is_drained(self):
        output = self.run_calculator("1\n" + "2" * 600 + "\n2\n10\n0\n")
        self.assert_input_error(output)
        self.assert_results(output, [(20, "V")])

    def test_exactly_255_byte_line_is_accepted(self):
        numeric_line = "2" + " " * 254
        self.assertEqual(len(numeric_line.encode("utf-8")), 255)
        output = self.run_calculator(f"1\n{numeric_line}\n10\n0\n")
        self.assertNotIn("错误", output)
        self.assert_results(output, [(20, "V")])

    def test_256_byte_line_is_rejected_and_recovers(self):
        numeric_line = "2" + " " * 255
        self.assertEqual(len(numeric_line.encode("utf-8")), 256)
        output = self.run_calculator(f"1\n{numeric_line}\n2\n10\n0\n")
        self.assertEqual(output.count("输入错误"), 1, output)
        self.assert_results(output, [(20, "V")])

    def test_embedded_nul_is_rejected_and_recovers(self):
        output = self.run_calculator("1\n2\0ignored\n2\n10\n0\n")
        self.assertEqual(output.count("输入错误"), 1, output)
        self.assert_results(output, [(20, "V")])

    def test_long_line_without_newline_terminates(self):
        output = self.run_calculator("1\n" + "2" * 600)
        self.assert_input_error(output)
        self.assert_results(output, [])

    def test_voltage_overflow_returns_to_menu(self):
        output = self.run_calculator("1\n1e308\n2\n1\n2\n10\n0\n")
        self.assertIn("计算错误", output)
        self.assert_results(output, [(20, "V")])

    def test_division_overflow_returns_to_menu(self):
        for operation in (2, 3):
            with self.subTest(operation=operation):
                output = self.run_calculator(f"{operation}\n1e308\n1e-100\n0\n")
                self.assertIn("计算错误", output)
                self.assert_results(output, [])

    def test_series_overflow_returns_to_menu(self):
        output = self.run_calculator("4\n2\n1e308\n1e308\n0\n")
        self.assertIn("计算错误", output)
        self.assert_results(output, [])

    def test_nonzero_result_underflow_is_reported(self):
        for input_text in (
            "1\n1e-200\n1e-200\n0\n",
            "2\n1e-300\n1e100\n0\n",
            "3\n1e-300\n1e100\n0\n",
        ):
            with self.subTest(input_text=input_text):
                output = self.run_calculator(input_text)
                self.assertIn("计算错误", output)
                self.assert_results(output, [])

    def test_parallel_extreme_resistors_remain_finite(self):
        for resistors, expected in (
            ((1e308, 1e308), 5e307),
            ((1e-300, 1e-300), 5e-301),
            ((1e-300, 1e308), 1e-300),
        ):
            with self.subTest(resistors=resistors):
                input_text = "5\n2\n" + "".join(f"{r}\n" for r in resistors) + "0\n"
                output = self.run_calculator(input_text)
                self.assertNotIn("计算错误", output)
                self.assert_results(output, [(expected, "Ω")])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", nargs="?", type=Path, default=CalculatorTests.executable)
    args, unittest_args = parser.parse_known_args()
    CalculatorTests.executable = args.executable.resolve()
    unittest.main(argv=[__file__, *unittest_args], verbosity=2)
