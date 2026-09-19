"""Unit registry and dimensional arithmetic for ucalc.

A :class:`Unit` is a triple of a dimension tuple, an SI conversion factor and
a display symbol.  Dimensions are 7-tuples of integer exponents over the SI
base dimensions, in the order

    (meter, second, kilogram, ampere, kelvin, mole, candela)

The factor is how many SI base units one of this unit equals
(``1 km`` -> factor ``1000``, ``1 cm`` -> factor ``1/100``).  All arithmetic
is done with :class:`fractions.Fraction`, so results never drift.
"""

from fractions import Fraction

BASE_SYMBOLS = ("m", "s", "kg", "A", "K", "mol", "cd")
BASE_NAMES = (
    "meter", "second", "kilogram", "ampere", "kelvin", "mole", "candela",
)
DIM_LETTERS = ("L", "T", "M", "I", "Th", "N", "Jv")

ZERO = (0, 0, 0, 0, 0, 0, 0)


class UnitError(Exception):
    """Raised when a unit symbol is not recognised."""


class DimensionalError(Exception):
    """Raised when quantities with incompatible dimensions meet."""


class Unit:
    """A physical unit: a dimension tuple, an SI factor and a symbol."""

    __slots__ = ("dims", "factor", "symbol")

    def __init__(self, dims, factor, symbol=""):
        self.dims = tuple(dims)
        self.factor = Fraction(factor)
        self.symbol = symbol

    @property
    def is_unitless(self):
        return self.dims == ZERO

    def mul(self, other):
        unit = Unit(
            tuple(a + b for a, b in zip(self.dims, other.dims)),
            self.factor * other.factor,
            merge_symbols(self.symbol, other.symbol, 1),
        )
        return canonicalize(unit)

    def div(self, other):
        unit = Unit(
            tuple(a - b for a, b in zip(self.dims, other.dims)),
            self.factor / other.factor,
            merge_symbols(self.symbol, other.symbol, -1),
        )
        return canonicalize(unit)

    def power(self, n):
        unit = Unit(
            tuple(d * n for d in self.dims),
            self.factor ** n,
            power_symbol(self.symbol, n),
        )
        return canonicalize(unit)

    def __eq__(self, other):
        return (
            isinstance(other, Unit)
            and self.dims == other.dims
            and self.factor == other.factor
            and self.symbol == other.symbol
        )

    def __hash__(self):
        return hash((self.dims, self.factor, self.symbol))

    def __str__(self):
        return self.symbol


def _u(dims, factor, symbol):
    return Unit(dims, factor, symbol)


UNITS = {
    "m":   _u((1, 0, 0, 0, 0, 0, 0), 1, "m"),
    "s":   _u((0, 1, 0, 0, 0, 0, 0), 1, "s"),
    "kg":  _u((0, 0, 1, 0, 0, 0, 0), 1, "kg"),
    "g":   _u((0, 0, 1, 0, 0, 0, 0), Fraction(1, 1000), "g"),
    "A":   _u((0, 0, 0, 1, 0, 0, 0), 1, "A"),
    "K":   _u((0, 0, 0, 0, 1, 0, 0), 1, "K"),
    "mol": _u((0, 0, 0, 0, 0, 1, 0), 1, "mol"),
    "cd":  _u((0, 0, 0, 0, 0, 0, 1), 1, "cd"),
    "N":   _u((1, -2, 1, 0, 0, 0, 0), 1, "N"),
    "J":   _u((2, -2, 1, 0, 0, 0, 0), 1, "J"),
    "W":   _u((2, -3, 1, 0, 0, 0, 0), 1, "W"),
    "Pa":  _u((-1, -2, 1, 0, 0, 0, 0), 1, "Pa"),
    "Hz":  _u((0, -1, 0, 0, 0, 0, 0), 1, "Hz"),
    "V":   _u((2, -3, 1, -1, 0, 0, 0), 1, "V"),
    "ohm": _u((2, -3, 1, -2, 0, 0, 0), 1, "ohm"),
    "F":   _u((-2, 4, -1, 2, 0, 0, 0), 1, "F"),
    "C":   _u((0, 1, 0, 1, 0, 0, 0), 1, "C"),
    "L":   _u((3, 0, 0, 0, 0, 0, 0), Fraction(1, 1000), "L"),
    "min": _u((0, 1, 0, 0, 0, 0, 0), 60, "min"),
    "h":   _u((0, 1, 0, 0, 0, 0, 0), 3600, "h"),
    "d":   _u((0, 1, 0, 0, 0, 0, 0), 86400, "d"),
    "yr":  _u((0, 1, 0, 0, 0, 0, 0), 31557600, "yr"),
    "deg": _u(ZERO, 1, "deg"),
    "pct": _u(ZERO, Fraction(1, 100), "pct"),
}

