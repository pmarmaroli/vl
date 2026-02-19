"""
VL to C Code Generator (Initial Implementation)

Generates C code from VL AST.
This is a basic implementation focusing on core constructs.
"""

from ..ast_nodes import *
from typing import List, Dict


class CCodeGenerator:
    """
    Generate C code from VL AST
    
    Usage:
        generator = CCodeGenerator(ast)
        c_code = generator.generate()
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.code = []
        self.includes = set()
        self.indent_level = 0
    
    def _emit(self, line: str = ""):
        """Emit a line of code with proper indentation"""
        if line:
            self.code.append("    " * self.indent_level + line)
        else:
            self.code.append("")
    
    def _type_to_c(self, vl_type: Type) -> str:
        """Convert VL type to C type"""
        type_map = {
            # Standard type names
            'int': 'int',
            'float': 'double',
            'str': 'char*',
            'bool': 'bool',
            'arr': 'void*',  # Generic array, needs more context
            'obj': 'void*',  # Generic object, needs more context
            'any': 'void*',
            'void': 'void',
            # Optimized single-char type aliases
            'I': 'int',              # I = int
            'N': 'double',           # N = number (float)
            'S': 'char*',            # S = str
            'B': 'bool',             # B = bool
            'A': 'void*',            # A = arr (array)
            'O': 'void*',            # O = obj (object)
            'V': 'void',             # V = void
        }
        return type_map.get(vl_type.name, 'void*')
    
    def generate(self) -> str:
        """Generate code for entire program"""
        node = self.ast
        
        # Header comments
        self._emit("/* Generated C code from VL */")
        self._emit()
        
        # Standard includes
        self.includes.add("stdbool.h")  # For bool type
        self.includes.add("stdio.h")    # For I/O
        self.includes.add("stdlib.h")   # For memory management
        
        # Emit includes
        for include in sorted(self.includes):
            self._emit(f"#include <{include}>")
        self._emit()
        
        # Forward declarations (if needed)
        for stmt in node.statements:
            if isinstance(stmt, FunctionDef):
                self._emit(self._generate_function_signature(stmt) + ";")
        self._emit()
        
        # Statements
        for stmt in node.statements:
            self._generate_statement(stmt)
        
        return '\n'.join(self.code)
    
    def _generate_function_signature(self, node: FunctionDef) -> str:
        """Generate C function signature"""
        # Parameters with types
        params = []
        for i, input_type in enumerate(node.input_types):
            c_type = self._type_to_c(input_type)
            params.append(f"{c_type} i{i}")
        
        params_str = ", ".join(params) if params else "void"
        return_type = self._type_to_c(node.output_type)
        
        return f"{return_type} {node.name}({params_str})"
    
    def _generate_statement(self, node: Statement):
        """Generate code for a statement"""
        if isinstance(node, FunctionDef):
            self._generate_function(node)
        elif isinstance(node, VariableDef):
            self._generate_variable_def(node)
        elif isinstance(node, ReturnStmt):
            self._generate_return_stmt(node)
        elif isinstance(node, IfStmt):
            self._generate_if_stmt(node)
        elif isinstance(node, ForLoop):
            self._generate_for_loop(node)
        elif isinstance(node, WhileLoop):
            self._generate_while_loop(node)
        else:
            # Unsupported statement type - likely needs implementation
            self._emit(f"/* UNSUPPORTED: {type(node).__name__} not yet implemented for C */")
            self._emit(f"/* Please report this at: github.com/vibe-language/issues */")

    def _generate_function(self, node: FunctionDef):
        """Generate C function definition"""
        signature = self._generate_function_signature(node)
        self._emit(f"{signature} {{")
        self.indent_level += 1
        
        # Generate body
        for stmt in node.body:
            self._generate_statement(stmt)
            
        self.indent_level -= 1
        self._emit("}")
        self._emit()

    def _generate_variable_def(self, node: VariableDef):
        """Generate C variable declaration and initialization"""
        val_code = self._generate_expression(node.value)
        
        # If we have type annotation, use it
        if node.type_annotation:
            c_type = self._type_to_c(node.type_annotation)
            self._emit(f"{c_type} {node.name} = {val_code};")
        else:
            # Auto type - use int as default
            self._emit(f"int {node.name} = {val_code};")

    def _generate_return_stmt(self, node: ReturnStmt):
        """Generate return statement"""
        val_code = self._generate_expression(node.value)
        self._emit(f"return {val_code};")

    def _generate_if_stmt(self, node: IfStmt):
        """Generate if statement"""
        cond_code = self._generate_expression(node.condition)
        
        self._emit(f"if ({cond_code}) {{")
        self.indent_level += 1
        
        # Handle expression in statement context
        if isinstance(node.true_expr, ReturnStmt):
            self._generate_return_stmt(node.true_expr)
        else:
            true_code = self._generate_expression(node.true_expr)
            self._emit(f"{true_code};")
        
        self.indent_level -= 1
        self._emit("} else {")
        self.indent_level += 1
        
        if isinstance(node.false_expr, ReturnStmt):
            self._generate_return_stmt(node.false_expr)
        else:
            false_code = self._generate_expression(node.false_expr)
            self._emit(f"{false_code};")
        
        self.indent_level -= 1
        self._emit("}")

    def _generate_for_loop(self, node: ForLoop):
        """Generate for loop (C-style with range support)"""
        # For now, assume iterable is a RangeExpr
        if isinstance(node.iterable, RangeExpr):
            start = self._generate_expression(node.iterable.start)
            end = self._generate_expression(node.iterable.end)
            self._emit(f"for (int {node.variable} = {start}; {node.variable} < {end}; {node.variable}++) {{")
        else:
            # Generic iteration (simplified for basic cases)
            iterable = self._generate_expression(node.iterable)
            self._emit(f"/* Note: C requires explicit array bounds for iteration */")
            self._emit(f"/* Assuming array size is known or using sentinel values */")
            self._emit(f"for (int i = 0; i < 10; i++) {{")
        
        self.indent_level += 1
        for stmt in node.body:
            self._generate_statement(stmt)
        self.indent_level -= 1
        self._emit("}")

    def _generate_while_loop(self, node: WhileLoop):
        """Generate while loop"""
        condition = self._generate_expression(node.condition)
        self._emit(f"while ({condition}) {{")
        self.indent_level += 1
        
        for stmt in node.body:
            self._generate_statement(stmt)
        
        self.indent_level -= 1
        self._emit("}")

    def _generate_expression(self, node: Expression) -> str:
        """Generate C expression"""
        if isinstance(node, NumberLiteral):
            return str(node.value)
            
        elif isinstance(node, StringLiteral):
            # Escape quotes
            escaped = node.value.replace('"', '\\"')
            return f'"{escaped}"'
            
        elif isinstance(node, BooleanLiteral):
            return "true" if node.value else "false"
            
        elif isinstance(node, Identifier):
            return node.name
            
        elif isinstance(node, VariableRef):
            return node.name
            
        elif isinstance(node, Operation):
            op_map = {
                '&&': '&&', '||': '||', '!': '!',
                'and': '&&', 'or': '||', 'not': '!',
                '==': '==', '!=': '!=',
                '<': '<', '>': '>', '<=': '<=', '>=': '>=',
                '+': '+', '-': '-', '*': '*', '/': '/',
                '%': '%', '**': 'pow'  # Power needs math.h
            }
            
            op = op_map.get(node.operator, node.operator)
            
            # Special case for power
            if op == 'pow':
                self.includes.add("math.h")
                left = self._generate_expression(node.operands[0])
                right = self._generate_expression(node.operands[1])
                return f"pow({left}, {right})"
            
            # Unary operators
            if len(node.operands) == 1:
                operand = self._generate_expression(node.operands[0])
                return f"{op}({operand})"
            
            # Binary operators
            if len(node.operands) == 2:
                left = self._generate_expression(node.operands[0])
                right = self._generate_expression(node.operands[1])
                return f"({left} {op} {right})"
                
        elif isinstance(node, FunctionCall):
            callee = self._generate_expression(node.callee)
            args = [self._generate_expression(arg) for arg in node.arguments]
            return f"{callee}({', '.join(args)})"
            
        elif isinstance(node, ArrayLiteral):
            # C doesn't have array literals like this, needs initialization
            elements = [self._generate_expression(e) for e in node.elements]
            return f"{{{', '.join(elements)}}}"
            
        elif isinstance(node, MemberAccess):
            obj = self._generate_expression(node.object)
            # Use -> for pointers, . for structs (default to .)
            return f"{obj}.{node.property}"
            
        elif isinstance(node, IndexAccess):
            obj = self._generate_expression(node.object)
            index = self._generate_expression(node.index)
            return f"{obj}[{index}]"
            
        elif isinstance(node, RangeExpr):
            # Ranges don't exist as expressions in C, return comment
            start = self._generate_expression(node.start)
            end = self._generate_expression(node.end)
            return f"/* range({start}, {end}) */"
        
        return "NULL"


def generate_c(ast: Program) -> str:
    """Main entry point for C code generation"""
    generator = CCodeGenerator(ast)
    return generator.generate()
