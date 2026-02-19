numbers = [1, 2, 3, 4, 5]
person = {'name': 'Alice', 'age': 30}
x = True and False
y = True or False
x = 10
"""Tests for Python to VL converter (full module passthrough mode)."""

import os
import sys
import textwrap

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.py_to_vl import PythonToVLConverter
from vl.compiler import Compiler, TargetLanguage


def _norm(source: str) -> str:
    return textwrap.dedent(source).strip()


def test_converter_returns_raw_wrapper():
    python_code = _norm(
        """
        def add(x: int, y: int) -> int:
            return x + y
        """
    )

    converter = PythonToVLConverter()
    vl_code = converter.convert(python_code)

    assert vl_code.startswith("py:__RAW_B64__(")
    # Decode payload to ensure source is preserved
    payload = vl_code[len("py:__RAW_B64__("):-1]  # strip prefix and closing paren
    decoded = __import__("base64").b64decode(eval(payload)).decode("utf-8")
    assert "def add" in decoded
    assert "return x + y" in decoded


def test_round_trip_preserves_source():
    python_code = _norm(
        '''
        """Docstring keeps header."""
        value = 42

        def double(x: int) -> int:
            return x * 2

        result = double(value)
        '''
    )

    converter = PythonToVLConverter()
    vl_code = converter.convert(python_code)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()

    assert _norm(generated_python) == python_code


def test_round_trip_preserves_unicode_and_bom():
    # Include BOM, ZWJ, accents, and explicit escape sequences
    original = "\ufeff" + _norm(
        """
        title = "Café"
        zwj = "\u200d"
        symbols = "≡ƒºæ\u200dΓÜò∩╕Å"
        snowman = "\u2603"
        def emit():
            return f"{title}-{zwj}-{symbols}-{snowman}"
        """
    ) + "\n"  # preserve trailing newline like the converter adds

    converter = PythonToVLConverter()
    vl_code = converter.convert(original)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()

    assert original == generated_python