NAMES = {
    "m": "meter", "s": "second", "kg": "kilogram", "g": "gram",
    "A": "ampere", "K": "kelvin", "mol": "mole", "cd": "candela",
    "N": "newton", "J": "joule", "W": "watt", "Pa": "pascal",
    "Hz": "hertz", "V": "volt", "ohm": "ohm", "F": "farad",
    "C": "coulomb", "L": "liter", "min": "minute", "h": "hour",
    "d": "day", "yr": "year", "deg": "degree", "pct": "percent",
}

# SI prefixes: symbol -> power of ten it scales a unit by.
PREFIXES = {
    "da": Fraction(10),
    "h":  Fraction(100),
    "k":  Fraction(1000),
    "M":  Fraction(10 ** 6),
    "G":  Fraction(10 ** 9),
    "T":  Fraction(10 ** 12),
    "d":  Fraction(1, 10),
    "c":  Fraction(1, 100),
    "m":  Fraction(1, 1000),
    "u":  Fraction(1, 10 ** 6),
    "\u00b5": Fraction(1, 10 ** 6),
    "n":  Fraction(1, 10 ** 9),
    "p":  Fraction(1, 10 ** 12),
}


def unitless_unit():
    """The dimensionless unit (empty symbol, factor 1)."""
    return Unit(ZERO, 1, "")


def dims_hint(dims):
    """Human-readable dimension hint such as 'L M T^-2'."""
    parts = []
    for exp, letter in zip(dims, DIM_LETTERS):
        if exp == 1:
            parts.append(letter)
        elif exp != 0:
            parts.append("%s^%d" % (letter, exp))
    return " ".join(parts) if parts else "dimensionless"


def parse_terms(symbol):
    """Split a product symbol like 'm^2/s' into a {base: exponent} dict."""
    terms = {}
    if not symbol:
        return terms
    for part in symbol.split("*"):
        if "^" in part:
            base, exp = part.split("^", 1)
            exp = int(exp)
        else:
            base, exp = part, 1
        terms[base] = terms.get(base, 0) + exp
    return terms


def render_terms(terms):
    """Rebuild a symbol string from a {base: exponent} dict."""
    num = [base if exp == 1 else "%s^%d" % (base, exp)
           for base, exp in terms.items() if exp > 0]
    den = [base if exp == -1 else "%s^%d" % (base, -exp)
           for base, exp in terms.items() if exp < 0]
    num_s = "*".join(num)
    den_s = "*".join(den)
    if num_s and den_s:
        return "%s/%s" % (num_s, den_s)
    if den_s:
        return "1/%s" % den_s
    return num_s


def merge_symbols(a, b, sign):
    """Multiply (sign=1) or divide (sign=-1) two unit symbols."""
    terms = parse_terms(a)
    for base, exp in parse_terms(b).items():
        terms[base] = terms.get(base, 0) + sign * exp
    terms = {base: exp for base, exp in terms.items() if exp}
    return render_terms(terms)


