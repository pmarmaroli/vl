"""
Final validation: compile VL snippets covering all fixed issues and edge
cases, execute the generated Python, and verify its behavior.
"""

import pytest

from vl.compiler import Compiler

CASES = [
    # Group 1: core Python features
    (
        "boolean_literals",
        "x=true|y=false",
        lambda g: g["x"] is True and g["y"] is False,
    ),
    (
        "type_annotations",
        "F:test|A,O|I|ret:5",
        lambda g: g["test"]([], {}) == 5,
    ),
    (
        "array_indexing",
        "F:first|A|I|ret:i0[0]",
        lambda g: g["first"]([10, 20, 30]) == 10,
    ),
    (
        "nested_indexing",
        "F:get|A|I|ret:i0[1][0]",
        lambda g: g["get"]([[1, 2], [3, 4]]) == 3,
    ),
    (
        "object_indexing",
        "F:getName|O|S|ret:i0['name']",
        lambda g: g["getName"]({"name": "Alice"}) == "Alice",
    ),
    (
        "member_access_chains",
        "F:getName|O|S|ret:i0.user.name",
        lambda g: g["getName"](
            type("", (), {"user": type("", (), {"name": "Bob"})()})()
        )
        == "Bob",
    ),
    # Group 2: data pipelines
    (
        "map_with_item_keyword",
        "F:double|A|A|ret:data:i0|map:item*2",
        lambda g: g["double"]([1, 2, 3]) == [2, 4, 6],
    ),
    (
        "filter_with_item_keyword",
        "F:evens|A|A|ret:data:i0|filter:item%2==0",
        lambda g: g["evens"]([1, 2, 3, 4, 5, 6]) == [2, 4, 6],
    ),
    (
        "chained_pipeline",
        "F:process|A|A|ret:data:i0|filter:item>2|map:item*10",
        lambda g: g["process"]([1, 2, 3, 4, 5]) == [30, 40, 50],
    ),
    # Group 3: complex scenarios
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
        "string_interpolation",
        "F:greet|S|S|ret:'Hello, ${i0}!'",
        lambda g: "Hello" in g["greet"]("World"),
    ),
    (
        "nested_data_structures",
        "x={name:'Alice',age:30,items:[1,2,3]}",
        lambda g: g["x"]["name"] == "Alice" and g["x"]["items"] == [1, 2, 3],
    ),
    (
        "range_expressions",
        "F:count|I|I|total=0|for:i,0..i0|total+=1|ret:total",
        lambda g: g["count"](5) == 5,
    ),
    # Group 4: Python FFI (py: prefix)
    (
        "direct_python_calls",
        "x=py:len([1,2,3])|y=py:'hello'.upper()",
        lambda g: g["x"] == 3 and g["y"] == "HELLO",
    ),
    (
        "ffi_in_function_returns",
        "F:parseJSON|S|O|ret:py:json.loads(i0)",
        lambda g: callable(g["parseJSON"]),
    ),
    (
        "method_chaining_via_ffi",
        "x=py:'   hello   '.strip().upper()",
        lambda g: g["x"] == "HELLO",
    ),
]


@pytest.mark.parametrize("name,vl_code,check", CASES, ids=[c[0] for c in CASES])
def test_final_validation(name, vl_code, check):
    compiler = Compiler(vl_code, type_check_enabled=False)
    python_code = compiler.compile()
    exec_globals = {}
    exec(python_code, exec_globals)
    assert check(exec_globals), f"{name}: generated Python misbehaved:\n{python_code}"
