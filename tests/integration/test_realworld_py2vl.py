"""
Python → VL conversion on real-world code shapes (classes, decorators,
context managers, exception handling, nested functions...).

Each sample must convert to VL and compile back to Python without error.
Samples using features the converter does not support yet are skipped.
"""

import pytest

from vl.py_to_vl import convert_python_to_vl
from vl.compiler import Compiler, TargetLanguage

# Real-world Python code samples
SAMPLES = {
    "requests_simple": """
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
    "flask_hello": """
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run()
""",
    "algorithm_quicksort": """
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
    "class_example": """
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
    "file_operations": """
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
    "exception_handling": """
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
    "nested_functions": """
def outer(x: int) -> int:
    def inner(y: int) -> int:
        return y * 2
    return inner(x) + x

result = outer(5)
print(result)
""",
    "multiple_assignment": """
def swap(a: int, b: int):
    temp = a
    a = b
    b = temp
    return a, b

x, y = swap(10, 20)
print(x, y)
""",
    "dictionary_operations": """
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
    "lambda_filter": """
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
}

# Features the converter does not support yet
UNSUPPORTED = ["lambda", "yield", "async ", "await "]


@pytest.mark.parametrize("name", SAMPLES, ids=list(SAMPLES))
def test_realworld_conversion(name):
    python_code = SAMPLES[name].strip()

    for feature in UNSUPPORTED:
        if feature in python_code:
            pytest.skip(f"contains unsupported feature: {feature.strip()}")

    vl_code = convert_python_to_vl(python_code)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()
    assert generated_python.strip(), f"{name}: compiled to empty output"
