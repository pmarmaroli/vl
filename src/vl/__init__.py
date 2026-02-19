"""
VL (Vibe Language) - Universal Programming Language for the AI Era

A token-efficient, multi-target programming language designed for
optimal collaboration between humans and AI language models.
"""

__version__ = "0.1.3"
__author__ = "VL Contributors"

from .compiler import Compiler, TargetLanguage
from .lexer import Lexer
from .parser import Parser
from .type_checker import TypeChecker

__all__ = ['Compiler', 'TargetLanguage', 'Lexer', 'Parser', 'TypeChecker']
