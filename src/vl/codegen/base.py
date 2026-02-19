"""
Base Code Generator
Abstract base class for all VL code generators

This provides common functionality shared across all target language codegens:
- Indentation management
- Code emission
- Common expression/statement handling patterns
"""

from abc import ABC, abstractmethod
from typing import List
from ..ast_nodes import *


class BaseCodeGenerator(ABC):
    """
    Abstract base class for all code generators
    
    Subclasses must implement:
    - generate() -> str
    - _generate_statement(node: Statement) -> None
    - _generate_expression(node: Expression) -> str
    - Target-specific type mappings and syntax
    """
    
    def __init__(self, ast: Program):
        self.ast = ast
        self.code: List[str] = []
        self.indent_level: int = 0
        self._indent_string: str = "    "  # 4 spaces, can be overridden
    
    # ===== Code Emission =====
    
    def _emit(self, line: str = ""):
        """Emit a line of code with proper indentation"""
        if line:
            self.code.append(self._indent_string * self.indent_level + line)
        else:
            self.code.append("")
    
    def _get_output(self) -> str:
        """Get the generated code as a string"""
        return '\n'.join(self.code)
    
    # ===== Indentation Management =====
    
    def _indent(self):
        """Increase indentation level"""
        self.indent_level += 1
    
    def _dedent(self):
        """Decrease indentation level"""
        self.indent_level = max(0, self.indent_level - 1)
    
    # ===== Abstract Methods - Must be Implemented by Subclasses =====
    
    @abstractmethod
    def generate(self) -> str:
        """
        Generate complete code for the program
        
        Returns:
            Generated code in target language
        """
        pass
    
    @abstractmethod
    def _generate_statement(self, node: Statement):
        """
        Generate code for a statement
        
        This should handle all statement types and emit code
        """
        pass
    
    @abstractmethod
    def _generate_expression(self, node: Expression) -> str:
        """
        Generate code for an expression
        
        Returns:
            Expression code as string (no side effects)
        """
        pass
    
    @abstractmethod
    def _type_to_target(self, vl_type: Type) -> str:
        """
        Convert VL type to target language type
        
        Args:
            vl_type: VL type annotation
            
        Returns:
            Target language type string
        """
        pass
    
    # ===== Common Helper Methods =====
    
    def _replace_item_keyword(self, code: str, replacement: str) -> str:
        """
        Replace 'item' keyword with specific variable name
        
        Used in map/filter operations to replace generic 'item' with
        the actual iteration variable (e.g., 'x', 'i', etc.)
        
        Args:
            code: Code containing 'item' references
            replacement: Variable name to use instead
            
        Returns:
            Modified code
        """
        import re
        # Match 'item' as a whole word (not part of another identifier)
        pattern = r'\bitem\b'
        return re.sub(pattern, replacement, code)
    
    def _is_simple_expression(self, node: Expression) -> bool:
        """
        Check if an expression is simple enough for inline generation
        
        Returns:
            True if expression is a simple literal, identifier, or variable ref
        """
        return isinstance(node, (NumberLiteral, StringLiteral, BooleanLiteral, 
                                Identifier, VariableRef))
    
    def _needs_parentheses(self, node: Expression) -> bool:
        """
        Determine if an expression needs parentheses for precedence
        
        Returns:
            True if expression should be wrapped in parentheses
        """
        return isinstance(node, Operation)
    
    # ===== Common Pattern Implementations =====
    
    def _generate_function_signature_params(self, input_types: List[Type], 
                                           param_prefix: str = "i") -> List[str]:
        """
        Generate parameter list for function signature
        
        Args:
            input_types: List of input type annotations
            param_prefix: Prefix for parameter names (default: "i")
            
        Returns:
            List of parameter strings (e.g., ["i0: int", "i1: str"])
        """
        params = []
        for i, input_type in enumerate(input_types):
            target_type = self._type_to_target(input_type)
            params.append(f"{param_prefix}{i}: {target_type}")
        return params
    
    def _collect_dependencies(self) -> List[str]:
        """
        Extract dependencies from the AST
        
        Returns:
            List of dependency strings
        """
        if self.ast.dependencies:
            return self.ast.dependencies.dependencies
        return []
    
    # ===== Statement Type Dispatch (Optional Helper) =====
    
    def _dispatch_statement(self, node: Statement, handlers: dict):
        """
        Dispatch statement to appropriate handler based on type
        
        Args:
            node: Statement to generate
            handlers: Dict mapping node types to handler functions
            
        Example:
            handlers = {
                FunctionDef: self._gen_function,
                VariableDef: self._gen_variable,
                ...
            }
        """
        node_type = type(node)
        if node_type in handlers:
            handlers[node_type](node)
        else:
            self._emit(f"# Unhandled statement: {node_type.__name__}")
    
    # ===== Expression Type Dispatch (Optional Helper) =====
    
    def _dispatch_expression(self, node: Expression, handlers: dict) -> str:
        """
        Dispatch expression to appropriate handler based on type
        
        Args:
            node: Expression to generate
            handlers: Dict mapping node types to handler functions
            
        Returns:
            Generated expression code
        """
        node_type = type(node)
        if node_type in handlers:
            return handlers[node_type](node)
        else:
            return f"/* Unhandled expression: {node_type.__name__} */"
