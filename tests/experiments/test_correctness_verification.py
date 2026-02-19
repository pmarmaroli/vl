#!/usr/bin/env python3
"""
VL Correctness Verification Test

This test verifies that LLMs produce EQUIVALENT CORRECT results
whether we use Python or VL as the communication format.

Supports: Claude (Anthropic) and Gemini (Google)

Usage:
    python test_correctness_verification.py --model claude
    python test_correctness_verification.py --model gemini

For each test:
1. Send task in Python mode → get Python response
2. Send same task in VL mode → get VL response → compile to Python
3. Execute BOTH and verify they produce correct results
4. Compare if both solutions are functionally equivalent
"""

import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except:
    pass

from vl.py_to_vl import PythonToVLConverter
from vl.compiler import Compiler, TargetLanguage

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

MODEL_NAME = "claude"  # Default, can be overridden by --model flag

def setup_claude():
    """Setup Claude/Anthropic client"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in .env file")
        sys.exit(1)
    
    try:
        import anthropic
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'anthropic', '-q'])
        import anthropic
    
    return anthropic.Anthropic(api_key=api_key)

def setup_gemini():
    """Setup Gemini/Google client"""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY in .env file")
        sys.exit(1)
    
    try:
        import google.generativeai as genai
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'google-generativeai', '-q'])
        import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-3-pro-preview')

def call_llm(client, prompt: str, model_name: str) -> dict:
    """Call LLM and return response with token counts"""
    if model_name == "claude":
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "text": msg.content[0].text.strip(),
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens
        }
    elif model_name == "gemini":
        response = client.generate_content(prompt)
        # Gemini token counting
        input_tokens = client.count_tokens(prompt).total_tokens
        output_tokens = client.count_tokens(response.text).total_tokens
        return {
            "text": response.text.strip(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
    else:
        raise ValueError(f"Unknown model: {model_name}")

VL_PRIMER = """VL syntax: F:name|types|retType|body. Types: I=int S=str N=float B=bool A=arr O=obj V=void. Params: i0,i1,i2. Keywords: ret:x, if:c?a:b, for:v,iter|body, @fn().
Examples: F:add|I,I|I|ret:i0+i1  F:max|I,I|I|ret:if:i0>i1?i0:i1  F:sum|A|I|t=0|for:x,i0|t+=x|ret:t
Respond ONLY in VL."""

# ============================================================================
# TEST CASES WITH VERIFICATION
# ============================================================================

TEST_CASES = [
    {
        "name": "Fix Addition Bug",
        "original_python": """
def calculate(a: int, b: int) -> int:
    return a - b  # BUG: should add
""",
        "task": "Fix the bug. Function should add the two numbers.",
        "test_inputs": [(3, 5), (0, 0), (-1, 1), (100, 200)],
        "expected_fn": lambda a, b: a + b,
        "func_name": "calculate"
    },
    {
        "name": "Division with Zero Check",
        "original_python": """
def safe_divide(x: int, y: int) -> int:
    return x // y
""",
        "task": "Add zero division protection. Return 0 if y is 0.",
        "test_inputs": [(10, 2), (10, 0), (0, 5), (100, 10)],
        "expected_fn": lambda x, y: 0 if y == 0 else x // y,
        "func_name": "safe_divide"
    },
    {
        "name": "Maximum of Two",
        "original_python": """
def find_max(a: int, b: int) -> int:
    return a  # Wrong: always returns first
""",
        "task": "Fix to return the larger of the two numbers.",
        "test_inputs": [(3, 5), (10, 2), (0, 0), (-5, -10), (7, 7)],
        "expected_fn": lambda a, b: max(a, b),
        "func_name": "find_max"
    },
    {
        "name": "Absolute Value",
        "original_python": """
def absolute(n: int) -> int:
    return n  # Wrong: doesn't handle negatives
""",
        "task": "Fix to return absolute value (positive) of n.",
        "test_inputs": [(5,), (-5,), (0,), (-100,), (42,)],
        "expected_fn": lambda n: abs(n),
        "func_name": "absolute"
    },
    {
        "name": "Number Classification",
        "original_python": """
def classify(n: int) -> str:
    return "unknown"
""",
        "task": "Return 'positive' if n>0, 'negative' if n<0, 'zero' if n==0.",
        "test_inputs": [(5,), (-3,), (0,), (100,), (-1,)],
        "expected_fn": lambda n: "positive" if n > 0 else ("negative" if n < 0 else "zero"),
        "func_name": "classify"
    },
    {
        "name": "Greeting Function",
        "original_python": """
def greet(name: str) -> str:
    return name
""",
        "task": "Return greeting in format 'Hello, {name}!'",
        "test_inputs": [("World",), ("Alice",), ("Bob",)],
        "expected_fn": lambda name: f"Hello, {name}!",
        "func_name": "greet"
    },
    {
        "name": "Is Even Check",
        "original_python": """
def is_even(n: int) -> bool:
    return True  # Wrong
