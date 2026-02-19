"""
VL Configuration
Centralized configuration for VL compiler and code generators
"""

# Boolean optimization settings
BOOLEAN_CHAIN_MIN_LENGTH = 3  # Minimum chain length for all()/any() optimization

# Code generation settings
DEFAULT_TARGET = 'python'
DEFAULT_INDENT = '    '  # 4 spaces

# Type checking settings
TYPE_CHECK_ENABLED_DEFAULT = True

# Output settings
MAX_LINE_LENGTH = 120  # Recommended max line length for generated code

# Optimization flags
OPTIMIZE_BOOLEAN_CHAINS = True  # Convert 3+ && to all() or || to any()
OPTIMIZE_STRING_CONCAT = False  # Future: optimize repeated string concatenation
OPTIMIZE_DEAD_CODE = False  # Future: remove unreachable code

# Target-specific settings
TARGET_SETTINGS = {
    'python': {
        'file_extension': '.py',
        'boolean_optimization': True,
        'supports_type_hints': True,
        'requires_semicolons': False,
    },
    'javascript': {
        'file_extension': '.js',
        'boolean_optimization': False,
        'supports_type_hints': False,
        'requires_semicolons': True,
    },
    'typescript': {
        'file_extension': '.ts',
        'boolean_optimization': False,
        'supports_type_hints': True,
        'requires_semicolons': True,
    },
    'c': {
        'file_extension': '.c',
        'boolean_optimization': False,
        'supports_type_hints': True,
        'requires_semicolons': True,
    },
    'rust': {
        'file_extension': '.rs',
        'boolean_optimization': False,
        'supports_type_hints': True,
        'requires_semicolons': True,
    },
}

# Runtime settings
EXECUTION_TIMEOUT = 30  # Max seconds for code execution in tests

# Logging settings
LOG_LEVEL_DEFAULT = 'INFO'  # INFO, DEBUG, WARNING, ERROR

def get_target_extension(target: str) -> str:
    """Get file extension for a target language"""
    target_lower = target.lower()
    settings = TARGET_SETTINGS.get(target_lower, {})
    return settings.get('file_extension', '.txt')

def should_optimize_booleans(target: str) -> bool:
    """Check if boolean optimization is enabled for target"""
    if not OPTIMIZE_BOOLEAN_CHAINS:
        return False
    target_lower = target.lower()
    settings = TARGET_SETTINGS.get(target_lower, {})
    return settings.get('boolean_optimization', False)

def get_indent(indent_level: int = 1) -> str:
    """Get indentation string for given level"""
    return DEFAULT_INDENT * indent_level
