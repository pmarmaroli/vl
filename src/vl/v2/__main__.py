"""CLI: expand VL v2 macros to plain Python.

Usage:
    python -m vl.v2 input.py            # expand to stdout
    python -m vl.v2 input.py -o out.py
    python -m vl.v2 --spec              # print the macro spec for LLM prompts
    echo "data = jload('c.json')" | python -m vl.v2 -
"""

import argparse
import sys
from pathlib import Path

from .macros import MACRO_SPEC, expand_macros

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="vl.v2", description="Expand VL v2 macros to plain Python"
    )
    parser.add_argument("input", nargs="?", help="Python file with macros (use - for stdin)")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    parser.add_argument(
        "--spec", action="store_true", help="Print the macro spec to include in LLM prompts"
    )
    args = parser.parse_args(argv)

    if args.spec:
        sys.stdout.write(MACRO_SPEC)
        return 0
    if not args.input:
        parser.error("input file required (or --spec)")

    source = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    try:
        result = expand_macros(source)
    except SyntaxError as exc:
        print(f"Error: invalid Python input: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error expanding macros: {exc}", file=sys.stderr)
        return 1

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
