"""Command-line interface for ucalc.

Usage::

    ucalc "2 m + 30 cm"
    ucalc "1.6 km in m"
    echo "3 m * 4 m" | ucalc -
    ucalc --list-units
    ucalc --precision 2 "1/3 m"
"""

import sys

from ucalc import __version__
from ucalc.parser import DEFAULT_PRECISION, ParseError, parse_expr
from ucalc.units import DimensionalError, UnitError, list_units

USAGE = "usage: ucalc [--precision N] [--list-units] [--version] [--help] [EXPR | -]"

HELP = """\
{usage}

A units-of-measurement calculator.  Expressions are given as command line
arguments (joined with spaces) or read from standard input when no
expression is given (or when "-" is used as the expression).

Options:
  --precision N      round results to N decimal places (default 12)
  --list-units       list every registered unit and exit
  --version          print the version and exit
  -h, --help         print this help and exit

Examples:
  ucalc "2 m + 30 cm"
  ucalc "1.6 km in m"
  ucalc "1 kWh in J"
  ucalc "6 J / 2 s"
  ucalc "1 m + 1 s"            (fails with a dimensional error, exit 1)
""".format(usage=USAGE)


def _precision_arg(value):
    try:
        precision = int(value)
    except ValueError:
        raise ValueError("invalid --precision value %r" % value)
    if precision < 0:
        raise ValueError("--precision must be >= 0")
    return precision


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    precision = DEFAULT_PRECISION
    show_units = False
    use_stdin = False
    parts = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            sys.stdout.write(HELP)
            return 0
        if arg == "--version":
            sys.stdout.write("ucalc %s\n" % __version__)
            return 0
        if arg == "--list-units":
            show_units = True
        elif arg == "--precision":
            i += 1
            if i >= len(argv):
                sys.stderr.write("ucalc: --precision requires a value\n")
                return 1
            try:
                precision = _precision_arg(argv[i])
            except ValueError as err:
                sys.stderr.write("ucalc: %s\n" % err)
                return 1
        elif arg.startswith("--precision="):
            try:
                precision = _precision_arg(arg.split("=", 1)[1])
            except ValueError as err:
                sys.stderr.write("ucalc: %s\n" % err)
                return 1
        elif arg == "-":
            use_stdin = True
        else:
            parts.append(arg)
        i += 1

    if show_units:
        sys.stdout.write(list_units() + "\n")
        return 0

    if use_stdin:
        text = sys.stdin.read()
    elif parts:
        text = " ".join(parts)
    else:
        text = sys.stdin.read()

    try:
        result = parse_expr(text)
    except (ParseError, UnitError, DimensionalError) as err:
        sys.stderr.write("ucalc: %s\n" % err)
        return 1

    sys.stdout.write(result.format(precision) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())