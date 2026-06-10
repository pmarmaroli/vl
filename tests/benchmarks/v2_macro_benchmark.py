"""Per-macro validation benchmark for VL v2.

Rule: a macro stays in the registry only if its call form costs fewer
real tokens than its own expansion. Also reports the spec overhead
(MACRO_SPEC must be sent once per conversation) and the break-even
number of macro uses.

Usage:
    python tests/benchmarks/v2_macro_benchmark.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vl.v2 import MACRO_SPEC, expand_macros  # noqa: E402

# Reuse the tokenizer resolution from the main benchmark
sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_token_benchmark import get_tokenizer  # noqa: E402

# Representative use of each macro (call form the LLM would write).
MACRO_USES = {
    "jload": "config = jload('config.json')\n",
    "jsave": "jsave(results, 'out/results.json')\n",
    "read_lines": "lines = read_lines('input.txt')\n",
    "group_agg": (
        "totals = group_agg(users, by='country', val='revenue', fn=sum, "
        "where=lambda u: u['age'] > 18)\n"
    ),
    "get_json": (
        "items = get_json('https://api.example.com/items', "
        "where=lambda r: r['status'] == 'active')\n"
    ),
}


def main():
    count, name = get_tokenizer()
    print(f"Tokenizer: {name}\n")

    header = f"{'macro':<12} {'call':>6} {'expanded':>9} {'saved':>6} {'saving':>8}  verdict"
    print(header)
    print("-" * len(header))

    savings = []
    failures = 0
    for macro, use in MACRO_USES.items():
        expanded = expand_macros(use)
        t_call, t_exp = count(use), count(expanded)
        saved = t_exp - t_call
        ok = saved > 0
        if not ok:
            failures += 1
        savings.append(saved)
        print(
            f"{macro:<12} {t_call:>6} {t_exp:>9} {saved:>6} "
            f"{100 * saved / t_exp:>7.1f}%  {'PASS' if ok else 'FAIL — drop this macro'}"
        )

    spec_tokens = count(MACRO_SPEC)
    mean_saving = sum(savings) / len(savings)
    print("-" * len(header))
    print(f"\nSpec overhead (sent once per conversation): {spec_tokens} tokens")
    if mean_saving > 0:
        print(f"Mean saving per macro use: {mean_saving:.1f} tokens")
        print(f"Break-even: {spec_tokens / mean_saving:.1f} macro uses per conversation")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
