"""
Test that generated Python code actually executes correctly.
This validates we're 100% operational as a Python transpiler.
"""

import pytest

from vl.compiler import Compiler

CASES = [
    (
        "boolean_literals",
        "x=true|y=false",
        lambda g: g["x"] is True and g["y"] is False,
    ),
    (
        "type_annotations",
        "F:process|A,O|I|ret:5",
        lambda g: callable(g["process"]) and g["process"]([], {}) == 5,
    ),
    (
        "array_indexing",
        "F:first|A|I|ret:i0[0]",
        lambda g: g["first"]([10, 20, 30]) == 10,
    ),
    (
        "object_member_access",
        "F:getName|O|S|ret:i0['name']",
        lambda g: g["getName"]({"name": "Alice"}) == "Alice",
    ),
    (
        "loop_with_accumulator",
        "F:sum|A|I|total=0|for:i,i0|total+=i|ret:total",
        lambda g: g["sum"]([1, 2, 3, 4, 5]) == 15,
    ),
    (
        "conditionals_with_booleans",
        "F:test|I|B|ret:if:i0>10?true:false",
        lambda g: g["test"](15) is True and g["test"](5) is False,
    ),
    (
        "python_ffi",
        "x=py:len([1,2,3])|y=py:'hello'.upper()",
        lambda g: g["x"] == 3 and g["y"] == "HELLO",
    ),
    (
        "nested_indexing",
        "F:get|A|I|ret:i0[1][0]",
        lambda g: g["get"]([[1, 2], [3, 4], [5, 6]]) == 3,
    ),
    (
        "multiple_variables_mixed_types",
        "x=10|y=true|z='hello'|items=[1,2,3]",
        lambda g: g["x"] == 10
        and g["y"] is True
        and g["z"] == "hello"
        and g["items"] == [1, 2, 3],
    ),
    (
        "range_expression",
        "F:count|I|I|total=0|for:i,0..i0|total+=1|ret:total",
        lambda g: g["count"](5) == 5,
    ),
]


@pytest.mark.parametrize("name,vl_code,check", CASES, ids=[c[0] for c in CASES])
def test_execution(name, vl_code, check):
    compiler = Compiler(vl_code, type_check_enabled=False)
    python_code = compiler.compile()
    exec_globals = {}
    exec(python_code, exec_globals)
    assert check(exec_globals), f"{name}: generated Python misbehaved:\n{python_code}"
