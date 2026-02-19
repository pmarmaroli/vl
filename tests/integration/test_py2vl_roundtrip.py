"""
Python → VL → Python Round-Trip Validation Suite

Tests the converter on real Python code samples by:
1. Converting Python to VL
2. Compiling VL back to Python
3. Executing both versions and comparing results
4. Reporting success rate and issues
"""

import sys
import os
import io
import traceback
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from vl.py_to_vl import convert_python_to_vl
from vl.compiler import Compiler, TargetLanguage


# Test dataset: real Python code samples
PYTHON_SAMPLES = {
    "simple_math": """
def add(x: int, y: int) -> int:
    return x + y

def subtract(x: int, y: int) -> int:
    return x - y

result1 = add(10, 5)
result2 = subtract(10, 5)
print(result1, result2)
""",

    "conditionals": """
def max_value(a: int, b: int) -> int:
    if a > b:
        return a
    else:
        return b

def classify(n: int) -> str:
    if n > 0:
        return 'positive'
    else:
        return 'negative'

print(max_value(10, 5))
print(classify(-3))
""",

    "loops": """
def sum_range(n: int) -> int:
    total = 0
    i = 0
    while i < n:
        total += i
        i += 1
    return total

result = sum_range(10)
print(result)
""",

    "lists": """
def double_all(numbers: list) -> list:
    result = []
    for num in numbers:
        result.append(num * 2)
    return result

nums = [1, 2, 3, 4, 5]
doubled = double_all(nums)
print(doubled)
""",

    "nested_calls": """
def square(x: int) -> int:
    return x * x

def sum_of_squares(a: int, b: int) -> int:
    return square(a) + square(b)

result = sum_of_squares(3, 4)
print(result)
""",

    "multiple_returns": """
def abs_value(x: int) -> int:
    if x < 0:
        return -x
    else:
        return x

print(abs_value(-5))
print(abs_value(5))
""",

    "boolean_logic": """
def validate(x: int, y: int) -> bool:
    return x > 0 and y < 100

print(validate(5, 50))
print(validate(-5, 50))
""",

    "string_ops": """
def greet(name: str) -> str:
    return 'Hello, ' + name

message = greet('World')
print(message)
""",

    "arithmetic": """
def calculate(a: int, b: int) -> int:
    sum_val = a + b
    diff = a - b
    prod = sum_val * diff
    return prod

result = calculate(10, 5)
print(result)
""",

    "chained_comparison": """
def in_range(x: int) -> bool:
    return x >= 0 and x <= 100

print(in_range(50))
print(in_range(150))
""",
}


def execute_code(code: str, test_name: str) -> tuple[bool, str, str]:
    """
    Execute Python code and capture output
    
    Returns:
        (success, stdout, stderr)
    """
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, {})
        return True, stdout_capture.getvalue(), stderr_capture.getvalue()
    except Exception as e:
        return False, stdout_capture.getvalue(), f"{type(e).__name__}: {e}\n{traceback.format_exc()}"


def test_roundtrip(test_name: str, python_code: str) -> dict:
    """
    Test Python → VL → Python round-trip
    
    Returns dict with test results
    """
    result = {
        'name': test_name,
        'success': False,
        'python_code': python_code,
        'vl_code': None,
        'generated_python': None,
        'original_output': None,
        'generated_output': None,
        'conversion_error': None,
        'compilation_error': None,
        'execution_error': None,
        'output_match': False
    }
    
    # Step 1: Convert Python → VL
    try:
        vl_code = convert_python_to_vl(python_code)
        result['vl_code'] = vl_code
    except Exception as e:
        result['conversion_error'] = f"{type(e).__name__}: {e}"
        return result
    
    # Step 2: Compile VL → Python
    try:
        compiler = Compiler(vl_code, TargetLanguage.PYTHON)
        generated_python = compiler.compile()
        result['generated_python'] = generated_python
    except Exception as e:
        result['compilation_error'] = f"{type(e).__name__}: {e}"
        return result
    
    # Step 3: Execute original Python
    orig_success, orig_stdout, orig_stderr = execute_code(python_code, test_name)
    result['original_output'] = orig_stdout if orig_success else orig_stderr
    
    if not orig_success:
        result['execution_error'] = f"Original Python failed: {orig_stderr}"
        return result
    
    # Step 4: Execute generated Python
    gen_success, gen_stdout, gen_stderr = execute_code(generated_python, test_name)
    result['generated_output'] = gen_stdout if gen_success else gen_stderr
    
    if not gen_success:
        result['execution_error'] = f"Generated Python failed: {gen_stderr}"
        return result
    
    # Step 5: Compare outputs
    result['output_match'] = orig_stdout == gen_stdout
    result['success'] = result['output_match']
    
    return result


def run_validation_suite():
    """Run all validation tests and report results"""
    print("=" * 80)
    print("Python -> VL -> Python Round-Trip Validation Suite")
    print("=" * 80)
    print()
    
    results = []
    passed = 0
    failed = 0
    
    for test_name, python_code in PYTHON_SAMPLES.items():
        print(f"Testing: {test_name}...", end=' ')
        result = test_roundtrip(test_name, python_code)
        results.append(result)
        
        if result['success']:
            print("[PASS]")
            passed += 1
        else:
            print("[FAIL]")
            failed += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"Failed: {failed} ({failed/len(results)*100:.1f}%)")
    print()
    
    # Show failures
    if failed > 0:
        print("=" * 80)
        print("FAILURES")
        print("=" * 80)
        
        for result in results:
            if not result['success']:
                print(f"\n[FAIL] {result['name']}")
                print("-" * 80)
                
                if result['conversion_error']:
                    print(f"Conversion Error: {result['conversion_error']}")
                elif result['compilation_error']:
                    print(f"Compilation Error: {result['compilation_error']}")
                elif result['execution_error']:
                    print(f"Execution Error: {result['execution_error']}")
                elif not result['output_match']:
                    print(f"Output Mismatch:")
                    print(f"  Original:  {repr(result['original_output'])}")
                    print(f"  Generated: {repr(result['generated_output'])}")
                
                print("\nOriginal Python:")
                print(result['python_code'])
                
                if result['vl_code']:
                    print("\nVL Code:")
                    print(result['vl_code'])
                
                if result['generated_python']:
                    print("\nGenerated Python:")
                    print(result['generated_python'])
    
    print()
    return passed, failed


if __name__ == '__main__':
    passed, failed = run_validation_suite()
    sys.exit(0 if failed == 0 else 1)
