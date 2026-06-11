"""
VL to Python Code Generator
Converts VL AST to Python source code
"""

from typing import List, Any

# Support both package and standalone usage
try:
    from ..ast_nodes import *
    from .. import config as vl_config
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ast_nodes import *
    import config as vl_config


class PythonCodeGenerator:
    """
    Generates Python code from VL AST
    
    Usage:
        generator = PythonCodeGenerator(ast)
        python_code = generator.generate()
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.indent_level = 0
        self.output = []
        # For roundtrip fidelity: don't emit type annotations if all types are 'any'
        self.omit_any_types = True  # Skip 'Any' annotations for better roundtrip
    
    def generate(self) -> str:
        """Generate Python code from AST"""
        self.output = []
        self._generate_program(self.ast)
        return '\n'.join(self.output)
    
    def _indent(self) -> str:
        """Get current indentation"""
        return '    ' * self.indent_level
    
    def _format_docstring_literal(self, value: str) -> str:
        """Format a docstring safely, avoiding delimiter conflicts."""
        if '"""' not in value:
            return f'"""{value}"""'
        if "'''" not in value:
            return f"'''{value}'''"
        return repr(value)
    
    def _convert_type_annotation(self, vl_type: str) -> str:
        """Convert VL type to Python type annotation"""
        type_map = {
            # Standard type names (lowercase for Python 3.9+ compatibility)
            'arr': 'list[Any]',
            'obj': 'dict[str, Any]',
            'str': 'str',
            'int': 'int',
            'bool': 'bool',
            'float': 'float',
            'any': 'Any',
            # Optimized single-char type aliases
            'I': 'int',           # I = int
            'N': 'float',         # N = number (float)
            'S': 'str',           # S = str
            'B': 'bool',          # B = bool
            'A': 'list[Any]',     # A = arr (array) - lowercase for Python 3.9+
            'O': 'dict[str, Any]',# O = obj (object) - lowercase for Python 3.9+
            'V': 'None',          # V = void
            'P': 'Any',           # P = promise (use Any for Python)
            'L': 'Callable',      # L = lambda/func
        }
        return type_map.get(vl_type, vl_type)
    
    def _typing_names_needed(self, node: Program) -> set:
        """Names to import from typing, based on what will actually be emitted.

        Bare 'Any' annotations are skipped when omit_any_types is set, but
        composite annotations (list[Any], dict[str, Any]) and Callable are
        always emitted and need their imports.
        """
        needed = set()

        def add_for(type_name: str) -> None:
            py_type = self._convert_type_annotation(type_name)
            if py_type == 'Any':
                if not self.omit_any_types:
                    needed.add('Any')
            elif 'Any' in py_type:
                needed.add('Any')
            elif py_type == 'Callable':
                needed.add('Callable')

        for stmt in node.statements:
            if isinstance(stmt, FunctionDef):
                for input_type in stmt.input_types:
                    add_for(input_type.name)
                if stmt.output_type:
                    add_for(stmt.output_type.name)
            elif isinstance(stmt, VariableDef):
                if stmt.type_annotation:
                    add_for(stmt.type_annotation.name)
        return needed
    
    def _replace_item_keyword(self, expr_str: str, loop_var: str = 'x') -> str:
        """Replace 'item' keyword in expressions with the actual loop variable"""
        # Replace 'item' identifier with loop variable
        # Need to be careful not to replace 'item' inside strings or as part of other identifiers
        import re
        # Match 'item' as a whole word (not part of another identifier)
        return re.sub(r'\bitem\b', loop_var, expr_str)
    
    def _emit(self, code: str):
        """Emit a line of code with proper indentation"""
        if code:
            self.output.append(self._indent() + code)
        else:
            self.output.append('')
    
    def _generate_program(self, node: Program):
        """Generate code for entire program"""
        if node.module_docstring:
            self._emit(self._format_docstring_literal(node.module_docstring))
            self._emit('')
        
        # Metadata as comment
        if node.metadata:
            self._emit(f"# VL Program: {node.metadata.name}")
            self._emit(f"# Type: {node.metadata.program_type}")
            self._emit(f"# Target: {node.metadata.target_language}")
            self._emit('')
        
        # Check if typing is already imported via py: passthrough
        has_typing_passthrough = False
        for stmt in node.statements:
            if isinstance(stmt, PythonStmt):
                if 'from typing import' in stmt.code or 'import typing' in stmt.code:
                    has_typing_passthrough = True
                    break
        
        # Check if we need typing imports (only if not already imported via passthrough)
        if not has_typing_passthrough:
            typing_names = self._typing_names_needed(node)
            if typing_names:
                self._emit(f"from typing import {', '.join(sorted(typing_names))}")
                self._emit('')
        
        # Dependencies (imports)
        if node.dependencies:
            for dep in node.dependencies.dependencies:
                self._emit(f"import {dep}")
            self._emit('')
        
        # Statements (functions, variables, etc.)
        for stmt in node.statements:
            self._generate_statement(stmt)
            if not isinstance(stmt, PythonStmt):
                self._emit('')
        
        # Export (if any)
        if node.export:
            self._emit(f"# Exported: {node.export.name}")
    
    def _generate_statement(self, node):
        """Generate code for a statement"""
        if isinstance(node, ClassDef):
            self._generate_class(node)
        elif isinstance(node, FunctionDef):
            self._generate_function(node)
        elif isinstance(node, VariableDef):
            self._generate_variable(node)
        elif isinstance(node, CompoundAssignment):
            self._generate_compound_assignment(node)
        elif isinstance(node, ReturnStmt):
            self._generate_return(node)
        elif isinstance(node, DirectCall):
            self._generate_direct_call(node)
        elif isinstance(node, IfStmt):
            self._generate_if_stmt(node)
        elif isinstance(node, IfElseBlock):
            self._generate_if_else_block(node)
        elif isinstance(node, ForLoop):
            self._generate_for_loop(node)
        elif isinstance(node, WhileLoop):
            self._generate_while_loop(node)
        elif isinstance(node, APICall):
            self._generate_api_call(node)
        elif isinstance(node, DataPipeline):
            self._generate_data_pipeline(node)
        elif isinstance(node, FileOperation):
            self._generate_file_operation(node)
        elif isinstance(node, UIComponent):
            self._generate_ui_component(node)
        elif isinstance(node, PythonStmt):
            self._generate_python_stmt(node)
        else:
            # Unsupported statement type - likely needs implementation
            self._emit(f"# UNSUPPORTED: {type(node).__name__} not yet implemented")
            self._emit(f"# Please report this at: github.com/pmarmaroli/vl/issues")
    
    def _generate_class(self, node: 'ClassDef'):
        """Generate Python class definition"""
        # Handle decorators
        if node.decorators:
            for decorator in node.decorators:
                self._emit(f"@{self._generate_decorator(decorator)}")
        
        # Class header
        bases_str = ""
        if node.base_classes:
            bases_str = f"({', '.join(node.base_classes)})"
        self._emit(f"class {node.name}{bases_str}:")
        
        self.indent_level += 1
        
        # Add class docstring if present
        if node.docstring:
            self._emit(f'"""{node.docstring}"""')
        
        # Generate class attributes (if any)
        if node.attributes:
            for attr in node.attributes:
                self._generate_statement(attr)
        
        # Generate class methods
        if node.methods:
            for method in node.methods:
                self._generate_function(method, is_method=True)
        
        # Empty class body fallback
        if not node.methods and not node.attributes:
            self._emit("pass")
        
        self.indent_level -= 1
        self._emit("")  # blank line after class
    
    def _generate_decorator(self, decorator: 'Decorator') -> str:
        """Generate decorator string"""
        if decorator.args:
            args_str = ", ".join(self._generate_expression(arg) for arg in decorator.args)
            return f"{decorator.name}({args_str})"
        return decorator.name
    
    def _generate_function(self, node: FunctionDef, is_method: bool = False):
        """Generate Python function definition"""
        # Check for @staticmethod decorator
        is_static = False
        if node.decorators:
            for decorator in node.decorators:
                if decorator.name == 'staticmethod':
                    is_static = True
                    break
        
        # Handle decorators for both functions and methods
        if node.decorators:
            for decorator in node.decorators:
                self._emit(f"@{self._generate_decorator(decorator)}")
        
        # Build parameter list
        params = []
        
        # For methods, add self parameter (except for @staticmethod)
        if is_method and not is_static:
            params.append("self")
        
        # Use param_names if available, otherwise fall back to i0, i1, etc.
        for idx, typ in enumerate(node.input_types):
            py_type = self._convert_type_annotation(typ.name)
            if node.param_names and idx < len(node.param_names):
                param_name = node.param_names[idx]
            else:
                param_name = f"i{idx}"
            
            # Skip 'Any' annotation if omit_any_types flag is set
            if self.omit_any_types and py_type == 'Any':
                params.append(param_name)
            else:
                params.append(f"{param_name}: {py_type}")
        
        params_str = ', '.join(params)
        
        # Skip return type annotation if it's 'Any' and omit_any_types is set
        return_type = self._convert_type_annotation(node.output_type.name)
        if self.omit_any_types and return_type == 'Any':
            self._emit(f"def {node.name}({params_str}):")
        else:
            self._emit(f"def {node.name}({params_str}) -> {return_type}:")
        
        self.indent_level += 1
        
        # Add docstring if present
        if node.docstring:
            self._emit(f'"""{node.docstring}"""')
        
        # Function body
        if node.body:
            for stmt in node.body:
                self._generate_statement(stmt)
        else:
            self._emit("pass")
        
        self.indent_level -= 1
    
    def _generate_function_expr(self, node: FunctionExpr) -> str:
        """Generate Python lambda or inline function for function expressions"""
        # Implicit parameter naming i0, i1... based on input types
        params = ', '.join([f"i{idx}" for idx in range(len(node.input_types))])
        
        # For simple single-expression returns, use lambda
        if len(node.body) == 1 and isinstance(node.body[0], ReturnStmt):
            return_expr = self._generate_expression(node.body[0].value)
            return f"lambda {params}: {return_expr}"
        
        # For complex bodies, we'd need to define a function inline
        # For now, generate a lambda that calls a nested function pattern
        # This is a simplified implementation
        if node.body:
            # Try to generate as lambda if body is simple enough
            body_parts = []
            for stmt in node.body:
                if isinstance(stmt, ReturnStmt):
                    body_parts.append(self._generate_expression(stmt.value))
            if body_parts:
                return f"lambda {params}: {body_parts[-1]}"
        
        return f"lambda {params}: None  # Complex function body"
    
    def _generate_variable(self, node: VariableDef):
        """Generate Python variable assignment"""
        value = self._generate_expression(node.value)
        
        # Handle both simple names and complex targets (subscripts, attributes)
        if isinstance(node.name, str):
            # Simple variable assignment: x = value
            type_hint = ""
            if node.type_annotation:
                py_type = self._convert_type_annotation(node.type_annotation.name)
                type_hint = f": {py_type}"
            self._emit(f"{node.name}{type_hint} = {value}")
        else:
            # Complex target (subscript or attribute): x[idx] = value or obj.prop = value
            target = self._generate_expression(node.name)
            self._emit(f"{target} = {value}")
    
    def _generate_compound_assignment(self, node: CompoundAssignment):
        """Generate Python compound assignment (+=, -=, *=, /=)"""
        value = self._generate_expression(node.value)
        self._emit(f"{node.name} {node.operator}= {value}")
    
    def _generate_return(self, node: ReturnStmt):
        """Generate Python return statement"""
        value = self._generate_expression(node.value)
        self._emit(f"return {value}")
    
    def _generate_direct_call(self, node: DirectCall):
        """Generate Python direct function call (without assignment)"""
        function_code = self._generate_expression(node.function)
        self._emit(function_code)

    def _generate_if_stmt(self, node: IfStmt):
        """Generate Python if statement"""
        condition = self._generate_expression(node.condition)
        self._emit(f"if {condition}:")
        self.indent_level += 1
        # Handle both expressions and return statements
        if isinstance(node.true_expr, ReturnStmt):
            self._generate_return(node.true_expr)
        else:
            self._emit(self._generate_expression(node.true_expr))
        self.indent_level -= 1
        self._emit("else:")
        self.indent_level += 1
        if isinstance(node.false_expr, ReturnStmt):
            self._generate_return(node.false_expr)
        else:
            self._emit(self._generate_expression(node.false_expr))
        self.indent_level -= 1
    
    def _generate_if_else_block(self, node):
        """Generate Python if/else block (imperative style)"""
        condition = self._generate_expression(node.condition)
        self._emit(f"if {condition}:")
        
        self.indent_level += 1
        if node.if_body:
            for stmt in node.if_body:
                self._generate_statement(stmt)
        else:
            self._emit("pass")  # Empty if body
        self.indent_level -= 1
        
        if node.else_body:
            self._emit("else:")
            self.indent_level += 1
            for stmt in node.else_body:
                self._generate_statement(stmt)
            self.indent_level -= 1
    
    def _generate_for_loop(self, node: ForLoop):
        """Generate Python for loop"""
        iterable = self._generate_expression(node.iterable)
        self._emit(f"for {node.variable} in {iterable}:")
        
        self.indent_level += 1
        for stmt in node.body:
            self._generate_statement(stmt)
        self.indent_level -= 1
    
    def _generate_while_loop(self, node: WhileLoop):
        """Generate Python while loop"""
        condition = self._generate_expression(node.condition)
        self._emit(f"while {condition}:")
        
        self.indent_level += 1
        for stmt in node.body:
            self._generate_statement(stmt)
        self.indent_level -= 1
    
    def _generate_api_call(self, node: APICall):
        """Generate Python API call"""
        method = node.method.lower()
        endpoint = self._generate_expression(node.endpoint)
        self._emit(f"# API Call: {node.method}")
        self._emit(f"requests.{method}({endpoint})")
    
    def _generate_api_call_expr(self, node: APICall) -> str:
        """Generate API call as expression (for assignment/return)"""
        method = node.method.lower()
        endpoint = self._generate_expression(node.endpoint)
        return f"requests.{method}({endpoint})"

    def _generate_data_pipeline(self, node: DataPipeline):
        """Generate Python data processing pipeline"""
        source = self._generate_expression(node.source)
        self._emit(f"# Data pipeline from: {source}")
        self._emit(f"data = {source}")
        
        for op in node.operations:
            if isinstance(op, FilterOp):
                condition = self._generate_expression(op.condition)
                condition = self._replace_item_keyword(condition, 'x')
                self._emit(f"data = [x for x in data if {condition}]")
            elif isinstance(op, MapOp):
                if op.expression:
                    expr = self._generate_expression(op.expression)
                    expr = self._replace_item_keyword(expr, 'x')
                    self._emit(f"data = [{expr} for x in data]")
            elif isinstance(op, GroupByOp):
                self._emit(f"# Group by {op.field}")
                self._emit(f"from collections import defaultdict")
                self._emit(f"_grouped = defaultdict(list)")
                self._emit(f"for x in data:")
                self._emit(f"    _grouped[x.get('{op.field}', x['{op.field}'] if isinstance(x, dict) else getattr(x, '{op.field}', None))].append(x)")
                self._emit(f"data = dict(_grouped)")
            elif isinstance(op, AggregateOp):
                self._emit(f"# Aggregate: {op.function}")
                if op.function == 'count':
                    self._emit(f"data = {{k: len(v) for k, v in data.items()}}")
                elif op.function == 'sum':
                    field = op.field or 'value'
                    self._emit(f"data = {{k: sum(x.get('{field}', x['{field}'] if isinstance(x, dict) else getattr(x, '{field}', 0)) for x in v) for k, v in data.items()}}")
                elif op.function == 'avg':
                    field = op.field or 'value'
                    self._emit(f"data = {{k: sum(x.get('{field}', x['{field}'] if isinstance(x, dict) else getattr(x, '{field}', 0)) for x in v) / len(v) if v else 0 for k, v in data.items()}}")
                elif op.function == 'min':
                    field = op.field or 'value'
                    self._emit(f"data = {{k: min(x.get('{field}', x['{field}'] if isinstance(x, dict) else getattr(x, '{field}', 0)) for x in v) for k, v in data.items()}}")
                elif op.function == 'max':
                    field = op.field or 'value'
                    self._emit(f"data = {{k: max(x.get('{field}', x['{field}'] if isinstance(x, dict) else getattr(x, '{field}', 0)) for x in v) for k, v in data.items()}}")
            elif isinstance(op, SortOp):
                reverse = "True" if op.order == 'desc' else "False"
                self._emit(f"data = sorted(data, key=lambda x: x.get('{op.field}', x['{op.field}'] if isinstance(x, dict) else getattr(x, '{op.field}', 0)), reverse={reverse})")
    
    def _generate_data_pipeline_expr(self, node: DataPipeline) -> str:
        """Generate data pipeline as an expression (for return statements)"""
        # Generate the source expression
        source_expr = self._generate_expression(node.source)
        
        # Build the pipeline by chaining comprehensions
        # Start with the source
        result = source_expr
        
        # Check if we have complex operations that need statement form
        has_complex_ops = any(isinstance(op, (GroupByOp, AggregateOp)) for op in node.operations)
        
        if has_complex_ops:
            # For complex operations, generate as a multiline expression with inline helper
            # This is a simplified version - full support would require statement context
            self._emit("# Complex pipeline - using itertools/functools")
            self._emit("from itertools import groupby")
            self._emit("from functools import reduce")
        
        # Apply each operation in sequence
        for op in node.operations:
            if isinstance(op, FilterOp):
                condition = self._generate_expression(op.condition)
                condition = self._replace_item_keyword(condition, 'x')
                result = f"[x for x in {result} if {condition}]"
            elif isinstance(op, MapOp):
                if op.expression:
                    expr = self._generate_expression(op.expression)
                    expr = self._replace_item_keyword(expr, 'x')
                    result = f"[{expr} for x in {result}]"
            elif isinstance(op, GroupByOp):
                # Use dict comprehension with setdefault pattern
                result = f"{{k: list(g) for k, g in groupby(sorted({result}, key=lambda x: x.get('{op.field}', '')), key=lambda x: x.get('{op.field}', ''))}}"
            elif isinstance(op, AggregateOp):
                if op.function == 'count':
                    result = f"{{k: len(v) for k, v in {result}.items()}}"
                elif op.function == 'sum':
                    field = op.field or 'value'
                    result = f"{{k: sum(x.get('{field}', 0) for x in v) for k, v in {result}.items()}}"
        
        return result
    
    def _generate_file_operation(self, node: FileOperation):
        """Generate Python file I/O operations"""
        op = node.operation
        path = self._generate_expression(node.path)
        
        if op == 'read':
            self._emit(f"with open({path}, 'r') as f:")
            self._emit(f"    content = f.read()")
        elif op == 'write':
            if node.arguments:
                content = self._generate_expression(node.arguments[0])
                self._emit(f"with open({path}, 'w') as f:")
                self._emit(f"    f.write({content})")
    
    def _generate_ui_component(self, node: UIComponent):
        """Generate React/UI component (basic support)"""
        self._emit(f"# UI Component: {node.name}")
        
        # Generate as a React functional component
        self._emit(f"def {node.name}(props):")
        self.indent_level += 1
        
        # Generate state hooks if any
        for state_name, state_type, state_value in node.state_vars:
            value = self._generate_expression(state_value) if state_value else "None"
            self._emit(f"# State: {state_name} = {value}")
        
        # Simple placeholder return
        self._emit(f"return None  # React JSX would go here")
        
        self.indent_level -= 1
    
    def _generate_python_stmt(self, node: 'PythonStmt'):
        """Generate code for Python statement passthrough"""
        # The code may have @@@ as line separators and @N@ as indentation markers
        # Convert them back to newlines and spaces
        code = node.code
        # Only treat @@@/@4@ as markers when the code is still single-line
        if '\n' not in code and ('@@@' in code or '@4@' in code):
            # Replace @4@ with 4 spaces (Python standard indentation)
            code = code.replace('@4@', '    ')
            # Replace @@@ with newlines
            code = code.replace('@@@', '\n')
        # Split into lines and emit each
        # Each line needs the current indentation level prepended
        lines = code.split('\n')
        for line in lines:
            # Add the line with current indentation prefix
            if line.strip():  # Only add indentation to non-empty lines
                self.output.append(self._indent() + line)
            else:
                self.output.append('')

    def _generate_expression(self, node: Expression) -> str:
        """Generate Python expression"""
        if isinstance(node, NumberLiteral):
            return str(node.value)
        
        elif isinstance(node, RangeExpr):
            start = self._generate_expression(node.start)
            end = self._generate_expression(node.end)
            return f"range({start}, {end})"
        
        elif isinstance(node, PythonExpr):
            # Direct Python code passthrough
            # Handle @@@-delimited multi-line Python code
            code = node.code
            if '\n' not in code and ('@@@' in code or '@4@' in code):
                code = code.replace('@4@', '    ')
                # Convert @@@ back to newlines with proper indentation
                lines = code.split('@@@')
                # Clean up and rejoin with newlines
                cleaned_lines = []
                for line in lines:
                    # Only strip leading/trailing whitespace from each line,
                    # but preserve internal spaces
                    line = line.strip()
                    if line:
                        cleaned_lines.append(self._indent() + line)
                return '\n'.join(cleaned_lines)
            # For single-line code without @@@ markers, return as-is
            # This preserves spaces in expressions like "[x*x for x in numbers]"
            return code
        
        elif isinstance(node, StringLiteral):
            if '${' in node.value:
                # Parse complex expressions in template strings
                result = self._process_string_template(node.value)
                return result
            else:
                return f"'{node.value}'"
        
        elif isinstance(node, BooleanLiteral):
            return 'True' if node.value else 'False'
        
        elif isinstance(node, Identifier):
            # Convert VL keywords to Python equivalents
            if node.name == 'true':
                return 'True'
            elif node.name == 'false':
                return 'False'
            elif node.name == 'null':
                return 'None'
            return node.name
        
        elif isinstance(node, VariableRef):
            return node.name 
        
        elif isinstance(node, FunctionCall):
            callee = self._generate_expression(node.callee)
            args = ', '.join([self._generate_expression(arg) for arg in node.arguments])
            return f"{callee}({args})"
            
        elif isinstance(node, MemberAccess):
            obj = self._generate_expression(node.object)
            return f"{obj}.{node.property}"
        
        elif isinstance(node, IndexAccess):
            obj = self._generate_expression(node.object)
            index = self._generate_expression(node.index)
            return f"{obj}[{index}]"

        elif isinstance(node, Operation):
            return self._generate_operation(node)
        
        elif isinstance(node, InOp):
            element = self._generate_expression(node.element)
            container = self._generate_expression(node.container)
            return f"({element} in {container})"
            
        elif isinstance(node, ArrayLiteral):
            elements = ', '.join([self._generate_expression(e) for e in node.elements])
            return f"[{elements}]"
        
        elif isinstance(node, ObjectLiteral):
            pair_strs = []
            for k, v in node.pairs:
                if isinstance(v, FunctionExpr):
                    # Generate lambda or method reference for function expressions
                    pair_strs.append(f"'{k}': {self._generate_function_expr(v)}")
                else:
                    pair_strs.append(f"'{k}': {self._generate_expression(v)}")
            return f"{{{', '.join(pair_strs)}}}"
        
        elif isinstance(node, FunctionExpr):
            return self._generate_function_expr(node)
        
        elif isinstance(node, IfStmt):
            # If statement can be used as expression (ternary)
            # Handle ReturnStmt in branches (can't be ternary if returns are involved)
            if isinstance(node.true_expr, ReturnStmt) or isinstance(node.false_expr, ReturnStmt):
                # This should be handled as a statement, not expression
                return "None  # ERROR: If with return branches should not be in expression context"
            condition = self._generate_expression(node.condition)
            true_val = self._generate_expression(node.true_expr)
            false_val = self._generate_expression(node.false_expr)
            return f"({true_val} if {condition} else {false_val})"
        
        elif isinstance(node, DataPipeline):
            # Data pipeline as expression
            return self._generate_data_pipeline_expr(node)
        
        elif isinstance(node, APICall):
            # API call as expression
            return self._generate_api_call_expr(node)
        
        else:
            # Unsupported expression type - likely needs implementation
            return f"None  # UNSUPPORTED: {type(node).__name__} - please report this"
    
    def _generate_operation(self, node: Operation) -> str:
        """Generate Python operation with optimization for boolean chains"""
        operator_map = {
            '+': '+', '-': '-', '*': '*', '/': '/', '//': '//', '%': '%',
            '**': '**', '==': '==', '!=': '!=',
            '<': '<', '>': '>', '<=': '<=', '>=': '>=',
            '&&': 'and', '||': 'or', '!': 'not',
        }
        
        op = operator_map.get(node.operator, node.operator)
        
        # Check if this is a known binary/unary operator
        is_known_operator = node.operator in operator_map
        
        # OPTIMIZATION: Convert chained && to all() and || to any()
        # This is more Pythonic and saves tokens in generated code
        # Controlled by vl_config.BOOLEAN_CHAIN_MIN_LENGTH
        if vl_config.should_optimize_booleans('python') and node.operator in ('&&', '||') and len(node.operands) == 2:
            # Collect all operands in the chain
            conditions = []
            self._collect_boolean_chain(node, node.operator, conditions)
            
            # If we have enough conditions, use all()/any()
            if len(conditions) >= vl_config.BOOLEAN_CHAIN_MIN_LENGTH:
                condition_strs = [self._generate_expression(cond) for cond in conditions]
                if node.operator == '&&':
                    return f"all([{', '.join(condition_strs)}])"
                else:  # ||
                    return f"any([{', '.join(condition_strs)}])"
        
        # Standard operation handling
        if len(node.operands) == 1:
            operand = self._generate_expression(node.operands[0])
            return f"{op} {operand}"
        elif len(node.operands) == 2 and is_known_operator:
            # Binary operator syntax (only for known operators)
            left = self._generate_expression(node.operands[0])
            right = self._generate_expression(node.operands[1])
            # Only wrap in parens if operands are also operations (for clarity)
            # or for low-precedence operators in potentially ambiguous contexts
            needs_parens = (
                isinstance(node.operands[0], Operation) or 
                isinstance(node.operands[1], Operation) or
                op in ('and', 'or')
            )
            if needs_parens:
                return f"({left} {op} {right})"
            return f"{left} {op} {right}"
        else:
            # Function call syntax (for unknown operators or != 2 operands)
            operands = ', '.join([self._generate_expression(o) for o in node.operands])
            return f"{op}({operands})"
    
    def _collect_boolean_chain(self, node: Expression, target_op: str, result: list):
        """Recursively collect all operands from a chain of the same boolean operator"""
        if isinstance(node, Operation) and node.operator == target_op and len(node.operands) == 2:
            # Recursively flatten left side
            self._collect_boolean_chain(node.operands[0], target_op, result)
            # Recursively flatten right side
            self._collect_boolean_chain(node.operands[1], target_op, result)
        else:
            # Base case: not a matching operation, add as-is
            result.append(node)
    
    def _process_string_template(self, template: str) -> str:
        """Process string template with complex VL expressions in ${...}"""
        import re
        from ..lexer import Lexer
        from ..parser import Parser
        
        result_parts = []
        last_end = 0
        
        # Find all ${...} blocks, respecting nesting
        i = 0
        while i < len(template):
            if i < len(template) - 1 and template[i:i+2] == '${':
                # Found start of interpolation
                # Add any literal text before this
                if i > last_end:
                    result_parts.append(repr(template[last_end:i]))
                
                # Find matching closing brace
                depth = 1
                j = i + 2
                while j < len(template) and depth > 0:
                    if template[j] == '{':
                        depth += 1
                    elif template[j] == '}':
                        depth -= 1
                    j += 1
                
                if depth == 0:
                    # Extract the VL expression
                    vl_expr = template[i+2:j-1]
                    
                    # Parse and generate Python code for it
                    try:
                        lexer = Lexer(vl_expr)
                        tokens = lexer.tokenize()
                        parser = Parser(tokens)
                        
                        # Parse as expression (could be if, op, identifier, etc.)
                        expr_node = parser.parse_expression()
                        py_expr = self._generate_expression(expr_node)
                        
                        result_parts.append(f"({py_expr})")
                    except Exception:
                        # Fallback to simple identifier
                        result_parts.append(f"{{{vl_expr}}}")
                    
                    last_end = j
                    i = j
                else:
                    i += 1
            else:
                i += 1
        
        # Add any remaining literal text
        if last_end < len(template):
            result_parts.append(repr(template[last_end:]))
        
        # Combine into Python f-string
        if len(result_parts) == 0:
            return "''"
        elif len(result_parts) == 1 and result_parts[0].startswith("'"):
            return result_parts[0]
        else:
            # Build f-string with proper formatting
            combined = 'f"' + ''.join([
                part[1:-1] if part.startswith("'") else '{' + part + '}'
                for part in result_parts
            ]) + '"'
            return combined


if __name__ == "__main__":
    # Test with a simple AST
    from ast_nodes import *
    
    # Create a simple function: F:sum|I,I|I|ret:op:+(i0,i1)
    metadata = MetadataNode("sum_function", "function", "python")
    param1 = ParameterNode("i0", "int")
    param2 = ParameterNode("i1", "int")
    
    op_node = OperationNode("+", [
        IdentifierNode("i0"),
        IdentifierNode("i1")
    ])
    
    return_node = ReturnNode(op_node)
    
    func = FunctionDefNode(
        name="sum",
        parameters=[param1, param2],
        return_type="int",
        body=[return_node]
    )
    
    program = ProgramNode(
        metadata=metadata,
        dependencies=[],
        statements=[func],
        export="sum"
    )
    
    generator = PythonCodeGenerator(program)
    output = generator.generate()
    
    print("Generated Python code:")
    print(output)
