"""
VL Lexer (Tokenizer)
Converts VL source code into a stream of tokens
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional
import re

# Support both package and standalone usage
try:
    from .errors import LexerError, SourceLocation
except ImportError:
    from errors import LexerError, SourceLocation


class TokenType(Enum):
    """All possible token types in VL"""
    
    # Keywords
    META = auto()
    DEPS = auto()
    EXPORT = auto()
    FN = auto()
    INPUT = auto()      # i:
    OUTPUT = auto()     # o:
    RET = auto()
    VAR = auto()        # v:
    OP = auto()
    IF = auto()
    ELSE = auto()       # else:
    FOR = auto()
    WHILE = auto()
    CLASS = auto()      # class:
    SELF = auto()       # self
    DECORATOR = auto()  # @decorator
    IN = auto()         # in operator for membership testing
    API = auto()
    ASYNC = auto()
    FILTER = auto()
    MAP = auto()
    PARSE = auto()
    UI = auto()
    STATE = auto()
    PROPS = auto()
    ON = auto()
    RENDER = auto()
    DATA = auto()
    GROUPBY = auto()
    AGG = auto()
    SORT = auto()
    FILE = auto()
    FFI = auto()
    PY = auto()          # py: for Python passthrough
    
    # Types
    TYPE_INT = auto()
    TYPE_FLOAT = auto()
    TYPE_STR = auto()
    TYPE_BOOL = auto()
    TYPE_ARR = auto()
    TYPE_OBJ = auto()
    TYPE_MAP = auto()
    TYPE_SET = auto()
    TYPE_ANY = auto()
    TYPE_VOID = auto()
    TYPE_PROMISE = auto()
    TYPE_FUNC = auto()
    
    # Operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    FLOOR_DIVIDE = auto()  # //
    MODULO = auto()
    POWER = auto()
    EQUAL = auto()
    NOT_EQUAL = auto()
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    AMPERSAND = auto()      # & (bitwise AND for Python passthrough)
    
    # Delimiters
    COLON = auto()          # :
    PIPE = auto()           # |
    COMMA = auto()          # ,
    EQUALS = auto()         # =
    PLUS_EQUALS = auto()    # +=
    MINUS_EQUALS = auto()   # -=
    TIMES_EQUALS = auto()   # *=
    DIV_EQUALS = auto()     # /=
    DOTDOT = auto()         # .. (range operator)
    QUESTION = auto()       # ?
    DOLLAR = auto()         # $
    AT = auto()             # @
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    DOT = auto()            # .
    
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    
    # Special
    NEWLINE = auto()
    EOF = auto()
    COMMENT = auto()


@dataclass
class Token:
    """Represents a single token"""
    type: TokenType
    value: str
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.name}, '{self.value}', {self.line}:{self.column})"


class Lexer:
    """VL Lexer - converts source code to tokens"""
    
    # Keywords mapping (includes optimized short forms)
    KEYWORDS = {
        # Standard keywords
        'meta': TokenType.META,
        'deps': TokenType.DEPS,
        'export': TokenType.EXPORT,
        'fn': TokenType.FN,
        'i': TokenType.INPUT,
        'o': TokenType.OUTPUT,
        'ret': TokenType.RET,
        'v': TokenType.VAR,
        'op': TokenType.OP,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'for': TokenType.FOR,
        'while': TokenType.WHILE,
        'in': TokenType.IN,
        'class': TokenType.CLASS,
        'self': TokenType.SELF,
        'api': TokenType.API,
        'async': TokenType.ASYNC,
        'filter': TokenType.FILTER,
        'map': TokenType.MAP,
        'parse': TokenType.PARSE,
        'ui': TokenType.UI,
        'state': TokenType.STATE,
        'props': TokenType.PROPS,
        'on': TokenType.ON,
        'render': TokenType.RENDER,
        'data': TokenType.DATA,
        'groupBy': TokenType.GROUPBY,
        'agg': TokenType.AGG,
        'sort': TokenType.SORT,
        'file': TokenType.FILE,
        'ffi': TokenType.FFI,
        'py': TokenType.PY,
        # Optimized short forms (token-efficient mode)
        'M': TokenType.META,      # M: = meta:
        'D': TokenType.DATA,      # D: = data: (context: after | it's data, at start it's deps)
        'E': TokenType.EXPORT,    # E: = export:
        'F': TokenType.FN,        # F: = fn:
        'R': TokenType.RET,       # R: = ret:
    }
    
    # Types mapping (includes optimized single-char forms)
    # Note: These are kept for reference but types are now handled by parser
    # to allow str(), int(), etc. as function calls
    TYPE_NAMES = {
        # Standard type names
        'int', 'float', 'str', 'bool', 'arr', 'obj', 'map', 'set', 
        'any', 'void', 'promise', 'func',
        # Optimized single-char type aliases
        'I', 'N', 'S', 'B', 'A', 'O', 'V', 'P', 'L'
    }
    
    # Operators mapping
    OPERATORS = {
        '+': TokenType.PLUS,
        '-': TokenType.MINUS,
        '*': TokenType.MULTIPLY,
        '/': TokenType.DIVIDE,
        '//': TokenType.FLOOR_DIVIDE,
        '%': TokenType.MODULO,
        '**': TokenType.POWER,
        '==': TokenType.EQUAL,
        '!=': TokenType.NOT_EQUAL,
        '<': TokenType.LESS_THAN,
        '>': TokenType.GREATER_THAN,
        '<=': TokenType.LESS_EQUAL,
        '>=': TokenType.GREATER_EQUAL,
        '&&': TokenType.AND,
        '||': TokenType.OR,
        '!': TokenType.NOT,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def current_char(self) -> Optional[str]:
        """Get current character without advancing"""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Look ahead at character without advancing"""
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self) -> Optional[str]:
        """Move to next character"""
        if self.pos >= len(self.source):
            return None
        
        char = self.source[self.pos]
        self.pos += 1
        
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        
        return char
    
    def skip_whitespace(self):
        """Skip spaces and tabs (but not newlines)"""
        while self.current_char() in (' ', '\t', '\r'):
            self.advance()
    
    def skip_comment(self):
        """Skip comment lines starting with #, but return special @-prefixed comments as tokens"""
        if self.current_char() == '#':
            start_line = self.line
            start_col = self.column
            self.advance()  # consume #
            
            # Skip whitespace after #
            while self.current_char() and self.current_char() == ' ':
                self.advance()
            
            # Read the rest of the comment
            comment_text = ''
            while self.current_char() and self.current_char() != '\n':
                comment_text += self.current_char()
                self.advance()
            
            # Check if this is a special @-prefixed comment
            if comment_text.startswith('@doc '):
                return Token(TokenType.COMMENT, comment_text, start_line, start_col)
            
            # Otherwise, it's a regular comment - skip it
            return None
    
    def read_number(self) -> Token:
        """Read a numeric literal. Stops at .. (range operator)"""
        start_line = self.line
        start_col = self.column
        num_str = ''
        has_decimal = False
        
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            # Check for range operator (..)
            if self.current_char() == '.' and self.peek_char() == '.':
                break  # Stop before range operator
            
            # Handle decimal point
            if self.current_char() == '.':
                if has_decimal:
                    break  # Already have decimal, this is something else
                has_decimal = True
            
            num_str += self.current_char()
            self.advance()
        
        return Token(TokenType.NUMBER, num_str, start_line, start_col)
    
    def read_string(self) -> Token:
        """Read a string literal with support for complex ${...} interpolation"""
        start_line = self.line
        start_col = self.column
        
        # Skip opening quote
        quote_char = self.current_char()
        self.advance()
        
        string_val = ''
        interpolation_depth = 0  # Track nesting level inside ${...}
        
        while self.current_char():
            # Check if we're starting an interpolation
            if self.current_char() == '$' and self.peek_char() == '{':
                string_val += self.current_char()  # Add $
                self.advance()
                string_val += self.current_char()  # Add {
                self.advance()
                interpolation_depth += 1
                continue
            
            # Track closing braces in interpolation
            if interpolation_depth > 0:
                if self.current_char() == '{':
                    interpolation_depth += 1
                elif self.current_char() == '}':
                    interpolation_depth -= 1
                
                # Inside interpolation, quotes don't terminate the string
                string_val += self.current_char()
                self.advance()
                continue
            
            # Outside interpolation, check for string termination
            if self.current_char() == quote_char:
                break
            
            # Handle escape sequences
            if self.current_char() == '\\':
                self.advance()
                escape_char = self.current_char()
                if escape_char == 'n':
                    string_val += '\n'
                elif escape_char == 't':
                    string_val += '\t'
                elif escape_char == '\\':
                    string_val += '\\'
                elif escape_char == quote_char:
                    string_val += quote_char
                else:
                    # Preserve unknown escapes (e.g., \uXXXX) by keeping the backslash
                    string_val += '\\' + escape_char
                self.advance()
            else:
                string_val += self.current_char()
                self.advance()
        
        # Skip closing quote
        if self.current_char() == quote_char:
            self.advance()
        else:
            loc = SourceLocation(start_line, start_col)
            raise LexerError(
                f"Unterminated string literal",
                location=loc,
                hints=["String must be closed with matching quote", f"String started with {quote_char}"]
            )
        
        return Token(TokenType.STRING, string_val, start_line, start_col)
    
    def read_identifier(self) -> Token:
        """Read an identifier or keyword"""
        start_line = self.line
        start_col = self.column
        identifier = ''
        
        # First character is letter or underscore
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_' or 
                                       (self.current_char() == '-' and self.peek_char() != '=')):
            identifier += self.current_char()
            self.advance()
        
        # Check if it's a keyword (these are always keywords, never identifiers)
        if identifier in self.KEYWORDS:
            return Token(self.KEYWORDS[identifier], identifier, start_line, start_col)
        
        # All other identifiers including type names (str, int, etc.) are treated as IDENTIFIER
        # The parser will interpret them as types in type contexts
        # This allows str(), int(), etc. to work as function calls
        return Token(TokenType.IDENTIFIER, identifier, start_line, start_col)
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source code"""
        while self.pos < len(self.source):
            self.skip_whitespace()
            
            char = self.current_char()
            if not char:
                break
            
            # Handle comments - may return a COMMENT token for special comments
            if char == '#':
                comment_token = self.skip_comment()
                if comment_token:
                    self.tokens.append(comment_token)
                continue
            
            # Newlines
            if char == '\n':
                token = Token(TokenType.NEWLINE, '\\n', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Numbers
            if char.isdigit():
                self.tokens.append(self.read_number())
                continue
                
            # Identifiers and keywords (start with letter or underscore)
            # But wait, what if it's a number like 1.2? read_number handles it.
            # What if it is a dot operator?
            if char == '.':
                # Check for range operator (..) first!
                if self.peek_char() == '.':
                    token = Token(TokenType.DOTDOT, '..', self.line, self.column)
                    self.tokens.append(token)
                    self.advance()
                    self.advance()
                    continue
                
                # Check if it's part of a number (e.g. .5)
                if self.peek_char() and self.peek_char().isdigit():
                     self.tokens.append(self.read_number())
                     continue
                
                # Otherwise it's a DOT delimiter
                token = Token(TokenType.DOT, '.', self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Strings
            if char in ('"', "'"):
                self.tokens.append(self.read_string())
                continue
            
            # Identifiers and keywords
            if char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
                continue
            
            # Two-character operators
            two_char = char + (self.peek_char() or '')
            if two_char in self.OPERATORS:
                token = Token(self.OPERATORS[two_char], two_char, self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            # Compound assignment operators and range operator
            compound_ops = {
                '+=': TokenType.PLUS_EQUALS,
                '-=': TokenType.MINUS_EQUALS,
                '*=': TokenType.TIMES_EQUALS,
                '/=': TokenType.DIV_EQUALS,
                '..': TokenType.DOTDOT,
            }
            if two_char in compound_ops:
                token = Token(compound_ops[two_char], two_char, self.line, self.column)
                self.tokens.append(token)
                self.advance()
                self.advance()
                continue
            
            # Single-character operators
            if char in self.OPERATORS:
                token = Token(self.OPERATORS[char], char, self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Delimiters
            delimiters = {
                ':': TokenType.COLON,
                '|': TokenType.PIPE,
                ',': TokenType.COMMA,
                '=': TokenType.EQUALS,
                '?': TokenType.QUESTION,
                '$': TokenType.DOLLAR,
                '@': TokenType.AT,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
                '&': TokenType.AMPERSAND,  # Bitwise AND (for Python passthrough)
            }
            
            if char in delimiters:
                token = Token(delimiters[char], char, self.line, self.column)
                self.tokens.append(token)
                self.advance()
                continue
            
            # Unknown character
            loc = SourceLocation(self.line, self.column)
            raise LexerError(
                f"Unexpected character '{char}'",
                location=loc,
                hints=["Check for typos or unsupported characters"]
            )
        
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


def tokenize(source: str) -> List[Token]:
    """Convenience function to tokenize VL source code"""
    lexer = Lexer(source)
    return lexer.tokenize()


if __name__ == "__main__":
    # Test the lexer
    test_code = """
    F:sum|I,I|I|ret:op:+(i0,i1)
    """
    
    tokens = tokenize(test_code)
    for token in tokens:
        if token.type != TokenType.NEWLINE:
            print(token)
