import unittest
from fractions import Fraction

from ucalc.units import (
    DimensionalError,
    UnitError,
    canonical_base_unit,
    conversion_factor,
    unit_for,
    unitless_unit,
)


class UnitRegistryTests(unittest.TestCase):
    def test_base_unit_dimensions(self):
        self.assertEqual(unit_for("m").dims, (1, 0, 0, 0, 0, 0, 0))
        self.assertEqual(unit_for("s").dims, (0, 1, 0, 0, 0, 0, 0))
        self.assertEqual(unit_for("kg").dims, (0, 0, 1, 0, 0, 0, 0))
        self.assertEqual(unit_for("A").dims, (0, 0, 0, 1, 0, 0, 0))
        self.assertEqual(unit_for("K").dims, (0, 0, 0, 0, 1, 0, 0))
        self.assertEqual(unit_for("mol").dims, (0, 0, 0, 0, 0, 1, 0))
        self.assertEqual(unit_for("cd").dims, (0, 0, 0, 0, 0, 0, 1))

    def test_derived_units_are_si_consistent(self):
        for sym in ("N", "J", "W", "Pa", "Hz", "V", "ohm", "F", "C"):
            self.assertEqual(unit_for(sym).factor, Fraction(1))

    def test_derived_unit_dimensions(self):
        self.assertEqual(unit_for("N").dims, (1, -2, 1, 0, 0, 0, 0))
        self.assertEqual(unit_for("J").dims, (2, -2, 1, 0, 0, 0, 0))
        self.assertEqual(unit_for("W").dims, (2, -3, 1, 0, 0, 0, 0))
        self.assertEqual(unit_for("Hz").dims, (0, -1, 0, 0, 0, 0, 0))

    def test_time_factors(self):
        self.assertEqual(unit_for("min").factor, Fraction(60))
        self.assertEqual(unit_for("h").factor, Fraction(3600))
        self.assertEqual(unit_for("d").factor, Fraction(86400))
        self.assertEqual(unit_for("yr").factor, Fraction(31557600))

    def test_prefixed_units(self):
        km = unit_for("km")
        self.assertEqual(km.factor, Fraction(1000))
        self.assertEqual(km.dims, (1, 0, 0, 0, 0, 0, 0))
        self.assertEqual(unit_for("cm").factor, Fraction(1, 100))
        self.assertEqual(unit_for("mW").factor, Fraction(1, 1000))
        self.assertEqual(unit_for("Ms").factor, Fraction(10 ** 6))

    def test_micro_aliases(self):
        self.assertEqual(unit_for("us").factor, unit_for("\u00b5s").factor)

    def test_units_are_case_sensitive(self):
        self.assertEqual(unit_for("m").symbol, "m")
        with self.assertRaises(UnitError):
            unit_for("M")
        with self.assertRaises(UnitError):
            unit_for("Kk")

    def test_kwh_decomposes_to_kilo_watt_hour(self):
        kwh = unit_for("kWh")
        self.assertEqual(kwh.factor, Fraction(3600000))
        self.assertEqual(kwh.dims, (2, -2, 1, 0, 0, 0, 0))

    def test_liter_and_percent_factors(self):
        self.assertEqual(unit_for("L").factor, Fraction(1, 1000))
        self.assertEqual(unit_for("pct").factor, Fraction(1, 100))

    def test_conversion_factor(self):
        self.assertEqual(conversion_factor(unit_for("km"), unit_for("m")),
                         Fraction(1000))
        self.assertEqual(conversion_factor(unit_for("m"), unit_for("cm")),
                         Fraction(100))
        self.assertEqual(conversion_factor(unit_for("h"), unit_for("min")),
                         Fraction(60))

    def test_incompatible_conversion_raises(self):
        with self.assertRaises(DimensionalError):
            conversion_factor(unit_for("m"), unit_for("s"))


class CanonicalBaseUnitTests(unittest.TestCase):
    def test_base_units(self):
        self.assertEqual(canonical_base_unit((1, 0, 0, 0, 0, 0, 0)).symbol, "m")
        self.assertEqual(canonical_base_unit((0, 1, 0, 0, 0, 0, 0)).symbol, "s")

    def test_derived_base(self):
        self.assertEqual(canonical_base_unit((1, -2, 1, 0, 0, 0, 0)).symbol, "N")

    def test_unitless(self):
        self.assertEqual(canonical_base_unit((0, 0, 0, 0, 0, 0, 0)),
                         unitless_unit())

    def test_compound_base(self):
        self.assertEqual(canonical_base_unit((2, 0, 0, 0, 0, 0, 0)).symbol, "m^2")


if __name__ == "__main__":
    unittest.main()