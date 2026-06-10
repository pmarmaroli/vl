"""Tests for the Python to VL converter."""

import os
import sys
import textwrap

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.py_to_vl import PythonToVLConverter
from vl.compiler import Compiler, TargetLanguage


def _norm(source: str) -> str:
    return textwrap.dedent(source).strip()


def test_simple_function_converts_to_vl():
    python_code = _norm(
        """
        def add(x: int, y: int) -> int:
            return x + y
        """
    )

    vl_code = PythonToVLConverter().convert(python_code)

    assert vl_code.strip() == "F:add|x:I,y:I|I|ret:x+y"


def test_simple_function_round_trips_through_compiler():
    python_code = _norm(
        """
        def add(x: int, y: int) -> int:
            return x + y
        """
    )

    vl_code = PythonToVLConverter().convert(python_code)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()

    assert _norm(generated_python) == python_code


def test_tuple_unpacking_uses_deterministic_temp_names():
    python_code = _norm(
        """
        def split_pair(pair):
            a, b = pair
            return a
        """
    )

    first = PythonToVLConverter().convert(python_code)
    second = PythonToVLConverter().convert(python_code)

    assert first == second
    assert "_t0" in first
    assert "_tmp_" not in first


def test_param_names_preserved():
    python_code = _norm(
        """
        def greet(name: str) -> str:
            return name
        """
    )

    vl_code = PythonToVLConverter().convert(python_code)

    assert "name:S" in vl_code
