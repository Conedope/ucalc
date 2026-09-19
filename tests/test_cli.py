import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(args, stdin=None):
    return subprocess.run(
        [sys.executable, "-m", "ucalc.cli"] + list(args),
        capture_output=True,
        text=True,
        cwd=ROOT,
        input=stdin,
    )


class CliTests(unittest.TestCase):
    def test_expression_argument(self):
        r = run(["1.6 km in m"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "1600 m")
        self.assertEqual(r.stderr, "")

    def test_multiple_arguments_are_joined(self):
        r = run(["2", "m", "+", "30", "cm"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "2.3 m")

    def test_kwh(self):
        r = run(["1 kWh in J"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "3600000 J")

    def test_dimensions_add(self):
        r = run(["3 m * 4 m"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "12 m^2")

    def test_dimensional_error_exits_one(self):
        r = run(["1 m + 1 s"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("dimensions", r.stderr)

    def test_unknown_unit_exits_one(self):
        r = run(["1 zzz"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown unit", r.stderr)

    def test_parse_error_exits_one(self):
        r = run(["2 +"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("expected", r.stderr)

    def test_list_units(self):
        r = run(["--list-units"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("meter (m): factor 1, dimension L", r.stdout)
        self.assertIn("newton (N): factor 1, dimension L T^-2 M", r.stdout)

    def test_version(self):
        r = run(["--version"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "ucalc 1.0.0")

    def test_help(self):
        r = run(["--help"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("usage:", r.stdout)

    def test_stdin_dash(self):
        r = run(["-"], stdin="3 m * 4 m\n")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "12 m^2")

    def test_stdin_no_arguments(self):
        r = run([], stdin="2 + 3 * 4\n")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "14")

    def test_precision(self):
        r = run(["--precision", "2", "5 / 3"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "1.67")

    def test_precision_equals_form(self):
        r = run(["--precision=2", "5 / 3"])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "1.67")

    def test_invalid_precision_exits_one(self):
        r = run(["--precision", "abc", "1 m"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("precision", r.stderr)


if __name__ == "__main__":
    unittest.main()