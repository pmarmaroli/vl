"""
VL to JavaScript Code Generator
Converts VL AST to JavaScript source code
"""

from ..ast_nodes import *
from typing import List, Any


class JSCodeGenerator:
    """
    Generates JavaScript code from VL AST
    
    Usage:
        generator = JSCodeGenerator(ast)
        js_code = generator.generate()
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.indent_level = 0
        self.output = []
    
    def generate(self) -> str:
        """Generate JavaScript code from AST"""
        self.output = []
        self._generate_program(self.ast)
        return '\n'.join(self.output)
    
    def _indent(self) -> str:
        """Get current indentation"""
        return '    ' * self.indent_level
    
    def _emit(self, code: str):
        """Emit a line of code with proper indentation"""
        if code:
            self.output.append(self._indent() + code)
        else:
            self.output.append('')
    
    def _generate_program(self, node: Program):
        """Generate code for entire program"""
        # Metadata as comment
        if node.metadata:
            self._emit(f"// VL Program: {node.metadata.name}")
            self._emit(f"// Type: {node.metadata.program_type}")
            self._emit(f"// Target: {node.metadata.target_language}")
            self._emit('')
        
        # Dependencies (require/import)
        # Note: In browser context, imports work differently. 
        # For now we emit CommonJS requires or ES6 imports depending on config.
        # Defaulting to CommonJS for generic JS script compatibility
        if node.dependencies:
            for dep in node.dependencies.dependencies:
                self._emit(f"const {dep} = require('{dep}');")
            self._emit('')
        
        # Statements (functions, variables, etc.)
        for stmt in node.statements:
            self._generate_statement(stmt)
            
        # Export
        if node.export:
            self._emit('')
            self._emit(f"module.exports = {{ {node.export.name} }};")

    def _generate_statement(self, stmt: Statement):
        """Generate code for a statement"""
        if isinstance(stmt, FunctionDef):
            self._generate_function_def(stmt)
        elif isinstance(stmt, VariableDef):
            self._generate_variable_def(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._generate_return_stmt(stmt)
        elif isinstance(stmt, DirectCall):
            self._generate_direct_call(stmt)
        elif isinstance(stmt, IfStmt):
            self._generate_if_stmt(stmt)
        elif isinstance(stmt, ForLoop):
            self._generate_for_loop(stmt)
        elif isinstance(stmt, WhileLoop):
            self._generate_while_loop(stmt)
        elif isinstance(stmt, CompoundAssignment):
            self._generate_compound_assignment(stmt)
        elif isinstance(stmt, APICall):
            self._generate_api_call(stmt)
        elif isinstance(stmt, DataPipeline):
            self._generate_data_pipeline(stmt)
        elif isinstance(stmt, FileOperation):
            self._generate_file_operation(stmt)
        elif isinstance(stmt, UIComponent):
            self._generate_ui_component(stmt)
        # Add other statement types here...
        else:
            self._emit(f"// Warning: Unsupported statement type {type(stmt).__name__}")

    def _generate_function_def(self, node: FunctionDef):
        """Generate code for function definition"""
        # Implicit parameter naming i0, i1... based on input types
        param_names = [f"i{i}" for i in range(len(node.input_types))] 
        params = ", ".join(param_names)
        
        self._emit(f"function {node.name}({params}) {{")
        self.indent_level += 1
        
        # Generate body
        for stmt in node.body:
            self._generate_statement(stmt)
            
        self.indent_level -= 1
        self._emit("}")
        self._emit('')

    def _generate_variable_def(self, node: VariableDef):
        """Generate code for variable definition"""
        val_code = self._generate_expression(node.value)
        self._emit(f"let {node.name} = {val_code};")
    
    def _generate_if_stmt(self, node: IfStmt):
        """Generate if statement"""
        # IfStmt in VL is ternary-like: if:condition?true_expr:false_expr
        # But depending on AST structure it might be Statement (block) or Expression.
        # Looking at ast_nodes: IfStmt is a Statement but has true_expr and false_expr which are Expressions?
        # Wait, ast_nodes.py says:
        # @dataclass class IfStmt(Statement): condition: Expression, true_expr: Expression, false_expr: Expression
        # This looks like the 'if' keyword in VL behaves like a ternary operator statement?
        # Let's check parser.py to be sure how `if` is parsed.
        # But assuming it's a statement, we can generate:
        # if (cond) { expr1; } else { expr2; }
        # NOTE: If true_expr is just an expression, we need to wrap it in a statement or return it?
        # Re-reading ast_nodes.py: true_expr is 'Expression'. 
        
        cond_code = self._generate_expression(node.condition)
        true_code = self._generate_expression(node.true_expr)
        false_code = self._generate_expression(node.false_expr)
        
        self._emit(f"if ({cond_code}) {{")
        self.indent_level += 1
        self._emit(f"{true_code};")
        self.indent_level -= 1
        self._emit("} else {")
        self.indent_level += 1
        self._emit(f"{false_code};")
        self.indent_level -= 1
        self._emit("}")

    def _generate_return_stmt(self, node: ReturnStmt):
        """Generate code for return statement"""
        val_code = self._generate_expression(node.value)
        self._emit(f"return {val_code};")

    def _generate_direct_call(self, node: DirectCall):
        """Generate code for direct function call"""
        # This is a statement-level expression call
        expr_code = self._generate_expression(node.function)
        self._emit(f"{expr_code};")

    def _generate_for_loop(self, node: ForLoop):
        """Generate for loop"""
        iterable = self._generate_expression(node.iterable)
        self._emit(f"for (const {node.variable} of {iterable}) {{")
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

    def _generate_compound_assignment(self, node: CompoundAssignment):
        """Generate compound assignment (+=, -=, *=, /=)"""
        value = self._generate_expression(node.value)
        self._emit(f"{node.name} {node.operator}= {value};")

    def _generate_api_call(self, node: APICall):
        """Generate API call using fetch"""
        method = node.method.upper()
        endpoint = self._generate_expression(node.endpoint)
        
        if node.options:
            options = self._generate_expression(node.options)
            self._emit(f"fetch({endpoint}, {{method: '{method}', ...{options}}})")
        else:
            if method == 'GET':
                self._emit(f"fetch({endpoint})")
            else:
                self._emit(f"fetch({endpoint}, {{method: '{method}'}})")

    def _generate_data_pipeline(self, node: DataPipeline):
        """Generate data pipeline using array methods"""
        # Flatten nested DataPipeline structures
        def flatten_pipeline(pipeline):
            """Recursively flatten nested DataPipeline structures"""
            if isinstance(pipeline.source, DataPipeline):
                base, ops = flatten_pipeline(pipeline.source)
                return base, ops + pipeline.operations
            else:
                return pipeline.source, pipeline.operations
        
        base_source, all_operations = flatten_pipeline(node)
        source = self._generate_expression(base_source)
        self._emit(f"// Data pipeline from: {source}")
        self._emit(f"let data = {source};")
        
        for op in all_operations:
            if isinstance(op, FilterOp):
                condition = self._generate_expression(op.condition)
                # Replace 'item' with lambda parameter
                condition = condition.replace('item', 'x')
                self._emit(f"data = data.filter(x => {condition});")
            elif isinstance(op, MapOp):
                if op.expression:
                    expr = self._generate_expression(op.expression)
                    expr = expr.replace('item', 'x')
                    self._emit(f"data = data.map(x => {expr});")
                elif op.fields:
                    fields = ', '.join(op.fields)
                    self._emit(f"data = data.map(x => ({{ {', '.join(f'{f}: x.{f}' for f in op.fields)} }}));")
            elif isinstance(op, GroupByOp):
                # Group by using reduce
                self._emit(f"data = data.reduce((groups, x) => {{")
                self._emit(f"    const key = x.{op.field} || x['{op.field}'];")
                self._emit(f"    if (!groups[key]) groups[key] = [];")
                self._emit(f"    groups[key].push(x);")
                self._emit(f"    return groups;")
                self._emit(f"}}, {{}});")
            elif isinstance(op, AggregateOp):
                # Aggregate operations on grouped data
                field = op.field or 'value'
                if op.function == 'count':
                    self._emit(f"data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v.length]));")
                elif op.function == 'sum':
                    self._emit(f"data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v.reduce((sum, x) => sum + (x.{field} || x['{field}'] || 0), 0)]));")
                elif op.function == 'avg':
                    self._emit(f"data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, v.reduce((sum, x) => sum + (x.{field} || x['{field}'] || 0), 0) / v.length]));")
                elif op.function == 'min':
                    self._emit(f"data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Math.min(...v.map(x => x.{field} || x['{field}'] || 0))]));")
                elif op.function == 'max':
                    self._emit(f"data = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, Math.max(...v.map(x => x.{field} || x['{field}'] || 0))]));")
            elif isinstance(op, SortOp):
                # Sort array by field
                if op.order == 'desc':
                    self._emit(f"data = data.sort((a, b) => (b.{op.field} || b['{op.field}']) - (a.{op.field} || a['{op.field}']));")
                else:
                    self._emit(f"data = data.sort((a, b) => (a.{op.field} || a['{op.field}']) - (b.{op.field} || b['{op.field}']));")

    def _generate_file_operation(self, node: FileOperation):
        """Generate Node.js file operations using fs module"""
        op = node.operation
        path = self._generate_expression(node.path)
        
        if op == 'read':
            self._emit(f"const fs = require('fs');")
            self._emit(f"const content = fs.readFileSync({path}, 'utf8');")
        elif op == 'write':
            if node.arguments:
                content = self._generate_expression(node.arguments[0])
                self._emit(f"const fs = require('fs');")
                self._emit(f"fs.writeFileSync({path}, {content}, 'utf8');")
        elif op == 'append':
            if node.arguments:
                content = self._generate_expression(node.arguments[0])
                self._emit(f"const fs = require('fs');")
                self._emit(f"fs.appendFileSync({path}, {content}, 'utf8');")
        elif op == 'delete':
            self._emit(f"const fs = require('fs');")
            self._emit(f"fs.unlinkSync({path});")

    def _generate_ui_component(self, node: UIComponent):
        """Generate React functional component"""
        self._emit(f"// React Component: {node.name}")
        self._emit(f"function {node.name}(props) {{")
        self.indent_level += 1
        
        # Generate state hooks
        for state_def in node.state_vars:
            initial = self._generate_expression(state_def.initial_value) if state_def.initial_value else 'null'
            self._emit(f"const [{state_def.name}, set{state_def.name.capitalize()}] = React.useState({initial});")
        
        # Generate event handlers
        for stmt in node.body:
            if isinstance(stmt, EventHandler):
                self._emit(f"const {stmt.event_name} = () => {{")
                self.indent_level += 1
                for handler_stmt in stmt.body:
                    self._generate_statement(handler_stmt)
                self.indent_level -= 1
                self._emit(f"}};")
            elif isinstance(stmt, RenderStmt):
                # Simplified JSX generation
                attrs = ''
                if stmt.attributes:
                    attrs = ' ' + self._generate_expression(stmt.attributes).strip('{}')
                children = ''.join([self._generate_expression(c) if isinstance(c, Expression) else '' for c in stmt.children])
                self._emit(f"// <{stmt.element}{attrs}>{children}</{stmt.element}>")
        
        self._emit(f"return null; // JSX would be generated here")
        self.indent_level -= 1
        self._emit(f"}}")
        self._emit('')

    def _generate_expression(self, node: Expression) -> str:
        """Generate code for an expression"""
        if isinstance(node, NumberLiteral):
            return str(node.value)
            
        elif isinstance(node, StringLiteral):
            # Template strings are handled during parsing - value already contains interpolated expressions
            quote = "`" if node.is_template else "'"
            return f"{quote}{node.value}{quote}"
            
        elif isinstance(node, BooleanLiteral):
            return "true" if node.value else "false"
            
        elif isinstance(node, Identifier):
            return node.name
            
        elif isinstance(node, VariableRef):
            return node.name # $name is just name in JS
            
        elif isinstance(node, Operation):
            op_map = {
                '&&': '&&', '||': '||', '!': '!',  # Already correct in VL
                'and': '&&', 'or': '||', 'not': '!',  # Legacy support
                '==': '===', '!=': '!=='  # Use strict equality
            }
            op = op_map.get(node.operator, node.operator)
            
            # Handle special operations
            if node.operator == 'range':
                # Convert range(start, end) to Array
                if len(node.operands) == 2:
                    start = self._generate_expression(node.operands[0])
                    end = self._generate_expression(node.operands[1])
                    return f"Array.from({{length: ({end}) - ({start}) + 1}}, (_, i) => i + ({start}))"
            
            # Handle unary op (not)
            if len(node.operands) == 1:
                return f"{op}({self._generate_expression(node.operands[0])})"
            
            # Handle binary ops
            # Note: Parentheses added for clarity, proper precedence handling is future work
            if len(node.operands) >= 2:
                operands = [self._generate_expression(op) for op in node.operands]
                return f"({f' {op} '.join(operands)})"
                
        elif isinstance(node, FunctionCall):
            callee = self._generate_expression(node.callee)
            args = [self._generate_expression(arg) for arg in node.arguments]
            return f"{callee}({', '.join(args)})"
            
        elif isinstance(node, ArrayLiteral):
            elements = [self._generate_expression(e) for e in node.elements]
            return f"[{', '.join(elements)}]"
            
        elif isinstance(node, ObjectLiteral):
            pairs = [f"{k}: {self._generate_expression(v)}" for k, v in node.pairs]
            return f"{{ {', '.join(pairs)} }}"
            
        elif isinstance(node, MemberAccess):
            obj = self._generate_expression(node.object)
            return f"{obj}.{node.property}"
            
        elif isinstance(node, IndexAccess):
            obj = self._generate_expression(node.object)
            index = self._generate_expression(node.index)
            return f"{obj}[{index}]"
            
        elif isinstance(node, RangeExpr):
            # Convert VL range 0..10 to JavaScript array
            start = self._generate_expression(node.start)
            end = self._generate_expression(node.end)
            # Create array from range: Array.from({length: end - start + 1}, (_, i) => i + start)
            return f"Array.from({{length: ({end}) - ({start}) + 1}}, (_, i) => i + ({start}))"
            
        elif isinstance(node, APICall):
            # API call as expression
            method = node.method.upper()
            endpoint = self._generate_expression(node.endpoint)
            if node.options:
                options = self._generate_expression(node.options)
                return f"fetch({endpoint}, {{method: '{method}', ...{options}}})"
            else:
                if method == 'GET':
                    return f"fetch({endpoint})"
                else:
                    return f"fetch({endpoint}, {{method: '{method}'}})"
        
        elif isinstance(node, DataPipeline):
            # Data pipeline as expression - build inline chain
            # Handle nested structure: source can be a DataPipeline
            def flatten_pipeline(pipeline):
                """Recursively flatten nested DataPipeline structures"""
                if isinstance(pipeline.source, DataPipeline):
                    base, ops = flatten_pipeline(pipeline.source)
                    return base, ops + pipeline.operations
                else:
                    return pipeline.source, pipeline.operations
            
            base_source, all_operations = flatten_pipeline(node)
            result = self._generate_expression(base_source)
            
            for op in all_operations:
                if isinstance(op, FilterOp):
                    condition = self._generate_expression(op.condition)
                    condition = condition.replace('item', 'x')
                    result = f"({result}).filter(x => {condition})"
                elif isinstance(op, MapOp):
                    if op.expression:
                        expr = self._generate_expression(op.expression)
                        expr = expr.replace('item', 'x')
                        result = f"({result}).map(x => {expr})"
                elif isinstance(op, GroupByOp):
                    # GroupBy as expression using reduce
                    result = f"({result}).reduce((groups, x) => {{ const key = x.{op.field} || x['{op.field}']; if (!groups[key]) groups[key] = []; groups[key].push(x); return groups; }}, {{}})"
                elif isinstance(op, AggregateOp):
                    # Aggregate as expression
                    field = op.field or 'value'
                    if op.function == 'count':
                        result = f"Object.fromEntries(Object.entries({result}).map(([k, v]) => [k, v.length]))"
                    elif op.function == 'sum':
                        result = f"Object.fromEntries(Object.entries({result}).map(([k, v]) => [k, v.reduce((sum, x) => sum + (x.{field} || x['{field}'] || 0), 0)]))"
                    elif op.function == 'avg':
                        result = f"Object.fromEntries(Object.entries({result}).map(([k, v]) => [k, v.reduce((sum, x) => sum + (x.{field} || x['{field}'] || 0), 0) / v.length]))"
                    elif op.function == 'min':
                        result = f"Object.fromEntries(Object.entries({result}).map(([k, v]) => [k, Math.min(...v.map(x => x.{field} || x['{field}'] || 0))]))"
                    elif op.function == 'max':
                        result = f"Object.fromEntries(Object.entries({result}).map(([k, v]) => [k, Math.max(...v.map(x => x.{field} || x['{field}'] || 0))]))"
                elif isinstance(op, SortOp):
                    # Sort as expression
                    if op.order == 'desc':
                        result = f"({result}).sort((a, b) => (b.{op.field} || b['{op.field}']) - (a.{op.field} || a['{op.field}']))"
                    else:
                        result = f"({result}).sort((a, b) => (a.{op.field} || a['{op.field}']) - (b.{op.field} || b['{op.field}']))"
            return result
            
        # Fallback
        return f"/* Unknown Expr: {type(node).__name__} */"

