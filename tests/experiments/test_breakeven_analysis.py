#!/usr/bin/env python3
"""
VL Efficiency Breakeven Analysis

Find the code size at which VL becomes more token-efficient than Python.

Theory:
- VL has a fixed primer cost (~100 tokens)
- VL compresses code by ~50%
- VL output is ~30% smaller

Breakeven formula:
  Python_tokens = VL_tokens
  code_size + response = (code_size * 0.5) + primer + (response * 0.7)
  
Solving for code_size ≈ 500-700 tokens (depending on response size)

This test verifies empirically by testing progressively larger code samples.

Usage:
  python test_breakeven_analysis.py              # Default: Claude
  python test_breakeven_analysis.py --model claude
  python test_breakeven_analysis.py --model gemini
"""

import os
import sys
import argparse
from pathlib import Path

# Skip this experimental, API-calling script when running under pytest
if 'pytest' in sys.modules:
    import pytest
    pytest.skip("Breakeven analysis is a manual LLM experiment", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except:
    pass

from vl.py_to_vl import PythonToVLConverter
from vl.compiler import Compiler, TargetLanguage

# Parse arguments
parser = argparse.ArgumentParser(description='VL Breakeven Analysis')
parser.add_argument('--model', choices=['claude', 'gemini'], default='claude',
                    help='Which model to test (default: claude)')
args = parser.parse_args()

MODEL_NAME = args.model

# Setup clients based on model
claude_client = None
gemini_model = None

if MODEL_NAME == 'claude':
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    if not ANTHROPIC_API_KEY:
        print("ERROR: Set ANTHROPIC_API_KEY in .env file")
        sys.exit(1)
    import anthropic
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
else:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        print("ERROR: Set GEMINI_API_KEY in .env file")
        sys.exit(1)
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-3-pro-preview')

# Minimal VL primer (~100 tokens)
VL_PRIMER = """VL syntax: F:name|types|retType|body. Types: I=int S=str N=float B=bool A=arr O=obj. Params: i0,i1,i2. Keywords: ret:x, if:c?a:b, for:v,iter|body, @fn().
Examples: F:add|I,I|I|ret:i0+i1  F:max|I,I|I|ret:if:i0>i1?i0:i1  F:sum|A|I|t=0|for:x,i0|t+=x|ret:t
Respond ONLY in VL."""

# ============================================================================
# CODE SAMPLES OF INCREASING SIZE
# ============================================================================

def generate_python_code(num_functions: int) -> str:
    """Generate Python code with N functions of varying complexity"""
    code = '''"""Auto-generated Python module for testing"""

'''
    
    function_templates = [
        '''def add_{i}(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
''',
        '''def multiply_{i}(x: int, y: int) -> int:
    """Multiply two numbers"""
    return x * y
''',
        '''def is_positive_{i}(n: int) -> bool:
    """Check if number is positive"""
    return n > 0
''',
        '''def greet_{i}(name: str) -> str:
    """Return a greeting"""
    return f"Hello, {{name}}!"
''',
        '''def max_of_two_{i}(a: int, b: int) -> int:
    """Return the larger of two numbers"""
    if a > b:
        return a
    return b
''',
        '''def absolute_{i}(n: int) -> int:
    """Return absolute value"""
    if n < 0:
        return -n
    return n
''',
        '''def factorial_{i}(n: int) -> int:
    """Calculate factorial"""
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result
''',
        '''def sum_list_{i}(numbers: list) -> int:
    """Sum all numbers in a list"""
    total = 0
    for num in numbers:
        total += num
    return total
''',
        '''def filter_positives_{i}(numbers: list) -> list:
    """Filter to only positive numbers"""
    result = []
    for n in numbers:
        if n > 0:
            result.append(n)
    return result
''',
        '''def classify_{i}(n: int) -> str:
    """Classify a number"""
    if n > 0:
        return "positive"
    elif n < 0:
        return "negative"
    else:
        return "zero"
''',
    ]
    
    for i in range(num_functions):
        template = function_templates[i % len(function_templates)]
        code += template.format(i=i) + "\n"
    
    return code


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken"""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Rough estimate: 4 chars per token
        return len(text) // 4


def call_llm(prompt: str) -> dict:
    """Call the selected LLM and return response with token counts"""
    if MODEL_NAME == 'claude':
        msg = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "text": msg.content[0].text,
            "input_tokens": msg.usage.input_tokens,
            "output_tokens": msg.usage.output_tokens,
            "total_tokens": msg.usage.input_tokens + msg.usage.output_tokens
        }
    else:
        response = gemini_model.generate_content(prompt)
        # Gemini token counting
        input_tokens = gemini_model.count_tokens(prompt).total_tokens
        output_tokens = gemini_model.count_tokens(response.text).total_tokens
        return {
            "text": response.text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }


def test_size(num_functions: int, dry_run: bool = False) -> dict:
    """Test a specific code size and compare Python vs VL tokens"""
    
    python_code = generate_python_code(num_functions)
    python_tokens = count_tokens(python_code)
    
    # Convert to VL
    converter = PythonToVLConverter()
    try:
        vl_code = converter.convert(python_code)
        vl_tokens = count_tokens(vl_code)
    except Exception as e:
        vl_code = f"# Conversion error: {e}"
        vl_tokens = count_tokens(vl_code)
    
    primer_tokens = count_tokens(VL_PRIMER)
    
    result = {
        "num_functions": num_functions,
        "python_code_tokens": python_tokens,
        "vl_code_tokens": vl_tokens,
        "primer_tokens": primer_tokens,
        "compression_ratio": vl_tokens / python_tokens if python_tokens > 0 else 0,
    }
    
    if dry_run:
        # Estimate without API call
        # Assume response is ~30% of input size
        est_py_response = int(python_tokens * 0.3)
        est_vl_response = int(est_py_response * 0.7)  # VL responses are smaller
        
        result["python_total_est"] = python_tokens + est_py_response
        result["vl_total_est"] = vl_tokens + primer_tokens + est_vl_response
        result["savings_est"] = result["python_total_est"] - result["vl_total_est"]
        result["savings_pct_est"] = (result["savings_est"] / result["python_total_est"]) * 100
        
    else:
        # Actually call LLM
        task = "Add input validation to all functions to handle None inputs gracefully. Return 0 or empty for None."
        
        # Python mode
        py_prompt = f"```python\n{python_code}\n```\n\nTask: {task}\n\nRespond with the complete modified Python code only."
        
        py_response = call_llm(py_prompt)
        
        result["python_input"] = py_response["input_tokens"]
        result["python_output"] = py_response["output_tokens"]
        result["python_total"] = py_response["total_tokens"]
        
        # VL mode
        vl_prompt = f"{VL_PRIMER}\n\nCode:\n{vl_code}\n\nTask: {task}\n\nRespond in VL only."
        
        vl_response = call_llm(vl_prompt)
        
        result["vl_input"] = vl_response["input_tokens"]
        result["vl_output"] = vl_response["output_tokens"]
        result["vl_total"] = vl_response["total_tokens"]
        
        result["savings"] = result["python_total"] - result["vl_total"]
        result["savings_pct"] = (result["savings"] / result["python_total"]) * 100
    
    return result


def main():
    print("="*80)
    print(f"VL EFFICIENCY BREAKEVEN ANALYSIS ({MODEL_NAME.upper()})")
    print("Finding the code size where VL becomes more efficient than Python")
    print("="*80)
    
    # First, do dry run estimates
    print("\n[PHASE 1] Dry Run Estimates (no API calls)")
    print("-"*80)
    print(f"{'Functions':<10} | {'Python':<12} | {'VL+Primer':<12} | {'Est. Savings':<15} | {'Efficient?'}")
    print("-"*80)
    
    sizes_to_test = [1, 2, 3, 5, 8, 10, 15, 20, 30, 50]
    estimates = []
    
    for n in sizes_to_test:
        r = test_size(n, dry_run=True)
        estimates.append(r)
        
        efficient = "✓ VL wins" if r["savings_est"] > 0 else "✗ Python wins"
        print(f"{r['num_functions']:<10} | {r['python_total_est']:<12} | {r['vl_total_est']:<12} | {r['savings_est']:>6} ({r['savings_pct_est']:>5.1f}%) | {efficient}")
    
    # Find estimated breakeven
    breakeven_est = None
    for r in estimates:
        if r["savings_est"] > 0:
            breakeven_est = r["num_functions"]
            break
    
    print("-"*80)
    print(f"Estimated breakeven: ~{breakeven_est} functions ({estimates[sizes_to_test.index(breakeven_est)]['python_code_tokens']} tokens)")
    
    # Now do real API tests around the breakeven point
    print("\n[PHASE 2] Real API Tests (around breakeven point)")
    print("-"*80)
    
    # Test a few sizes around breakeven
    test_sizes = [5, 15, 30, 50]
    print(f"\nTesting {test_sizes} functions with actual Claude API calls...")
    
    results = []
    for n in test_sizes:
        print(f"\nTesting {n} functions...")
        r = test_size(n, dry_run=False)
        results.append(r)
        
        efficient = "✓ VL" if r["savings"] > 0 else "✗ Python"
        print(f"  Python: {r['python_total']} tokens ({r['python_input']} in + {r['python_output']} out)")
        print(f"  VL:     {r['vl_total']} tokens ({r['vl_input']} in + {r['vl_output']} out)")
        print(f"  Savings: {r['savings']} tokens ({r['savings_pct']:.1f}%) → {efficient}")
    
    # Summary
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"\n{'Functions':<10} | {'Code Tokens':<12} | {'Python Total':<14} | {'VL Total':<14} | {'Savings':<15} | {'Winner'}")
    print("-"*90)
    
    for r in results:
        winner = "VL ✓" if r["savings"] > 0 else "Python"
        print(f"{r['num_functions']:<10} | {r['python_code_tokens']:<12} | {r['python_total']:<14} | {r['vl_total']:<14} | {r['savings']:>5} ({r['savings_pct']:>5.1f}%) | {winner}")
    
    # Find actual breakeven
    print("\n" + "="*80)
    print("CONCLUSIONS")
    print("="*80)
    
    breakeven_actual = None
    for r in results:
        if r["savings"] > 0:
            breakeven_actual = r
            break
    
    if breakeven_actual:
        print(f"\n✓ BREAKEVEN POINT: ~{breakeven_actual['num_functions']} functions ({breakeven_actual['python_code_tokens']} code tokens)")
        print(f"  At this size, VL saves {breakeven_actual['savings']} tokens ({breakeven_actual['savings_pct']:.1f}%)")
    else:
        print(f"\n⚠ VL was not more efficient at any tested size")
        print("  Consider: larger codebases, system prompt caching, or smaller primer")
    
    print("\nRecommendation:")
    if breakeven_actual:
        print(f"  Use VL for codebases with >{breakeven_actual['python_code_tokens']} tokens")
        print(f"  Use Python directly for smaller code snippets")
    else:
        print("  VL primer cost is too high for these test sizes")
        print("  Try system prompt caching to amortize primer cost")


if __name__ == "__main__":
    main()
