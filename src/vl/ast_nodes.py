"""
VL Abstract Syntax Tree (AST) Node Definitions

This module defines all AST node types that represent VL program structure.
Each node type corresponds to a language construct (function, variable, operation, etc.)
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Union
from enum import Enum


# Base AST Node
@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int
    column: int


# Program Structure
@dataclass
class Program(ASTNode):
    """Root node representing entire VL program"""
    metadata: Optional['Metadata']
    dependencies: Optional['Dependencies']
    module_docstring: Optional[str]
    statements: List['Statement']
    export: Optional['Export']


@dataclass
class Metadata(ASTNode):
    """meta:name,type,target"""
    name: str
    program_type: str  # function, api_function, ui_component, etc.
    target_language: str  # python, javascript, react, etc.


@dataclass
class Dependencies(ASTNode):
    """deps:[dep1,dep2] or deps:single_dep"""
    dependencies: List[str]


@dataclass
class Export(ASTNode):
    """export:name"""
    name: str


# Types
@dataclass
class Type(ASTNode):
    """Represents a type annotation"""
    name: str  # int, float, str, arr, obj, etc.


# Statements
@dataclass
class Statement(ASTNode):
    """Base class for all statements"""
    pass


@dataclass
class FunctionDef(Statement):
    """F:name|name:type,name:type|type|body"""
    name: str
    input_types: List[Type]
    output_type: Type
    body: List[Statement]
    decorators: List['Decorator'] = None  # Optional decorators
    param_names: List[str] = None  # Original parameter names (if preserved)
    docstring: str = None  # Docstring (if preserved)


@dataclass
class ClassDef(Statement):
    """class:name|methods"""
    name: str
    base_classes: List[str] = None
    methods: List[FunctionDef] = None
    attributes: List['VariableDef'] = None  # Forward reference
    decorators: List['Decorator'] = None
    docstring: str = None


@dataclass
class Decorator(ASTNode):
    """@decorator_name or @decorator_name(args)"""
    name: str
    args: List['Expression'] = None


@dataclass
class VariableDef(Statement):
    """v:name=value or v:name:type=value or name=value (implicit) or arr[idx]=value or obj.prop=value"""
    name: Union[str, 'Expression']  # Can be simple name or IndexAccess/MemberAccess expression
    type_annotation: Optional[Type]
    value: 'Expression'


@dataclass
class CompoundAssignment(Statement):
    """name+=value, name-=value, name*=value, name/=value"""
    name: str
    operator: str  # '+', '-', '*', '/'
    value: 'Expression'


@dataclass
class ReturnStmt(Statement):
    """ret:value"""
    value: 'Expression'


@dataclass
class DirectCall(Statement):
    """@function(args) - Direct function call without assignment"""
    function: 'Expression'


@dataclass
class IfStmt(Statement):
    """if:condition?true_expr:false_expr (ternary expression)"""
    condition: 'Expression'
    true_expr: 'Expression'
    false_expr: 'Expression'


@dataclass
class IfElseBlock(Statement):
    """
    Imperative if/else block:
    if:condition
      body_statements
    else:
      else_statements
    """
    condition: 'Expression'
    if_body: List[Statement]
    else_body: List[Statement] = None


@dataclass
class ForLoop(Statement):
    """for:var,iterable|body"""
    variable: str
    iterable: 'Expression'
    body: List[Statement]


@dataclass
class WhileLoop(Statement):
    """while:condition|body"""
    condition: 'Expression'
    body: List[Statement]


# Expressions
@dataclass
class Expression(ASTNode):
    """Base class for all expressions"""
    pass


@dataclass
class FunctionExpr(Expression):
    """F:name|types|type|body - Function as expression (for object properties)"""
    name: str
    input_types: List['Type']
    output_type: 'Type'
    body: List['Statement']


@dataclass
class PythonExpr(Expression):
    """py:code - Direct Python code passthrough"""
    code: str


@dataclass
class PythonStmt(Statement):
    """Python statement passthrough - for with, try/except, etc."""
    code: str


@dataclass
class IndexAccess(Expression):
    """Array/object indexing: arr[index] or obj['key']"""
    object: Expression
    index: Expression


@dataclass
class NumberLiteral(Expression):
    """Numeric literal: 42, 3.14, 1.5e10"""
    value: Union[int, float]


@dataclass
class StringLiteral(Expression):
    """String literal: 'hello', "world", 'hello ${name}'"""
    value: str
    is_template: bool = False  # True if contains ${...}


@dataclass
class BooleanLiteral(Expression):
    """Boolean literal: true, false"""
    value: bool


@dataclass
class ArrayLiteral(Expression):
    """Array literal: [1,2,3]"""
    elements: List[Expression]


@dataclass
class ObjectLiteral(Expression):
    """Object literal: {key:'value',num:42}"""
    pairs: List[tuple[str, Expression]]  # [(key, value), ...]


@dataclass
class Identifier(Expression):
    """Variable reference or identifier"""
    name: str


@dataclass
class VariableRef(Expression):
    """Variable reference with $ prefix: $varname"""
    name: str


@dataclass
class MemberAccess(Expression):
    """obj.property"""
    object: Expression
    property: str


@dataclass
class Operation(Expression):
    """op:operator(arg1,arg2,...)"""
    operator: str  # +, -, *, /, ==, !=, etc.
    operands: List[Expression]


@dataclass
class InOp(Expression):
    """Membership test: element in container"""
    element: Expression
    container: Expression


@dataclass
class FunctionCall(Expression):
    """Function call: funcName(arg1,arg2)"""
    callee: Expression
    arguments: List[Expression]


@dataclass
class RangeExpr(Expression):
    """Range expression: start..end (e.g., 0..10)"""
    start: Expression
    end: Expression


# Domain-Specific Constructs

# API Domain
@dataclass
class APICall(Statement):
    """api:METHOD,endpoint[,options]"""
    method: str  # GET, POST, PUT, DELETE, PATCH
    endpoint: Expression
    options: Optional[ObjectLiteral]
    is_async: bool = False
    operations: List['DataOperation'] = None  # Chained operations (filter, map)


@dataclass
class FilterOp(Statement):
    """filter:condition"""
    condition: Expression


@dataclass
class MapOp(Statement):
    """map:field1,field2 or map:expr"""
    fields: Optional[List[str]]  # For field extraction
    expression: Optional[Expression]  # For transformation


@dataclass
class ParseOp(Statement):
    """parse:format"""
    format: str  # json, xml, csv, yaml, etc.


# UI Domain
@dataclass
class UIComponent(Statement):
    """ui:name|props:...|state:...|body"""
    name: str
    props: List['PropDef']
    state_vars: List['StateDef']
    body: List[Statement]


@dataclass
class PropDef(ASTNode):
    """props:name:type,name:type"""
    name: str
    type_annotation: Type


@dataclass
class StateDef(ASTNode):
    """state:name:type=value"""
    name: str
    type_annotation: Type
    initial_value: Expression


@dataclass
class SetState(Statement):
    """setState:varName,newValue"""
    variable: str
    value: Expression


@dataclass
class EventHandler(Statement):
    """on:eventName|handler_body"""
    event_name: str  # onClick, onChange, etc.
    body: List[Statement]


@dataclass
class RenderStmt(Statement):
    """render:element[,{attrs}]|children"""
    element: str
    attributes: Optional[ObjectLiteral]
    children: List[Union[Statement, Expression]]


@dataclass
class HookCall(Statement):
    """hook:hookName(args)"""
    hook_name: str  # useEffect, useCallback, useMemo, useRef
    arguments: List[Expression]


# Data Domain
@dataclass
class DataPipeline(Statement):
    """data:source|operation|operation|..."""
    source: Expression
    operations: List['DataOperation']


@dataclass
class DataOperation(ASTNode):
    """Base for data operations"""
    pass


@dataclass
class GroupByOp(DataOperation):
    """groupBy:field"""
    field: str


@dataclass
class AggregateOp(DataOperation):
    """agg:function[,field]"""
    function: str  # sum, avg, count, min, max
    field: Optional[str]


@dataclass
class SortOp(DataOperation):
    """sort:field[,order]"""
    field: str
    order: str = 'asc'  # asc or desc


@dataclass
class LimitOp(DataOperation):
    """limit:n"""
    limit: int


@dataclass
class SkipOp(DataOperation):
    """skip:n"""
    skip: int


@dataclass
class JoinOp(DataOperation):
    """join:other,on:key or join:other,left:key1,right:key2"""
    other: Expression
    left_key: str
    right_key: Optional[str]
    join_type: str = 'inner'  # inner, left, right, outer


# File Domain
@dataclass
class FileOperation(Statement):
    """file:operation,path[,args]"""
    operation: str  # read, write, append, delete, copy, move, etc.
    path: Expression
    arguments: List[Expression]


@dataclass
class DirOperation(Statement):
    """dir:operation,path[,args]"""
    operation: str  # list, create, delete, etc.
    path: Expression
    arguments: List[Expression]


@dataclass
class PathOperation(Expression):
    """path:operation,args..."""
    operation: str  # join, dirname, basename, extname, etc.
    arguments: List[Expression]


# FFI
@dataclass
class FFICall(Expression):
    """ffi:language,function_path,args..."""
    language: str  # python, node, rust, c
    function_path: str  # numpy.array, express.Router, etc.
    arguments: List[Expression]


# Helper functions for AST visualization
def ast_to_string(node: ASTNode, indent: int = 0) -> str:
    """Convert AST to readable string representation"""
    spaces = "  " * indent
    
    if isinstance(node, Program):
        result = f"{spaces}Program:\n"
        if node.metadata:
            result += ast_to_string(node.metadata, indent + 1)
        if node.dependencies:
            result += ast_to_string(node.dependencies, indent + 1)
        if node.module_docstring:
            result += f"{spaces}  ModuleDocstring: {repr(node.module_docstring)}\n"
        for stmt in node.statements:
            result += ast_to_string(stmt, indent + 1)
        if node.export:
            result += ast_to_string(node.export, indent + 1)
        return result
    
    elif isinstance(node, Metadata):
        return f"{spaces}Metadata(name={node.name}, type={node.program_type}, target={node.target_language})\n"
    
    elif isinstance(node, FunctionDef):
        result = f"{spaces}FunctionDef(name={node.name}, inputs={[t.name for t in node.input_types]}, output={node.output_type.name}):\n"
        for stmt in node.body:
            result += ast_to_string(stmt, indent + 1)
        return result
    
    elif isinstance(node, Operation):
        result = f"{spaces}Operation({node.operator}):\n"
        for operand in node.operands:
            result += ast_to_string(operand, indent + 1)
        return result
    
    elif isinstance(node, NumberLiteral):
        return f"{spaces}Number({node.value})\n"
    
    elif isinstance(node, StringLiteral):
        return f"{spaces}String('{node.value}')\n"
    
    elif isinstance(node, Identifier):
        return f"{spaces}Identifier({node.name})\n"
    
    elif isinstance(node, VariableRef):
        return f"{spaces}VarRef(${node.name})\n"
    
    elif isinstance(node, ReturnStmt):
        result = f"{spaces}Return:\n"
        result += ast_to_string(node.value, indent + 1)
        return result
    
    else:
        return f"{spaces}{node.__class__.__name__}\n"


if __name__ == "__main__":
    # Example: Create a simple AST
    program = Program(
        line=1, column=1,
        metadata=Metadata(
            line=1, column=1,
            name="test",
            program_type="function",
            target_language="python"
        ),
        dependencies=None,
        module_docstring=None,
        statements=[
            FunctionDef(
                line=2, column=1,
                name="add",
                input_types=[Type(2, 1, "int"), Type(2, 1, "int")],
                output_type=Type(2, 1, "int"),
                body=[
                    ReturnStmt(
                        line=2, column=20,
                        value=Operation(
                            line=2, column=25,
                            operator="+",
                            operands=[
                                Identifier(2, 30, "i0"),
                                Identifier(2, 33, "i1")
                            ]
                        )
                    )
                ]
            )
        ],
        export=Export(line=3, column=1, name="add")
    )
    
    print(ast_to_string(program))
