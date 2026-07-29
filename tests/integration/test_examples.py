"""Every VL example program in examples/ must compile to Python."""

from pathlib import Path

import pytest

from vl.compiler import Compiler, TargetLanguage

EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"
VL_FILES = sorted(EXAMPLES_DIR.rglob("*.vl"))


def test_examples_found():
    assert VL_FILES, f"no .vl examples found under {EXAMPLES_DIR}"


@pytest.mark.parametrize("vl_file", VL_FILES, ids=[f.name for f in VL_FILES])
def test_example_compiles(vl_file):
    vl_code = vl_file.read_text(encoding="utf-8")
    compiler = Compiler(vl_code, TargetLanguage.PYTHON)
    py_code = compiler.compile()
    assert py_code.strip(), f"{vl_file.name} compiled to empty output"
