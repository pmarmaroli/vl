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

from vl.py_minify import minify  # noqa: E402
from vl.v2 import MACRO_SPEC, compress_macros, expand_macros  # noqa: E402

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


# Realistic module exercising several detectable patterns, for the
# end-to-end pipeline measurement (detector + minifier).
PIPELINE_SAMPLE = '''"""Sales reporting job."""
import json
import requests


def load_config(path):
    """Read the job configuration."""
    with open(path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config


def fetch_orders(url):
    # Pull the order list from the API
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    orders = resp.json()
    orders = [o for o in orders if o['status'] == 'paid']
    return orders


def revenue_by_country(orders):
    """Aggregate paid revenue per country."""
    grouped = {}
    for order in orders:
        country = order['country']
        if country not in grouped:
            grouped[country] = []
        grouped[country].append(order)
    return {k: sum(o['amount'] for o in v) for k, v in grouped.items()}


def save_report(report, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
'''


def run_pipeline_benchmark(count):
    print("\nEnd-to-end pipeline (realistic module):")
    compressed, stats = compress_macros(PIPELINE_SAMPLE)
    compressed_min = minify(compressed)
    t_orig = count(PIPELINE_SAMPLE)
    t_min = count(minify(PIPELINE_SAMPLE))
    t_comp = count(compressed)
    t_both = count(compressed_min)
    print(f"  detected: {', '.join(f'{k} x{v}' for k, v in sorted(stats.items()))}")
    print(f"  original                  : {t_orig:>4} tokens")
    print(f"  minified only             : {t_min:>4} tokens ({100 * (t_orig - t_min) / t_orig:.1f}% saved)")
    print(f"  macro-compressed only     : {t_comp:>4} tokens ({100 * (t_orig - t_comp) / t_orig:.1f}% saved)")
    print(f"  compressed + minified     : {t_both:>4} tokens ({100 * (t_orig - t_both) / t_orig:.1f}% saved)")
    return stats


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

    pipeline_stats = run_pipeline_benchmark(count)
    if len(pipeline_stats) < 4:
        print("FAIL: detector missed expected patterns in the pipeline sample")
        failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
