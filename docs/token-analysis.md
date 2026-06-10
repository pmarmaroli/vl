# Token Analysis: Measuring VL with a Real Tokenizer

**Date:** June 2026
**Tokenizer:** Mistral Tekken (`mistral-common`, 130k-vocab BPE — same technology family as the Claude and GPT tokenizers, and available fully offline)
**Tool:** `tests/benchmarks/real_token_benchmark.py`

## TL;DR

The project's original premise — *fewer characters ⇒ fewer tokens* — does not
hold under a real BPE tokenizer. Measured honestly:

| Strategy | Real token savings vs plain Python |
|---|---|
| VL conversion (current syntax) | **−36% to +6%** (usually negative) |
| Semantic Python minification (`vl.py_minify`) | **+19% to +58%** (typically ~25%) |

The earlier "47% savings" figure came from a **chars/2.58 estimate**, which
systematically overstates VL's efficiency because BPE tokenizers compress
idiomatic Python far better than they compress novel syntax.

## Why compact syntax loses tokens

BPE tokenizers are trained on massive amounts of real-world code. As a result,
Python's "verbose" surface syntax is almost free:

```
"def greet(name: str) -> str:"   → 9 tokens:  def | greet | (name | : |  str | ) |  -> |  str | :
"F:greet|name:S|S|"              → 11 tokens: F | : | g | reet | | | name | : | S | | | S | |
```

Three effects work against any compact notation:

1. **Keywords and whitespace are single tokens.** `def `, ` return`, ` in `,
   `:\n`, and a full level of indentation each cost ~1 token. Removing them
   saves almost nothing.
2. **Separators fragment identifiers.** ` adults` is 1 token, but after a `:`
   or `|` the same word becomes `ad|ult|s` (3 tokens). Every VL delimiter
   breaks BPE merges on both sides.
3. **Novel digraphs don't merge.** `F:`, `ret:`, `|S|` never appear in
   training data, so they tokenize character-by-character.

Measured examples (Tekken tokenizer):

| Construct | Python tokens | VL tokens |
|---|---|---|
| `def greet(name: str) -> str:` | 9 | 11 |
| `return f'Hello, {name}!'` (indented) | 10 | 8 |
| `if n <= 1: return n` (2 lines) | 9 | 9 |
| `for user in adults:` | 5 | 8 |

VL only wins where it replaces *many lines* with one high-level construct
(e.g. the `data:users|filter:...|groupBy:...|agg:...` pipeline, which
legitimately collapses ~8 lines of dict bookkeeping). It loses everywhere
the translation is 1-line-to-1-line.

There is also a hidden cost not counted above: the LLM must be given the VL
specification (or examples) in the prompt for every conversation, and
correctness on an unfamiliar language is measurably worse than on Python.

## What actually saves tokens: semantic minification

Most token weight in real files is **redundancy the model doesn't need**:
comments, docstrings, blank lines. Removing them keeps the code 100% valid
Python (zero spec overhead, zero correctness risk) and saves 20–30% on real
files:

| File | Original | Minified | Saving |
|---|---|---|---|
| `src/vl/parser.py` | 18,557 | 13,473 | 27.4% |
| `src/vl/py_to_vl.py` | 11,182 | 7,925 | 29.1% |
| `src/vl/lexer.py` | 4,166 | 3,141 | 24.6% |
| `src/vl/compiler.py` | 1,718 | 1,119 | 34.9% |
| **All `src/vl` (21 files)** | **70,645** | **52,212** | **26.1%** |

This is now shipped as `vl.py_minify`:

```bash
python -m vl.py_minify script.py -o script.min.py
```

The minifier verifies its own output: the result must parse and its AST must
be identical to the original's (docstrings excepted). On any mismatch it
returns the input unchanged.

## Design directions for a genuinely token-efficient language (VL v2)

If the goal remains a dedicated AI language, the design must be driven by the
tokenizer, not by character count:

1. **Keep Python's surface syntax** where BPE already compresses it
   (keywords, indentation, identifiers). Don't replace cheap tokens.
2. **Add macro constructs only where they collapse multi-line patterns** —
   pipelines (`filter/groupBy/agg`), API-call+parse+filter idioms, common
   boilerplate (argparse setup, dataclass plumbing). This is where VL's
   measured wins were real (up to 85% on pipelines).
3. **Never introduce separators adjacent to identifiers** (`|name`, `:name`)
   — always keep a space or use syntax the tokenizer already merges.
4. **Benchmark every proposed construct** with `real_token_benchmark.py`
   before adopting it. A construct that doesn't beat plain Python on the
   real tokenizer is rejected.
5. **Count the spec overhead.** A custom language costs `spec_tokens` per
   conversation; it must amortize. Python + minification costs zero.

In short: the highest-value evolution of this project is *"Python, minus
everything the model doesn't need, plus macros for the patterns models see
constantly"* — not an alternative character-level syntax.

## Reproducing these numbers

```bash
pip install mistral-common
python tests/benchmarks/real_token_benchmark.py                 # built-in samples
python tests/benchmarks/real_token_benchmark.py path/to/file.py # your own code
```
