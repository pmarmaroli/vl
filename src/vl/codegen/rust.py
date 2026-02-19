"""
VL to Rust Code Generator (Initial Implementation)

Generates Rust code from VL AST.
This is a basic implementation focusing on core constructs.
"""

from ..ast_nodes import *
from typing import List


class RustCodeGenerator:
    """
    Generate Rust code from VL AST
    
    Usage:
        generator = RustCodeGenerator(ast)
        rust_code = generator.generate()
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.code = []
        self.indent_level = 0
    
    def _emit(self, line: str = ""):
        """Emit a line of code with proper indentation"""
        if line:
            self.code.append("    " * self.indent_level + line)
        else:
            self.code.append("")
    
    def _type_to_rust(self, vl_type: Type) -> str:
        """Convert VL type to Rust type"""
        type_map = {
            # Standard type names
            'int': 'i32',
            'float': 'f64',
            'str': '&str',
            'bool': 'bool',
            'arr': 'Vec<i32>',  # Generic, needs more context
            'obj': 'HashMap<String, String>',  # Simplified
            'any': 'Box<dyn Any>',
            'void': '()',
            # Optimized single-char type aliases
            'I': 'i32',                # I = int
            'N': 'f64',                # N = number (float)
            'S': '&str',               # S = str
            'B': 'bool',               # B = bool
            'A': 'Vec<i32>',           # A = arr (array)
            'O': 'HashMap<String, String>', # O = obj (object)
            'V': '()',                 # V = void
        }
        return type_map.get(vl_type.name, 'i32')
    
    def generate(self) -> str:
        """Generate code for entire program"""
        node = self.ast
        
        # Header comment
        self._emit("// Generated Rust code from VL")
        self._emit()
        
        # Common imports
        self._emit("use std::collections::HashMap;")
        self._emit()
        
        # Statements
        for stmt in node.statements:
            self._generate_statement(stmt)
        
        return '\n'.join(self.code)
    
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
            self._emit(f"// UNSUPPORTED: {type(node).__name__} not yet implemented for Rust")
            self._emit(f"// Please report this at: github.com/vibe-language/issues")

    def _generate_function(self, node: FunctionDef):
        """Generate Rust function with type annotations"""
        # Parameters with types
        params = []
        for i, input_type in enumerate(node.input_types):
            rust_type = self._type_to_rust(input_type)
            params.append(f"i{i}: {rust_type}")
        
        params_str = ", ".join(params)
        return_type = self._type_to_rust(node.output_type)
        
        self._emit(f"fn {node.name}({params_str}) -> {return_type} {{")
        self.indent_level += 1
        
        # Generate body
        for stmt in node.body:
            self._generate_statement(stmt)
            
        self.indent_level -= 1
        self._emit("}")
        self._emit()

    def _generate_variable_def(self, node: VariableDef):
        """Generate Rust variable declaration"""
        val_code = self._generate_expression(node.value)
        
        # Rust prefers let with type inference, but we can add explicit types
        if node.type_annotation:
            rust_type = self._type_to_rust(node.type_annotation)
            self._emit(f"let {node.name}: {rust_type} = {val_code};")
        else:
            self._emit(f"let {node.name} = {val_code};")

    def _generate_return_stmt(self, node: ReturnStmt):
        """Generate return statement (or expression without semicolon)"""
        val_code = self._generate_expression(node.value)
        # In Rust, the last expression without semicolon is returned
        # But we'll use explicit return for clarity
        self._emit(f"return {val_code};")

    def _generate_if_stmt(self, node: IfStmt):
        """Generate if statement"""
        cond_code = self._generate_expression(node.condition)
        
        self._emit(f"if {cond_code} {{")
        self.indent_level += 1
        
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
        """Generate for loop using Rust iterator syntax"""
        iterable = self._generate_expression(node.iterable)
        
        # Rust uses 'for var in iterator' syntax
        self._emit(f"for {node.variable} in {iterable} {{")
        self.indent_level += 1
        
        for stmt in node.body:
            self._generate_statement(stmt)
        
        self.indent_level -= 1
        self._emit("}")

    def _generate_while_loop(self, node: WhileLoop):
        """Generate while loop"""
        condition = self._generate_expression(node.condition)
        self._emit(f"while {condition} {{")
        self.indent_level += 1
        
        for stmt in node.body:
            self._generate_statement(stmt)
        
        self.indent_level -= 1
        self._emit("}")

    def _generate_expression(self, node: Expression) -> str:
        """Generate Rust expression"""
        if isinstance(node, NumberLiteral):
            return str(node.value)
            
        elif isinstance(node, StringLiteral):
            # Use raw string literals when possible
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
                '%': '%', '**': 'pow'  # Requires .pow() method
            }
            
            op = op_map.get(node.operator, node.operator)
            
            # Special case for power
            if op == 'pow':
                left = self._generate_expression(node.operands[0])
                right = self._generate_expression(node.operands[1])
                return f"{left}.pow({right})"
            
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
            elements = [self._generate_expression(e) for e in node.elements]
            return f"vec![{', '.join(elements)}]"
            
        elif isinstance(node, ObjectLiteral):
            # Generate HashMap initialization
            pairs = []
            for k, v in node.pairs:
                v_expr = self._generate_expression(v)
                pairs.append(f'map.insert("{k}".to_string(), {v_expr});')
            
            # This is a bit verbose, but shows the pattern
            return f"{{ let mut map = HashMap::new(); {''.join(pairs)} map }}"
            
        elif isinstance(node, MemberAccess):
            obj = self._generate_expression(node.object)
            return f"{obj}.{node.property}"
            
        elif isinstance(node, IndexAccess):
            obj = self._generate_expression(node.object)
            index = self._generate_expression(node.index)
            return f"{obj}[{index}]"
            
        elif isinstance(node, RangeExpr):
            start = self._generate_expression(node.start)
            end = self._generate_expression(node.end)
            # Rust uses start..end for ranges (exclusive end)
            return f"({start}..{end})"
        
        return "()"


def generate_rust(ast: Program) -> str:
    """Main entry point for Rust code generation"""
    generator = RustCodeGenerator(ast)
    return generator.generate()
