"""
Test VL standard syntax (v0.1.2): the token-efficient syntax
(F:, I/S/N/B/A/O types, M:/E:, pipelines, loops...).
"""

import pytest

from vl.compiler import Compiler, TargetLanguage

SYNTAX_CASES = [
    # Basic functions with different types
    ("int_types", "F:add|I,I|I|ret:i0+i1"),
    ("string_types", "F:concat|S,S|S|ret:i0+i1"),
    ("float_types", "F:scale|N,N|N|ret:i0*i1"),
    ("bool_types", "F:check|B|B|ret:!i0"),
    ("array_types", "F:process|A|A|ret:i0"),
    ("object_types", "F:transform|O|O|ret:i0"),
    # Conditional
    ("conditional_function", "F:max|I,I|I|ret:if:i0>i1?i0:i1"),
    # Data pipeline
    ("data_pipeline_map", "F:double_all|A|A|ret:data:i0|map:item*2"),
    # Loop with accumulator
    (
        "loop_with_accumulator",
        "F:sum_range|I|I|v:total=0|for:idx,range(0,i0)|total+=idx|ret:total",
    ),
    # Multiple parameters
    ("mixed_type_parameters", "F:calc|I,I,N|N|ret:(i0+i1)*i2"),
    # Variables
    ("implicit_variable", "x=5"),
    ("string_variable", "name='Alice'"),
    ("array_variable", "items=[1,2,3]"),
    # Meta and Export
    (
        "full_program_structure",
        "M:test,function,python\nF:add|I,I|I|ret:i0+i1\nE:add",
    ),
]


@pytest.mark.parametrize("name,vl_code", SYNTAX_CASES, ids=[c[0] for c in SYNTAX_CASES])
def test_standard_syntax(name, vl_code):
    result = Compiler(vl_code, TargetLanguage.PYTHON).compile()
    assert result.strip(), f"{name}: compiled to empty output"


ALL_TARGETS = [
    TargetLanguage.PYTHON,
    TargetLanguage.JAVASCRIPT,
    TargetLanguage.TYPESCRIPT,
    TargetLanguage.C,
    TargetLanguage.RUST,
]


@pytest.mark.parametrize("target", ALL_TARGETS, ids=[t.name.lower() for t in ALL_TARGETS])
def test_all_targets(target):
    result = Compiler("F:add|I,I|I|ret:i0+i1", target).compile()
    assert result.strip(), f"{target.name}: compiled to empty output"
