"""
VL Type Checker
Basic type validation for VL programs

Validates type annotations and reports mismatches.
"""

from typing import Dict, Optional, Set, List, Tuple
from dataclasses import dataclass

# Support both package and standalone usage
try:
    from .ast_nodes import (
        ASTNode, Program, FunctionDef, VariableDef, ReturnStmt,
        Type, Expression, NumberLiteral, StringLiteral, BooleanLiteral,
        Identifier, Operation, FunctionCall,
        ArrayLiteral, ObjectLiteral, MemberAccess, DataPipeline,
        UIComponent, FunctionExpr, CompoundAssignment, RangeExpr, IfStmt
    )
    from .errors import TypeError, SourceLocation
except ImportError:
    from ast_nodes import (
        ASTNode, Program, FunctionDef, VariableDef, ReturnStmt,
        Type, Expression, NumberLiteral, StringLiteral, BooleanLiteral,
        Identifier, Operation, FunctionCall,
        ArrayLiteral, ObjectLiteral, MemberAccess, DataPipeline,
        UIComponent, FunctionExpr, CompoundAssignment, RangeExpr, IfStmt
    )
    from errors import TypeError, SourceLocation


@dataclass
class TypeInfo:
    """Information about a type"""
    name: str
    is_numeric: bool = False
    is_collection: bool = False
    element_type: Optional['TypeInfo'] = None


# Built-in type definitions
BUILTIN_TYPES = {
    # Standard type names
    'int': TypeInfo('int', is_numeric=True),
    'float': TypeInfo('float', is_numeric=True),
    'str': TypeInfo('str'),
    'bool': TypeInfo('bool'),
    'arr': TypeInfo('arr', is_collection=True),
    'obj': TypeInfo('obj'),
    'any': TypeInfo('any'),
    'void': TypeInfo('void'),
    'promise': TypeInfo('promise'),
    'func': TypeInfo('func'),
    'map': TypeInfo('map', is_collection=True),
    'set': TypeInfo('set', is_collection=True),
    # Optimized single-char type aliases (map to same TypeInfo)
    'I': TypeInfo('int', is_numeric=True),      # I = int
    'N': TypeInfo('float', is_numeric=True),    # N = number (float)
    'S': TypeInfo('str'),                        # S = str
    'B': TypeInfo('bool'),                       # B = bool
    'A': TypeInfo('arr', is_collection=True),   # A = arr (array)
    'O': TypeInfo('obj'),                        # O = obj (object)
    'V': TypeInfo('void'),                       # V = void
    'P': TypeInfo('promise'),                    # P = promise
    'L': TypeInfo('func'),                       # L = lambda/func
}

# Type compatibility rules: target -> allowed_sources
# Include both standard and short aliases
TYPE_COMPATIBILITY = {
    'any': {'int', 'float', 'str', 'bool', 'arr', 'obj', 'any', 'void', 'promise', 'func', 'map', 'set',
            'I', 'N', 'S', 'B', 'A', 'O', 'V', 'P', 'L'},
    'float': {'int', 'float', 'I', 'N'},  # int can be assigned to float
    'int': {'int', 'I'},
    'str': {'str', 'S'},
    'bool': {'bool', 'B'},
    'arr': {'arr', 'A'},
    'obj': {'obj', 'O'},
    'void': {'void', 'V'},
    'promise': {'promise', 'P'},
    'func': {'func', 'L'},
    'map': {'map'},
    'set': {'set'},
    # Short aliases also as targets
    'I': {'int', 'I'},
    'N': {'int', 'float', 'I', 'N'},
    'S': {'str', 'S'},
    'B': {'bool', 'B'},
    'A': {'arr', 'A'},
    'O': {'obj', 'O'},
    'V': {'void', 'V'},
    'P': {'promise', 'P'},
    'L': {'func', 'L'},
}


