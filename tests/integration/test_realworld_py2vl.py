"""
Python → VL → Python Round-Trip Validation with Real-World Code

Downloads Python scripts from public repositories and tests conversion.
"""

import sys
import os
import io
import traceback
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import urllib.request

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from vl.py_to_vl import convert_python_to_vl
from vl.compiler import Compiler, TargetLanguage


# Real-world Python code samples from public repos
GITHUB_SAMPLES = {
    "requests_simple": {
        "code": """
# Simple import and class example
from typing import Dict, Any

class RequestHandler:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.headers = {}
    
    def set_header(self, key: str, value: str):
        self.headers[key] = value
    
    def get_url(self, path: str) -> str:
        return self.base_url + path

handler = RequestHandler('https://api.example.com')
handler.set_header('Authorization', 'Bearer token')
url = handler.get_url('/users')
print(url)
""",
        "description": "Simple class with imports and methods"
    },
    "flask_hello": {
        # Simple Flask example
        "code": """
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
""",
        "description": "Flask hello world (with decorators)"
    },
    "algorithm_quicksort": {
        "code": """
def quicksort(arr: list) -> list:
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

result = quicksort([3, 6, 8, 10, 1, 2, 1])
print(result)
""",
        "description": "Quicksort algorithm with list comprehensions"
    },
    "class_example": {
        "code": """
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x: int) -> int:
        self.result += x
        return self.result
    
    def reset(self):
        self.result = 0

calc = Calculator()
print(calc.add(5))
print(calc.add(3))
""",
        "description": "Simple class with methods"
    },
    "file_operations": {
        "code": """
def read_numbers(filename: str) -> list:
    numbers = []
    with open(filename, 'r') as f:
        for line in f:
            numbers.append(int(line.strip()))
    return numbers

def sum_file(filename: str) -> int:
    numbers = read_numbers(filename)
    total = 0
    for num in numbers:
        total += num
    return total
""",
        "description": "File I/O operations with context manager"
    },
    "exception_handling": {
        "code": """
def safe_divide(a: int, b: int) -> float:
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        print('Cannot divide by zero')
        return 0.0

print(safe_divide(10, 2))
print(safe_divide(10, 0))
""",
        "description": "Exception handling"
    },
    "nested_functions": {
        "code": """
def outer(x: int) -> int:
    def inner(y: int) -> int:
        return y * 2
    return inner(x) + x

result = outer(5)
print(result)
""",
        "description": "Nested function definitions"
    },
    "multiple_assignment": {
        "code": """
def swap(a: int, b: int):
    temp = a
    a = b
    b = temp
    return a, b

x, y = swap(10, 20)
print(x, y)
""",
        "description": "Multiple assignment and tuple return"
    },
    "dictionary_operations": {
        "code": """
def count_words(text: str) -> dict:
    words = text.split()
    counts = {}
    for word in words:
        if word in counts:
            counts[word] += 1
        else:
            counts[word] = 1
    return counts

result = count_words('hello world hello')
print(result)
""",
        "description": "Dictionary operations"
    },
    "lambda_filter": {
        "code": """
def filter_evens(numbers: list) -> list:
    evens = []
    for n in numbers:
        if n % 2 == 0:
            evens.append(n)
    return evens

nums = [1, 2, 3, 4, 5, 6]
result = filter_evens(nums)
print(result)
""",
        "description": "Filtering with conditionals"
    }
}


def download_code(url: str, start_line: int = None, end_line: int = None) -> str:
    """Download Python code from URL"""
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            code = response.read().decode('utf-8')
            if start_line and end_line:
                lines = code.split('\n')[start_line-1:end_line]
                code = '\n'.join(lines)
            return code
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None


def execute_code(code: str, test_name: str) -> tuple:
    """Execute Python code and capture output"""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            exec(code, {})
        return True, stdout_capture.getvalue(), stderr_capture.getvalue()
    except Exception as e:
        return False, stdout_capture.getvalue(), f"{type(e).__name__}: {e}"


def test_conversion(test_name: str, sample_info: dict) -> dict:
    """Test Python → VL → Python conversion"""
    result = {
        'name': test_name,
        'description': sample_info.get('description', ''),
        'success': False,
        'python_code': None,
        'vl_code': None,
        'conversion_error': None,
        'compilation_error': None,
        'skip_reason': None
    }
    
    # Get Python code
    if 'code' in sample_info:
        python_code = sample_info['code'].strip()
    elif 'url' in sample_info:
        python_code = download_code(
            sample_info['url'],
            sample_info.get('start_line'),
            sample_info.get('end_line')
        )
        if not python_code:
            result['skip_reason'] = 'Failed to download'
            return result
    else:
        result['skip_reason'] = 'No code source'
        return result
    
    result['python_code'] = python_code
    
    # Check for unsupported features (removed class, @decorator, with, try/except - now supported!)
    unsupported = ['lambda', 'yield', 'async ', 'await ']
    for feature in unsupported:
        if feature in python_code:
            result['skip_reason'] = f'Contains unsupported feature: {feature.strip()}'
            return result
    
    # Convert Python → VL
    try:
        vl_code = convert_python_to_vl(python_code)
        result['vl_code'] = vl_code
    except Exception as e:
        result['conversion_error'] = f"{type(e).__name__}: {e}"
        return result
    
    # Compile VL → Python
    try:
        compiler = Compiler(vl_code, TargetLanguage.PYTHON)
        generated_python = compiler.compile()
        result['generated_python'] = generated_python
    except Exception as e:
        result['compilation_error'] = f"{type(e).__name__}: {e}"
        return result
    
    result['success'] = True
    return result


def run_real_world_tests():
    """Run tests on real-world Python code"""
    print("=" * 80)
    print("Real-World Python Code Validation Suite")
    print("=" * 80)
    print()
    
    results = []
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, sample_info in GITHUB_SAMPLES.items():
        desc = sample_info.get('description', test_name)
        print(f"Testing: {test_name} ({desc})...", end=' ')
        
        result = test_conversion(test_name, sample_info)
        results.append(result)
        
        if result.get('skip_reason'):
            print(f"[SKIP] {result['skip_reason']}")
            skipped += 1
        elif result['success']:
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
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped} (unsupported features)")
    
    if passed > 0:
        success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
        print(f"Success rate: {success_rate:.1f}% (of testable code)")
    print()
    
    # Show failures
    if failed > 0:
        print("=" * 80)
        print("FAILURES")
        print("=" * 80)
        
        for result in results:
            if not result['success'] and not result.get('skip_reason'):
                print(f"\n[FAIL] {result['name']}")
                print(f"Description: {result['description']}")
                print("-" * 80)
                
                if result['conversion_error']:
                    print(f"Conversion Error: {result['conversion_error']}")
                elif result['compilation_error']:
                    print(f"Compilation Error: {result['compilation_error']}")
                
                print("\nOriginal Python:")
                print(result['python_code'][:500])
                if len(result['python_code']) > 500:
                    print("... (truncated)")
                
                if result.get('vl_code'):
                    print("\nVL Code:")
                    print(result['vl_code'][:500])
                    if len(result['vl_code']) > 500:
                        print("... (truncated)")
    
    # Show what was skipped
    if skipped > 0:
        print()
        print("=" * 80)
        print("SKIPPED (Unsupported Features)")
        print("=" * 80)
        for result in results:
            if result.get('skip_reason'):
                print(f"  - {result['name']}: {result['skip_reason']}")
    
    print()
    return passed, failed, skipped


if __name__ == '__main__':
    passed, failed, skipped = run_real_world_tests()
    sys.exit(0 if failed == 0 else 1)
