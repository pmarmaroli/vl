---
description: Adopt VL v2 macro generation for this session (56-93% fewer output tokens on covered patterns)
allowed-tools: Bash(vl2 *)
---

For the rest of this session, when generating Python code dominated by the
patterns below, write the macro call form instead of the expanded boilerplate,
then expand with `vl2 draft.py -o final.py` before delivering — the user must
always receive the expanded, dependency-free standard Python.

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

Only use a macro when it fits the need exactly; write normal Python otherwise.
If `vl2` is not installed, suggest `pip install very-little`.

Confirm to the user that VL v2 macro generation is now active, in one sentence.
