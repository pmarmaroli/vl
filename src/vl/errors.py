"""
VL Error Handling
Unified error classes with rich diagnostic information
"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class SourceLocation:
    """Location in source code"""
    line: int
    column: int
    length: int = 1
    
    def __str__(self):
        return f"{self.line}:{self.column}"


class VLError(Exception):
    """Base class for all VL errors"""
    
    def __init__(self, message: str, location: Optional[SourceLocation] = None, 
                 source_line: str = "", hints: List[str] = None):
        self.message = message
        self.location = location
        self.source_line = source_line
        self.hints = hints or []
        super().__init__(self._format_error())
    
    def _format_error(self) -> str:
        """Format error with source context"""
        parts = []
        
        # Error type and message
        error_type = self.__class__.__name__
        if self.location:
            parts.append(f"{error_type} at line {self.location.line}, column {self.location.column}:")
        else:
            parts.append(f"{error_type}:")
        parts.append(f"  {self.message}")
        
        # Source line with pointer
        if self.source_line and self.location:
            parts.append("")
            parts.append(f"  {self.location.line} | {self.source_line}")
            pointer_offset = len(str(self.location.line)) + 3 + self.location.column - 1
            parts.append(" " * pointer_offset + "^" * self.location.length)
        
        # Hints
        if self.hints:
            parts.append("")
            for hint in self.hints:
                parts.append(f"  Hint: {hint}")
        
        return "\n".join(parts)


class LexerError(VLError):
    """Error during tokenization"""
    pass


class ParseError(VLError):
    """Error during parsing"""
    pass


class TypeError(VLError):
    """Error during type checking"""
    pass


class CodeGenError(VLError):
    """Error during code generation"""
    pass


def format_error_context(source: str, line: int, column: int) -> str:
    """Extract the source line for error context"""
    lines = source.split('\n')
    if 0 < line <= len(lines):
        return lines[line - 1]
    return ""
