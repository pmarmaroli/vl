#!/usr/bin/env python3
"""
Python to VL Converter CLI
Converts Python source files to VL

Usage:
    python -m vl.py2vl input.py
    python -m vl.py2vl input.py -o output.vl
    python -m vl.py2vl --help
"""

import sys
import argparse
from pathlib import Path
from .py_to_vl import convert_python_to_vl

# Ensure UTF-8 encoding for stdout/stderr on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description='Convert Python source code to VL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert Python file to VL (print to stdout)
  python -m vl.py2vl script.py
  
  # Convert and save to file
  python -m vl.py2vl script.py -o script.vl
  
  # Read from stdin
  echo "def add(x,y): return x+y" | python -m vl.py2vl -
"""
    )
    
    parser.add_argument(
        'input',
        help='Input Python file (use - for stdin)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output VL file (default: stdout)',
        default=None
    )
    
    args = parser.parse_args()
    
    # Read input
    if args.input == '-':
        python_code = sys.stdin.read()
    else:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        python_code = input_path.read_text(encoding='utf-8')
    
    # Convert
    try:
        vl_code = convert_python_to_vl(python_code)
    except Exception as e:
        print(f"Error converting Python to VL: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(vl_code, encoding='utf-8')
        print(f"Converted {args.input} -> {args.output}", file=sys.stderr)
    else:
        print(vl_code)


if __name__ == '__main__':
    main()
