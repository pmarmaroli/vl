"""
Test script to verify all fixes are working
"""

test_cases = [
    # Test 1: Attribute assignment (self.x = value)
    {
        "name": "Attribute Assignment",
        "code": """
class Counter:
    def __init__(self, start=0):
        self.value = start
    
    def increment(self):
        self.value += 1
        return self.value
""".strip()
    },
    
    # Test 2: Tuple return
    {
        "name": "Tuple Return",
        "code": """
def get_coords():
    x = 10
    y = 20
    return x, y
""".strip()
    },
    
    # Test 3: Try/except with proper indentation
    {
        "name": "Try/Except",
        "code": """
def safe_divide(a, b):
    try:
        result = a / b
        return result
    except ZeroDivisionError:
        return 0
""".strip()
    },
    
    # Test 4: Nested function
    {
        "name": "Nested Function",
        "code": """
def outer(x):
    def inner(y):
        return x + y
    return inner
""".strip()
    },
    
    # Test 5: List comprehension (should not have double brackets)
    {
        "name": "List Comprehension",
        "code": """
def squares(numbers):
    return [x*x for x in numbers]
""".strip()
    },
    
    # Test 6: For loop with 'item' variable (should not rename)
    {
        "name": "For Loop with 'item'",
        "code": """
def process_items(items):
    total = 0
    for item in items:
        total += item
    return total
""".strip()
    },
    
    # Test 7: Function with type hints but no Any
    {
        "name": "Type Hints without Any",
        "code": """
def greet(name: str, age: int) -> str:
    return f"Hello {name}, you are {age} years old"
""".strip()
    }
]

import ast

def test_roundtrip(code):
    """Test Python -> VL -> Python roundtrip"""
    # Import the VL modules
    import sys
    sys.path.insert(0, 'vl-compiler/src')
    
    from vl.py_to_vl import PythonToVLConverter
    from vl.lexer import tokenize
    from vl.parser import Parser
    from vl.codegen.python import PythonCodeGenerator
    
    try:
        # Convert Python to VL
        converter = PythonToVLConverter()
        vl_code = converter.convert(code)
        
        # Convert VL back to Python
        tokens = tokenize(vl_code)
        parser = Parser(tokens, vl_code)
        program = parser.parse()
        generator = PythonCodeGenerator(program)
        python_code = generator.generate()
        
        # Compare ASTs
        try:
            original_ast = ast.parse(code)
            roundtrip_ast = ast.parse(python_code)
            
            # Compare dumps
            original_dump = ast.dump(original_ast)
            roundtrip_dump = ast.dump(roundtrip_ast)
            
            success = original_dump == roundtrip_dump
            
            return {
                "success": success,
                "vl_code": vl_code,
                "python_code": python_code,
                "original_ast": original_dump[:200],
                "roundtrip_ast": roundtrip_dump[:200]
            }
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error in roundtrip: {e}",
                "vl_code": vl_code,
                "python_code": python_code
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Conversion error: {e}",
            "vl_code": vl_code if 'vl_code' in locals() else "N/A"
        }

# Run tests
print("=" * 80)
print("TESTING ROUNDTRIP CONVERSION FIXES")
print("=" * 80)

successes = 0
failures = 0

for test_case in test_cases:
    print(f"\n{'='*80}")
    print(f"TEST: {test_case['name']}")
    print(f"{'='*80}")
    print("\nOriginal Python:")
    print(test_case['code'])
    print()
    
    result = test_roundtrip(test_case['code'])
    
    if result['success']:
        print("[SUCCESS] - Roundtrip matched!")
        successes += 1
    else:
        print("[FAILED]")
        failures += 1
        if 'error' in result:
            print(f"Error: {result['error']}")
    
    print(f"\nVL Code:\n{result.get('vl_code', 'N/A')}")
    print(f"\nRoundtrip Python:\n{result.get('python_code', 'N/A')}")

print(f"\n{'='*80}")
print(f"RESULTS: {successes}/{len(test_cases)} tests passed ({successes/len(test_cases)*100:.1f}%)")
print(f"{'='*80}")
