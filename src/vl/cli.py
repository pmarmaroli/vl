#!/usr/bin/env python3
"""
VL (Vibe Language) Interpreter
Main entry point for executing VL programs

Usage:
    python vl.py <file.vl>
    python vl.py --version
    python vl.py --help
"""

import sys
import argparse
from pathlib import Path
from .lexer import tokenize, TokenType
from .parser import Parser, ParseError
from .codegen.python import PythonCodeGenerator
from .codegen.javascript import JSCodeGenerator
from .codegen.typescript import TSCodeGenerator
from .codegen.c import CCodeGenerator
from .codegen.rust import RustCodeGenerator
from .logging_config import setup_logging, get_logger

# Setup logging
logger = get_logger(__name__)

# Version info
__version__ = "0.1.0-alpha"
__author__ = "Patrick Marmaroli"

def main():
    """Main entry point for VL interpreter"""
    parser = argparse.ArgumentParser(
        description="VL (Vibe Language) Interpreter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vl.py program.vl              Run a VL program
  vl.py --version               Show version
  vl.py --debug program.vl      Run with debug output
        """
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        type=str,
        help='VL source file to execute (.vl)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'VL Interpreter v{__version__}'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output (show tokens, AST)'
    )
    
    parser.add_argument(
        '--target',
        choices=['python', 'py', 'javascript', 'js', 'typescript', 'ts', 'c', 'rust', 'rs'],
        default='python',
        help='Target language: python/py, javascript/js, typescript/ts, c, rust/rs (default: python)'
    )

    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output file for compiled code'
    )

    parser.add_argument(
        '--tokens-only',
        action='store_true',
        help='Only tokenize and show tokens (for debugging)'
    )
    
    parser.add_argument(
        '--ast-only',
        action='store_true',
        help='Only parse and show AST (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Setup logging based on debug flag
    setup_logging(debug=args.debug)
    
    # If no file provided, show help
    if not args.file:
        parser.print_help()
        sys.exit(1)
    
    # Check file exists
    vl_file = Path(args.file)
    if not vl_file.exists():
        logger.error(f"File not found: {args.file}")
        sys.exit(1)
    
    if not vl_file.suffix == '.vl':
        logger.warning(f"File does not have .vl extension: {args.file}")
    
    # Read source code
    try:
        source_code = vl_file.read_text(encoding='utf-8')
        logger.debug(f"Read {len(source_code)} characters from {args.file}")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        sys.exit(1)
    
    # 1. Tokenize (Lexer)
    try:
        tokens = tokenize(source_code)
        logger.debug(f"Tokenized into {len(tokens)} tokens")
    except Exception as e:
        logger.error(f"Lexer Error: {e}")
        sys.exit(1)

    # Handle --tokens-only flag
    if args.tokens_only:
        for token in tokens:
            if token.type != TokenType.NEWLINE:
                print(token)
        sys.exit(0)

    # 2. Parse (Parser -> AST)
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        logger.debug(f"Successfully parsed AST with {len(ast.statements)} statements")
    except ParseError as e:
        logger.error(f"Parser Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected Parser Error: {e}")
        # Check if debug mode to show full trace
        if args.debug:
            raise
        sys.exit(1)

    # Handle --ast-only flag
    if args.ast_only:
        print(ast)
        sys.exit(0)

    # 3. Code Generation
    try:
        # Normalize target names
        target = args.target.lower()
        target_map = {
            'python': 'python', 'py': 'python',
            'javascript': 'javascript', 'js': 'javascript',
            'typescript': 'typescript', 'ts': 'typescript',
            'c': 'c',
            'rust': 'rust', 'rs': 'rust'
        }
        target = target_map.get(target, 'python')
        
        if target == 'python':
            generator = PythonCodeGenerator(ast)
            generated_code = generator.generate()
        elif target == 'javascript':
            generator = JSCodeGenerator(ast)
            generated_code = generator.generate()
        elif target == 'typescript':
            generator = TSCodeGenerator(ast)
            generated_code = generator.generate()
        elif target == 'c':
            generator = CCodeGenerator(ast)
            generated_code = generator.generate()
        elif target == 'rust':
            generator = RustCodeGenerator(ast)
            generated_code = generator.generate()
        else:
            logger.error(f"Unsupported target: {target}")
            sys.exit(1)
        
        logger.info(f"Successfully generated {target} code")
        logger.debug(f"Generated {len(generated_code)} characters")
    except Exception as e:
        logger.error(f"Code Generation Error: {e}")
        if args.debug:
            raise
        sys.exit(1)

    if args.debug:
        logger.debug(f"Generated {target} Code:\n{generated_code}\n")

    # Output to file if requested
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            logger.info(f"Written to {args.output}")
        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            sys.exit(1)
        # If we compiled to file, we generally stop unless it's python and we implicitly want to run?
        # Standard compiler behavior: compile -> exit. 
        # Interpreter behavior: run.
        # If output is specified, we behave like a compiler.
        return 0

    # 4. Execute (only for Python currently)
    if target == 'python':
        logger.debug("Executing generated Python code...")
        try:
            # Create a new namespace for execution
            exec_globals = {"__name__": "__main__"}
            exec(generated_code, exec_globals)
            logger.debug("Execution completed successfully")
        except Exception as e:
            logger.error(f"Runtime Error: {e}")
            sys.exit(1)
    else:
        # For other targets without output file, assume we just print it
        print(generated_code)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