""",
        "task": "Return True if n is even, False if odd.",
        "test_inputs": [(2,), (3,), (0,), (100,), (99,)],
        "expected_fn": lambda n: n % 2 == 0,
        "func_name": "is_even"
    },
    {
        "name": "Double Value",
        "original_python": """
def double(n: int) -> int:
    return n  # Wrong
""",
        "task": "Return n multiplied by 2.",
        "test_inputs": [(5,), (0,), (-3,), (100,)],
        "expected_fn": lambda n: n * 2,
        "func_name": "double"
    },
]


def clean_response(response: str) -> str:
    """Remove markdown code blocks if present"""
    if '```' in response:
        lines = response.split('\n')
        code_lines = []
        in_code = False
        for line in lines:
            if line.startswith('```'):
                in_code = not in_code
            elif in_code:
                code_lines.append(line)
        return '\n'.join(code_lines)
    return response


def execute_and_test(code: str, func_name: str, test_inputs: list, expected_fn) -> dict:
    """Execute code and test with inputs"""
    result = {
        "compiles": False,
        "runs": False,
        "all_correct": False,
        "results": [],
        "error": None
    }
    
    try:
        from typing import Any, Callable
        exec_globals = {'Any': Any, 'Callable': Callable}
        exec(code, exec_globals)
        result["compiles"] = True
        
        # Find the function
        fn = None
        for name, obj in exec_globals.items():
            if callable(obj) and name == func_name:
                fn = obj
                break
            elif callable(obj) and not name.startswith('_') and name not in ('Any', 'Callable'):
                fn = obj  # Fallback to any function found
        
        if fn is None:
            result["error"] = f"Function '{func_name}' not found"
            return result
        
        result["runs"] = True
        
        # Test with inputs
        all_correct = True
        for inputs in test_inputs:
            try:
                actual = fn(*inputs)
                expected = expected_fn(*inputs)
                correct = actual == expected
                if not correct:
                    all_correct = False
                result["results"].append({
                    "inputs": inputs,
                    "expected": expected,
                    "actual": actual,
                    "correct": correct
                })
            except Exception as e:
                all_correct = False
                result["results"].append({
                    "inputs": inputs,
                    "error": str(e),
                    "correct": False
                })
        
        result["all_correct"] = all_correct
        
    except SyntaxError as e:
        result["error"] = f"Syntax error: {e}"
    except Exception as e:
        result["error"] = f"Execution error: {e}"
    
    return result


def run_test(test_case: dict, client, model_name: str) -> dict:
    """Run a single test case in both Python and VL modes"""
    
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['name']}")
    print('='*70)
    
    # Convert original to VL
    converter = PythonToVLConverter()
    try:
        vl_original = converter.convert(test_case['original_python'])
    except:
        vl_original = ""
    
    # === PYTHON MODE ===
    print("\n[PYTHON MODE]")
    py_prompt = f"""```python
{test_case['original_python'].strip()}
```

Task: {test_case['task']}

Respond with ONLY the corrected Python function. No explanations."""

    py_result = call_llm(client, py_prompt, model_name)
    py_response = clean_response(py_result["text"])
    print(f"  Response: {py_response[:80]}...")
    print(f"  Tokens: {py_result['input_tokens']} in, {py_result['output_tokens']} out")
    
    py_test = execute_and_test(
        py_response, 
        test_case['func_name'],
        test_case['test_inputs'], 
        test_case['expected_fn']
    )
    
    py_status = "✓ ALL CORRECT" if py_test['all_correct'] else f"✗ FAILED ({py_test.get('error', 'wrong results')})"
    print(f"  Result: {py_status}")
    
    # === VL MODE ===
    print("\n[VL MODE]")
    vl_prompt = f"""{VL_PRIMER}

Code:
{vl_original.strip() if vl_original.strip() else "(create new)"}

Task: {test_case['task']}

