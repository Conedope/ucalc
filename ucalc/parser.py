"""Parser and Quantity for ucalc.

``parse_expr`` turns a string such as ``"1.6 km in m"`` into a
:class:`Quantity` (a ``Fraction`` value plus a :class:`~ucalc.units.Unit`).
Grammar (recursive descent, ``in`` binds loosest, ``^`` tightest)::

    expr   := add ( 'in' add )*
    add    := mul ( ('+'|'-') mul )*
    mul    := group ( ('*'|'/') group )*
    group  := unary ( unary )*          ; adjacent operands multiply
    unary  := ('-'|'+') unary | power
    power  := primary ( '^' unary )?
    primary:= NUMBER | UNIT | '(' expr ')'

Implicit multiplication (``2 m``) binds tighter than ``*`` and ``/``, so
``6 J / 2 s`` means ``(6 J)/(2 s)``; ``2 m^2`` means ``2*(m^2)`` while
``(2 m)^2`` means ``(2*m)^2``; unary minus binds looser than ``^``.
"""

import re
from fractions import Fraction

from ucalc.units import (
    Unit,
    UnitError,
    DimensionalError,
    canonical_base_unit,
    conversion_factor,
    unit_for,
    unitless_unit,
)

DEFAULT_PRECISION = 12

_NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_IDENT_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "\u00b5\u03bc"  # micro sign and greek mu
)


class ParseError(Exception):
    """Raised when an expression cannot be parsed."""


class Quantity:
    """An exact numeric value together with its unit."""

    __slots__ = ("value", "unit")

    def __init__(self, value, unit=None):
        self.value = Fraction(value)
        self.unit = unit if unit is not None else unitless_unit()

    def format(self, precision=DEFAULT_PRECISION):
        text = format_fraction(self.value, precision)
        if self.unit.symbol:
            text += " " + self.unit.symbol
        return text

    def __str__(self):
        return self.format()

    def __repr__(self):
        return "Quantity(%r, %r)" % (self.value, self.unit.symbol)


