"""
Python to VL Converter
Converts Python AST to VL source code

Usage:
    from vl.py_to_vl import PythonToVLConverter
    
    converter = PythonToVLConverter()
    vl_code = converter.convert(python_code)
"""

import ast
import base64
from typing import List, Optional, Any


class PythonToVLConverter:
    """
    Converts Python source code to VL source code
    
    Strategy:
    1. Parse Python code into AST
    2. Walk AST and generate VL constructs
    3. Handle Python-specific idioms (comprehensions, decorators, etc.)
    """
    
    def __init__(self):
        self.indent_level = 0
        self.output: List[str] = []
        self.imports: List[str] = []
        self.import_froms: List[tuple] = []  # List of (module, [names]) tuples
        self.has_typing = False
        self.source_code: str = ""
        self.original_source: str = ""
        self.param_map: dict = {}  # Maps Python param names to VL i0, i1, etc.
        self.renamed_vars: dict = {}  # Maps Python var names that conflict with VL keywords
        # VL reserved words that can't be used as variable names
        self.vl_reserved = {'op', 'data', 'item', 'meta', 'deps', 'if', 'else', 'for', 'while', 'ret', 'fn', 'class', 'file', 'api', 'async', 'filter', 'map', 'parse', 'ui', 'state', 'props', 'on', 'render', 'sort', 'ffi', 'py', 'i', 'o', 'v', 't'}
    
    def _encode_python_passthrough(self, code: str) -> str:
        """Encode Python code for py: passthrough using a base64 wrapper."""
        payload = base64.b64encode(code.encode('utf-8')).decode('ascii')
        return f"__RAW_B64__({payload!r})"

    def _emit_module_docstring(self, expr_node: ast.Expr) -> None:
        """Emit the exact module docstring literal as a passthrough."""
        literal = ast.get_source_segment(self.source_code, expr_node) or repr(expr_node.value.value)
        if not literal.endswith('\n'):
            literal += '\n'
        encoded_doc = self._encode_python_passthrough(literal)
        self.output.append(f"py:{encoded_doc}")

    def _get_source(self, node: ast.AST) -> Optional[str]:
        """Best-effort capture of original source for a node."""
        return ast.get_source_segment(self.source_code, node)

    def _is_docstring_constant(self, owner: ast.AST, const_node: ast.Constant) -> bool:
        """Check if const_node is the leading docstring of owner."""
        if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if owner.body and isinstance(owner.body[0], ast.Expr) and owner.body[0].value is const_node:
                return True
        return False

    def _statement_needs_passthrough(self, node: ast.AST) -> bool:
        """Heuristic to determine if statement should use py: passthrough.
        
        Use passthrough for:
        - Complex/unsupported Python features
        - from...import statements (to preserve exact import style)
        
        DO NOT use passthrough for:
        - Simple functions, classes, variables (VL can handle these)
        """
        # Always use passthrough for from-imports (preserve style)
        if isinstance(node, ast.ImportFrom):
            return True
        
        # Use VL conversion for supported constructs
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, 
                            ast.Assign, ast.AnnAssign, ast.AugAssign,
                            ast.Return, ast.If, ast.For, ast.While,
                            ast.Expr, ast.Pass)):
            return False
        
        # Everything else uses passthrough (for now)
        return True

    def _safe_var_name(self, name: str) -> str:
        """Ensure variable name doesn't conflict with VL reserved words"""
        if name in self.vl_reserved:
            return f"{name}_var"
        return name
    
    def _expression_needs_passthrough(self, node: ast.AST) -> bool:
        """Check if expression contains constructs that conflict with VL syntax.
        
        Use passthrough for:
        - Bitwise operators (&, |, ^, ~, <<, >>) - conflict with VL's | separator
        - Complex nested boolean expressions with & or |
        - Ternary operators in dict values
        """
        class PassthroughChecker(ast.NodeVisitor):
            def __init__(self):
                self.needs_passthrough = False
            
            def visit_BinOp(self, node):
                # Bitwise operators conflict with VL syntax
                if isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor, 
                                       ast.LShift, ast.RShift)):
                    self.needs_passthrough = True
                self.generic_visit(node)
            
            def visit_UnaryOp(self, node):
                # Bitwise NOT (~) conflicts with VL syntax
                if isinstance(node.op, ast.Invert):
                    self.needs_passthrough = True
                self.generic_visit(node)
        
        checker = PassthroughChecker()
        checker.visit(node)
        return checker.needs_passthrough
    
    def convert(self, python_code: str) -> str:
        """
        Convert Python source code to VL
        
        Args:
            python_code: Python source code as string
            
        Returns:
            VL source code as string
        """
        try:
            self.original_source = python_code
            # Strip BOM for parsing, but preserve original bytes for passthrough
            clean_code = python_code.lstrip('\ufeff')
            self.source_code = clean_code
            tree = ast.parse(clean_code)
            return self._convert_module(tree)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
    
    def _convert_module(self, node: ast.Module) -> str:
        """Convert Python module to VL program"""
        # REMOVED: Blanket Base64 encoding fallback that was defeating VL conversion
        # This was causing 33% size increase on all Python files!
        
        # Reset state
        self.indent_level = 0
        self.output = []
        self.imports = []
        self.import_froms = []
        self.has_typing = False
        
        # First pass: collect imports
        for stmt in node.body:
            self._collect_import(stmt)
        
        # Handle module docstring (if present)
        body_start_idx = 0
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                # Module docstring - use passthrough to preserve formatting
                self._emit_module_docstring(node.body[0])
                self.output.append("")  # Blank line after docstring
                body_start_idx = 1
        
        # Emit dependencies (plain imports only)
        # Separate simple imports (no dots) from complex ones (with dots)
        simple_imports = [imp for imp in self.imports if '.' not in imp]
        dotted_imports = [imp for imp in self.imports if '.' in imp]
        
        if simple_imports:
            self.output.append(f"deps:[{','.join(simple_imports)}]")
            self.output.append("")
        
        # Emit dotted imports as py: passthrough (VL parser doesn't accept dots)
        for imp in dotted_imports:
            self.output.append(f"py: import {imp}")
        if dotted_imports:
            self.output.append("")
        
        # Emit from-imports as py: passthrough
        for module, names in self.import_froms:
            if names == ['*']:
                self.output.append(f"py: from {module} import *")
            else:
                self.output.append(f"py: from {module} import {', '.join(names)}")
        if self.import_froms:
            self.output.append("")
        
        # Second pass: convert statements
        for stmt in node.body[body_start_idx:]:
            if not isinstance(stmt, (ast.Import, ast.ImportFrom)):
                self._convert_statement(stmt)
        
        return '\n'.join(self.output)
    
    def _collect_import(self, node: ast.AST) -> None:
        """Collect import information"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                # Keep the module name as-is for deps (plain import X statement)
                module_name = alias.name
                self.imports.append(module_name)
                if alias.name == 'typing':
                    self.has_typing = True
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Handle relative imports (level > 0 means relative)
                if node.level > 0:
                    # Relative import: from .module import X
                    prefix = '.' * node.level
                    module_name = f"{prefix}{node.module}" if node.module else prefix
                else:
                    module_name = node.module
                
                # Collect import names for from X import Y, Z
                names = [alias.name for alias in node.names]
                self.import_froms.append((module_name, names))
                
                # DON'T add to self.imports - we'll use py: passthrough for from-imports
                # This avoids duplicate imports (deps: AND py:from)
                
                if node.module == 'typing':
                    self.has_typing = True
            elif node.level > 0:
                # from . import X (relative with no module name)
                names = [alias.name for alias in node.names]
                prefix = '.' * node.level
                self.import_froms.append((prefix, names))
    
    def _convert_statement(self, stmt: ast.AST) -> None:
        """Convert a Python statement to VL"""
        if self._statement_needs_passthrough(stmt):
            source = self._get_source(stmt) or ast.unparse(stmt)
            if not source.endswith('\n'):
                source += '\n'
            encoded = self._encode_python_passthrough(source)
            self.output.append(f"{self._indent()}py:{encoded}")
            return
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            source = self._get_source(stmt) or ast.unparse(stmt)
            if not source.endswith('\n'):
                source += '\n'
            encoded = self._encode_python_passthrough(source)
            self.output.append(f"{self._indent()}py:{encoded}")
            return
        if isinstance(stmt, ast.ClassDef):
            self._convert_class(stmt)
        elif isinstance(stmt, ast.FunctionDef):
            self._convert_function(stmt)
        elif isinstance(stmt, ast.Assign):
            self._convert_assignment(stmt)
        elif isinstance(stmt, ast.AugAssign):
            self._convert_aug_assignment(stmt)
        elif isinstance(stmt, ast.Expr):
            self._convert_expr_statement(stmt)
        elif isinstance(stmt, ast.If):
            self._convert_if(stmt)
        elif isinstance(stmt, ast.While):
            self._convert_while(stmt)
        elif isinstance(stmt, ast.For):
            self._convert_for(stmt)
        elif isinstance(stmt, ast.Return):
            self._convert_return(stmt)
        elif isinstance(stmt, ast.With):
            self._convert_with(stmt)
        elif isinstance(stmt, ast.Try):
            self._convert_try(stmt)
        elif isinstance(stmt, ast.Raise):
            self._convert_raise(stmt)
        elif isinstance(stmt, ast.Break):
            self._convert_break(stmt)
        elif isinstance(stmt, ast.Continue):
            self._convert_continue(stmt)
        elif isinstance(stmt, (ast.Import, ast.ImportFrom)):
            # Already handled in first pass
            pass
        elif isinstance(stmt, ast.Pass):
            # Pass statement - just skip it (VL doesn't need explicit pass)
            pass
        else:
            # Fallback: use Python passthrough
            self.output.append(f"{self._indent()}# TODO: Unsupported statement type: {type(stmt).__name__}")
    
    def _convert_class(self, node: ast.ClassDef) -> None:
        """Convert Python class to VL class"""
        # Check for class docstring
        class_docstring = None
        body_start = 0
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                class_docstring = node.body[0].value.value
                body_start = 1
        
        # Handle class decorators
        for decorator in node.decorator_list:
            decorator_str = self._convert_decorator(decorator)
            self.output.append(f"{self._indent()}{decorator_str}")
        
        # Class definition: class:name or class:name[BaseClass]
        class_line = f"{self._indent()}class:{node.name}"
        if node.bases:
            base_names = []
            has_dotted_base = False
            for base in node.bases:
                base_str = self._convert_expression(base)
                if '.' in base_str:
                    # VL parser doesn't support dotted names in class inheritance
                    has_dotted_base = True
                    break
                base_names.append(base_str)
            
            if has_dotted_base:
                # Use Python passthrough for entire class if base has dots
                self.output.append(f"{self._indent()}py:{ast.unparse(node)}")
                return
            else:
                class_line += f"[{','.join(base_names)}]"
        self.output.append(class_line)
        
        # Class body
        self.indent_level += 1
        
        # Add class docstring if present
        if class_docstring:
            first_line = class_docstring.strip().split('\n')[0].strip()
            self.output.append(f"{self._indent()}# @doc {first_line}|")
        
        body_to_convert = node.body[body_start:]
        for stmt in body_to_convert:
            if isinstance(stmt, ast.FunctionDef):
                self._convert_function(stmt, is_method=True)
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                # Skip standalone docstrings in class body (already handled)
                pass
            else:
                self._convert_statement(stmt)
        self.indent_level -= 1
        self.output.append("")  # blank line after class
    
    def _convert_decorator(self, node: ast.AST) -> str:
        """Convert a decorator node to VL @decorator syntax"""
        if isinstance(node, ast.Name):
            return f"@{node.id}"
        elif isinstance(node, ast.Call):
            func_name = self._convert_expression(node.func)
            if node.args:
                args_str = ",".join(self._convert_expression(arg) for arg in node.args)
                return f"@{func_name}({args_str})"
            else:
                return f"@{func_name}()"
        else:
            return f"@{self._convert_expression(node)}"
    
    def _convert_function(self, node: ast.FunctionDef, is_method: bool = False, is_nested: bool = False) -> None:
        """Convert Python function to VL function"""
        # Nested functions (defined inside other functions) should use Python passthrough
        # because VL doesn't support nested function definitions natively
        if is_nested:
            python_code = ast.unparse(node)
            single_line = python_code.replace('\n', '@@@').replace('    ', '@4@')
            self.output.append(f"{self._indent()}py:{single_line}")
            return
        
        # Check for @staticmethod or @classmethod
        is_static = False
        is_classmethod = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == 'staticmethod':
                    is_static = True
                elif decorator.id == 'classmethod':
                    is_classmethod = True
        
        # Handle decorators
        for decorator in node.decorator_list:
            decorator_str = self._convert_decorator(decorator)
            self.output.append(f"{self._indent()}{decorator_str}")
        
        # Extract function signature
        name = node.name
        param_specs = []  # List of "name:type" strings
        return_type = None
        
        # Build parameter name mapping: Python names -> VL names (may be renamed if conflicts with keywords)
        self.param_map = {}
        
        # VL keywords that conflict with common variable names
        VL_KEYWORDS = {'data', 'file', 'op', 'meta', 'deps', 'export', 'fn', 'ret', 'if', 'else', 'for', 'while', 'in', 'class', 'api', 'async', 'filter', 'map', 'parse', 'ui', 'state', 'props', 'on', 'render', 'sort', 'ffi', 'py'}
        
        # For methods, skip 'self' parameter (unless @staticmethod)
        args_to_process = node.args.args
        if is_method and not is_static and args_to_process:
            if args_to_process[0].arg == 'self':
                args_to_process = args_to_process[1:]
            elif args_to_process[0].arg == 'cls' and is_classmethod:
                args_to_process = args_to_process[1:]
        
        # Process parameters - get names and types
        for arg in args_to_process:
            param_name = arg.arg
            # Rename parameters that conflict with VL keywords
            if param_name in VL_KEYWORDS:
                vl_name = f"{param_name}_var"
            else:
                vl_name = param_name
            self.param_map[param_name] = vl_name
            
            # Check for type annotations
            if arg.annotation:
                param_type = self._convert_type_annotation(arg.annotation)
            else:
                param_type = 'any'
            
            # Store as "vl_name:type" pair (use renamed name if keyword conflict)
            param_specs.append(f"{vl_name}:{param_type}")
        
        # Check for return type annotation
        if node.returns:
            return_type = self._convert_type_annotation(node.returns)
        else:
            return_type = 'any'
        
        # Build VL function signature: F:name|name:type,name:type|returntype|
        # Note: The trailing | will be added based on whether it's single or multi-line
        if param_specs:
            params_str = ','.join(param_specs)
            signature = f"{self._indent()}F:{name}|{params_str}|{return_type}"
        else:
            signature = f"{self._indent()}F:{name}|{return_type}"
        
        # Temporarily store signature (we'll add it back later with proper formatting)
        self.output.append(signature)
        
        # Convert function body - collect body statements first
        self.indent_level += 1
        body_statements = []
        
        # Check for docstring as first statement
        docstring = None
        body_to_convert = node.body
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
                docstring = node.body[0].value.value
                body_to_convert = node.body[1:]  # Skip docstring in body
        
        # Add docstring as special comment if present
        if docstring:
            # Clean up docstring - replace newlines with spaces for single-line, or use first line
            doc_lines = docstring.strip().split('\n')
            first_line = doc_lines[0].strip()
            body_statements.append(f"{self._indent()}# @doc {first_line}|")
        
        for stmt in body_to_convert:
            # Capture the current output position
            start_len = len(self.output)
            # Check for nested function definitions - use passthrough
            if isinstance(stmt, ast.FunctionDef):
                self._convert_function(stmt, is_nested=True)
            else:
                self._convert_statement(stmt)
            # Get the statements that were added
            new_stmts = self.output[start_len:]
            body_statements.extend(new_stmts)
            # Remove them from output temporarily
            self.output = self.output[:start_len]
        
        self.indent_level -= 1
        
        # Handle empty body (abstract methods, pass-only functions)
        if len(body_statements) == 0:
            # Add trailing | for empty functions
            self.output[-1] = self.output[-1] + '|'
        # Check if we can do single-line format (only one statement)
        # But avoid single-line for methods with 'self' references as they need proper parsing
        elif len(body_statements) == 1 and not (is_method and any('self' in stmt for stmt in body_statements)):
            # Single-line format: F:name|types|type|statement
            stmt = body_statements[0].strip()
            # Add the statement to the signature line
            self.output[-1] = self.output[-1] + '|' + stmt
        else:
            # Multi-line format: F:name|types|type|
            #   stmt1|
            #   stmt2
            # The signature MUST have a trailing |
            # Then body statements follow, all but last ending with |
            self.output[-1] = self.output[-1] + '|'
            self.indent_level += 1
            for i, stmt in enumerate(body_statements):
                is_last = (i == len(body_statements) - 1)
                if not is_last:
                    # Not the last statement - must end with |
                    if not stmt.rstrip().endswith('|'):
                        stmt = stmt.rstrip() + '|'
                else:
                    # Last statement - must NOT end with | (this terminates the function)
                    if stmt.rstrip().endswith('|'):
                        stmt = stmt.rstrip()[:-1]
                self.output.append(stmt)
            self.indent_level -= 1
        self.param_map = {}  # Clear mapping after function
        self.output.append("")
        self.output.append("")  # Extra blank line to help parser
    
    def _convert_assignment(self, node: ast.Assign) -> None:
        """Convert Python assignment to VL"""
        if len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                var_name = target.id
                # Avoid VL keyword conflicts - use comprehensive keyword list
                VL_KEYWORDS = {'data', 'file', 'op', 'meta', 'deps', 'export', 'fn', 'ret', 'if', 'else', 'for', 'while', 'in', 'class', 'api', 'async', 'filter', 'map', 'parse', 'ui', 'state', 'props', 'on', 'render', 'sort', 'ffi', 'py', 'i', 'o', 'v', 't', 'item'}
                if var_name in VL_KEYWORDS:
                    new_name = f'{var_name}_var'
                    self.renamed_vars[var_name] = new_name
                    var_name = new_name
                value = self._convert_expression(node.value)
                self.output.append(f"{self._indent()}{var_name}={value}")
            elif isinstance(target, ast.Subscript):
                # Array/object indexing
                obj = self._convert_expression(target.value)
                index = self._convert_expression(target.slice)
                value = self._convert_expression(node.value)
                self.output.append(f"{self._indent()}{obj}[{index}]={value}")
            elif isinstance(target, ast.Tuple):
                # Tuple unpacking: a, b, c = value
                var_names = []
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        var_names.append(elt.id)
                    else:
                        # Complex unpacking not supported - fall back to Python passthrough
                        self.output.append(f"{self._indent()}py:{ast.unparse(node)}")
                        return
                value = self._convert_expression(node.value)
                # Generate individual assignments by indexing into the result
                # Store result in temp variable first
                temp_var = f"_tmp_{id(node)}"
                self.output.append(f"{self._indent()}{temp_var}={value}")
                for idx, var_name in enumerate(var_names):
                    self.output.append(f"{self._indent()}{var_name}={temp_var}[{idx}]")
            else:
                # Fallback for unsupported assignment targets
                self.output.append(f"{self._indent()}# TODO: Unsupported assignment target: {type(target).__name__}")
    
    def _convert_aug_assignment(self, node: ast.AugAssign) -> None:
        """Convert augmented assignment (+=, -=, etc.)"""
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            # Use renamed variable if it exists
            if var_name in self.renamed_vars:
                var_name = self.renamed_vars[var_name]
            op = self._convert_operator(node.op)
            value = self._convert_expression(node.value)
            self.output.append(f"{self._indent()}{var_name}{op}={value}")
    
    def _convert_expr_statement(self, node: ast.Expr) -> None:
        """Convert expression statement"""
        # Check if this is a docstring (standalone string constant)
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Convert docstrings to comments
            docstring = node.value.value
            # Split into lines and add as comments
            lines = docstring.strip().split('\n')
            for line in lines:
                if line.strip():  # Skip empty lines
                    self.output.append(f"{self._indent()}# {line.strip()}")
            return
        
        expr = self._convert_expression(node.value)
        self.output.append(f"{self._indent()}{expr}")
    
    def _convert_if(self, node: ast.If) -> None:
        """Convert if statement to VL"""
        # Check if this is a simple if-return pattern (can be inline)
        if (len(node.body) == 1 and isinstance(node.body[0], ast.Return) and
            len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Return)):
            # Convert to inline ternary: if:condition?value:other
            condition = self._convert_expression(node.test)
            true_val = self._convert_expression(node.body[0].value) if node.body[0].value else ''
            false_val = self._convert_expression(node.orelse[0].value) if node.orelse[0].value else ''
            self.output.append(f"{self._indent()}ret:if:{condition}?{true_val}:{false_val}")
        else:
            # Multi-line if/else block form
            condition = self._convert_expression(node.test)
            # Only add trailing | if there are multiple statements in the body
            has_multiple = len(node.body) > 1
            if has_multiple:
                self.output.append(f"{self._indent()}if:{condition}|")
            else:
                self.output.append(f"{self._indent()}if:{condition}")
            
            self.indent_level += 1
            for i, stmt in enumerate(node.body):
                self._convert_statement(stmt)
                # Add pipe after each statement except the last
                if i < len(node.body) - 1 and self.output and not self.output[-1].rstrip().endswith('|'):
                    self.output[-1] = self.output[-1].rstrip() + '|'
            self.indent_level -= 1
            
            if node.orelse:
                # Only add trailing | if there are multiple statements in else
                has_multiple_else = len(node.orelse) > 1
                if has_multiple_else:
                    self.output.append(f"{self._indent()}else:|")
                else:
                    self.output.append(f"{self._indent()}else:")
                self.indent_level += 1
                for i, stmt in enumerate(node.orelse):
                    self._convert_statement(stmt)
                    # Add pipe after each statement except the last
                    if i < len(node.orelse) - 1 and self.output and not self.output[-1].rstrip().endswith('|'):
                        self.output[-1] = self.output[-1].rstrip() + '|'
                self.indent_level -= 1
    
    def _convert_while(self, node: ast.While) -> None:
        """Convert while loop to VL"""
        condition = self._convert_expression(node.test)
        # Multi-line while needs pipe
        self.output.append(f"{self._indent()}while:{condition}|")
        
        self.indent_level += 1
        for stmt in node.body:
            self._convert_statement(stmt)
        self.indent_level -= 1
    
    def _convert_for(self, node: ast.For) -> None:
        """Convert for loop to VL"""
        if isinstance(node.target, ast.Name):
            original_name = node.target.id
            var_name = self._safe_var_name(original_name)
            iterable = self._convert_expression(node.iter)
            # VL syntax: for:var,iterable| (multi-line needs pipe)
            self.output.append(f"{self._indent()}for:{var_name},{iterable}|")
            
            # Save current renamed_vars state
            old_renamed = self.renamed_vars.copy()
            # Add the loop variable mapping (only if it was renamed)
            if var_name != original_name:
                self.renamed_vars[original_name] = var_name
            
            self.indent_level += 1
            for stmt in node.body:
                self._convert_statement(stmt)
            self.indent_level -= 1
            
            # Restore renamed_vars state after loop
            self.renamed_vars = old_renamed
    
    def _convert_return(self, node: ast.Return) -> None:
        """Convert return statement"""
        if node.value:
            value = self._convert_expression(node.value)
            self.output.append(f"{self._indent()}ret:{value}")
        else:
            self.output.append(f"{self._indent()}ret:")
    
    def _convert_expression(self, expr: ast.AST) -> str:
        """Convert Python expression to VL"""
        if isinstance(expr, ast.Constant):
            return self._convert_constant(expr)
        elif isinstance(expr, ast.Name):
            # Check if this is a parameter name that needs mapping
            if expr.id in self.param_map:
                return self.param_map[expr.id]
            # Check if this is a renamed variable
            if expr.id in self.renamed_vars:
                return self.renamed_vars[expr.id]
            return expr.id
        elif isinstance(expr, ast.BinOp):
            return self._convert_binop(expr)
        elif isinstance(expr, ast.Compare):
            return self._convert_compare(expr)
        elif isinstance(expr, ast.BoolOp):
            return self._convert_boolop(expr)
        elif isinstance(expr, ast.UnaryOp):
            return self._convert_unaryop(expr)
        elif isinstance(expr, ast.Call):
            return self._convert_call(expr)
        elif isinstance(expr, ast.List):
            return self._convert_list(expr)
        elif isinstance(expr, ast.Set):
            return self._convert_set(expr)
        elif isinstance(expr, ast.Dict):
            return self._convert_dict(expr)
        elif isinstance(expr, ast.Subscript):
            return self._convert_subscript(expr)
        elif isinstance(expr, ast.ListComp):
            return self._convert_list_comprehension(expr)
        elif isinstance(expr, ast.DictComp):
            return self._convert_dict_comprehension(expr)
        elif isinstance(expr, ast.GeneratorExp):
            return self._convert_generator_expression(expr)
        elif isinstance(expr, ast.Attribute):
            return self._convert_attribute(expr)
        elif isinstance(expr, ast.JoinedStr):
            # F-strings: convert to string concatenation
            return self._convert_joinedstr(expr)
        elif isinstance(expr, ast.IfExp):
            # Ternary operator: a if cond else b
            return self._convert_ifexp(expr)
        elif isinstance(expr, ast.Tuple):
            # Tuples not directly supported - convert to array
            elements = [self._convert_expression(e) for e in expr.elts]
            return f"[{','.join(elements)}]"
        elif isinstance(expr, ast.Lambda):
            # Lambdas: convert to Python lambda expression
            return self._convert_lambda(expr)
        else:
            # Fallback for truly unsupported expressions
            # Use repr only for debugging - actual compilation will fail
            return f"# TODO: Unsupported expression: {type(expr).__name__}"
    
    def _convert_constant(self, node: ast.Constant) -> str:
        """Convert constant value"""
        value = node.value
        if isinstance(value, str):
            # For all strings, escape for VL single-line format
            # Escape backslashes first, then quotes, then control chars
            # Also escape ${ since VL uses it for string interpolation
            escaped = value.replace('\\', '\\\\')
            escaped = escaped.replace('${', '\\${')  # Escape interpolation syntax
            escaped = escaped.replace("'", "\\'")
            escaped = escaped.replace('\n', '\\n')
            escaped = escaped.replace('\r', '\\r')
            escaped = escaped.replace('\t', '\\t')
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif value is None:
            return 'null'
        elif isinstance(value, float):
            # Convert scientific notation to explicit decimal to avoid VL parser issues
            # e.g., 1e-06 becomes 0.000001
            str_val = str(value)
            if 'e' in str_val or 'E' in str_val:
                # Format as decimal (never scientific notation)
                formatted = format(value, '.15f').rstrip('0').rstrip('.')
                return formatted if formatted else '0'
            return str(value)
        else:
            return str(value)
    
    def _convert_binop(self, node: ast.BinOp) -> str:
        """Convert binary operation"""
        # Handle power operator specially - VL doesn't support **
        if isinstance(node.op, ast.Pow):
            left = self._convert_expression(node.left)
            right = self._convert_expression(node.right)
            return f"pow({left},{right})"
        
        left = self._convert_expression(node.left)
        right = self._convert_expression(node.right)
        op = self._convert_operator(node.op)
        return f"{left}{op}{right}"
    
    def _convert_compare(self, node: ast.Compare) -> str:
        """Convert comparison"""
        left = self._convert_expression(node.left)
        
        # Handle 'in' operator
        if isinstance(node.ops[0], ast.In):
            right = self._convert_expression(node.comparators[0])
            # VL syntax: in:element,container
            return f"in:{left},{right}"
        
        # Handle 'not in' operator
        if isinstance(node.ops[0], ast.NotIn):
            right = self._convert_expression(node.comparators[0])
            # VL syntax: !in:element,container
            return f"!in:{left},{right}"
        
        op = self._convert_comparator(node.ops[0])
        right = self._convert_expression(node.comparators[0])
        return f"{left}{op}{right}"
    
    def _convert_boolop(self, node: ast.BoolOp) -> str:
        """Convert boolean operation (and/or)"""
        op = '&&' if isinstance(node.op, ast.And) else '||'
        values = [self._convert_expression(v) for v in node.values]
        return f"({op.join(values)})"
    
    def _convert_unaryop(self, node: ast.UnaryOp) -> str:
        """Convert unary operation"""
        operand = self._convert_expression(node.operand)
        if isinstance(node.op, ast.Not):
            return f"!{operand}"
        elif isinstance(node.op, ast.USub):
            return f"-{operand}"
        elif isinstance(node.op, ast.UAdd):
            return f"+{operand}"
        return operand
    
    def _convert_call(self, node: ast.Call) -> str:
        """Convert function call"""
        # Check if this is a method call (obj.method())
        if isinstance(node.func, ast.Attribute):
            # Method calls and module functions have issues with VL : syntax
            # Use Python passthrough for all attribute-based calls
            return f"py:{ast.unparse(node)}"
        else:
            # Regular function call
            func_name = self._convert_expression(node.func)
            args = [self._convert_expression(arg) for arg in node.args]
            
            if args:
                args_str = ','.join(args)
                return f"{func_name}({args_str})"
            else:
                return f"{func_name}()"
    
    def _convert_list(self, node: ast.List) -> str:
        """Convert list literal"""
        elements = [self._convert_expression(e) for e in node.elts]
        return f"[{','.join(elements)}]"
    
    def _convert_set(self, node: ast.Set) -> str:
        """Convert set literal to list (VL doesn't have native set type)"""
        # Convert set to list since VL doesn't have set literals
        # Usage: {'a', 'b', 'c'} -> ['a', 'b', 'c']
        elements = [self._convert_expression(e) for e in node.elts]
        return f"[{','.join(elements)}]"
    
    def _convert_dict(self, node: ast.Dict) -> str:
        """Convert dict literal"""
        # VL/Python keywords that shouldn't be used as unquoted dict keys
        vl_keywords = {'if', 'else', 'for', 'while', 'ret', 'and', 'or', 'not', 'in', 
                       'class', 'def', 'return', 'import', 'from', 'as', 'with', 'try', 
                       'except', 'finally', 'async', 'await', 'fn', 'meta', 'deps'}
        
        pairs = []
        for key, value in zip(node.keys, node.values):
            # Handle dict unpacking (**kwargs) - key is None when unpacking
            if key is None:
                # This is **expr - use py: passthrough for the spread
                spread_expr = self._convert_expression(value)
                # Skip dict unpacking in VL object literals - not directly supported
                # Instead, we'll merge it in Python later
                continue
            
            # Check if key is a string constant that can be an identifier
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                # Use identifier form if it's a valid identifier and not a keyword
                key_str = key.value
                if key_str.isidentifier() and not key_str.startswith('_') and key_str.lower() not in vl_keywords:
                    # Valid identifier - use without quotes
                    value_str = self._convert_expression(value)
                    pairs.append(f"{key_str}:{value_str}")
                else:
                    # Not a valid identifier or is a keyword - keep as string
                    key_str = self._convert_expression(key)
                    value_str = self._convert_expression(value)
                    pairs.append(f"{key_str}:{value_str}")
            else:
                # Non-string key - convert normally
                key_str = self._convert_expression(key)
                value_str = self._convert_expression(value)
                pairs.append(f"{key_str}:{value_str}")
        return f"{{{','.join(pairs)}}}"
    
    def _convert_subscript(self, node: ast.Subscript) -> str:
        """Convert subscript (array/object access)"""
        value = self._convert_expression(node.value)
        
        # Handle slice notation (e.g., array[1:3], array[:5], array[2:])
        if isinstance(node.slice, ast.Slice):
            # VL doesn't have native Python slice syntax [start:end]
            # Convert to list slicing function call or Python passthrough
            lower = self._convert_expression(node.slice.lower) if node.slice.lower else 'None'
            upper = self._convert_expression(node.slice.upper) if node.slice.upper else 'None'
            
            if node.slice.step:
                # With step: use list() wrapper with Python slice
                step = self._convert_expression(node.slice.step)
                return f"list({value})[slice({lower},{upper},{step})]"
            else:
                # Simple slice: use list() wrapper with Python slice  
                return f"list({value})[slice({lower},{upper})]"
        
        # Handle division in subscript
        if isinstance(node.slice, ast.BinOp):
            index = self._convert_expression(node.slice)
            # Wrap complex expressions in parens
            return f"{value}[{index}]"
        index = self._convert_expression(node.slice)
        return f"{value}[{index}]"
    
    def _convert_list_comprehension(self, node: ast.ListComp) -> str:
        """Convert list comprehension to Python passthrough (VL parser doesn't support Python for keyword in expressions)"""
        # Use ast.unparse for exact Python comprehension syntax
        return f"py:[{ast.unparse(node)}]"
    
    def _convert_dict_comprehension(self, node: ast.DictComp) -> str:
        """Convert dict comprehension to Python passthrough (VL parser doesn't support Python for keyword in expressions)"""
        # Use ast.unparse for exact Python comprehension syntax
        return f"py:{{{ast.unparse(node)}}}"
    
    def _convert_generator_expression(self, node: ast.GeneratorExp) -> str:
        """Convert generator expression to Python passthrough"""
        # Use ast.unparse for exact Python generator syntax
        return f"py:({ast.unparse(node)})"
    
    def _convert_lambda(self, node: ast.Lambda) -> str:
        """Convert lambda to Python passthrough (VL parser has issues with lambda syntax)"""
        # Use ast.unparse for exact Python lambda syntax
        return f"py:{ast.unparse(node)}"
    
    def _convert_attribute(self, node: ast.Attribute) -> str:
        """Convert attribute access (e.g., obj.attr)"""
        value = self._convert_expression(node.value)
        attr = node.attr
        return f"{value}.{attr}"
    
    def _convert_joinedstr(self, node: ast.JoinedStr) -> str:
        """Convert f-string to VL string interpolation or concatenation"""
        # Check if we have any string parts that contain quotes
        has_quotes = any(
            isinstance(v, ast.Constant) and isinstance(v.value, str) and "'" in v.value
            for v in node.values
        )
        
        # If string parts contain quotes, use concatenation instead of interpolation
        # to avoid escaping issues with ${} syntax
        if has_quotes:
            parts = []
            for value in node.values:
                if isinstance(value, ast.Constant):
                    # String literal part - use normal string escaping
                    parts.append(self._convert_constant(value))
                elif isinstance(value, ast.FormattedValue):
                    # Expression part - convert to string
                    expr = self._convert_expression(value.value)
                    parts.append(f"str({expr})")
            return '+'.join(parts) if parts else "''"
        else:
            # No quotes - safe to use VL ${} interpolation
            result = "'"
            for value in node.values:
                if isinstance(value, ast.Constant):
                    # String literal part
                    text = value.value
                    # Only escape backslashes and newlines, not quotes
                    text = text.replace('\\', '\\\\')
                    text = text.replace('\n', '\\n')
                    text = text.replace('\r', '\\r')
                    text = text.replace('\t', '\\t')
                    result += text
                elif isinstance(value, ast.FormattedValue):
                    # {expression} part - use VL ${} syntax
                    expr = self._convert_expression(value.value)
                    result += f"${{{expr}}}"
            result += "'"
            return result
    
    def _convert_ifexp(self, node: ast.IfExp) -> str:
        """Convert ternary operator (a if cond else b)"""
        test = self._convert_expression(node.test)
        body = self._convert_expression(node.body)
        orelse = self._convert_expression(node.orelse)
        # VL ternary: if:test?body:orelse
        return f"if:{test}?{body}:{orelse}"
    
    def _convert_operator(self, op: ast.AST) -> str:
        """Convert operator to VL syntax"""
        if isinstance(op, ast.Add):
            return '+'
        elif isinstance(op, ast.Sub):
            return '-'
        elif isinstance(op, ast.Mult):
            return '*'
        elif isinstance(op, ast.Div):
            return '/'
        elif isinstance(op, ast.FloorDiv):
            # Floor division - wrap in parens to avoid ambiguity
            return '//'
        elif isinstance(op, ast.Mod):
            return '%'
        elif isinstance(op, ast.Pow):
            return '**'
        else:
            return '?'
    
    def _convert_comparator(self, op: ast.AST) -> str:
        """Convert comparison operator"""
        if isinstance(op, ast.Eq):
            return '=='
        elif isinstance(op, ast.NotEq):
            return '!='
        elif isinstance(op, ast.Lt):
            return '<'
        elif isinstance(op, ast.LtE):
            return '<='
        elif isinstance(op, ast.Gt):
            return '>'
        elif isinstance(op, ast.GtE):
            return '>='
        elif isinstance(op, ast.Is):
            # Python 'is' for identity - use == in VL
            return '=='
        elif isinstance(op, ast.IsNot):
            # Python 'is not' - use != in VL
            return '!='
        else:
            return '?'
    
    def _convert_type_annotation(self, annotation: ast.AST) -> str:
        """Convert Python type annotation to VL type (single-char format)"""
        if isinstance(annotation, ast.Name):
            type_map = {
                'str': 'S',
                'int': 'I',
                'float': 'N',
                'bool': 'B',
                'list': 'A',
                'dict': 'O',
                'Any': 'any',
                'None': 'V',
                'void': 'V'
            }
            return type_map.get(annotation.id, 'any')
        elif isinstance(annotation, ast.Subscript):
            # Handle List[T], Dict[K, V], etc.
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ['List', 'list']:
                    return 'A'
                elif annotation.value.id in ['Dict', 'dict']:
                    return 'O'
        return 'any'
    
    def _convert_with(self, node: ast.With) -> None:
        """Convert with statement using py: passthrough - use @@@ as line separator"""
        # Convert the entire with block to Python code
        python_code = ast.unparse(node)
        # Use @@@ as line separator (@ is a valid VL token)
        single_line = python_code.replace('\n', '@@@').replace('    ', '@4@')
        self.output.append(f"{self._indent()}py:{single_line}")
    
    def _convert_try(self, node: ast.Try) -> None:
        """Convert try/except statement using py: passthrough - use @@@ as line separator with @indent@ markers"""
        # Convert the entire try block to Python code
        python_code = ast.unparse(node)
        # Use @@@ as line separator and @4@ for 4-space indentation
        single_line = python_code.replace('\n', '@@@').replace('    ', '@4@')
        self.output.append(f"{self._indent()}py:{single_line}")
    
    def _convert_raise(self, node: ast.Raise) -> None:
        """Convert raise statement using py: passthrough"""
        python_code = ast.unparse(node)
        self.output.append(f"{self._indent()}py:{python_code}")
    
    def _convert_break(self, node: ast.Break) -> None:
        """Convert break statement using py: passthrough"""
        self.output.append(f"{self._indent()}py:break")
    
    def _convert_continue(self, node: ast.Continue) -> None:
        """Convert continue statement using py: passthrough"""
        self.output.append(f"{self._indent()}py:continue")
    
    def _embed_python_block(self, python_code: str) -> None:
        """Embed a block of Python code in VL using Python passthrough"""
        # Split into lines and add proper indentation
        lines = python_code.split('\n')
        for line in lines:
            if line.strip():  # Skip empty lines
                self.output.append(f"{self._indent()}{line}")
    
    def _indent(self) -> str:
        """Get current indentation"""
        return '  ' * self.indent_level


def convert_python_to_vl(python_code: str) -> str:
    """
    Convenience function to convert Python code to VL
    
    Args:
        python_code: Python source code as string
        
    Returns:
        VL source code as string
    """
    converter = PythonToVLConverter()
    return converter.convert(python_code)


if __name__ == '__main__':
    # Test the converter
    test_code = """
def add(x: int, y: int) -> int:
    return x + y

def greet(name: str) -> str:
    message = 'Hello, ' + name
    return message

result = add(5, 3)
print(result)
"""
    
    converter = PythonToVLConverter()
    vl_code = converter.convert(test_code)
    print(vl_code)
