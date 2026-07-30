"""Honest token benchmark: measures with a real LLM tokenizer, not a chars/token estimate.

Compares, for each input Python file (or the built-in samples):
  1. the original Python source
  2. the minified Python (vl.py_minify) — semantics preserved
  3. macro-compressed + minified (vl.v2 detector + minifier)

Tokenizer resolution order:
  - Mistral Tekken (bundled offline in the `mistral-common` package, 130k-vocab
    BPE, same family as Claude/GPT tokenizers)
  - tiktoken o200k_base (requires network on first use)
  - fallback: chars/2.58 estimate, clearly flagged as UNRELIABLE

Usage:
    python tests/benchmarks/real_token_benchmark.py [file.py ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from vl.py_minify import minify  # noqa: E402
from vl.v2 import compress_macros  # noqa: E402


def get_tokenizer():
    try:
        import glob

        import mistral_common
        from mistral_common.tokens.tokenizers.tekken import Tekkenizer

        data_dir = Path(mistral_common.__file__).parent / "data"
        candidates = sorted(glob.glob(str(data_dir / "tekken_*.json")))
        if candidates:
            tok = Tekkenizer.from_file(candidates[-1])
            return lambda s: len(tok.encode(s, bos=False, eos=False)), "tekken (mistral-common)"
    except ImportError:
        pass
    try:
        import tiktoken

        enc = tiktoken.get_encoding("o200k_base")
        return lambda s: len(enc.encode(s)), "tiktoken o200k_base"
    except Exception:
        pass
    return lambda s: int(len(s) / 2.58), "CHARS/2.58 ESTIMATE — UNRELIABLE, install mistral-common"


SAMPLES = {
    "simple_func.py": "def greet(name: str) -> str:\n    return f'Hello, {name}!'\n",
    "fib.py": (
        "def fib(n: int) -> int:\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    return fib(n - 1) + fib(n - 2)\n"
    ),
    "data_processing.py": (
        "def process_users(users: list) -> dict:\n"
        "    adults = [u for u in users if u['age'] > 18]\n"
        "    grouped = {}\n"
        "    for user in adults:\n"
        "        country = user['country']\n"
        "        if country not in grouped:\n"
        "            grouped[country] = []\n"
        "        grouped[country].append(user)\n"
        "    return {k: sum(u['revenue'] for u in v) for k, v in grouped.items()}\n"
    ),
    "documented_module.py": (
        '"""Utilities for order handling.\n\nUsed by the billing pipeline.\n"""\n'
        "\n"
        "def total(items: list) -> float:\n"
        '    """Sum item prices.\n\n    Args:\n        items: list of dicts with a price key.\n    """\n'
        "    # accumulate prices\n"
        "    result = 0.0\n"
        "    for item in items:\n"
        "        result += item['price']  # may be Decimal\n"
        "    return result\n"
    ),
}


def main(argv):
    count, name = get_tokenizer()
    print(f"Tokenizer: {name}\n")

    if argv:
        sources = {p: Path(p).read_text(encoding="utf-8") for p in argv}
    else:
        sources = SAMPLES

    header = f"{'file':<28} {'python':>7} {'minified':>9} {'min_sav':>8} {'v2+min':>7} {'v2_sav':>8}"
    print(header)
    print("-" * len(header))
    tot_py = tot_min = tot_v2 = 0
    for fname, src in sources.items():
        minified = minify(src)
        try:
            compressed, _stats = compress_macros(src)
            v2_min = minify(compressed)
        except SyntaxError:
            v2_min = minified
        t_py, t_min, t_v2 = count(src), count(minified), count(v2_min)
        tot_py += t_py
        tot_min += t_min
        tot_v2 += t_v2
        print(
            f"{Path(fname).name:<28} {t_py:>7} {t_min:>9} {100 * (t_py - t_min) / t_py:>7.1f}% "
            f"{t_v2:>7} {100 * (t_py - t_v2) / t_py:>7.1f}%"
        )
    print("-" * len(header))
    print(
        f"{'TOTAL':<28} {tot_py:>7} {tot_min:>9} {100 * (tot_py - tot_min) / tot_py:>7.1f}% "
        f"{tot_v2:>7} {100 * (tot_py - tot_v2) / tot_py:>7.1f}%"
    )
    print(
        "\nPositive % = tokens saved vs original Python. "
        "v2+min = macro compression (vl.v2) followed by minification."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
