"""
Python → VL → Python round-trip validation suite.

For each real Python sample: convert to VL, compile back to Python,
execute both versions, and require identical stdout.
"""

import io
from contextlib import redirect_stdout, redirect_stderr

import pytest

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


def _execute(code: str) -> str:
    """Execute Python code and return captured stdout (raises on failure)."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        exec(code, {})
    return stdout_capture.getvalue()


@pytest.mark.parametrize("name", PYTHON_SAMPLES, ids=list(PYTHON_SAMPLES))
def test_roundtrip(name):
    python_code = PYTHON_SAMPLES[name]

    vl_code = convert_python_to_vl(python_code)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()

    original_output = _execute(python_code)
    generated_output = _execute(generated_python)

    assert generated_output == original_output, (
        f"round-trip output mismatch for {name}:\n"
        f"  original:  {original_output!r}\n"
        f"  generated: {generated_output!r}\n"
        f"VL:\n{vl_code}\n\nGenerated Python:\n{generated_python}"
    )