def format_fraction(value, precision=DEFAULT_PRECISION):
    """Render a Fraction as a clean decimal (with rounding to `precision`).

    Terminating decimals are shown exactly with trailing zeros trimmed;
    other values are rounded to `precision` decimal places.
    """
    precision = max(0, min(int(precision), 100))
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    scaled = round(value * 10 ** precision)
    f = Fraction(scaled, 10 ** precision)
    neg = "-" if f.numerator < 0 else ""
    num, den = abs(f.numerator), f.denominator
    if den == 1:
        return neg + str(num)
    whole, rem = divmod(num, den)
    digits = []
    while rem:
        rem *= 10
        digits.append(str(rem // den))
        rem %= den
    return "%s%d.%s" % (neg, whole, "".join(digits))


def _parse_number(text):
    mantissa, _, exponent = text.partition("e")
    if not exponent:
        mantissa, _, exponent = text.partition("E")
    if exponent:
        return Fraction(mantissa) * Fraction(10) ** int(exponent)
    return Fraction(text)


def tokenize(text):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if _NUMBER_RE.match(text, i):
            m = _NUMBER_RE.match(text, i)
            tokens.append(("NUM", m.group()))
            i = m.end()
            continue
        if ch in _IDENT_CHARS:
            j = i
            while j < n and text[j] in _IDENT_CHARS:
                j += 1
            tokens.append(("ID", text[i:j]))
            i = j
            continue
        if ch in "+-*/^()":
            tokens.append(("OP", ch))
            i += 1
            continue
        raise ParseError("unexpected character %r" % ch)
    return tokens


def _describe(quantity):
    return quantity.unit.symbol or "a dimensionless value"


def q_neg(a):
    return Quantity(-a.value, a.unit)


def q_mul(a, b):
    return Quantity(a.value * b.value, a.unit.mul(b.unit))


def q_div(a, b):
    if b.value == 0:
        raise ParseError("division by zero")
    return Quantity(a.value / b.value, a.unit.div(b.unit))


def q_add(a, b):
    if a.unit.dims != b.unit.dims:
        raise DimensionalError(
            "cannot add %s and %s (dimensions differ)"
            % (_describe(a), _describe(b)))
    base = canonical_base_unit(a.unit.dims)
    total = a.value * a.unit.factor + b.value * b.unit.factor
    return Quantity(total / base.factor, base)


def q_sub(a, b):
    if a.unit.dims != b.unit.dims:
        raise DimensionalError(
            "cannot subtract %s and %s (dimensions differ)"
            % (_describe(a), _describe(b)))
    base = canonical_base_unit(a.unit.dims)
    total = a.value * a.unit.factor - b.value * b.unit.factor
    return Quantity(total / base.factor, base)


def q_pow(base, exponent):
    if not exponent.unit.is_unitless:
        raise ParseError("exponent must be dimensionless (got %s)"
                         % _describe(exponent))
    if exponent.value.denominator != 1:
        raise ParseError("exponent must be an integer (got %s)"
                         % format_fraction(exponent.value))
    exp = int(exponent.value)
    if base.value == 0 and exp < 0:
        raise ParseError("division by zero")
    return Quantity(base.value ** exp, base.unit.power(exp))


def q_convert(quantity, target_unit):
    ratio = conversion_factor(quantity.unit, target_unit)
    return Quantity(quantity.value * ratio, target_unit)


class _Parser:
    def __init__(self, text):
        self.tokens = tokenize(text)
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def advance(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect_op(self, op):
        kind, value = self.peek()
        if kind != "OP" or value != op:
            raise ParseError("expected %r but found %r" % (op, value))
        return self.advance()

    def expect_end(self):
        if self.pos != len(self.tokens):
            kind, value = self.peek()
            raise ParseError("unexpected trailing token %r" % value)

    def conv(self):
        left = self.add()
        while True:
            kind, value = self.peek()
            if kind == "ID" and value == "in":
                self.advance()
                target = self.add()
                left = q_convert(left, target.unit)
            else:
                return left

    def add(self):
        left = self.mul()
        while True:
            kind, value = self.peek()
            if kind == "OP" and value in ("+", "-"):
                self.advance()
                right = self.mul()
                left = q_sub(left, right) if value == "-" else q_add(left, right)
            else:
                return left

    def mul(self):
        left = self.group()
        while True:
            kind, value = self.peek()
            if kind == "OP" and value in ("*", "/"):
                self.advance()
                right = self.group()
                left = q_div(left, right) if value == "/" else q_mul(left, right)
            else:
                return left

    def group(self):
        left = self.unary()
        while True:
            kind, value = self.peek()
            if kind == "NUM" or (kind == "ID" and value != "in"):
                right = self.unary()
                left = q_mul(left, right)
            else:
                return left

    def power(self):
        left = self.primary()
        kind, value = self.peek()
        if kind == "OP" and value == "^":
            self.advance()
            right = self.unary()
            return q_pow(left, right)
        return left

    def unary(self):
        kind, value = self.peek()
        if kind == "OP" and value in ("-", "+"):
            self.advance()
            operand = self.unary()
            return q_neg(operand) if value == "-" else operand
        return self.power()

    def primary(self):
        kind, value = self.peek()
        if kind == "NUM":
            self.advance()
            return Quantity(_parse_number(value))
        if kind == "ID":
            if value == "in":
                raise ParseError("unexpected %r" % value)
            self.advance()
            return Quantity(1, unit_for(value))
        if kind == "OP" and value == "(":
            self.advance()
            inner = self.conv()
            self.expect_op(")")
            return inner
        if kind is None:
            raise ParseError("unexpected end of expression")
        raise ParseError("unexpected token %r" % value)


def parse_expr(text):
    """Parse an expression string into a Quantity."""
    parser = _Parser(text)
    result = parser.conv()
    parser.expect_end()
    return result