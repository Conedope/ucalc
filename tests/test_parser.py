import unittest
from fractions import Fraction

from ucalc.parser import parse_expr, ParseError
from ucalc.units import DimensionalError, UnitError


class LiteralAndPrecedenceTests(unittest.TestCase):
    def test_add_over_mul_precedence(self):
        self.assertEqual(str(parse_expr("2 + 3 * 4")), "14")

    def test_parentheses_override(self):
        self.assertEqual(str(parse_expr("(2 + 3) * 4")), "20")

    def test_precedence_scopes_unit_to_its_operand(self):
        # 3 * (4 m) is formed first, then 2 + 12 m is dimensionally invalid.
        with self.assertRaises(DimensionalError):
            parse_expr("2 + 3 * 4 m")

    def test_power_binds_tightest(self):
        self.assertEqual(str(parse_expr("3 + 2 ^ 2")), "7")
        self.assertEqual(str(parse_expr("2 ^ 3 * 4")), "32")

    def test_power_is_right_associative(self):
        self.assertEqual(str(parse_expr("2 ^ 3 ^ 2")), "512")

    def test_implicit_multiplication(self):
        self.assertEqual(str(parse_expr("2 m")), "2 m")
        self.assertEqual(str(parse_expr("10 cm")), "10 cm")

    def test_decimals_and_scientific_notation(self):
        self.assertEqual(str(parse_expr("1e3 m in m")), "1000 m")
        self.assertEqual(str(parse_expr("2.5e-3 m in mm")), "2.5 mm")

    def test_exact_fraction_math(self):
        self.assertEqual(parse_expr("0.1 + 0.2").value, Fraction(3, 10))
        self.assertEqual(str(parse_expr("0.1 + 0.2")), "0.3")


class DimensionalAdditionTests(unittest.TestCase):
    def test_multiplication_combines_dimensions(self):
        q = parse_expr("2 m * 3 m")
        self.assertEqual(q.value, Fraction(6))
        self.assertEqual(q.unit.dims, (2, 0, 0, 0, 0, 0, 0))
        self.assertEqual(str(q), "6 m^2")

    def test_division_composes_units_into_watts(self):
        q = parse_expr("6 J / 2 s")
        self.assertEqual(q.value, Fraction(3))
        self.assertEqual(q.unit.dims, parse_expr("1 W").unit.dims)
        self.assertEqual(str(q), "3 W")

    def test_adding_different_dimensions_raises(self):
        with self.assertRaises(DimensionalError):
            parse_expr("1 m + 1 s")

    def test_converting_different_dimensions_raises(self):
        with self.assertRaises(DimensionalError):
            parse_expr("1 m in s")

    def test_add_compatible_units(self):
        self.assertEqual(str(parse_expr("1 m + 10 cm")), "1.1 m")
        self.assertEqual(str(parse_expr("1 m + 1 cm")), "1.01 m")

    def test_add_km_and_m(self):
        self.assertEqual(str(parse_expr("1 km + 500 m")), "1500 m")

    def test_subtract_km_and_m(self):
        self.assertEqual(str(parse_expr("1 km - 500 m")), "500 m")

    def test_speed(self):
        self.assertEqual(str(parse_expr("2 m / s")), "2 m/s")
        self.assertEqual(str(parse_expr("100 km / 1 h in m/s")),
                         "27.777777777778 m/s")


class PrefixTests(unittest.TestCase):
    def test_kilometer_plus_meter(self):
        self.assertEqual(str(parse_expr("1 km + 500 m")), "1500 m")

    def test_kwh_in_joules(self):
        q = parse_expr("1 kWh in J")
        self.assertEqual(q.value, Fraction(3600000))
        self.assertEqual(str(q), "3600000 J")

    def test_kwh_in_megajoules(self):
        self.assertEqual(str(parse_expr("1 kWh in MJ")), "3.6 MJ")

    def test_hour_to_minutes(self):
        self.assertEqual(str(parse_expr("1 h in min")), "60 min")

    def test_hour_to_seconds(self):
        self.assertEqual(str(parse_expr("1.5 h in s")), "5400 s")

    def test_milli_to_watt(self):
        self.assertEqual(str(parse_expr("1000 mW in W")), "1 W")

    def test_microsecond(self):
        self.assertEqual(str(parse_expr("1 us in s")), "0.000001 s")

    def test_mega_is_case_sensitive(self):
        self.assertEqual(str(parse_expr("1 Mm in m")), "1000000 m")
        with self.assertRaises(UnitError):
            parse_expr("1 M")

    def test_megawatt_hour(self):
        self.assertEqual(str(parse_expr("1 MWh in J")), "3600000000 J")

    def test_gram_and_kilogram(self):
        self.assertEqual(str(parse_expr("1 kg in g")), "1000 g")


class PowerTests(unittest.TestCase):
    def test_power_of_quantity(self):
        q = parse_expr("(2 m)^2")
        self.assertEqual(q.value, Fraction(4))
        self.assertEqual(str(q), "4 m^2")

    def test_power_binds_to_unit_not_number(self):
        q = parse_expr("2 m^2")
        self.assertEqual(q.value, Fraction(2))
        self.assertEqual(q.unit.dims, (2, 0, 0, 0, 0, 0, 0))
        self.assertEqual(str(q), "2 m^2")

    def test_cube(self):
        self.assertEqual(str(parse_expr("(2 m)^3")), "8 m^3")

    def test_negative_exponent(self):
        q = parse_expr("3 m^-2")
        self.assertEqual(q.unit.dims, (-2, 0, 0, 0, 0, 0, 0))

    def test_zero_power_is_dimensionless(self):
        self.assertEqual(str(parse_expr("(2 m)^0")), "1")

    def test_exponent_must_be_dimensionless_integer(self):
        with self.assertRaises(ParseError):
            parse_expr("2 m ^ (1 m)")
        with self.assertRaises(ParseError):
            parse_expr("2 m ^ 0.5")


class UnaryTests(unittest.TestCase):
    def test_unary_minus(self):
        self.assertEqual(str(parse_expr("-3 kg")), "-3 kg")

    def test_unary_minus_parens(self):
        self.assertEqual(str(parse_expr("-(3 m)")), "-3 m")

    def test_unary_minus_times_quantity(self):
        self.assertEqual(str(parse_expr("-2 * 3 m")), "-6 m")

    def test_power_beats_unary_minus(self):
        self.assertEqual(str(parse_expr("-(2 m)^2")), "-4 m^2")


class ErrorTests(unittest.TestCase):
    def test_trailing_operator(self):
        with self.assertRaises(ParseError):
            parse_expr("2 +")

    def test_unbalanced_parens(self):
        with self.assertRaises(ParseError):
            parse_expr("(2 + 3")

    def test_bad_character(self):
        with self.assertRaises(ParseError):
            parse_expr("2 ? 3")

    def test_lone_in(self):
        with self.assertRaises(ParseError):
            parse_expr("in m")

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            parse_expr("1 furlong")
        with self.assertRaises(UnitError):
            parse_expr("2 quux m")

    def test_dimension_mismatch_in(self):
        with self.assertRaises(DimensionalError):
            parse_expr("1 m in s")

    def test_dimension_mismatch_add(self):
        with self.assertRaises(DimensionalError):
            parse_expr("1 m + 1 s")


if __name__ == "__main__":
    unittest.main()