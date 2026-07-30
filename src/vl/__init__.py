"""
VL (Very Little) - Token-efficiency toolkit for AI coding

Two measured strategies to send very little to the model:

- ``vl.py_minify``: semantic Python minification (comments, docstrings and
  blank lines removed, AST-verified identical semantics). ~20-30% real
  token savings.
- ``vl.v2``: single-line, valid-Python macros that stand for multi-line
  patterns; a conservative detector compresses existing code into macro
  form and ``expand_macros`` turns it back into dependency-free Python.
  56-93% measured savings per macro use.
"""

__version__ = "0.3.0a0"
__author__ = "VL Contributors"

from .py_minify import minify
from .v2 import MACRO_SPEC, MACROS, compress_macros, expand_macros

__all__ = ["minify", "MACRO_SPEC", "MACROS", "compress_macros", "expand_macros"]
