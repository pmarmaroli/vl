"""Convert real-world Python patterns to VL, compile back, and execute both."""

import pytest

from vl.py_to_vl import convert_python_to_vl
from vl.compiler import Compiler, TargetLanguage

CASES = [
    ("simple_assignment", "x = 1\ny = 2\nz = x + y"),
    (
        "function_definition",
        """
def add(a, b):
    return a + b
result = add(5, 3)
""",
    ),
    (
        "dict_subscript_assignment",
        """
settings = {"downlink": {}}
settings["downlink"]["delay"] = 100
""",
    ),
    (
        "if_statement",
        """
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
""",
    ),
    (
        "for_loop",
        """
total = 0
for i in range(5):
    total += i
""",
    ),
    (
        "list_comprehension",
        """
numbers = [1, 2, 3, 4, 5]
squares = [x * x for x in numbers]
""",
    ),
    (
        "try_except",
        """
try:
    x = 1 / 1
    result = "ok"
except:
    result = "error"
""",
    ),
]


@pytest.mark.parametrize("name,python_code", CASES, ids=[c[0] for c in CASES])
def test_py2vl_execution(name, python_code):
    # The original sample must execute
    exec(python_code, {})

    vl_code = convert_python_to_vl(python_code)
    generated_python = Compiler(vl_code, TargetLanguage.PYTHON).compile()

    # The regenerated Python must also execute
    try:
        exec(generated_python, {})
    except Exception as e:
        pytest.fail(
            f"{name}: generated Python failed ({type(e).__name__}: {e})\n"
            f"VL:\n{vl_code}\n\nGenerated:\n{generated_python}"
        )