Respond ONLY in VL."""

    vl_result = call_llm(client, vl_prompt, model_name)
    vl_response = clean_response(vl_result["text"])
    print(f"  VL Response: {vl_response}")
    print(f"  Tokens: {vl_result['input_tokens']} in, {vl_result['output_tokens']} out")
    
    # Compile VL to Python
    try:
        compiler = Compiler(vl_response, TargetLanguage.PYTHON, type_check_enabled=False)
        vl_compiled = compiler.compile()
        compile_ok = True
    except Exception as e:
        vl_compiled = f"# Compile error: {e}"
        compile_ok = False
    
    print(f"  Compiled: {vl_compiled[:80]}...")
    
    if compile_ok:
        vl_test = execute_and_test(
            vl_compiled,
            test_case['func_name'],
            test_case['test_inputs'],
            test_case['expected_fn']
        )
        vl_status = "✓ ALL CORRECT" if vl_test['all_correct'] else f"✗ FAILED ({vl_test.get('error', 'wrong results')})"
    else:
        vl_test = {"all_correct": False, "error": "Compilation failed"}
        vl_status = "✗ COMPILE ERROR"
    
    print(f"  Result: {vl_status}")
    
    # === COMPARISON ===
    both_correct = py_test['all_correct'] and vl_test['all_correct']
    print(f"\n[COMPARISON] Both correct: {'✓ YES' if both_correct else '✗ NO'}")
    
    # Token comparison
    py_total = py_result['input_tokens'] + py_result['output_tokens']
    vl_total = vl_result['input_tokens'] + vl_result['output_tokens']
    savings = py_total - vl_total
    savings_pct = (savings / py_total * 100) if py_total > 0 else 0
    print(f"[TOKENS] Python: {py_total}, VL: {vl_total}, Savings: {savings} ({savings_pct:.1f}%)")
    
    return {
        "name": test_case['name'],
        "python": {
            "response": py_response,
            "all_correct": py_test['all_correct'],
            "error": py_test.get('error'),
            "tokens": py_total
        },
        "vl": {
            "response": vl_response,
            "compiled": vl_compiled if compile_ok else None,
            "all_correct": vl_test['all_correct'],
            "error": vl_test.get('error'),
            "tokens": vl_total
        },
        "both_correct": both_correct,
        "equivalent": both_correct,
        "token_savings": savings,
        "token_savings_pct": savings_pct
    }


def main():
    parser = argparse.ArgumentParser(description='VL Correctness Verification Test')
    parser.add_argument('--model', choices=['claude', 'gemini'], default='claude',
                        help='Which model to test (default: claude)')
    args = parser.parse_args()
    
    model_name = args.model
    
    print("="*70)
    print(f"VL CORRECTNESS VERIFICATION TEST - {model_name.upper()}")
    print("Does the model produce equivalent correct results with VL vs Python?")
    print("="*70)
    
    # Setup client
    if model_name == "claude":
        client = setup_claude()
    else:
        client = setup_gemini()
    
    results = []
    
    for test_case in TEST_CASES:
        result = run_test(test_case, client, model_name)
        results.append(result)
    
    # Summary
    print("\n" + "="*70)
    print(f"SUMMARY - {model_name.upper()}")
    print("="*70)
    
    print(f"\n{'Test':<25} | {'Python':<8} | {'VL':<8} | {'Equiv':<6} | {'Py Tok':<8} | {'VL Tok':<8} | {'Savings'}")
    print("-"*85)
    
    py_correct = 0
    vl_correct = 0
    both_correct = 0
    total_py_tokens = 0
    total_vl_tokens = 0
    
    for r in results:
        py_status = "✓" if r['python']['all_correct'] else "✗"
        vl_status = "✓" if r['vl']['all_correct'] else "✗"
        equiv_status = "✓" if r['equivalent'] else "✗"
        
        if r['python']['all_correct']:
            py_correct += 1
        if r['vl']['all_correct']:
            vl_correct += 1
        if r['both_correct']:
            both_correct += 1
        
        total_py_tokens += r['python']['tokens']
        total_vl_tokens += r['vl']['tokens']
        
        print(f"{r['name']:<25} | {py_status:<8} | {vl_status:<8} | {equiv_status:<6} | {r['python']['tokens']:<8} | {r['vl']['tokens']:<8} | {r['token_savings']:>4} ({r['token_savings_pct']:>5.1f}%)")
    
    total_savings = total_py_tokens - total_vl_tokens
    total_savings_pct = (total_savings / total_py_tokens * 100) if total_py_tokens > 0 else 0
    
    print("-"*85)
    print(f"{'TOTAL':<25} | {py_correct}/{len(results):<5} | {vl_correct}/{len(results):<5} | {both_correct}/{len(results):<4} | {total_py_tokens:<8} | {total_vl_tokens:<8} | {total_savings:>4} ({total_savings_pct:>5.1f}%)")
    
    print("\n" + "="*70)
    print("CONCLUSIONS")
    print("="*70)
    
    print(f"\nModel: {model_name.upper()}")
    print(f"Python mode accuracy: {py_correct}/{len(results)} ({100*py_correct/len(results):.0f}%)")
    print(f"VL mode accuracy:     {vl_correct}/{len(results)} ({100*vl_correct/len(results):.0f}%)")
    print(f"Both equivalent:      {both_correct}/{len(results)} ({100*both_correct/len(results):.0f}%)")
    print(f"\nToken usage:")
    print(f"  Python total: {total_py_tokens} tokens")
    print(f"  VL total:     {total_vl_tokens} tokens")
    print(f"  Savings:      {total_savings} tokens ({total_savings_pct:.1f}%)")
    
    if vl_correct == py_correct:
        print(f"\n✓ VL produces EQUIVALENT correctness to Python on {model_name.upper()}!")
        print("  The VL syntax is a valid intermediate language for LLM communication.")
    elif vl_correct >= py_correct - 1:
        print(f"\n≈ VL produces NEARLY equivalent results to Python on {model_name.upper()}")
        print("  Minor differences may be due to syntax edge cases.")
    else:
        print(f"\n⚠ VL has LOWER accuracy than Python on {model_name.upper()}")
        print("  The VL primer may need improvement for this model.")
    
    return 0 if both_correct == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