def power_symbol(symbol, n):
    """Raise a unit symbol to an integer power."""
    terms = {base: exp * n for base, exp in parse_terms(symbol).items()}
    terms = {base: exp for base, exp in terms.items() if exp}
    return render_terms(terms)


_COLLAPSEABLE = BASE_SYMBOLS + (
    "N", "J", "W", "Pa", "Hz", "V", "ohm", "F", "C", "L", "min", "h", "d",
    "yr",
)
_COLLAPSE = {}
for _sym in _COLLAPSEABLE:
    _collapse_unit = UNITS[_sym]
    _COLLAPSE[(_collapse_unit.dims, _collapse_unit.factor)] = _sym
del _collapse_unit, _sym


def canonicalize(unit):
    """Replace a computed unit with a named SI unit when it is exactly one."""
    if not unit.symbol or unit.is_unitless:
        return unit
    symbol = _COLLAPSE.get((unit.dims, unit.factor))
    if symbol is not None:
        return Unit(unit.dims, unit.factor, symbol)
    return unit


def canonical_base_unit(dims):
    """The factor-1 representative unit for a dimension (used by + and -)."""
    if dims == ZERO:
        return unitless_unit()
    for sym in BASE_SYMBOLS:
        u = UNITS[sym]
        if u.dims == dims:
            return Unit(dims, Fraction(1), sym)
    for sym in ("N", "J", "W", "Pa", "Hz", "V", "ohm", "F", "C"):
        u = UNITS[sym]
        if u.dims == dims:
            return Unit(dims, Fraction(1), sym)
    terms = {}
    for exp, sym in zip(dims, BASE_SYMBOLS):
        if exp:
            terms[sym] = exp
    return Unit(dims, Fraction(1), render_terms(terms))


def conversion_factor(source, target):
    """How many ``target`` units one ``source`` unit equals.

    Raises :class:`DimensionalError` when the units are incompatible.
    """
    if source.dims != target.dims:
        raise DimensionalError(
            "cannot convert %r to %r (dimensions differ)"
            % (source.symbol or "a dimensionless value",
               target.symbol or "a dimensionless value"))
    return source.factor / target.factor


def _scaled(unit, prefix):
    return Unit(unit.dims, unit.factor * PREFIXES[prefix],
                prefix + unit.symbol)


def _prefix_unit(sym):
    """A registered unit, or a single SI prefix applied to one.

    Returns ``None`` when ``sym`` is neither.
    """
    if sym in UNITS:
        return UNITS[sym]
    for prefix in sorted(PREFIXES, key=len, reverse=True):
        if sym.startswith(prefix) and sym[len(prefix):] in UNITS:
            return _scaled(UNITS[sym[len(prefix):]], prefix)
    return None


def _chain_unit(sym):
    """Decompose a run-on symbol such as 'kWh' into a product of units."""
    parts = []
    i, n = 0, len(sym)
    while i < n:
        hit = None
        for end in range(n, i, -1):
            u = _prefix_unit(sym[i:end])
            if u is not None:
                hit = (u, end)
                break
        if hit is None:
            raise UnitError("unknown unit %r" % sym)
        parts.append(hit[0])
        i = hit[1]
    unit = parts[0]
    for u in parts[1:]:
        unit = unit.mul(u)
    return Unit(unit.dims, unit.factor, sym)


def unit_for(sym):
    """Resolve a unit symbol (possibly prefixed or run-on) to a Unit."""
    if not sym:
        return unitless_unit()
    u = _prefix_unit(sym)
    if u is not None:
        return u
    return _chain_unit(sym)


def list_units():
    """A human-readable, symbol-sorted listing of the unit registry."""
    lines = []
    for sym in sorted(UNITS):
        u = UNITS[sym]
        name = NAMES.get(sym, sym)
        lines.append("%s (%s): factor %s, dimension %s"
                     % (name, sym, u.factor, dims_hint(u.dims)))
    return "\n".join(lines)