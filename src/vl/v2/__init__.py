"""VL v2: tokenizer-aware macros.

Design principles (see docs/token-analysis.md):
  1. Macro calls are valid Python syntax, so BPE tokenizers compress them
     like ordinary code — no separators that fragment identifiers.
  2. A macro is only adopted if it beats its own expansion on a real
     tokenizer (tests/benchmarks/v2_macro_benchmark.py).
  3. Every macro expands to dependency-free Python via `expand_macros`.
"""

from .macros import MACRO_SPEC, MACROS, expand_macros

__all__ = ["MACROS", "MACRO_SPEC", "expand_macros"]