class TypeChecker:
    """
    Type checker for VL programs.
    
    Performs basic type validation:
    - Validates variable type annotations match assigned values
    - Checks function return types
    - Tracks variable types in scope
    - Reports type mismatches with helpful messages
    """
    
    def __init__(self, source: str = ""):
        self.source = source
        self.errors: List[TypeError] = []
        self.warnings: List[str] = []
        # Symbol table: variable name -> type info
        self.symbols: Dict[str, TypeInfo] = {}
        # Function signatures: function name -> (input_types, output_type)
        self.functions: Dict[str, Tuple[List[TypeInfo], TypeInfo]] = {}
        # Current function context (for return type checking)
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[TypeInfo] = None
    
    def check(self, program: Program) -> List[TypeError]:
        """
        Type check a program.
        Returns list of type errors found.
        """
        self.errors = []
        self.symbols = {}
        self.functions = {}
        
        # First pass: collect function signatures
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                self._register_function(stmt)
        
        # Second pass: check all statements
        for stmt in program.statements:
            self._check_statement(stmt)
        
        return self.errors
    
    def _register_function(self, func: FunctionDef):
        """Register a function's type signature"""
        input_types = [self._resolve_type(t) for t in func.input_types]
        output_type = self._resolve_type(func.output_type)
        self.functions[func.name] = (input_types, output_type)
    
    def _resolve_type(self, type_node: Type) -> TypeInfo:
        """Convert a Type AST node to TypeInfo"""
        type_name = type_node.name
        
        # Check for exact match first (handles single-char aliases A, I, S, etc.)
        if type_name in BUILTIN_TYPES:
            return BUILTIN_TYPES[type_name]
        
        # Try lowercase for standard type names (int, str, etc.)
        type_name_lower = type_name.lower()
        if type_name_lower in BUILTIN_TYPES:
            return BUILTIN_TYPES[type_name_lower]
        
        # Unknown type - treat as any
        return TypeInfo(type_name)
    
    def _check_statement(self, stmt: ASTNode):
        """Type check a statement"""
        if isinstance(stmt, FunctionDef):
            self._check_function(stmt)
        elif isinstance(stmt, VariableDef):
            self._check_variable_def(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._check_return(stmt)
        elif isinstance(stmt, CompoundAssignment):
            self._check_compound_assignment(stmt)
        # Other statements don't need type checking for now
    
    def _check_function(self, func: FunctionDef):
        """Type check a function definition"""
        # Save current scope
        old_symbols = self.symbols.copy()
        old_function = self.current_function
        old_return_type = self.current_return_type
        
        # Set function context
        self.current_function = func.name
        self.current_return_type = self._resolve_type(func.output_type)
        
        # Add parameters to scope
        for idx, input_type in enumerate(func.input_types):
            param_name = f"i{idx}"
            self.symbols[param_name] = self._resolve_type(input_type)
        
        # Check function body
        for stmt in func.body:
            self._check_statement(stmt)
        
        # Restore scope
        self.symbols = old_symbols
        self.current_function = old_function
        self.current_return_type = old_return_type
    
    def _check_variable_def(self, var: VariableDef):
        """Type check a variable definition"""
        # Infer value type
        value_type = self._infer_type(var.value)
        
        if var.type_annotation:
            # Declared type
            declared_type = self._resolve_type(var.type_annotation)
            
            # Check compatibility
            if not self._types_compatible(declared_type, value_type):
                self._add_error(
                    f"Type mismatch: variable '{var.name}' declared as '{declared_type.name}' "
                    f"but assigned value of type '{value_type.name}'",
                    var.line, var.column,
                    hints=[
                        f"Change the type annotation to '{value_type.name}'",
                        f"Or convert the value to type '{declared_type.name}'"
                    ]
                )
            
            # Store declared type (only for simple variable names)
            if isinstance(var.name, str):
                self.symbols[var.name] = declared_type
        else:
            # No type annotation - use inferred type (only for simple variable names)
            if isinstance(var.name, str):
                self.symbols[var.name] = value_type
    
    def _check_return(self, ret: ReturnStmt):
        """Type check a return statement"""
        if self.current_return_type is None:
            return  # Not in a function
        
        value_type = self._infer_type(ret.value)
        
        if not self._types_compatible(self.current_return_type, value_type):
            self._add_error(
                f"Return type mismatch: function '{self.current_function}' should return "
                f"'{self.current_return_type.name}' but returning '{value_type.name}'",
                ret.line, ret.column,
                hints=[
                    f"Change the function's return type to '{value_type.name}'",
                    f"Or convert the return value to '{self.current_return_type.name}'"
                ]
            )
    
    def _check_compound_assignment(self, stmt: CompoundAssignment):
        """Type check compound assignment (+=, -=, etc.)"""
        if stmt.name in self.symbols:
            var_type = self.symbols[stmt.name]
            value_type = self._infer_type(stmt.value)
            
            # Numeric operators require numeric types
            if stmt.operator in ['+', '-', '*', '/']:
                if not var_type.is_numeric:
                    # String concatenation is allowed for +=
                    if not (stmt.operator == '+' and var_type.name == 'str'):
                        self._add_error(
                            f"Cannot use '{stmt.operator}=' operator on non-numeric type '{var_type.name}'",
                            stmt.line, stmt.column,
                            hints=[f"Variable '{stmt.name}' must be int or float for arithmetic operations"]
                        )
    
    def _infer_type(self, expr: Expression) -> TypeInfo:
        """Infer the type of an expression"""
        if isinstance(expr, NumberLiteral):
            return self._infer_number_type(expr)
        elif isinstance(expr, StringLiteral):
            return BUILTIN_TYPES['str']
        elif isinstance(expr, BooleanLiteral):
            return BUILTIN_TYPES['bool']
        elif isinstance(expr, Identifier):
            return self._infer_identifier_type(expr)
        elif isinstance(expr, Operation):
            return self._infer_operation_type(expr)
        elif isinstance(expr, FunctionCall):
            return self._infer_call_type(expr)
        elif isinstance(expr, ArrayLiteral):
            return BUILTIN_TYPES['arr']
        elif isinstance(expr, ObjectLiteral):
            return BUILTIN_TYPES['obj']
        elif isinstance(expr, MemberAccess):
            return BUILTIN_TYPES['any']  # Can't know member types statically
        elif isinstance(expr, DataPipeline):
            return BUILTIN_TYPES['arr']  # Data pipelines return arrays
        elif isinstance(expr, RangeExpr):
            return BUILTIN_TYPES['arr']  # Ranges are arrays
        elif isinstance(expr, IfStmt):
            # If statements - infer from branches (simplified - just use 'any')
            return BUILTIN_TYPES['any']
        elif isinstance(expr, FunctionExpr):
            return BUILTIN_TYPES['func']
        else:
            return BUILTIN_TYPES['any']
    
    def _infer_number_type(self, num: NumberLiteral) -> TypeInfo:
        """Infer type of a number literal"""
        value = num.value
        if isinstance(value, float) and not value.is_integer():
            return BUILTIN_TYPES['float']
        return BUILTIN_TYPES['int']
    
    def _infer_identifier_type(self, ident: Identifier) -> TypeInfo:
        """Infer type of an identifier"""
        if ident.name in self.symbols:
            return self.symbols[ident.name]
        return BUILTIN_TYPES['any']  # Unknown variable
    
    def _infer_operation_type(self, op: Operation) -> TypeInfo:
        """Infer type of an operation"""
        if len(op.operands) == 0:
            return BUILTIN_TYPES['any']
        
        left_type = self._infer_type(op.operands[0])
        right_type = self._infer_type(op.operands[1]) if len(op.operands) > 1 else left_type
        
        # Comparison operators return bool
        if op.operator in ['==', '!=', '<', '>', '<=', '>=']:
            return BUILTIN_TYPES['bool']
        
        # Logical operators return bool
        if op.operator in ['and', 'or', '&&', '||']:
            return BUILTIN_TYPES['bool']
        
        # String concatenation
        if op.operator == '+' and (left_type.name == 'str' or right_type.name == 'str'):
            return BUILTIN_TYPES['str']
        
        # Numeric operations
        if op.operator in ['+', '-', '*', '/', '%', '**']:
            if left_type.name == 'float' or right_type.name == 'float':
                return BUILTIN_TYPES['float']
            if left_type.is_numeric and right_type.is_numeric:
                return BUILTIN_TYPES['int']
        
        # Division always returns float
        if op.operator == '/':
            return BUILTIN_TYPES['float']
        
        return BUILTIN_TYPES['any']
    
    def _infer_call_type(self, call: FunctionCall) -> TypeInfo:
        """Infer type of a function call"""
        # If we know the function, use its return type
        if isinstance(call.callee, Identifier):
            func_name = call.callee.name
            if func_name in self.functions:
                _, return_type = self.functions[func_name]
                return return_type
            
            # Built-in functions with known return types
            builtin_returns = {
                'len': BUILTIN_TYPES['int'],
                'str': BUILTIN_TYPES['str'],
                'int': BUILTIN_TYPES['int'],
                'float': BUILTIN_TYPES['float'],
                'bool': BUILTIN_TYPES['bool'],
                'list': BUILTIN_TYPES['arr'],
                'dict': BUILTIN_TYPES['obj'],
                'range': BUILTIN_TYPES['arr'],
                'print': BUILTIN_TYPES['void'],
                'input': BUILTIN_TYPES['str'],
                'abs': BUILTIN_TYPES['float'],
                'min': BUILTIN_TYPES['any'],
                'max': BUILTIN_TYPES['any'],
                'sum': BUILTIN_TYPES['float'],
            }
            if func_name in builtin_returns:
                return builtin_returns[func_name]
        
        return BUILTIN_TYPES['any']
    
    def _types_compatible(self, target: TypeInfo, source: TypeInfo) -> bool:
        """Check if source type can be assigned to target type"""
        # Any accepts anything
        if target.name == 'any' or source.name == 'any':
            return True
        
        # Same type is always compatible
        if target.name == source.name:
            return True
        
        # Check explicit compatibility rules
        if target.name in TYPE_COMPATIBILITY:
            return source.name in TYPE_COMPATIBILITY[target.name]
        
        return False
    
    def _add_error(self, message: str, line: int, column: int, hints: List[str] = None):
        """Add a type error"""
        source_line = self._get_source_line(line)
        location = SourceLocation(line, column)
        error = TypeError(
            message=message,
            location=location,
            source_line=source_line,
            hints=hints or []
        )
        self.errors.append(error)
    
    def _get_source_line(self, line: int) -> str:
        """Get a source line for error context"""
        if not self.source:
            return ""
        lines = self.source.split('\n')
        if 0 < line <= len(lines):
            return lines[line - 1]
        return ""


def type_check(program: Program, source: str = "") -> List[TypeError]:
    """
    Type check a VL program.
    
    Args:
        program: The parsed AST
        source: Original source code (for error context)
    
    Returns:
        List of type errors found (empty if program is type-correct)
    """
    checker = TypeChecker(source)
    return checker.check(program)
