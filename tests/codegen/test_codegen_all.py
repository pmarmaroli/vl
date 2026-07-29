"""
Comprehensive code generation test suite.

Tests all 5 targets (Python, JavaScript, TypeScript, C, Rust) for basic
constructs, so regressions in any backend are caught early.
"""

import pytest

from vl.compiler import Compiler, TargetLanguage

CORE_CASES = [
    ("simple_function", "F:add|I,I|I|ret:i0+i1"),
    ("variable_assignment", "x=5\ny=10\nresult=x+y"),
    ("boolean_expression", "F:validate|I,I|B|ret:i0>0&&i1<100"),
    ("if_statement", "F:max|I,I|I|ret:if:i0>i1?i0:i1"),
    ("array_literal", "nums=[1,2,3,4,5]"),
    ("object_literal", "user={name:'Alice',age:30}"),
    ("string_template", "name='World'\nmsg='Hello ${name}!'"),
    ("comparison", "F:compare|I,I|B|ret:i0==i1"),
    ("arithmetic", "F:calc|I,I|I|ret:(i0+i1)*2"),
    ("return_constant", "F:get_five|I|I|ret:5"),
]

ALL_TARGETS = [
    TargetLanguage.PYTHON,
    TargetLanguage.JAVASCRIPT,
    TargetLanguage.TYPESCRIPT,
    TargetLanguage.C,
    TargetLanguage.RUST,
]


def _compile(vl_code: str, target: TargetLanguage) -> str:
    compiler = Compiler(vl_code, target, type_check_enabled=False)
    output = compiler.compile()
    assert output and len(output) > 10, "empty or too short output"
    return output


@pytest.mark.parametrize("target", ALL_TARGETS, ids=[t.value for t in ALL_TARGETS])
@pytest.mark.parametrize("name,vl_code", CORE_CASES, ids=[c[0] for c in CORE_CASES])
def test_core_construct(name, vl_code, target):
    _compile(vl_code, target)


TARGET_SPECIFIC_CASES = [
    ("python_type_annotations", "F:typed|I,S,B|N|ret:3.14", TargetLanguage.PYTHON),
    ("typescript_full_typing", "F:typed|I,S|S|ret:i1", TargetLanguage.TYPESCRIPT),
    ("javascript_no_types", "F:simple|I|I|ret:i0*2", TargetLanguage.JAVASCRIPT),
]


@pytest.mark.parametrize(
    "name,vl_code,target", TARGET_SPECIFIC_CASES, ids=[c[0] for c in TARGET_SPECIFIC_CASES]
)
def test_target_specific(name, vl_code, target):
    _compile(vl_code, target)


def test_python_all_optimization():
    """3+ conditions should compile to all([...]) in Python."""
    vl_code = "F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2"
    output = _compile(vl_code, TargetLanguage.PYTHON)
    assert "all([" in output


def test_javascript_native_and():
    """JavaScript should keep native && (no all() helper)."""
    vl_code = "F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2"
    output = _compile(vl_code, TargetLanguage.JAVASCRIPT)
    assert "&&" in output and "all(" not in output


EDGE_CASES = [
    ("single_parameter", "F:identity|I|I|ret:i0"),
    ("nested_operations", "F:nested|I|I|ret:((i0+1)*2)-3"),
    ("multiple_returns", "F:abs|I|I|ret:if:i0<0?-i0:i0"),
]


@pytest.mark.parametrize(
    "target",
    [TargetLanguage.PYTHON, TargetLanguage.JAVASCRIPT],
    ids=["python", "javascript"],
)
@pytest.mark.parametrize("name,vl_code", EDGE_CASES, ids=[c[0] for c in EDGE_CASES])
def test_edge_case(name, vl_code, target):
    _compile(vl_code, target)
