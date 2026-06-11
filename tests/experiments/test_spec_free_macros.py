#!/usr/bin/env python3
"""Spec-free experiment: can an LLM handle VL v2 macros WITHOUT the spec?

VL v2 macro names (jload, group_agg, ...) are descriptive enough that a
capable model may infer their semantics with no spec at all, which would
make the 150-token spec overhead optional. This experiment measures that.

Protocol, for each macro scenario:
  1. Ask the model to rewrite the macro snippet as plain standard Python —
     once WITHOUT the spec, once WITH it.
  2. Execute the model's code and the reference expansion (vl.v2.expand_macros)
     on the same data.
  3. Score: identical results = correct.

Usage:
    # Set ANTHROPIC_API_KEY in tests/experiments/.env or the environment
    python tests/experiments/test_spec_free_macros.py
    python tests/experiments/test_spec_free_macros.py --model claude-haiku-4-5-20251001

    # Or, with no API key, route through an authenticated Claude Code CLI:
    python tests/experiments/test_spec_free_macros.py --backend cli --model sonnet
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from vl.v2 import MACRO_SPEC, expand_macros

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class FakeRequests:
    """Offline stand-in for requests, used to execute get_json scenarios."""

    def __init__(self, payload):
        self._payload = payload

    def get(self, url, **kwargs):
        return FakeResponse(self._payload)


def make_scenarios(tmpdir: str):
    """Each scenario: (name, macro_code, namespace_factory, result_var)."""
    cfg_path = os.path.join(tmpdir, "config.json")
    Path(cfg_path).write_text('{"retries": 3}', encoding="utf-8")
    txt_path = os.path.join(tmpdir, "input.txt")
    Path(txt_path).write_text("alpha\nbeta\n", encoding="utf-8")
    csv_path = os.path.join(tmpdir, "data.csv")
    Path(csv_path).write_text("name,age\nAlice,30\n", encoding="utf-8")
    out_path = os.path.join(tmpdir, "out.json")

    users = [
        {"country": "CH", "age": 30, "revenue": 100},
        {"country": "CH", "age": 10, "revenue": 999},
        {"country": "FR", "age": 40, "revenue": 50},
    ]
    api_items = [{"id": 1, "status": "active"}, {"id": 2, "status": "closed"}]

    return [
        ("jload", f"result = jload({cfg_path!r})", lambda: {}, "result"),
        (
            "jsave",
            f"jsave({{'x': 1}}, {out_path!r})\nresult = open({out_path!r}).read()",
            lambda: {},
            "result",
        ),
        ("read_lines", f"result = read_lines({txt_path!r})", lambda: {}, "result"),
        ("csv_rows", f"result = csv_rows({csv_path!r})", lambda: {}, "result"),
        (
            "run_cmd",
            f"r = run_cmd([{sys.executable!r}, '-c', 'print(42)'])\nresult = r.stdout.strip()",
            lambda: {},
            "result",
        ),
        (
            "group_agg",
            "result = group_agg(users, by='country', val='revenue', fn=sum, "
            "where=lambda u: u['age'] > 18)",
            lambda: {"users": [dict(u) for u in users]},
            "result",
        ),
        (
            "get_json",
            "result = get_json('https://api.example.com/items', "
            "where=lambda r: r['status'] == 'active')",
            lambda: {"requests": FakeRequests([dict(i) for i in api_items])},
            "result",
        ),
    ]


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    return blocks[0] if blocks else text


def run_candidate(code: str, namespace: dict, result_var: str):
    ns = dict(namespace)
    # `import requests` in candidate code must resolve to the offline fake
    fake = ns.get("requests")
    saved = sys.modules.get("requests")
    if fake is not None:
        sys.modules["requests"] = fake
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    finally:
        if fake is not None:
            if saved is not None:
                sys.modules["requests"] = saved
            else:
                sys.modules.pop("requests", None)
    return ns[result_var]


def build_prompt(macro_code: str, with_spec: bool) -> str:
    spec_part = f"\n\nHelper reference:\n{MACRO_SPEC}" if with_spec else ""
    return (
        "The following Python snippet uses small helper functions whose "
        "definitions are not shown. Infer their behavior and rewrite the "
        "snippet as plain standard Python (stdlib + requests only), with "
        "identical behavior. Keep the same variable names. Output only the "
        f"code.{spec_part}\n\n```python\n{macro_code}\n```"
    )


def ask_api(client, model: str, macro_code: str, with_spec: bool) -> str:
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": build_prompt(macro_code, with_spec)}],
    )
    return response.content[0].text


def ask_cli(model: str, macro_code: str, with_spec: bool) -> str:
    """Route the question through an authenticated `claude` CLI (print mode).

    Each call is a fresh conversation, so there is no contamination
    between the with-spec and without-spec conditions.
    """
    result = subprocess.run(
        ["claude", "-p", build_prompt(macro_code, with_spec), "--model", model],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr.strip()[:200]}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=None, help="Model id (API) or alias (CLI)")
    parser.add_argument(
        "--backend",
        choices=["auto", "api", "cli"],
        default="auto",
        help="api = Anthropic SDK with ANTHROPIC_API_KEY; cli = authenticated `claude` CLI",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    backend = args.backend
    if backend == "auto":
        if api_key:
            backend = "api"
        elif shutil.which("claude"):
            backend = "cli"
        else:
            print(
                "SKIP: set ANTHROPIC_API_KEY in tests/experiments/.env, or install "
                "an authenticated `claude` CLI, to run this experiment"
            )
            return 0

    if backend == "api":
        if not api_key:
            print("SKIP: --backend api requires ANTHROPIC_API_KEY")
            return 0
        try:
            import anthropic
        except ImportError:
            print("SKIP: pip install anthropic")
            return 0
        client = anthropic.Anthropic(api_key=api_key)
        model = args.model or DEFAULT_MODEL

        def ask(macro_code, with_spec):
            return ask_api(client, model, macro_code, with_spec)
    else:
        if not shutil.which("claude"):
            print("SKIP: --backend cli requires the `claude` CLI on PATH")
            return 0
        model = args.model or "sonnet"

        def ask(macro_code, with_spec):
            return ask_cli(model, macro_code, with_spec)

    scores = {"with_spec": 0, "without_spec": 0}
    total = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        scenarios = make_scenarios(tmpdir)
        print(f"Backend: {backend}  Model: {model}\n")
        print(f"{'macro':<12} {'no spec':>8} {'with spec':>10}")
        print("-" * 32)
        for name, macro_code, ns_factory, result_var in scenarios:
            total += 1
            expected = run_candidate(expand_macros(macro_code), ns_factory(), result_var)
            row = {}
            for label, with_spec in (("without_spec", False), ("with_spec", True)):
                try:
                    answer = ask(macro_code, with_spec)
                    got = run_candidate(extract_code(answer), ns_factory(), result_var)
                    ok = got == expected
                except Exception as exc:
                    ok = False
                    row.setdefault("errors", []).append(f"{label}: {exc}")
                if ok:
                    scores[label] += 1
                row[label] = "OK" if ok else "FAIL"
            print(f"{name:<12} {row['without_spec']:>8} {row['with_spec']:>10}", flush=True)
            for err in row.get("errors", []):
                print(f"    ! {err}")

    print("-" * 32)
    print(f"\nWithout spec: {scores['without_spec']}/{total}")
    print(f"With spec:    {scores['with_spec']}/{total}")
    if scores["without_spec"] == total:
        print("\nVerdict: spec-free mode viable for this model — the 150-token "
              "spec can be dropped.")
    elif scores["without_spec"] >= scores["with_spec"]:
        print("\nVerdict: spec adds nothing for this model.")
    else:
        print("\nVerdict: keep the spec — it improves macro comprehension.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
