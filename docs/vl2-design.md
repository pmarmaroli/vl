# VL v2: Tokenizer-Aware Macros

**Status:** Prototype (validated by benchmark)
**Prerequisite reading:** [token-analysis.md](token-analysis.md) — why compact
character-level syntax loses tokens on real BPE tokenizers.

## The v2 thesis

> *Python, minus everything the model doesn't need, plus macros for the
> patterns models see constantly.*

VL v1 replaced Python's surface syntax and lost: BPE tokenizers already
compress idiomatic Python to ~1 token per keyword/indent, and v1's separators
fragmented identifiers. VL v2 keeps Python as the carrier syntax and adds
**macros**: single-line, valid-Python calls that stand for multi-line
patterns. Savings come from removing *lines*, not characters.

Two layers compose:

1. **Semantic minification** (`vl.py_minify`) — ~20–30% on any file, zero risk.
2. **Macros** (`vl.v2`) — 56–80% on the specific patterns they cover.

## The adoption rule

A macro stays in the registry **only if its call form costs fewer real tokens
than its own expansion**. `tests/benchmarks/v2_macro_benchmark.py` enforces
this (exit code 1 on any FAIL) and reports the spec amortization.

Current registry (Tekken tokenizer, June 2026):

| Macro | Call tokens | Expanded tokens | Saving |
|---|---|---|---|
| `jload(path)` | 8 | 32 | 75.0% |
| `jsave(obj, path)` | 10 | 38 | 73.7% |
| `read_lines(path)` | 8 | 40 | 80.0% |
| `csv_rows(path)` | 8 | 39 | 79.5% |
| `run_cmd(cmd)` | 10 | 23 | 56.5% |
| `group_agg(items, by=, val=, fn=, where=)` | 34 | 77 | 55.8% |
| `get_json(url, where=)` | 25 | 58 | 56.9% |

**Spec overhead:** the LLM needs the macro spec once per conversation
(`python -m vl.v2 --spec`, 150 tokens). Mean saving is ~29 tokens per macro
use, so the spec amortizes after **~5 macro uses** — and prompt caching makes
it nearly free on subsequent requests.

## How it works

```bash
# Show the spec to paste into an LLM system prompt
python -m vl.v2 --spec

# The LLM writes compact code:
#   config = jload('config.json')
#   totals = group_agg(users, by='country', val='revenue', fn=sum,
#                      where=lambda u: u['age'] > 18)

# Expand to dependency-free Python before running it:
python -m vl.v2 generated.py -o runnable.py

# Reverse direction — compress existing Python before sending it to an LLM:
python -m vl.v2 -c existing.py
```

### The detector (Python → macros)

`compress_macros` recognizes the expanded idioms in existing code — JSON
file I/O `with` blocks, `read_lines` variants, `csv.DictReader` blocks,
`subprocess.run` boilerplate, `requests.get` + `raise_for_status` +
`.json()` (+ filter comprehension), and group-by accumulation in its
`setdefault`, verbose `if key not in` and `return {dictcomp}` forms,
including a pre-filter comprehension feeding the loop (folded into
`where=`) — and rewrites them as macro calls. Combined with minification,
the measured end-to-end result on a realistic reporting module (Tekken
tokenizer):

| Stage | Tokens | Saving |
|---|---|---|
| original | 250 | — |
| minified only | 219 | 12.4% |
| macro-compressed only | 127 | 49.2% |
| **compressed + minified** | **107** | **57.2%** |

Matchers are conservative by design — a rewrite happens only when it is
semantically safe:

- A pattern's internal names (file handle, loop variable, accumulator,
  response object) leak out of `with`/`for` blocks in Python, so the
  detector skips the rewrite if they may be *read* afterwards: a
  `symtable` pass catches free/global uses in nested scopes, and a
  positional first-occurrence rule distinguishes rebinding from reading
  in the following statements (conditional rebinds count as reads).
- `requests.get` without `raise_for_status()` is never compressed —
  the round-trip would silently add error-raising behavior.
- `open()` with a non-utf-8 encoding or unusual modes is left alone.
- Two documented normalizations remain: `json.dump` indent → 2 and
  request timeout → 30 on round-trip. Avoid `-c` if those matter.

Every detected form has a unit test that executes the original and the
compress→expand round-trip on sample data and asserts identical results.

Expansion details:

- Macro calls are recognized as `target = macro(...)` assignments (or bare
  statements for `jsave`) anywhere in the module, including function bodies.
- `where=lambda x: ...` predicates are **inlined** (parameter substituted),
  so the expansion reads like handwritten code and costs no closure.
- Required imports (`json`, `requests`) are added once, after the module
  docstring, only if missing.
- Misuse (e.g. `jload` without an assignment target) raises `MacroError`
  rather than producing wrong code.

## Design rules for new macros

1. **Valid Python call syntax only.** No new separators — they fragment BPE
   merges (see token-analysis.md).
2. **Must collapse ≥3 lines.** One-line patterns never amortize.
3. **Expansion must be dependency-free, executable Python** verified by a
   unit test that runs it (`tests/unit/test_v2_macros.py`).
4. **Benchmark before merging.** Add the call form to `MACRO_USES` in
   `v2_macro_benchmark.py`; if it doesn't PASS, it doesn't ship.
5. **Spec line ≤ 1 line.** The spec is paid for in every conversation.

## Candidate macros (not yet implemented)

Each needs benchmark validation first:

- `csv_rows(path)` → `csv.DictReader` boilerplate
- `run_cmd(cmd)` → `subprocess.run(..., capture_output=True, text=True, check=True)`
- `retry(fn, times=3, delay=1)` → retry loop with backoff
- `clamp(x, lo, hi)` — probably FAILs the rule (1 line in Python already); listed
  as an example of what *not* to add.

## Roadmap status

1. ~~**Detector (Python → macros)**~~ — done, see above.
2. ~~**Extension integration**~~ — done. `vl.optimizationMode: "v2"` runs the
   compress+minify pipeline (`python -m vl.v2 -c --minify --json`); the macro
   spec is added to the system prompt only when macros were actually
   detected, and its token cost is counted in the never-worse-than-original
   comparison. Plain-Python contexts no longer carry any spec at all.
3. ~~**More detectable forms**~~ — done: pre-filtered list feeding the group
   loop (folded into `where=`), `csv_rows`, `run_cmd`. All pass the adoption
   rule (see registry table above).
4. ~~**Spec-free mode**~~ — measurement harness shipped:
   `tests/experiments/test_spec_free_macros.py` asks a model to rewrite each
   macro snippet as plain Python with and without the spec, executes both
   against reference expansions, and reports a per-macro verdict. Requires
   `ANTHROPIC_API_KEY` (offline reference paths are pre-verified). If a model
   scores 7/7 without the spec, drop the 150-token spec for that model.

## Possible next steps

- Run the spec-free experiment across models and make spec inclusion
  per-model automatic.
- More macro candidates (`retry`, argparse boilerplate, logging setup) —
  same adoption rule.
- Make `v2` the extension default once it has soaked in real use.
