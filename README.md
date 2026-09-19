# ucalc

A units-of-measurement calculator for the command line.  Parse arithmetic
with units, convert between compatible units, and get a hard error when you
mix incompatible dimensions.

Everything is pure Python standard library: numbers are
[`fractions.Fraction`](https://docs.python.org/3/library/fractions.html)
so there is **no floating-point drift** — `0.1 + 0.2` is exactly `0.3`,
and `1 kWh` is exactly `3600000 J`.

## Install

```bash
pip install -e .
ucalc --version
```

Python 3.9+ is required.  No third-party dependencies.

## Usage

```text
usage: ucalc [--precision N] [--list-units] [--version] [--help] [EXPR | -]
```

* An expression is given as command line arguments (joined with spaces).
* With `-` or no expression, the expression is read from standard input.
* `--precision N` rounds the printed value to `N` decimal places
  (default 12).  Terminating decimals are always shown exactly.
* `--list-units` prints every registered unit and exits.
* Errors are written to stderr and the process exits with status 1.

### Examples

These are real outputs:

```console
$ ucalc "1.6 km in m"
1600 m

$ ucalc "1 kWh in J"
3600000 J

$ ucalc "6 J / 2 s"
3 W

$ ucalc "2 m + 30 cm"
2.3 m

$ ucalc "1 km + 500 m"
1500 m

$ ucalc "1 h in min"
60 min

$ ucalc "1.5 h in s"
5400 s

$ ucalc "1000 mW in W"
1 W

$ ucalc "5 kg * 9.81 m / s^2"
49.05 N

$ ucalc "-3 kg"
-3 kg

$ ucalc "(2 m)^2"
4 m^2

$ ucalc "2 m^2"              # ^ binds to the unit, not the coefficient
2 m^2

$ ucalc "0.1 + 0.2"
0.3

$ ucalc "2 + 3 * 4 m"        # 3*(4 m) = 12 m, then 2 + 12 m fails
ucalc: cannot add a dimensionless value and m (dimensions differ)

$ ucalc "1 m + 1 s"
ucalc: cannot add m and s (dimensions differ)

$ ucalc "1 m in s"
ucalc: cannot convert 'm' to 's' (dimensions differ)

$ ucalc "1 furlong"          # unknown unit
ucalc: unknown unit 'furlong'

$ ucalc "2 +"                # parse error
ucalc: unexpected end of expression

$ echo "3 m * 4 m" | ucalc -
12 m^2

$ ucalc --precision 2 "5 / 3"
1.67
```

The exit status is `0` on success and `1` on any error.

## Expressions

A hand-rolled recursive-descent parser handles the usual operators, with `^`
binding tightest and `in` loosest:

```text
expr   := add ( 'in' add )*
add    := mul ( ('+'|'-') mul )*
mul    := group ( ('*'|'/') group )*
group  := unary ( unary )*          ; adjacent operands multiply
unary  := ('-'|'+') unary | power
power  := primary ( '^' unary )?
primary:= NUMBER | UNIT | '(' expr ')'
```

* Numbers accept decimals and scientific notation: `1.6`, `2.5e-3`, `1e3`.
* Adjacent operands multiply: `2 m` is `2*m`; `10 cm` is `10*cm`.
* Implicit multiplication binds tighter than `*` and `/`, so
  `6 J / 2 s` means `(6 J)/(2 s)` (and evaluates to `3 W`).
* `^` binds tighter than unary minus: `-2^2` is `-4`.
* `2 m^2` means `2*(m^2)`, while `(2 m)^2` means `(2*m)^2 = 4 m^2`.
* `kWh` is a run-on product of `k` (kilo) · `W` (watt) · `h` (hour), so
  `1 kWh in J` gives exactly `3600000 J`.

### Dimensional rules

* `*` and `/` combine dimensions: `2 m * 3 m = 6 m^2`,
  `6 J / 2 s = 3 W`, `5 kg * 9.81 m / s^2 = 49.05 N`.
* `^` raises dimension powers: `(2 m)^2 = 4 m^2`.
* `+` and `-` require identical dimensions, and convert both operands to the
  factor-1 (SI) unit for that dimension before adding:
  `1 m + 10 cm = 1.1 m`, `1 km + 500 m = 1500 m`.
* `in` converts between compatible units and keeps the target's spelling:
  `1.6 km in m = 1600 m`, `1 h in min = 60 min`.
* A dimensionless value can only combine with other dimensionless values.

## Units

Unit symbols are **case-sensitive**: `m` is meter, `M` is mega.  Run
`ucalc --list-units` for the full listing.

### SI base units

| Unit   | Symbol | Dimension |
|--------|--------|-----------|
| meter  | m      | L         |
| second | s      | T         |
| kilogram | kg   | M         |
| ampere | A      | I         |
| kelvin | K      | Th        |
| mole   | mol    | N         |
| candela| cd     | Jv        |

Gram (`g`) is registered as `1/1000 kg`, so `kg = k·g` consistent.

### Derived units

All listed below have SI-consistent factors (factor 1) unless noted.

| Unit   | Symbol | Dimension hint       |
|--------|--------|----------------------|
| newton | N      | L T^-2 M             |
| joule  | J      | L^2 T^-2 M           |
| watt   | W      | L^2 T^-3 M           |
| pascal | Pa     | L^-1 T^-2 M          |
| hertz  | Hz     | T^-1                 |
| volt   | V      | L^2 T^-3 M I^-1      |
| ohm    | ohm    | L^2 T^-3 M I^-2      |
| farad  | F      | L^-2 T^4 M^-1 I^2    |
| coulomb| C      | T I                  |
| liter  | L      | L^3 (factor 1/1000)  |
| minute | min    | T (factor 60)        |
| hour   | h      | T (factor 3600)      |
| day    | d      | T (factor 86400)     |
| year   | yr     | T (factor 31557600)  |
| degree | deg    | dimensionless        |
| percent| pct    | dimensionless (1/100)|

### SI prefixes

Prefixes scale any registered unit by a power of ten.

| Prefix | Factor   | Prefix | Factor |
|--------|----------|--------|--------|
| da (deca) | 10  | d (deci)    | 10^-1 |
| h  (hecto) | 100 | c (centi)   | 10^-2 |
| k  (kilo)  | 10^3 | m (milli)  | 10^-3 |
| M  (mega)  | 10^6 | u (micro)  | 10^-6 |
| G  (giga)  | 10^9 | n (nano)   | 10^-9 |
| T  (tera)  | 10^12 | p (pico)  | 10^-12 |

Micro also accepts the Unicode `µ`.  Both `u` and `µ` work.

## Development

```bash
python -m unittest discover -s tests -v
```

The test suite covers literal parsing and precedence, dimensional
addition/division into derived units, prefixes (including `kWh`),
powers of quantities, unary minus, all three error classes, and the CLI
(subprocess, exit codes, stdin mode).  GitHub Actions runs the suite on
Python 3.9 and 3.12 (`.github/workflows/ci.yml`).

## License

MIT — see [LICENSE](LICENSE).  Copyright (c) 2026 Conedope.