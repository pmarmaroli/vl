---
description: Read Python file(s) into context in minified form (20-30% fewer tokens, semantics identical)
argument-hint: [file.py ...]
allowed-tools: Bash(vl-minify *) Bash(vl2 *)
---

Load the following Python file(s) into context in token-minified form: $ARGUMENTS

For each file, run `vl-minify <file>` via Bash and treat its output as your
reading copy of that file (comments, docstrings and blank lines are removed;
the logic is AST-verified identical). Do not `Read` the raw files as well —
that would defeat the purpose. If `vl-minify` is not installed, say so and
suggest `pip install very-little`, then fall back
to a normal `Read`.

Remember: the files on disk remain the source of truth. If you later edit one
of these files, `Read` it first to get its exact text; never write minified
content back to disk.

Afterwards, briefly report the token estimate saved (the tool prints nothing
extra — compare the minified output length to the file size) and continue with
whatever the user asks about this code.
