---
name: vl-optimize
description: Token-efficient Python handling. Use when reading large Python files into context (read them minified via vl-minify, 20-30% fewer tokens) or when generating Python dominated by common I/O patterns (JSON/CSV/HTTP/subprocess/retry - write VL v2 macros, then expand with vl2, 56-93% fewer output tokens). Saves usage-limit budget and context space; no API key involved.
allowed-tools: Bash(vl-minify *) Bash(vl2 *)
---

# VL (Very Little) — send very little to the model

Two CLI tools from the `very-little` package reduce the tokens spent on Python
code. Everything is plain Python in and plain Python out.

## Setup check

Run `vl-minify --help` once. If the command is missing:

```bash
pip install very-little
```

If installation is impossible, continue without optimization — never block the
user's task on this.

## Reading Python economically

For a Python file you need in context but will NOT edit line-by-line
(understanding code, answering questions, reviewing architecture, summarizing):

```bash
vl-minify path/to/file.py        # comments/docstrings/blank lines removed
vl2 -c path/to/file.py           # additionally folds known patterns into macros
```

Use the minified output as your reading copy instead of `Read` on the raw file.
The transformation is AST-verified: the logic is byte-for-byte semantically
identical, only comments, docstrings and blank lines are gone.

Rules:
- The original file on disk stays the source of truth. **Never write minified
  content back to a file**, never quote minified code to the user as if it
  were the file's real text, and use `Read` when you need exact line numbers,
  comments, or docstrings (edits with `Edit` need the real file text).
- Not worth it for small files (< ~50 lines) — just `Read` them.
- Sparsely commented code saves ~10-15%; heavily documented code saves up to 58%.

## Generating Python economically (v2 macros)

When writing Python dominated by these patterns, emit the macro call instead of
the expanded boilerplate:

```text
data = jload(path)                      # read JSON file
jsave(obj, path)                        # write JSON file (indent=2)
lines = read_lines(path)                # file -> list of lines, no \n
write_lines(lines, path)                # list of lines -> file, adds \n
rows = csv_rows(path)                   # CSV file -> list of dicts
csv_save(rows, path)                    # list of dicts -> CSV file (w/ header)
r = run_cmd(cmd)                        # subprocess.run, capture+text+check
out = group_agg(items, by='key', val='field', fn=sum, where=lambda x: ...)
items = get_json(url, where=lambda r: ...)  # HTTP GET -> filtered JSON list
resp = post_json(url, payload)          # HTTP POST json -> parsed JSON
x = retry(lambda: fn(...), tries=3, delay=1)  # retry w/ exponential backoff
cfg = env_load(path)                    # .env file -> dict (skips #comments)
files = walk_files(root, pattern)       # recursive glob -> sorted str paths
```

Then expand before delivering, so the user receives standard dependency-free
Python (imports are added automatically):

```bash
vl2 draft.py -o final.py
```

Rules:
- **The file you save/commit for the user is always the expanded version.**
  Macro calls are a wire format, not a runtime — they only exist between you
  and the expander.
- Only use macros that fit exactly; write normal Python for everything else.
  Misuse fails loudly (`MacroError`) rather than producing wrong code.
- Writing macro-form output saves 56-93% of the tokens on covered patterns —
  this is where the biggest usage-limit savings are, since output tokens are
  the expensive ones.

## When not to use any of this

- Files you are actively editing with exact-match tools (`Edit` needs real text).
- Non-Python code (JS/TS support not yet available).
- Tiny snippets where the tool invocation costs more than it saves.
