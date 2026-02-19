"""
VL to TypeScript Code Generator

Generates TypeScript code from VL AST.
Based on JavaScript codegen with TypeScript-specific type annotations.
"""

from ..ast_nodes import *
from typing import List, Any


class TSCodeGenerator:
    """
    Generate TypeScript code from VL AST
    
    Usage:
        generator = TSCodeGenerator(ast)
        ts_code = generator.generate()
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.code = []
        self.indent_level = 0
    
    def _emit(self, line: str = ""):
        """Emit a line of code with proper indentation"""
        if line:
            self.code.append("  " * self.indent_level + line)
        else:
            self.code.append("")
    
    def _type_to_ts(self, vl_type: Type) -> str:
        """Convert VL type to TypeScript type"""
        type_map = {
            # Standard type names
            'int': 'number',
            'float': 'number',
            'str': 'string',
            'bool': 'boolean',
            'arr': 'any[]',
            'obj': 'Record<string, any>',
            'map': 'Map<any, any>',
            'set': 'Set<any>',
            'any': 'any',
            'void': 'void',
            'promise': 'Promise<any>',
            'func': 'Function',
            # Optimized single-char type aliases
            'I': 'number',           # I = int
            'N': 'number',           # N = number (float)
            'S': 'string',           # S = str
            'B': 'boolean',          # B = bool
            'A': 'any[]',            # A = arr (array)
            'O': 'Record<string, any>', # O = obj (object)
            'V': 'void',             # V = void
            'P': 'Promise<any>',     # P = promise
            'L': 'Function',         # L = lambda/func
        }
        return type_map.get(vl_type.name, 'any')
    
    def generate(self) -> str:
        """Generate code for entire program"""
        node = self.ast
        
        # Header comment
        self._emit("// Generated TypeScript code from VL")
        self._emit()
        
        # Dependencies (ES6 imports)
        if node.dependencies:
            for dep in node.dependencies.dependencies:
                # Simple import generation - future: parse import aliases and specific exports
                self._emit(f"import * as {dep.replace('/', '_')} from '{dep}';")
            self._emit()
        
        # Statements
        for stmt in node.statements:
            self._generate_statement(stmt)
        
        # Export
        if node.export:
            self._emit()
            self._emit(f"export {{ {node.export.name} }};")
        
        return '\n'.join(self.code)
    
    def _generate_statement(self, node: Statement):
        """Generate code for a statement"""
        if isinstance(node, FunctionDef):
            self._generate_function(node)
        elif isinstance(node, VariableDef):
            self._generate_variable_def(node)
        elif isinstance(node, CompoundAssignment):
            self._generate_compound_assignment(node)
        elif isinstance(node, ReturnStmt):
            self._generate_return_stmt(node)
        elif isinstance(node, DirectCall):
            self._generate_direct_call(node)
        elif isinstance(node, IfStmt):
            self._generate_if_stmt(node)
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
        else:
            # Unsupported statement type - likely needs implementation
            self._emit(f"// UNSUPPORTED: {type(node).__name__} not yet implemented for TypeScript")
            self._emit(f"// Please report this at: github.com/vibe-language/issues")

    def _generate_function(self, node: FunctionDef):
        """Generate TypeScript function with type annotations"""
        # Implicit parameter naming i0, i1... based on input types
        params = []
        for i, input_type in enumerate(node.input_types):
            ts_type = self._type_to_ts(input_type)
            params.append(f"i{i}: {ts_type}")
        
        params_str = ", ".join(params)
        return_type = self._type_to_ts(node.output_type)
        
        self._emit(f"function {node.name}({params_str}): {return_type} {{")
        self.indent_level += 1
        
        # Generate body
        for stmt in node.body:
            self._generate_statement(stmt)
            
        self.indent_level -= 1
        self._emit("}")
        self._emit()

    def _generate_variable_def(self, node: VariableDef):
        """Generate code for variable definition"""
        val_code = self._generate_expression(node.value)
        
        # Add type annotation if available
        if node.type_annotation:
            ts_type = self._type_to_ts(node.type_annotation)
            self._emit(f"let {node.name}: {ts_type} = {val_code};")
        else:
            self._emit(f"let {node.name} = {val_code};")
    
    def _generate_if_stmt(self, node: IfStmt):
        """Generate if statement"""
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
        """Generate API call using fetch with proper typing"""
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
                condition = condition.replace('item', 'x')
                self._emit(f"data = data.filter((x: any) => {condition});")
            elif isinstance(op, MapOp):
                if op.expression:
                    expr = self._generate_expression(op.expression)
                    expr = expr.replace('item', 'x')
                    self._emit(f"data = data.map((x: any) => {expr});")
                elif op.fields:
                    fields = ', '.join(op.fields)
                    self._emit(f"data = data.map((x: any) => ({{ {', '.join(f'{f}: x.{f}' for f in op.fields)} }}));")
            elif isinstance(op, GroupByOp):
                self._emit(f"data = data.reduce((groups: Record<string, any[]>, x: any) => {{")
                self._emit(f"    const key = x.{op.field} || x['{op.field}'];")
                self._emit(f"    if (!groups[key]) groups[key] = [];")
                self._emit(f"    groups[key].push(x);")
                self._emit(f"    return groups;")
                self._emit(f"}}, {{}});")
            elif isinstance(op, SortOp):
                if op.order == 'desc':
                    self._emit(f"data = data.sort((a: any, b: any) => (b.{op.field} || b['{op.field}']) - (a.{op.field} || a['{op.field}']));")
                else:
                    self._emit(f"data = data.sort((a: any, b: any) => (a.{op.field} || a['{op.field}']) - (b.{op.field} || b['{op.field}']));")

    def _generate_file_operation(self, node: FileOperation):
        """Generate Node.js file operations using fs module"""
        op = node.operation
        path = self._generate_expression(node.path)
        
        if op == 'read':
            self._emit(f"import * as fs from 'fs';")
            self._emit(f"const content: string = fs.readFileSync({path}, 'utf8');")
        elif op == 'write':
            if node.arguments:
                content = self._generate_expression(node.arguments[0])
                self._emit(f"import * as fs from 'fs';")
                self._emit(f"fs.writeFileSync({path}, {content}, 'utf8');")

    def _generate_ui_component(self, node: UIComponent):
        """Generate React TypeScript functional component"""
        self._emit(f"// React Component: {node.name}")
        self._emit(f"function {node.name}(props: any): JSX.Element {{")
        self.indent_level += 1
        
        # Generate state hooks
        for state_def in node.state_vars:
            initial = self._generate_expression(state_def.initial_value) if state_def.initial_value else 'null'
            self._emit(f"const [{state_def.name}, set{state_def.name.capitalize()}] = React.useState({initial});")
        
        self._emit(f"return null as any; // JSX would be generated here")
        self.indent_level -= 1
        self._emit(f"}}")
        self._emit()

    def _generate_expression(self, node: Expression) -> str:
        """Generate code for an expression"""
        if isinstance(node, NumberLiteral):
            return str(node.value)
            
        elif isinstance(node, StringLiteral):
            quote = "`" if node.is_template else "'"
            return f"{quote}{node.value}{quote}"
            
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
                '==': '===', '!=': '!=='
            }
            op = op_map.get(node.operator, node.operator)
            
            if len(node.operands) == 1:
                return f"{op}({self._generate_expression(node.operands[0])})"
            
            if len(node.operands) >= 2:
                operands = [self._generate_expression(o) for o in node.operands]
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
            start = self._generate_expression(node.start)
            end = self._generate_expression(node.end)
            return f"Array.from({{length: ({end}) - ({start}) + 1}}, (_, i) => i + ({start}))"
            
        elif isinstance(node, APICall):
            method = node.method.upper()
            endpoint = self._generate_expression(node.endpoint)
            if node.options:
                options = self._generate_expression(node.options)
                return f"fetch({endpoint}, {{method: '{method}', ...{options}}})"
            else:
                return f"fetch({endpoint})" if method == 'GET' else f"fetch({endpoint}, {{method: '{method}'}})"
        
        return "null"


def generate_typescript(ast: Program) -> str:
    """Main entry point for TypeScript code generation"""
    generator = TSCodeGenerator(ast)
    return generator.generate()
