"""
VL Compiler
Main compiler orchestrator that coordinates lexing, parsing, and code generation
"""

import sys
from pathlib import Path
from typing import Optional, List
from enum import Enum

# Support both package and standalone usage
try:
    from .lexer import Lexer
    from .parser import Parser
    from .type_checker import type_check
    from .errors import TypeError
    from .codegen.python import PythonCodeGenerator
    from .codegen.javascript import JSCodeGenerator
    from .codegen.typescript import TSCodeGenerator
    from .codegen.c import CCodeGenerator
    from .codegen.rust import RustCodeGenerator
except ImportError:
    from lexer import Lexer
    from parser import Parser
    from type_checker import type_check
    from errors import TypeError
    from codegen.python import PythonCodeGenerator
    from codegen.javascript import JSCodeGenerator
    from codegen.typescript import TSCodeGenerator
    from codegen.c import CCodeGenerator
    from codegen.rust import RustCodeGenerator


class TargetLanguage(Enum):
    """Supported compilation targets"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    C = "c"
    RUST = "rust"


class Compiler:
    """
    VL Compiler - compiles VL source code to target languages
    
    Usage:
        compiler = Compiler(source_code, TargetLanguage.PYTHON)
        output_code = compiler.compile()
    """
    
    def __init__(self, source: str, target: TargetLanguage = TargetLanguage.PYTHON,
                 type_check_enabled: bool = True):
        self.source = source
        self.target = target
        self.type_check_enabled = type_check_enabled
        self.lexer = None
        self.parser = None
        self.ast = None
        self.type_errors: List[TypeError] = []
        self.output = None
    
    def compile(self) -> str:
        """
        Compile VL source code to target language
        
        Returns:
            Generated code in target language
        
        Raises:
            TypeError: If type checking is enabled and errors are found
        """
        # Step 1: Lexical analysis (tokenization)
        self.lexer = Lexer(self.source)
        tokens = self.lexer.tokenize()
        
        # Step 2: Syntax analysis (parsing)
        self.parser = Parser(tokens, self.source)  # Pass source for error context
        self.ast = self.parser.parse()
        
        # Step 3: Type checking (optional)
        if self.type_check_enabled:
            self.type_errors = type_check(self.ast, self.source)
            if self.type_errors:
                # Report first error (or all, depending on preference)
                raise self.type_errors[0]
        
        # Step 4: Code generation
        self.output = self._generate_code()
        
        return self.output
    
    def compile_with_warnings(self) -> tuple[str, List[TypeError]]:
        """
        Compile VL source code, returning warnings instead of raising errors.
        
        Returns:
            Tuple of (generated code, list of type errors as warnings)
        """
        # Step 1: Lexical analysis
        self.lexer = Lexer(self.source)
        tokens = self.lexer.tokenize()
        
        # Step 2: Parsing
        self.parser = Parser(tokens, self.source)
        self.ast = self.parser.parse()
        
        # Step 3: Type checking (collect but don't raise)
        if self.type_check_enabled:
            self.type_errors = type_check(self.ast, self.source)
        
        # Step 4: Code generation (always proceed)
        self.output = self._generate_code()
        
        return self.output, self.type_errors
    
    def _generate_code(self) -> str:
        """Generate code for the target language"""
        if self.target == TargetLanguage.PYTHON:
            generator = PythonCodeGenerator(self.ast)
            return generator.generate()
        
        elif self.target == TargetLanguage.JAVASCRIPT:
            generator = JSCodeGenerator(self.ast)
            return generator.generate()
        
        elif self.target == TargetLanguage.TYPESCRIPT:
            generator = TSCodeGenerator(self.ast)
            return generator.generate()
        
        elif self.target == TargetLanguage.C:
            generator = CCodeGenerator(self.ast)
            return generator.generate()
        
        elif self.target == TargetLanguage.RUST:
            generator = RustCodeGenerator(self.ast)
            return generator.generate()
        
        else:
            raise ValueError(f"Unsupported target language: {self.target}")
    
    def compile_file(self, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Compile a VL file to target language
        
        Args:
            input_path: Path to .vl source file
            output_path: Path to output file (auto-generated if None)
        
        Returns:
            Path to generated output file
        """
        # Read source file
        source = input_path.read_text(encoding='utf-8')
        
        # Compile
        output_code = self.compile()
        
        # Determine output path
        if output_path is None:
            output_path = self._auto_output_path(input_path)
        
        # Write output file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_code, encoding='utf-8')
        
        return output_path
    
    def _auto_output_path(self, input_path: Path) -> Path:
        """
        Generate output path based on input path and target language
        
        Example:
            input: hello.vl, target: python  -> output: hello.py
            input: hello.vl, target: javascript -> output: hello.js
        """
        extensions = {
            TargetLanguage.PYTHON: '.py',
            TargetLanguage.JAVASCRIPT: '.js',
            TargetLanguage.TYPESCRIPT: '.ts',
            TargetLanguage.C: '.c',
            TargetLanguage.RUST: '.rs',
        }
        
        ext = extensions.get(self.target, '.txt')
        return input_path.with_suffix(ext)


def compile_vl(source: str, target: str = "python") -> str:
    """
    Convenience function to compile VL source code
    
    Args:
        source: VL source code string
        target: Target language ('python', 'javascript', etc.)
    
    Returns:
        Generated code in target language
    """
    target_enum = TargetLanguage(target.lower())
    compiler = Compiler(source, target_enum)
    return compiler.compile()


def compile_vl_file(input_path: str, output_path: Optional[str] = None, 
                     target: str = "python") -> str:
    """
    Convenience function to compile a VL file
    
    Args:
        input_path: Path to .vl source file
        output_path: Path to output file (optional)
        target: Target language ('python', 'javascript', etc.)
    
    Returns:
        Path to generated output file
    """
    target_enum = TargetLanguage(target.lower())
    compiler = Compiler("", target_enum)  # Source loaded from file
    
    input_path_obj = Path(input_path)
    output_path_obj = Path(output_path) if output_path else None
    
    result_path = compiler.compile_file(input_path_obj, output_path_obj)
    return str(result_path)


if __name__ == "__main__":
    # Simple test
    test_code = """
    F:sum|I,I|I|ret:op:+(i0,i1)
    """
    
    try:
        output = compile_vl(test_code, "python")
        print("Compiled successfully!")
        print("\nGenerated Python code:")
        print(output)
    except Exception as e:
        print(f"Compilation error: {e}")
        import traceback
        traceback.print_exc()
