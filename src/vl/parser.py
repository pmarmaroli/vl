"""
VL Parser

Converts tokens from the lexer into an Abstract Syntax Tree (AST).
Uses recursive descent parsing with operator precedence.

Parser Structure:
- parse() -> Program
- parse_statement() -> Statement
- parse_expression() -> Expression
    - parse_logical -> parse_comparison -> parse_term -> parse_factor
    - parse_unary -> parse_postfix -> parse_primary

Key Design Decisions:
- Infix operators (+, -, *, /, ==, etc.) parsed with precedence climbing
- Pipeline operations (|filter:|map:) parsed as postfix operations
- Function expressions allowed in object literals for method definitions
"""

import ast
import base64
from typing import List, Optional, Union, Tuple

# Support both package and standalone usage
try:
    from .lexer import Token, TokenType, tokenize
    from .ast_nodes import *
    from .errors import ParseError, SourceLocation
except ImportError:
    from lexer import Token, TokenType, tokenize
    from ast_nodes import *
    from errors import ParseError, SourceLocation


class Parser:
    """
    VL Parser - converts tokens to AST
    
    Uses recursive descent with operator precedence for expression parsing.
    """
    
    # Token types that represent pipeline operations
    PIPELINE_OPS = frozenset([TokenType.FILTER, TokenType.MAP, TokenType.PARSE])
    
    # Token types that can start a statement
    STATEMENT_STARTERS = frozenset([
        TokenType.FN, TokenType.VAR, TokenType.RET, TokenType.IF,
        TokenType.FOR, TokenType.WHILE, TokenType.API, TokenType.ASYNC,
        TokenType.UI, TokenType.DATA, TokenType.FILE, TokenType.AT,
        TokenType.IDENTIFIER
    ])
    
    def __init__(self, tokens: List[Token], source: str = ""):
        self.tokens = tokens
        self.source = source
        self.pos = 0
        self.current_token = self.tokens[0] if tokens else None
        # Flag to prevent nested pipeline parsing
        self._in_pipeline = False
    
    # ===== Error Handling =====
    
    def error(self, message: str, hints: List[str] = None) -> ParseError:
        """Create parse error with current token location and context"""
        if self.current_token:
            loc = SourceLocation(self.current_token.line, self.current_token.column)
            source_line = self._get_source_line(self.current_token.line)
        else:
            loc = SourceLocation(1, 1)
            source_line = ""
        return ParseError(message, location=loc, source_line=source_line, hints=hints or [])
    
    def _get_source_line(self, line_num: int) -> str:
        """Extract a specific line from source"""
        if not self.source:
            return ""
        lines = self.source.split('\n')
        return lines[line_num - 1] if 0 < line_num <= len(lines) else ""
    
    # ===== Token Navigation =====
    
    # ===== Token Navigation =====
    
    def peek(self, offset: int = 0) -> Optional[Token]:
        """Look ahead at token without consuming"""
        pos = self.pos + offset
        return self.tokens[pos] if pos < len(self.tokens) else None
    
    def advance(self) -> Token:
        """Move to next token, returning the current one"""
        token = self.current_token
        self.pos += 1
        self.current_token = self.tokens[self.pos] if self.pos < len(self.tokens) else None
        return token
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        return self.current_token and self.current_token.type in token_types
    
    def expect(self, token_type: TokenType) -> Token:
        """Consume token of expected type or raise error with helpful message"""
        if self.match(token_type):
            return self.advance()
        
        got = self.current_token.type.name if self.current_token else 'EOF'
        hints = self._get_expect_hints(token_type, got)
        raise self.error(f"Expected {token_type.name}, got {got}", hints)
    
    def _get_expect_hints(self, expected: TokenType, got: str) -> List[str]:
        """Generate context-specific hints for expect() errors"""
        hints = []
        hint_map = {
            TokenType.PIPE: [
                "VL uses | to separate statements and clauses",
                "Example: F:name|I|I|ret:value"
            ],
            TokenType.COLON: [
                "VL uses : after keywords",
                "Example: F:name, v:var, ret:value"
            ],
            TokenType.IDENTIFIER: [
                "Expected a variable or function name"
            ],
            TokenType.RPAREN: ["Check for matching parentheses"],
            TokenType.RBRACE: ["Check for matching braces"],
            TokenType.RBRACKET: ["Check for matching brackets"],
        }
        hints = hint_map.get(expected, [])
        if expected == TokenType.IDENTIFIER and got in ("INPUT", "OUTPUT", "DATA", "FILTER", "MAP"):
            hints.append(f"'{got}' is a reserved keyword, try a different name")
        return hints
    
    def skip_newlines(self):
        """Skip newline tokens"""
        while self.match(TokenType.NEWLINE):
            self.advance()
    
    def _is_pipeline_lookahead(self) -> bool:
        """Check if current PIPE token is followed by a pipeline operation"""
        next_tok = self.peek(1)
        return next_tok and next_tok.type in self.PIPELINE_OPS
    
    def parse(self) -> Program:
        """Parse entire VL program"""
        self.skip_newlines()
        module_docstring = None
        leading_statements: List[Statement] = []

        # Capture leading Python passthrough as module docstring if it is a string literal
        if self.match(TokenType.PY):
            possible_doc = self.parse_python_stmt()
            decoded = self._decode_python_passthrough(possible_doc.code).strip()
            try:
                literal = ast.literal_eval(decoded)
            except Exception:
                literal = None
            if isinstance(literal, str):
                module_docstring = literal
            else:
                leading_statements.append(possible_doc)
            self.skip_newlines()
        
        # Parse metadata (optional)
        metadata = None
        if self.match(TokenType.META):
            metadata = self.parse_metadata()
            self.skip_newlines()
        
        # Parse dependencies (optional)
        dependencies = None
        if self.match(TokenType.DEPS):
            dependencies = self.parse_dependencies()
            self.skip_newlines()
        
        # Parse statements
        statements = []
        loop_count = 0
        max_loops = 1000  # Safety limit
        while (self.current_token and self.current_token.type not in (TokenType.EXPORT, TokenType.EOF) and 
               loop_count < max_loops):
            loop_count += 1
            
            if self.current_token.type == TokenType.NEWLINE:
                self.skip_newlines()
                continue
            
            # Handle PIPE separator at top level (e.g. v:x=1|v:y=2)
            if self.match(TokenType.PIPE):
                self.advance()
                continue
            
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
            self.skip_newlines()
        
        # Parse export (optional)
        export = None
        if self.match(TokenType.EXPORT):
            export = self.parse_export()
        
        if module_docstring is None:
            module_docstring, statements = self._extract_module_docstring(statements)
        statements = leading_statements + statements
        
        return Program(
            line=1, column=1,
            metadata=metadata,
            dependencies=dependencies,
            module_docstring=module_docstring,
            statements=statements,
            export=export
        )

    def _extract_module_docstring(self, statements: List[Statement]) -> Tuple[Optional[str], List[Statement]]:
        """Detect leading Python passthrough docstring and lift to Program field."""
        if not statements or not isinstance(statements[0], PythonStmt):
            return None, statements
        decoded = self._decode_python_passthrough(statements[0].code).strip()
        try:
            literal = ast.literal_eval(decoded)
        except Exception:
            literal = None
        if isinstance(literal, str):
            return literal, statements[1:]
        return None, statements

    def _decode_python_passthrough(self, code: str) -> str:
        """Reverse the py: passthrough markers back to Python code."""
        if code.startswith('__RAW_B64__(') and code.endswith(')'):
            inner = code[len('__RAW_B64__('):-1]
            try:
                payload = ast.literal_eval(inner)
                return base64.b64decode(payload).decode('utf-8', errors='replace')
            except Exception:
                return code
        if code.startswith('__RAW__(') and code.endswith(')'):
            inner = code[len('__RAW__('):-1]
            try:
                return ast.literal_eval(inner)
            except Exception:
                return code
        # Only expand marker placeholders when the code is still a single line
        if '\n' not in code and ('@@@' in code or '@4@' in code):
            return code.replace('@4@', '    ').replace('@@@', '\n')
        return code
    
    def parse_metadata(self) -> Metadata:
        """Parse: meta:name,type,target"""
        token = self.expect(TokenType.META)
        self.expect(TokenType.COLON)
        
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COMMA)
        
        prog_type = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COMMA)
        
        target = self.expect(TokenType.IDENTIFIER).value
        
        return Metadata(
            line=token.line, column=token.column,
            name=name,
            program_type=prog_type,
            target_language=target
        )
    
    def parse_dependencies(self) -> Dependencies:
        """Parse: deps:lib or deps:[lib1,lib2]"""
        token = self.expect(TokenType.DEPS)
        self.expect(TokenType.COLON)
        
        deps = []
        
        if self.match(TokenType.LBRACKET):
            # Array of dependencies
            self.advance()
            while not self.match(TokenType.RBRACKET):
                deps.append(self.expect(TokenType.IDENTIFIER).value)
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACKET)
        else:
            # Single dependency
            deps.append(self.expect(TokenType.IDENTIFIER).value)
        
        return Dependencies(
            line=token.line, column=token.column,
            dependencies=deps
        )
    
    def parse_export(self) -> Export:
        """Parse: export:name"""
        token = self.expect(TokenType.EXPORT)
        self.expect(TokenType.COLON)
        name = self.expect(TokenType.IDENTIFIER).value
        
        return Export(
            line=token.line, column=token.column,
            name=name
        )
    
    def parse_statement(self) -> Optional[Statement]:
        """Parse a single statement"""
        if not self.current_token:
            return None
        
        # If we hit ELSE, it belongs to parent if block, not a statement
        if self.match(TokenType.ELSE):
            return None
        
        # Decorator (can precede function or class)
        if self.match(TokenType.AT):
            return self.parse_decorated_statement()
        
        # Class definition
        if self.match(TokenType.CLASS):
            return self.parse_class_def()
        
        # Function definition
        if self.match(TokenType.FN):
            return self.parse_function_def()
        
        # Variable definition (explicit v: prefix)
        elif self.match(TokenType.VAR):
            return self.parse_variable_def()
        
        # Implicit variable definition: name=value (no v: prefix)
        # Also handles compound assignment: name+=value, name-=value, etc.
        # Also handles subscript assignment: arr[i]=value, self.prop=value
        # Also handles implicit function calls: func(args)
        elif self.match(TokenType.IDENTIFIER, TokenType.SELF):
            next_tok = self.peek(1)
            # Simple assignment or compound assignment on variable
            if next_tok and next_tok.type in (TokenType.EQUALS, TokenType.PLUS_EQUALS, 
                                               TokenType.MINUS_EQUALS, TokenType.TIMES_EQUALS,
                                               TokenType.DIV_EQUALS):
                return self.parse_implicit_variable_or_compound()
            # Subscript or member access assignment: arr[idx]=value or obj.prop=value or self.prop=value
            elif next_tok and next_tok.type in (TokenType.LBRACKET, TokenType.DOT):
                # Need to parse full expression to see if it's assignment
                saved_pos = self.pos
                saved_token = self.current_token
                # Parse the full left-hand side expression
                expr = self.parse_expression()
                # Check if this is an assignment
                if self.match(TokenType.EQUALS, TokenType.PLUS_EQUALS, 
                              TokenType.MINUS_EQUALS, TokenType.TIMES_EQUALS, TokenType.DIV_EQUALS):
                    op_token = self.advance()  # consume assignment operator
                    value = self.parse_expression()
                    # Create appropriate statement

                    if op_token.type == TokenType.EQUALS:
                        return VariableDef(
                            line=expr.line, column=expr.column,
                            name=expr,  # Keep as Expression for subscript/member access
                            type_annotation=None,
                            value=value
                        )
                    else:
                        # Compound assignment
                        op_map = {
                            TokenType.PLUS_EQUALS: '+',
                            TokenType.MINUS_EQUALS: '-',
                            TokenType.TIMES_EQUALS: '*',
                            TokenType.DIV_EQUALS: '/'
                        }
                        return CompoundAssignment(
                            line=expr.line, column=expr.column,
                            name=f"{self._expr_to_string(expr)}",
                            operator=op_map[op_token.type],
                            value=value
                        )
                else:
                    # Not assignment - this is an expression statement (e.g., method call)
                    # Keep the parsed expression and treat as DirectCall

                    return DirectCall(
                        line=expr.line, column=expr.column,
                        function=expr
                    )
            # Implicit function call: func(args) - but only if followed by (
            elif next_tok and next_tok.type == TokenType.LPAREN:
                return self.parse_implicit_call()
            # If we get here, it's an IDENTIFIER we don't know how to handle
            # This shouldn't happen in valid VL code
            else:
                raise self.error(f"Unexpected identifier pattern - identifier not followed by assignment, subscript, member access, or call")
        
        # Return statement
        elif self.match(TokenType.RET):
            return self.parse_return_stmt()
        
        # If statement (conditional)
        elif self.match(TokenType.IF):
            return self.parse_if_stmt()
        
        # For loop
        elif self.match(TokenType.FOR):
            return self.parse_for_loop()
        
        # While loop
        elif self.match(TokenType.WHILE):
            return self.parse_while_loop()
        
        # API call
        elif self.match(TokenType.API, TokenType.ASYNC):
            return self.parse_api_call()
        
        # UI component
        elif self.match(TokenType.UI):
            return self.parse_ui_component()
        
        # Data pipeline
        elif self.match(TokenType.DATA):
            return self.parse_data_pipeline()
        
        # File operation
        elif self.match(TokenType.FILE):
            return self.parse_file_operation()
        
        # Python passthrough statement (py:...)
        elif self.match(TokenType.PY):
            return self.parse_python_stmt()
        
        else:
            raise self.error(f"Unexpected token: {self.current_token.type.name}")
    
    def parse_decorated_statement(self) -> Statement:
        """Parse @decorator syntax (for functions or classes)"""
        decorators = []
        
        # Collect all decorators
        while self.current_token and self.current_token.type == TokenType.AT:
            decorator_line = self.current_token.line
            decorator_col = self.current_token.column
            self.advance()  # consume @
            
            # Parse decorator name with possible member access: @app.route or @decorator
            decorator_parts = [self.expect(TokenType.IDENTIFIER).value]
            while self.match(TokenType.DOT):
                self.advance()  # consume .
                # Allow keywords as member names in decorators
                member_token = self.current_token
                if member_token and (member_token.type == TokenType.IDENTIFIER or (member_token.value and isinstance(member_token.value, str))):
                    decorator_parts.append(member_token.value)
                    self.advance()
                else:
                    decorator_parts.append(self.expect(TokenType.IDENTIFIER).value)
            
            decorator_name = '.'.join(decorator_parts)
            
            # Check for decorator arguments: @decorator(args)
            args = None
            if self.current_token and self.current_token.type == TokenType.LPAREN:
                self.advance()  # consume (
                args = []
                while self.current_token and self.current_token.type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    if self.current_token and self.current_token.type == TokenType.COMMA:
                        self.advance()
                self.expect(TokenType.RPAREN)
            
            decorators.append(Decorator(
                line=decorator_line,
                column=decorator_col,
                name=decorator_name,
                args=args
            ))
            
            # Skip newlines between decorators
            while self.current_token and self.current_token.type == TokenType.NEWLINE:
                self.advance()
        
        # Now parse the decorated thing (function or class)
        if self.match(TokenType.FN):
            func_def = self.parse_function_def()
            func_def.decorators = decorators
            return func_def
        elif self.match(TokenType.CLASS):
            class_def = self.parse_class_def()
            class_def.decorators = decorators
            return class_def
        else:
            self.error(f"Expected function or class after decorator, got {self.current_token.type if self.current_token else 'EOF'}")
    
    def parse_class_def(self) -> 'ClassDef':
        """Parse: class:name|methods"""
        token = self.expect(TokenType.CLASS)
        self.expect(TokenType.COLON)
        
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Optional base classes: class:name[BaseClass]
        base_classes = []
        if self.current_token and self.current_token.type == TokenType.LBRACKET:
            self.advance()  # consume [
            while self.current_token and self.current_token.type != TokenType.RBRACKET:
                base_classes.append(self.expect(TokenType.IDENTIFIER).value)
                if self.current_token and self.current_token.type == TokenType.COMMA:
                    self.advance()
            self.expect(TokenType.RBRACKET)
        
        # Expect newline before body
        self.expect(TokenType.NEWLINE)
        
        # Parse class body (indented methods and attributes)
        methods = []
        attributes = []
        class_docstring = None
        pending_docstring = None  # Docstring for the next method
        
        while self.current_token and self.current_token.column > 1:
            # Skip decorators for now, parse function definitions as methods
            if self.match(TokenType.COMMENT):
                # Check for docstring comment: # @doc ...
                comment_text = self.current_token.value
                if comment_text.startswith('@doc '):
                    doc = comment_text[5:].strip()
                    # Remove trailing | if present
                    if doc.endswith('|'):
                        doc = doc[:-1]
                    # If no methods yet, this is the class docstring
                    # Otherwise, it's for the next method
                    if not methods and not pending_docstring and class_docstring is None:
                        class_docstring = doc
                    else:
                        pending_docstring = doc
                self.advance()
                # Skip newlines after comment
                while self.current_token and self.current_token.type == TokenType.NEWLINE:
                    self.advance()
                continue
            elif self.match(TokenType.AT):
                method = self.parse_decorated_statement()
                if isinstance(method, FunctionDef):
                    # Attach pending docstring to method
                    if pending_docstring:
                        method.docstring = pending_docstring
                        pending_docstring = None
                    methods.append(method)
            elif self.match(TokenType.FN):
                method = self.parse_function_def()
                # Attach pending docstring to method
                if pending_docstring:
                    method.docstring = pending_docstring
                    pending_docstring = None
                methods.append(method)
            elif self.match(TokenType.VAR):
                attributes.append(self.parse_variable_def())
            elif self.match(TokenType.IDENTIFIER):
                # Could be implicit variable: self.x = value
                attributes.append(self.parse_implicit_variable_or_compound())
            else:
                break
            
            # Skip newlines
            while self.current_token and self.current_token.type == TokenType.NEWLINE:
                self.advance()
        
        return ClassDef(
            line=token.line, column=token.column,
            name=name,
            base_classes=base_classes if base_classes else None,
            methods=methods if methods else None,
            attributes=attributes if attributes else None,
            decorators=None,  # Set by parse_decorated_statement if present
            docstring=class_docstring  # Add class docstring
        )
    
    def parse_function_def(self) -> FunctionDef:
        """Parse: F:name|name:type,name:type|type|body"""
        name, input_types, output_type, body, token, param_names, docstring = self._parse_function_common(
            stop_tokens=[TokenType.EOF, TokenType.EXPORT, TokenType.FN, TokenType.META, TokenType.DEPS]
        )
        
        return FunctionDef(
            line=token.line, column=token.column,
            name=name,
            input_types=input_types,
            output_type=output_type,
            body=body,
            param_names=param_names,
            docstring=docstring
        )
    
    def parse_function_expr(self) -> FunctionExpr:
        """Parse: F:name|types|type|body - Function as expression inside objects"""
        name, input_types, output_type, body, token, param_names, docstring = self._parse_function_common(
            stop_tokens=[TokenType.EOF, TokenType.RBRACE, TokenType.COMMA]
        )
        
        return FunctionExpr(
            line=token.line, column=token.column,
            name=name,
            input_types=input_types,
            output_type=output_type,
            body=body
        )
    
    def _parse_function_common(self, stop_tokens: List[TokenType]):
        """
        Parse common function structure.
        
        Standard syntax: F:name|name:type,name:type|type|body (with param names)
        Legacy syntax: F:name|type,type|type|body (without param names)
        
        Args:
            stop_tokens: Token types that signal end of function body
        
        Returns:
            Tuple of (name, input_types, output_type, body, start_token, param_names, docstring)
        """
        token = self.expect(TokenType.FN)
        self.expect(TokenType.COLON)
        
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.PIPE)
        
        param_names = None
        docstring = None
        
        # Detect syntax mode: check if next token is INPUT (i:) or a type
        if self.match(TokenType.INPUT):
            # Standard syntax: i:type,type|o:type
            self.advance()  # consume 'i'
            self.expect(TokenType.COLON)
            
            # Check if input list is empty (next token is PIPE)
            if self.match(TokenType.PIPE):
                input_types = []
            else:
                input_types = self.parse_type_list()
            
            self.expect(TokenType.PIPE)
            
            # Parse output: o:type
            self.expect(TokenType.OUTPUT)
            self.expect(TokenType.COLON)
            output_type = self.parse_type()
            self.expect(TokenType.PIPE)
        else:
            # Optimized syntax: name:type,name:type|type|body (with param names)
            # Or legacy: type,type|type|body (without param names)
            # Types are positional: inputs|output
            # Support three formats:
            # 1. F:name|name:type,name:type|returntype|body  (with param names - NEW)
            # 2. F:name|type1,type2|returntype|body  (with params, no names - legacy)
            # 3. F:name||returntype|body              (no params, double pipe)
            # 4. F:name|returntype|body               (no params, single pipe - cleaner syntax)
            
            if self.match(TokenType.PIPE):
                # Empty inputs: F:name||type|body
                input_types = []
                self.advance()  # consume the pipe
                output_type = self.parse_type()
                self.expect(TokenType.PIPE)
            else:
                # Parse first param(s) - may have names: name:type,name:type or just type,type
                first_types, first_names = self.parse_param_list()
                param_names = first_names  # Will be None if no names were provided
                
                # After first type list, must see a pipe
                if not self.match(TokenType.PIPE):
                    raise self.error("Expected PIPE after types")
                
                self.advance()  # consume pipe
                
                # Now determine: is next thing a type (more inputs) or body?
                # Check if it's a valid type identifier (but NOT name:type format)
                valid_types = {'int', 'float', 'str', 'bool', 'arr', 'obj', 'map', 'set',
                             'any', 'void', 'promise', 'func', 'I', 'N', 'S', 'B', 'A', 'O', 'V', 'P', 'L'}
                
                is_type = (self.match(TokenType.IDENTIFIER) and self.current_token.value in valid_types) or \
                         self.match(TokenType.TYPE_INT, TokenType.TYPE_FLOAT, TokenType.TYPE_STR,
                                   TokenType.TYPE_BOOL, TokenType.TYPE_ARR, TokenType.TYPE_OBJ,
                                   TokenType.TYPE_ANY, TokenType.TYPE_VOID, TokenType.TYPE_PROMISE,
                                   TokenType.TYPE_FUNC, TokenType.TYPE_MAP, TokenType.TYPE_SET)
                
                if is_type:
                    # F:name|inputtypes|returntype|body format
                    input_types = first_types
                    output_type = self.parse_type()
                    self.expect(TokenType.PIPE)
                else:
                    # F:name|returntype|body format (no params)
                    if len(first_types) > 1:
                        raise self.error("Multiple return types not supported")
                    input_types = []
                    param_names = None  # No params means no names
                    output_type = first_types[0]
                    # Pipe already consumed above
        
        # Parse body - statements separated by | or newlines
        body, docstring = self._parse_function_body_with_docstring(stop_tokens)
        
        return name, input_types, output_type, body, token, param_names, docstring
    
    def _parse_function_body_with_docstring(self, stop_tokens: List[TokenType]) -> tuple:
        """
        Parse function body until a stop token is encountered or we hit a module-level statement.
        Also extracts docstring if present (# @doc comment).
        
        Returns: (body: List[Statement], docstring: str or None)
        """
        body = []
        docstring = None
        iterations = 0
        max_iterations = 10000
        
        while self.current_token and self.current_token.type not in stop_tokens:
            iterations += 1
            if iterations > max_iterations:
                raise self.error(f"Infinite loop detected in function body parsing")
            
            if self.match(TokenType.NEWLINE):
                self.skip_newlines()
                
                # After newlines, if next token is at column 1 (module level), stop
                if self.current_token and self.current_token.column == 1:
                    break
                
                continue
            
            # Check for docstring comment: # @doc ...
            if self.match(TokenType.COMMENT):
                comment_text = self.current_token.value
                if comment_text.startswith('@doc '):
                    docstring = comment_text[5:].strip()
                    # Remove trailing | if present
                    if docstring.endswith('|'):
                        docstring = docstring[:-1]
                    self.advance()
                    # Skip pipe after docstring comment
                    if self.match(TokenType.PIPE):
                        self.advance()
                    continue
            
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            
            # Consume pipe separators
            if self.match(TokenType.PIPE) and not self._is_pipeline_lookahead():
                self.advance()
        
        return body, docstring
    
    def _parse_function_body(self, stop_tokens: List[TokenType]) -> List[Statement]:
        """
        Parse function body until a stop token is encountered or we hit a module-level statement.
        
        Module-level statements are identified by being at column 1 after a newline.
        This handles both single-line functions:
            F:name|...|ret:value
            module_statement
        And multi-line functions:
            F:name|...|
              body_statement
              body_statement
            module_statement
        """
        body = []
        
        while self.current_token and self.current_token.type not in stop_tokens:
            if self.match(TokenType.NEWLINE):
                self.skip_newlines()
                
                # After newlines, if next token is at column 1 (module level), stop parsing function body
                # This prevents module-level statements from being parsed as function body
                if self.current_token and self.current_token.column == 1:
                    break
                
                continue
            
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
            
            # Consume pipe separators (but not pipeline operations)
            if self.match(TokenType.PIPE) and not self._is_pipeline_lookahead():
                self.advance()
        
        return body
    
    def parse_type_list(self) -> List[Type]:
        """Parse comma-separated types (legacy format without names)"""
        types = []
        types.append(self.parse_type())
        
        while self.match(TokenType.COMMA):
            self.advance()
            types.append(self.parse_type())
        
        return types
    
    def parse_param_list(self) -> tuple:
        """Parse comma-separated parameters with optional names: name:type,name:type or just type,type
        
        Returns: (types: List[Type], param_names: List[str] or None)
        """
        types = []
        param_names = []
        has_names = False
        
        # Parse first parameter
        first_type, first_name = self.parse_param()
        types.append(first_type)
        if first_name:
            param_names.append(first_name)
            has_names = True
        else:
            param_names.append(None)
        
        # Parse remaining parameters
        while self.match(TokenType.COMMA):
            self.advance()
            param_type, param_name = self.parse_param()
            types.append(param_type)
            if param_name:
                param_names.append(param_name)
                has_names = True
            else:
                param_names.append(None)
        
        # If any param has a name, return all names (using defaults for missing ones)
        if has_names:
            # Fill in default names for any that are missing
            final_names = []
            for i, name in enumerate(param_names):
                if name:
                    final_names.append(name)
                else:
                    final_names.append(f"i{i}")
            return types, final_names
        else:
            return types, None
    
    def parse_param(self) -> tuple:
        """Parse a single parameter: name:type or just type
        
        Returns: (Type, name: str or None)
        """
        token = self.current_token
        
        # Check if this is name:type format
        # Accept both IDENTIFIER and keywords as parameter names
        if self.match(TokenType.IDENTIFIER) or (self.current_token and hasattr(self.current_token, 'value')):
            # Check if it might be a keyword used as parameter name
            # (e.g., data:O, file:S, etc.)
            is_keyword = self.current_token.type not in (TokenType.IDENTIFIER, TokenType.EOF)
            name_or_type = self.current_token.value
            self.advance()
            
            # Check if followed by COLON (name:type format)
            if self.match(TokenType.COLON):
                self.advance()  # consume :
                param_type = self.parse_type()
                return param_type, name_or_type
            elif is_keyword:
                # This was a keyword not followed by colon - it's not a valid parameter
                raise self.error(f"Expected name:type format for keyword parameter '{name_or_type}'")
            else:
                # No colon - this was a type, not a name (legacy format)
                # Check if it's a valid type
                valid_types = {
                    'int', 'float', 'str', 'bool', 'arr', 'obj', 'map', 'set',
                    'any', 'void', 'promise', 'func',
                    'I', 'N', 'S', 'B', 'A', 'O', 'V', 'P', 'L'
                }
                if name_or_type in valid_types:
                    return Type(line=token.line, column=token.column, name=name_or_type), None
                else:
                    raise self.error(f"Expected type or name:type, got '{name_or_type}'")
        
        # Legacy TYPE_* tokens
        if self.match(TokenType.TYPE_INT, TokenType.TYPE_FLOAT, TokenType.TYPE_STR,
                     TokenType.TYPE_BOOL, TokenType.TYPE_ARR, TokenType.TYPE_OBJ,
                     TokenType.TYPE_ANY, TokenType.TYPE_VOID, TokenType.TYPE_PROMISE,
                     TokenType.TYPE_FUNC, TokenType.TYPE_MAP, TokenType.TYPE_SET):
            type_token = self.advance()
            return Type(line=token.line, column=token.column, name=type_token.value), None
        
        raise self.error(f"Expected parameter (name:type or type), got {token.type.name if token else 'EOF'}")
    
    def parse_type(self) -> Type:
        """Parse a type annotation"""
        token = self.current_token
        
        # Types are now identifiers - check if it's a valid type name
        if self.match(TokenType.IDENTIFIER):
            type_name = self.current_token.value
            # Valid type names
            valid_types = {
                'int', 'float', 'str', 'bool', 'arr', 'obj', 'map', 'set',
                'any', 'void', 'promise', 'func',
                'I', 'N', 'S', 'B', 'A', 'O', 'V', 'P', 'L'
            }
            if type_name in valid_types:
                self.advance()
                return Type(
                    line=token.line, column=token.column,
                    name=type_name
                )
            else:
                raise self.error(f"Unknown type: {type_name}", 
                               ["Valid types: int, float, str, bool, arr, obj, any, void, etc."])
        
        # Legacy: Still support old TYPE_* tokens for backward compatibility
        if self.match(TokenType.TYPE_INT, TokenType.TYPE_FLOAT, TokenType.TYPE_STR,
                     TokenType.TYPE_BOOL, TokenType.TYPE_ARR, TokenType.TYPE_OBJ,
                     TokenType.TYPE_ANY, TokenType.TYPE_VOID, TokenType.TYPE_PROMISE,
                     TokenType.TYPE_FUNC, TokenType.TYPE_MAP, TokenType.TYPE_SET):
            type_token = self.advance()
            return Type(
                line=token.line, column=token.column,
                name=type_token.value
            )
        
        raise self.error(f"Expected type, got {token.type.name if token else 'EOF'}")
    
    def parse_implicit_variable_or_compound(self) -> Union[VariableDef, 'CompoundAssignment']:
        """Parse: name=value (implicit variable) or name+=value (compound assignment)"""
        token = self.current_token
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Check for compound assignment operators
        if self.match(TokenType.PLUS_EQUALS):
            self.advance()
            value = self.parse_expression()
            return CompoundAssignment(
                line=token.line, column=token.column,
                name=name, operator='+', value=value
            )
        elif self.match(TokenType.MINUS_EQUALS):
            self.advance()
            value = self.parse_expression()
            return CompoundAssignment(
                line=token.line, column=token.column,
                name=name, operator='-', value=value
            )
        elif self.match(TokenType.TIMES_EQUALS):
            self.advance()
            value = self.parse_expression()
            return CompoundAssignment(
                line=token.line, column=token.column,
                name=name, operator='*', value=value
            )
        elif self.match(TokenType.DIV_EQUALS):
            self.advance()
            value = self.parse_expression()
            return CompoundAssignment(
                line=token.line, column=token.column,
                name=name, operator='/', value=value
            )
        
        # Simple assignment: name=value
        self.expect(TokenType.EQUALS)
        value = self.parse_expression()
        
        return VariableDef(
            line=token.line, column=token.column,
            name=name,
            type_annotation=None,
            value=value
        )
    
    def parse_variable_def(self) -> VariableDef:
        """Parse: v:name=value or v:name:type=value"""
        token = self.expect(TokenType.VAR)
        self.expect(TokenType.COLON)
        
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Optional type annotation
        type_annotation = None
        if self.match(TokenType.COLON):
            self.advance()
            type_annotation = self.parse_type()
        
        self.expect(TokenType.EQUALS)
        value = self.parse_expression()
        
        return VariableDef(
            line=token.line, column=token.column,
            name=name,
            type_annotation=type_annotation,
            value=value
        )
    
    def parse_return_stmt(self) -> ReturnStmt:
        """Parse: ret:value or ret: (empty return)"""
        token = self.expect(TokenType.RET)
        self.expect(TokenType.COLON)
        
        # Check for empty return (ret:|)
        if self.match(TokenType.PIPE, TokenType.NEWLINE, TokenType.EOF):
            # Empty return - return None

            value = Identifier(line=token.line, column=token.column, name='null')
        else:
            value = self.parse_expression()
        
        return ReturnStmt(
            line=token.line, column=token.column,
            value=value
        )
    
    def parse_implicit_call(self) -> DirectCall:
        """Parse: function(args) or obj.method(args) - Implicit call without @ prefix"""
        token = self.current_token
        # Parse the entire expression (identifier with possible member access and call)
        function_expr = self.parse_expression()
        
        return DirectCall(
            line=token.line, column=token.column,
            function=function_expr
        )
    
    def parse_direct_call(self) -> DirectCall:
        """Parse: @function(args) - Direct function call without variable assignment"""
        token = self.expect(TokenType.AT)
        function_expr = self.parse_expression()
        
        return DirectCall(
            line=token.line, column=token.column,
            function=function_expr
        )
    
    def parse_if_stmt(self):
        """
        Parse if statement - supports two forms:
        1. Ternary: if:condition?true_expr:false_expr
        2. Block: if:condition\n  body_statements\n[else:\n  else_statements]
        """
        token = self.expect(TokenType.IF)
        self.expect(TokenType.COLON)
        
        condition = self.parse_expression()
        
        # Check if this is ternary (?) or block (newline/pipe)
        if self.match(TokenType.QUESTION):
            # Ternary form: if:condition?true_expr:false_expr
            self.advance()
            
            # Parse true branch - could be ret:value or just value
            if self.match(TokenType.RET):
                self.advance()
                self.expect(TokenType.COLON)
                true_value = self.parse_expression()
                true_expr = ReturnStmt(line=token.line, column=token.column, value=true_value)
            else:
                true_expr = self.parse_expression()
            
            self.expect(TokenType.COLON)
            
            # Parse false branch - could be ret:value or just value
            if self.match(TokenType.RET):
                self.advance()
                self.expect(TokenType.COLON)
                false_value = self.parse_expression()
                false_expr = ReturnStmt(line=token.line, column=token.column, value=false_value)
            else:
                false_expr = self.parse_expression()
            
            return IfStmt(
                line=token.line, column=token.column,
                condition=condition,
                true_expr=true_expr,
                false_expr=false_expr
            )
        else:
            # Block form: if:condition followed by indented body
            # Expect newline or pipe
            if self.match(TokenType.PIPE):
                self.advance()
            self.skip_newlines()
            
            # Parse if body (indented statements)
            # Track the expected indentation level - should be greater than if statement's column
            if_column = token.column
            expected_body_column = None
            if_body = []
            
            while self.current_token and self.current_token.type != TokenType.EOF and self.current_token.column > if_column:
                # Set expected column from first statement
                if expected_body_column is None and self.current_token.column > if_column:
                    expected_body_column = self.current_token.column
                
                # If indentation decreased but still > if_column, we've left this block
                if expected_body_column and self.current_token.column < expected_body_column:
                    break
                
                stmt = self.parse_statement()
                if stmt:
                    if_body.append(stmt)
                
                # Consume pipes
                if self.match(TokenType.PIPE):
                    self.advance()
                    # After pipe, skip any newlines
                    while self.match(TokenType.NEWLINE):
                        self.advance()
                    # Check if we've exited the block
                    if not self.current_token or self.current_token.column <= if_column:
                        break
                    continue
                    
                # Skip newlines but stop if we're back at or before if column
                if self.match(TokenType.NEWLINE):
                    self.advance()
                    self.skip_newlines()
                    if not self.current_token or self.current_token.column <= if_column:
                        break
                    continue
                
                # If no statement and no special token, we might be stuck - break
                if not stmt and self.current_token:
                    break
            
            # Check for else clause
            else_body = []
            if self.match(TokenType.ELSE):
                else_token_column = self.current_token.column if self.current_token else if_column
                self.advance()
                self.expect(TokenType.COLON)
                if self.match(TokenType.PIPE):
                    self.advance()
                self.skip_newlines()
                
                # Parse else body with same indentation tracking
                expected_else_column = None
                while self.current_token and self.current_token.type != TokenType.EOF and self.current_token.column > else_token_column:
                    # Set expected column from first statement
                    if expected_else_column is None and self.current_token.column > else_token_column:
                        expected_else_column = self.current_token.column
                    
                    # If indentation decreased but still > else_column, we've left this block
                    if expected_else_column and self.current_token.column < expected_else_column:
                        break
                    
                    stmt = self.parse_statement()
                    if stmt:
                        else_body.append(stmt)
                        
                    if self.match(TokenType.PIPE):
                        self.advance()
                        # After pipe, skip any newlines
                        while self.match(TokenType.NEWLINE):
                            self.advance()
                        # Check if we've exited the block
                        if not self.current_token or self.current_token.column <= else_token_column:
                            break
                        continue
                        
                    if self.match(TokenType.NEWLINE):
                        self.advance()
                        self.skip_newlines()
                        if not self.current_token or self.current_token.column <= else_token_column:
                            break
                        continue
                    
                    # Prevent infinite loop
                    if not stmt and self.current_token:
                        break
            

            return IfElseBlock(
                line=token.line, column=token.column,
                condition=condition,
                if_body=if_body,
                else_body=else_body if else_body else None
            )
    
    def parse_if_expr(self) -> IfStmt:
        """Parse if as expression: if:condition?true_expr:false_expr
        Same as parse_if_stmt since IfStmt is actually an expression in VL"""
        return self.parse_if_stmt()
    
    def parse_for_loop(self) -> ForLoop:
        """Parse: for:var,iterable|body"""
        token = self.expect(TokenType.FOR)
        self.expect(TokenType.COLON)
        
        # Allow keywords as variable names in loop context (i, o, etc.)
        if self.match(TokenType.IDENTIFIER):
            variable = self.advance().value
        elif self.current_token:
            # Accept keywords as identifiers in this context
            variable = self.advance().value
        else:
            raise self.error("Expected variable name in for loop")
        
        self.expect(TokenType.COMMA)
        
        iterable = self.parse_expression()
        self.expect(TokenType.PIPE)
        
        # Parse loop body - continue until we hit a token that ends the loop
        # This could be EOF, a newline followed by non-indented code, or certain keywords
        body = []
        loop_column = token.column
        body_column = None
        body_column = None
        iterations = 0
        max_iterations = 10000  # Safety limit to prevent infinite loops
        while self.current_token and self.current_token.type not in (TokenType.EOF,):
            iterations += 1
            if iterations > max_iterations:
                raise self.error(f"Infinite loop detected in for loop parsing (>{max_iterations} iterations)")
            
            # Check if we've hit a statement that shouldn't be in this loop
            # (like a return, another top-level statement, etc.)
            if self.match(TokenType.RET, TokenType.FN, TokenType.META, TokenType.DEPS, TokenType.EXPORT):
                break
            
            if self.match(TokenType.NEWLINE):
                self.skip_newlines()
                # Dedent: if we've recorded a body indent, and the next token is less indented, end the loop body
                if body_column is not None and self.current_token and self.current_token.column < body_column:
                    break
                # Also allow dedent to loop start column for safety
                if self.current_token and self.current_token.column <= loop_column:
                    break
                continue
            
            # Save position to detect if we're making progress
            saved_pos = self.pos
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
                if body_column is None and hasattr(stmt, 'column'):
                    body_column = getattr(stmt, 'column', None)
            elif self.pos == saved_pos:
                # If parse_statement returned None and didn't advance, we're stuck
                # This means we hit something that's not part of this loop
                break
            
            # Consume pipe separators (but not pipeline operations)
            if self.match(TokenType.PIPE) and not self._is_pipeline_lookahead():
                self.advance()
            else:
                # If we hit a pipe that's not a separator, we're done
                if self.match(TokenType.PIPE):
                    break
        
        return ForLoop(
            line=token.line, column=token.column,
            variable=variable,
            iterable=iterable,
            body=body
        )
    
    def parse_while_loop(self) -> WhileLoop:
        """Parse: while:condition|body"""
        token = self.expect(TokenType.WHILE)
        self.expect(TokenType.COLON)
        
        condition = self.parse_expression()
        self.expect(TokenType.PIPE)
        
        # Parse loop body - same logic as for loop
        body = []
        loop_column = token.column
        body_column = None
        while self.current_token and self.current_token.type not in (TokenType.EOF,):
            # Check if we've hit a statement that shouldn't be in this loop
            if self.match(TokenType.RET, TokenType.FN, TokenType.META, TokenType.DEPS, TokenType.EXPORT):
                break
            
            if self.match(TokenType.NEWLINE):
                self.skip_newlines()
                if body_column is not None and self.current_token and self.current_token.column < body_column:
                    break
                if self.current_token and self.current_token.column <= loop_column:
                    break
                continue
            
            stmt = self.parse_statement()
            if stmt:
                body.append(stmt)
                if body_column is None and hasattr(stmt, 'column'):
                    body_column = getattr(stmt, 'column', None)
                if body_column is None and hasattr(stmt, 'column'):
                    body_column = getattr(stmt, 'column', None)
            
            # Consume pipe separators (but not pipeline operations)
            if self.match(TokenType.PIPE) and not self._is_pipeline_lookahead():
                self.advance()
            else:
                # If we hit a pipe that's not a separator, we're done
                if self.match(TokenType.PIPE):
                    break
        
        return WhileLoop(
            line=token.line, column=token.column,
            condition=condition,
            body=body
        )
    
    def parse_api_call(self) -> APICall:
        """Parse: api:METHOD,endpoint[,options] or async|api:..."""
        is_async = False
        if self.match(TokenType.ASYNC):
            is_async = True
            self.advance()
            self.expect(TokenType.PIPE)
        
        token = self.expect(TokenType.API)
        self.expect(TokenType.COLON)
        
        method = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COMMA)
        
        endpoint = self.parse_expression()
        
        options = None
        if self.match(TokenType.COMMA):
            self.advance()
            options = self.parse_expression()  # Should be ObjectLiteral
        
        # Parse chained operations (filter, map, etc.)
        operations = []
        while self.match(TokenType.PIPE):
            # Look ahead to see if it's a data operation
            next_token = self.peek(1)
            if next_token and next_token.type in (TokenType.FILTER, TokenType.MAP, TokenType.PARSE):
                self.advance() # consume PIPE
                if self.match(TokenType.FILTER):
                    operations.append(self.parse_filter_op())
                elif self.match(TokenType.MAP):
                    operations.append(self.parse_map_op())
                elif self.match(TokenType.PARSE):
                    operations.append(self.parse_parse_op())
            else:
                break
        
        return APICall(
            line=token.line, column=token.column,
            method=method,
            endpoint=endpoint,
            options=options,
            is_async=is_async,
            operations=operations
        )
    
    # Note: parse_api_call serves as both statement and expression parser
    
    def parse_filter_op(self) -> FilterOp:
        token = self.expect(TokenType.FILTER)
        self.expect(TokenType.COLON)
        condition = self.parse_expression()
        return FilterOp(line=token.line, column=token.column, condition=condition)

    def parse_map_op(self) -> MapOp:
        token = self.expect(TokenType.MAP)
        self.expect(TokenType.COLON)
        # Note: Currently only supports expression-based mapping
        # Future enhancement: Support field extraction syntax like map:field1,field2
        # For now, assume expression
        expr = self.parse_expression()
        return MapOp(line=token.line, column=token.column, fields=None, expression=expr)

    def parse_parse_op(self) -> ParseOp:
        token = self.expect(TokenType.PARSE)
        self.expect(TokenType.COLON)
        format = self.expect(TokenType.IDENTIFIER).value
        return ParseOp(line=token.line, column=token.column, format=format)

    def parse_ui_component(self) -> UIComponent:
        """Parse: ui:name|state:...|props:...|on:...|render:..."""
        token = self.expect(TokenType.UI)
        self.expect(TokenType.COLON)
        
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Parse optional clauses
        props = []
        state_vars = []
        handlers = []
        render_element = None
        
        while self.match(TokenType.PIPE):
            self.advance()
            
            # Skip empty pipes
            if self.match(TokenType.PIPE, TokenType.NEWLINE, TokenType.EOF):
                continue
            
            # Parse state declaration
            if self.match(TokenType.STATE):
                self.advance()
                self.expect(TokenType.COLON)
                # Simple format: state:name=value or state:name:type=value
                state_name = self.expect(TokenType.IDENTIFIER).value
                state_type = None
                
                if self.match(TokenType.COLON):
                    self.advance()
                    # Accept type tokens or identifiers
                    if self.current_token:
                        state_type = self.advance().value
                
                if self.match(TokenType.EQUALS):
                    self.advance()
                    state_value = self.parse_expression()
                    state_vars.append((state_name, state_type, state_value))
                continue
            
            # Parse props declaration
            if self.match(TokenType.PROPS):
                self.advance()
                self.expect(TokenType.COLON)
                # Simple format: props:name:type
                prop_name = self.expect(TokenType.IDENTIFIER).value
                prop_type = None
                if self.match(TokenType.COLON):
                    self.advance()
                    # Accept type tokens or identifiers
                    if self.current_token:
                        prop_type = self.advance().value
                props.append((prop_name, prop_type))
                continue
            
            # Parse event handlers
            if self.match(TokenType.ON):
                self.advance()
                self.expect(TokenType.COLON)
                handler_name = self.expect(TokenType.IDENTIFIER).value
                handlers.append(handler_name)
                continue
            
            # Parse render clause
            if self.match(TokenType.RENDER):
                self.advance()
                self.expect(TokenType.COLON)
                render_element = self.expect(TokenType.IDENTIFIER).value
                continue
            
            # Break if we hit something that's not part of UI component
            break
        
        return UIComponent(
            line=token.line, column=token.column,
            name=name,
            props=props,
            state_vars=state_vars,
            body=[]  # body now stores render info
        )
    
    def parse_data_pipeline(self) -> DataPipeline:
        """Parse: data:source|operation|operation|..."""
        token = self.expect(TokenType.DATA)
        self.expect(TokenType.COLON)
        
        source = self.parse_expression()
        
        operations = []
        max_ops = 100  # Safety limit
        while self.match(TokenType.PIPE) and not self.match(TokenType.NEWLINE, TokenType.EOF) and len(operations) < max_ops:
            self.advance()
            
            # Parse data operations
            if self.match(TokenType.FILTER):
                self.advance()
                self.expect(TokenType.COLON)
                condition = self.parse_expression()
                operations.append(FilterOp(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    condition=condition
                ))
            elif self.match(TokenType.MAP):
                self.advance()
                self.expect(TokenType.COLON)
                # Note: Field extraction syntax (map:field1,field2) not yet implemented
                # Current support: expression-based transformation only
                transformation = self.parse_expression()
                operations.append(MapOp(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    fields=None,
                    expression=transformation
                ))
            elif self.match(TokenType.GROUPBY):
                self.advance()
                self.expect(TokenType.COLON)
                field = self.expect(TokenType.IDENTIFIER).value
                operations.append(GroupByOp(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    field=field
                ))
            elif self.match(TokenType.AGG):
                self.advance()
                self.expect(TokenType.COLON)
                func = self.expect(TokenType.IDENTIFIER).value
                operations.append(AggregateOp(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    function=func,
                    field=None
                ))
            elif self.match(TokenType.SORT):
                self.advance()
                self.expect(TokenType.COLON)
                field = self.expect(TokenType.IDENTIFIER).value
                operations.append(SortOp(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    field=field,
                    order='asc'
                ))
        
        return DataPipeline(
            line=token.line, column=token.column,
            source=source,
            operations=operations
        )
    
    # Note: parse_data_pipeline serves as both statement and expression parser
    
    def parse_file_operation(self) -> FileOperation:
        """Parse: file:operation,path[,args]"""
        token = self.expect(TokenType.FILE)
        self.expect(TokenType.COLON)
        
        operation = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.COMMA)
        
        path = self.parse_expression()
        
        arguments = []
        while self.match(TokenType.COMMA):
            self.advance()
            arguments.append(self.parse_expression())
        
        return FileOperation(
            line=token.line, column=token.column,
            operation=operation,
            path=path,
            arguments=arguments
        )
    
    def parse_expression(self) -> Expression:
        """Parse an expression"""
        return self.parse_logical()
    
    def parse_logical(self) -> Expression:
        """Parse logical AND/OR operators"""
        left = self.parse_comparison()
        
        while self.match(TokenType.AND, TokenType.OR):
            op_token = self.advance()
            right = self.parse_comparison()
            left = Operation(
                line=op_token.line, column=op_token.column,
                operator=op_token.value,
                operands=[left, right]
            )
        
        return left
    
    def parse_comparison(self) -> Expression:
        """Parse comparison operators"""
        left = self.parse_term()
        
        while self.match(TokenType.EQUAL, TokenType.NOT_EQUAL, TokenType.LESS_THAN,
                         TokenType.GREATER_THAN, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL):
            op_token = self.advance()
            right = self.parse_term()
            left = Operation(
                line=op_token.line, column=op_token.column,
                operator=op_token.value,
                operands=[left, right]
            )
        
        return left
    
    def parse_term(self) -> Expression:
        """Parse addition/subtraction"""
        left = self.parse_factor()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.advance()
            right = self.parse_factor()
            left = Operation(
                line=op_token.line, column=op_token.column,
                operator=op_token.value,
                operands=[left, right]
            )
        
        return left
    
    def parse_factor(self) -> Expression:
        """Parse multiplication/division"""
        left = self.parse_unary()
        
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.FLOOR_DIVIDE, TokenType.MODULO):
            op_token = self.advance()
            right = self.parse_unary()
            left = Operation(
                line=op_token.line, column=op_token.column,
                operator=op_token.value,
                operands=[left, right]
            )
        
        return left
    
    def parse_unary(self) -> Expression:
        """Parse unary operators"""
        if self.match(TokenType.MINUS, TokenType.NOT):
            op_token = self.advance()
            operand = self.parse_unary()
            return Operation(
                line=op_token.line, column=op_token.column,
                operator=op_token.value,
                operands=[operand]
            )
        
        return self.parse_postfix()

    def parse_postfix(self) -> Expression:
        """Parse postfix expressions (calls, member access, pipeline operations)"""
        expr = self.parse_primary()
        
        while True:
            # Member access: obj.prop
            if self.match(TokenType.DOT):
                self.advance()
                # Allow keywords as property names (e.g., obj.export, obj.file, obj.parse)
                prop_token = self.current_token
                if not prop_token or prop_token.type == TokenType.EOF:
                    raise self.error("Expected property name after '.'")
                # Accept IDENTIFIER or any token that has a string value (including keywords)
                # Keywords are tokenized with their keyword text as the value
                if prop_token.type == TokenType.IDENTIFIER or (prop_token.value and isinstance(prop_token.value, str)):
                    self.advance()
                else:
                    raise self.error(f"Expected property name, got {prop_token.type.name}")
                expr = MemberAccess(
                    line=expr.line,
                    column=expr.column,
                    object=expr,
                    property=prop_token.value
                )
            
            # Array/object indexing: obj[index]
            elif self.match(TokenType.LBRACKET):
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = IndexAccess(
                    line=expr.line,
                    column=expr.column,
                    object=expr,
                    index=index
                )
            
            # Function call: func(args)
            elif self.match(TokenType.LPAREN):
                expr = self._parse_call_args(expr)
            
            # Pipeline operations: expr|filter:...|map:...  
            elif self.match(TokenType.PIPE) and not self._in_pipeline:
                if self._is_pipeline_lookahead():
                    expr = self._parse_pipeline_chain(expr)
                else:
                    break  # PIPE but not a pipeline operation
            
            else:
                break
                
        return expr
    
    def _parse_call_args(self, callee: Expression) -> FunctionCall:
        """Parse function call arguments: (arg1, arg2, ...)"""
        self.advance()  # consume LPAREN
        args = []
        while not self.match(TokenType.RPAREN):
            args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        self.expect(TokenType.RPAREN)
        return FunctionCall(
            line=callee.line,
            column=callee.column,
            callee=callee,
            arguments=args
        )
    
    def _parse_pipeline_chain(self, source: Expression) -> DataPipeline:
        """Parse a chain of pipeline operations: |filter:...|map:..."""
        operations = []
        self._in_pipeline = True
        
        try:
            while self.match(TokenType.PIPE) and self._is_pipeline_lookahead():
                self.advance()  # consume PIPE
                
                # Parse the operation (now current token is FILTER, MAP, or PARSE)
                if self.match(TokenType.FILTER):
                    operations.append(self.parse_filter_op())
                elif self.match(TokenType.MAP):
                    operations.append(self.parse_map_op())
                elif self.match(TokenType.PARSE):
                    operations.append(self.parse_parse_op())
        finally:
            self._in_pipeline = False
        
        return DataPipeline(
            line=source.line,
            column=source.column,
            source=source,
            operations=operations
        )
    
    def parse_primary(self) -> Expression:
        """Parse primary expressions (literals, identifiers, etc.)"""
        token = self.current_token
        
        # Number literal (and check for range: 0..10)
        if self.match(TokenType.NUMBER):
            self.advance()
            value = float(token.value) if '.' in token.value else int(token.value)
            num_literal = NumberLiteral(
                line=token.line, column=token.column,
                value=value
            )
            
            # Check for range operator (..)
            if self.match(TokenType.DOTDOT):
                self.advance()
                end_expr = self.parse_primary()  # Parse the end value
                return RangeExpr(
                    line=token.line, column=token.column,
                    start=num_literal,
                    end=end_expr
                )
            
            return num_literal
        
        # String literal
        if self.match(TokenType.STRING):
            self.advance()
            is_template = '${' in token.value
            return StringLiteral(
                line=token.line, column=token.column,
                value=token.value,
                is_template=is_template
            )
        
        # Variable reference ($var)
        if self.match(TokenType.DOLLAR):
            self.advance()
            name = self.expect(TokenType.IDENTIFIER).value
            return VariableRef(
                line=token.line, column=token.column,
                name=name
            )
        
        # Direct function call (@func(args))
        if self.match(TokenType.AT):
            self.advance()
            func_name = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.LPAREN)
            
            args = []
            while not self.match(TokenType.RPAREN):
                args.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RPAREN)
            
            # Create FunctionCall with Identifier as callee
            callee = Identifier(line=token.line, column=token.column, name=func_name)
            return FunctionCall(
                line=token.line, column=token.column,
                callee=callee,
                arguments=args
            )
        
        # Python passthrough (py:code)
        if self.match(TokenType.PY):
            return self.parse_python_expr()
        
        # Operation (op:+(...))
        if self.match(TokenType.OP):
            return self.parse_operation_expr()
        
        # If expression (if:condition?true:false)
        if self.match(TokenType.IF):
            return self.parse_if_expr()
        
        # In operator (in:element,container)
        if self.match(TokenType.IN):
            token_start = self.advance()
            self.expect(TokenType.COLON)
            element = self.parse_expression()
            self.expect(TokenType.COMMA)
            container = self.parse_expression()

            return InOp(
                line=token_start.line, column=token_start.column,
                element=element,
                container=container
            )
        
        # Data pipeline expression (data:source|filter:...)
        if self.match(TokenType.DATA):
            return self.parse_data_pipeline()
        
        # API call as expression (api:GET,url)
        if self.match(TokenType.API, TokenType.ASYNC):
            return self.parse_api_call()
        
        # 'self' keyword used as identifier (in method context)
        if self.match(TokenType.SELF):
            name = self.advance().value
            return Identifier(
                line=token.line, column=token.column,
                name='self'
            )
        
        # Identifier (variable or function name)
        if self.match(TokenType.IDENTIFIER):
            name = self.advance().value
            
            # Just identifier
            return Identifier(
                line=token.line, column=token.column,
                name=name
            )
        
        # Single-letter keywords can be used as identifiers in expressions (i, j, o, etc.)
        # This allows loop variables and function parameters
        if self.current_token and len(self.current_token.value) <= 2:
            # Allow short keywords as identifiers (i, o, v, etc.)
            if self.current_token.type in (TokenType.INPUT, TokenType.OUTPUT, TokenType.VAR):
                name = self.advance().value
                return Identifier(
                    line=token.line, column=token.column,
                    name=name
                )
        
        # Parenthesized expression
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        # Array literal
        if self.match(TokenType.LBRACKET):
            return self.parse_array_literal()
        
        # Object literal
        if self.match(TokenType.LBRACE):
            return self.parse_object_literal()
        
        raise self.error(f"Unexpected token in expression: {token.type.name}")
    
    def parse_python_expr(self) -> 'PythonExpr':
        """
        Parse: py:code
        
        Captures raw Python code until we hit a delimiter.
        Supports:
        - py:np.array([1,2,3])
        - py:pd.read_csv('file.csv')
        - py:some_func(a, b, c)
        """
        token = self.expect(TokenType.PY)
        self.expect(TokenType.COLON)
        
        # Simplified approach: collect everything until a VL delimiter
        # We need to handle strings and brackets to avoid breaking on delimiters inside them
        code_parts = []
        paren_depth = 0
        bracket_depth = 0
        brace_depth = 0
        in_string = False
        string_char = None
        
        while self.current_token and self.current_token.type != TokenType.EOF:
            tok_type = self.current_token.type
            tok_value = self.current_token.value
            
            # Handle string literals
            if tok_type == TokenType.STRING:
                code_parts.append(f"'{tok_value}'")
                self.advance()
                continue
            
            # Track parentheses depth
            if tok_type == TokenType.LPAREN:
                paren_depth += 1
                code_parts.append('(')
                self.advance()
            elif tok_type == TokenType.RPAREN:
                if paren_depth > 0:
                    paren_depth -= 1
                    code_parts.append(')')
                    self.advance()
                else:
                    break  # End of expression
            elif tok_type == TokenType.LBRACKET:
                bracket_depth += 1
                code_parts.append('[')
                self.advance()
            elif tok_type == TokenType.RBRACKET:
                if bracket_depth > 0:
                    bracket_depth -= 1
                    code_parts.append(']')
                    self.advance()
                else:
                    break
            elif tok_type == TokenType.LBRACE:
                brace_depth += 1
                code_parts.append('{')
                self.advance()
            elif tok_type == TokenType.RBRACE:
                if brace_depth > 0:
                    brace_depth -= 1
                    code_parts.append('}')
                    self.advance()
                else:
                    break
            # Handle PIPE inside parentheses/brackets (Python bitwise OR operator)
            elif tok_type == TokenType.PIPE:
                if paren_depth > 0 or bracket_depth > 0 or brace_depth > 0:
                    # Inside brackets, PIPE is Python's bitwise OR, not VL delimiter
                    code_parts.append('|')
                    self.advance()
                else:
                    # Outside brackets, PIPE is VL statement separator
                    break
            # Handle AMPERSAND inside parentheses/brackets (Python bitwise AND operator)
            elif tok_type == TokenType.AMPERSAND:
                if paren_depth > 0 or bracket_depth > 0 or brace_depth > 0:
                    # Inside brackets, AMPERSAND is Python's bitwise AND
                    code_parts.append('&')
                    self.advance()
                else:
                    # Outside brackets, ampersand shouldn't appear in VL
                    break
            # Stop at VL delimiters when not inside brackets
            elif paren_depth == 0 and bracket_depth == 0 and brace_depth == 0:
                if tok_type in (TokenType.COMMA, TokenType.NEWLINE, TokenType.COLON):
                    break
                else:
                    # Add token value and advance
                    code_parts.append(tok_value)
                    self.advance()
            else:
                # Inside brackets - keep collecting
                code_parts.append(tok_value)
                self.advance()
        
        # Join tokens with spaces, but handle operators and punctuation carefully
        code = ''
        for i, part in enumerate(code_parts):
            if i == 0:
                code = part
            else:
                prev = code_parts[i-1]
                # Don't add space before/after certain punctuation or @ symbols
                if part in ('(', '[', '{', ')', ']', '}', ',', '.', ':', '@') or prev in ('(', '[', '{', '.', '@'):
                    code += part
                else:
                    code += ' ' + part
        
        return PythonExpr(
            line=token.line,
            column=token.column,
            code=code
        )
    
    def parse_python_stmt(self) -> 'PythonStmt':
        """
        Parse: py:code for statement-level Python passthrough
        
        Used for with statements, try/except, and other Python constructs
        not natively supported in VL.
        
        Example: py:with open('file.txt') as f:@@@  contents = f.read()
        Special markers:
        - @@@ = newline
        - @4@ = 4-space indentation (Python standard)
        """

        
        token = self.current_token
        self.expect(TokenType.PY)
        self.expect(TokenType.COLON)
        
        # Raw passthrough wrapper: py:__RAW__('code...') or py:__RAW_B64__('...')
        if self.current_token and self.current_token.type == TokenType.IDENTIFIER and self.current_token.value in {'__RAW__', '__RAW_B64__'}:
            wrapper = self.current_token.value
            self.advance()  # consume wrapper
            if self.match(TokenType.LPAREN):
                self.advance()
            code_token = self.expect(TokenType.STRING)
            # Consume optional closing paren
            if self.match(TokenType.RPAREN):
                self.advance()
            # Skip to line end
            while self.current_token and self.current_token.type not in (TokenType.NEWLINE, TokenType.EOF):
                self.advance()

            literal_value = code_token.value
            if wrapper == '__RAW_B64__':
                try:
                    decoded = base64.b64decode(literal_value).decode('utf-8', errors='replace')
                except Exception:
                    decoded = literal_value
            else:
                decoded = literal_value

            return PythonStmt(line=token.line, column=token.column, code=decoded)

        # Fallback legacy parsing
        code_parts = []
        while self.current_token and self.current_token.type not in (TokenType.EOF, TokenType.PIPE, TokenType.NEWLINE):
            code_parts.append(str(self.current_token.value))
            self.advance()
        
        # Join tokens with spaces, but handle operators and punctuation carefully
        code = ''
        for i, part in enumerate(code_parts):
            if i == 0:
                code = part
            else:
                prev = code_parts[i-1]
                # Don't add space before/after certain punctuation or @ symbols
                if part in ('(', '[', '{', ')', ']', '}', ',', '.', ':', '@') or prev in ('(', '[', '{', '.', '@'):
                    code += part
                else:
                    code += ' ' + part
        
        return PythonStmt(line=token.line, column=token.column, code=code)
    
    def parse_operation_expr(self) -> Operation:
        """Parse: op:operator(arg1,arg2,...)"""
        token = self.expect(TokenType.OP)
        self.expect(TokenType.COLON)
        
        # Get operator
        op = self.advance().value
        
        # Parse arguments
        self.expect(TokenType.LPAREN)
        operands = []
        while not self.match(TokenType.RPAREN):
            operands.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        self.expect(TokenType.RPAREN)
        
        return Operation(
            line=token.line, column=token.column,
            operator=op,
            operands=operands
        )
    
    def parse_array_literal(self) -> ArrayLiteral:
        """Parse: [1,2,3] or Python list comprehension [x for x in ...]"""
        token = self.expect(TokenType.LBRACKET)
        
        # Check if this might be a list comprehension (contains FOR keyword)
        # Scan ahead to see if there's a FOR before RBRACKET
        saved_pos = self.pos
        is_comprehension = False
        depth = 1
        while self.pos < len(self.tokens) and depth > 0:
            tok = self.tokens[self.pos]
            if tok.type == TokenType.LBRACKET:
                depth += 1
            elif tok.type == TokenType.RBRACKET:
                depth -= 1
            elif tok.type == TokenType.FOR and depth == 1:
                is_comprehension = True
                break
            self.pos += 1
        self.pos = saved_pos
        self.current_token = self.tokens[self.pos] if self.pos < len(self.tokens) else None
        
        # If it's a comprehension, collect everything until ] as Python code
        if is_comprehension:
            # Collect all tokens until matching ]
            py_tokens = []
            depth = 1
            while self.current_token and depth > 0:
                if self.current_token.type == TokenType.LBRACKET:
                    depth += 1
                elif self.current_token.type == TokenType.RBRACKET:
                    depth -= 1
                    if depth == 0:
                        break
                py_tokens.append(self.current_token.value)
                self.advance()
            self.expect(TokenType.RBRACKET)
            
            # Create a Python passthrough expression
            py_code = '[' + ' '.join(py_tokens) + ']'

            return PythonExpr(
                line=token.line, column=token.column,
                code=py_code
            )
        
        # Regular array literal
        elements = []
        while not self.match(TokenType.RBRACKET):
            elements.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.expect(TokenType.RBRACKET)
        
        return ArrayLiteral(
            line=token.line, column=token.column,
            elements=elements
        )
    
    def parse_object_literal(self) -> ObjectLiteral:
        """Parse: {key:value,key2:value2} - values can include F: for methods"""
        token = self.expect(TokenType.LBRACE)
        
        pairs = []
        while not self.match(TokenType.RBRACE):
            # Allow identifiers, reserved keywords, and string literals as object literal keys
            if self.current_token.type == TokenType.IDENTIFIER:
                key = self.current_token.value
                self.advance()
            elif self.current_token.type == TokenType.STRING:
                # String literals can be dict keys (e.g., {'&&': 'value'})
                key = self.current_token.value
                self.advance()
            elif self.current_token.type.name in ['INPUT', 'OUTPUT', 'FN', 'META', 'VAR', 'FOR', 'WHILE', 'IF', 'ELSE', 'RET', 'EXPORT', 'CALL', 'OP', 'PY', 'FILE', 'DATA', 'CLASS', 'API', 'STATE', 'PROPS']:
                key = self.current_token.value if self.current_token.value else self.current_token.type.name.lower()
                self.advance()
            else:
                raise self.error(f"Expected object key (identifier or keyword), got {self.current_token.type.name}")
            self.expect(TokenType.COLON)
            
            # Check if value is a function expression (F:name|...)
            if self.match(TokenType.FN):
                value = self.parse_function_expr()
            # Check if value is a ternary expression (if:cond?true:false)
            # In dict context, after key:, if we see IF, it's a ternary value
            elif self.match(TokenType.IF):
                self.advance()  # consume IF
                self.expect(TokenType.COLON)  # consume the : after if
                # Now manually parse the ternary: condition?true:false
                condition = self.parse_expression()
                self.expect(TokenType.QUESTION)
                true_expr = self.parse_expression()
                self.expect(TokenType.COLON)
                false_expr = self.parse_expression()

                value = IfStmt(
                    line=self.current_token.line,
                    column=self.current_token.column,
                    condition=condition,
                    true_expr=true_expr,
                    false_expr=false_expr
                )
            else:
                value = self.parse_expression()
            pairs.append((key, value))
            
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.expect(TokenType.RBRACE)
        
        return ObjectLiteral(
            line=token.line, column=token.column,
            pairs=pairs
        )
    
    def _expr_to_string(self, expr: Expression) -> str:
        """Convert an expression AST to string representation (for subscript assignments)"""

        if isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, IndexAccess):
            obj_str = self._expr_to_string(expr.object)
            index_str = self._expr_to_string(expr.index)
            return f"{obj_str}[{index_str}]"
        elif isinstance(expr, MemberAccess):
            obj_str = self._expr_to_string(expr.object)
            return f"{obj_str}.{expr.property}"
        else:
            # Fallback: return placeholder
            return str(expr)


def parse(source: str) -> Program:
    """Convenience function to parse VL source code"""
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()


if __name__ == "__main__":
    # Test the parser
    test_code = """
F:sum|I,I|I|ret:op:+(i0,i1)
    """
    
    try:
        ast = parse(test_code)
        print(ast_to_string(ast))
    except ParseError as e:
        print(f"Parse Error: {e}")
