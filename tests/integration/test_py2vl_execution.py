"""Test if generated code is functionally correct by executing it"""
from vl.py_to_vl import convert_python_to_vl
from vl.compiler import Compiler, TargetLanguage
import sys
import io
import traceback

def test_execution(name, python_code):
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"{'='*60}")
    
    # Execute original
    print("Executing original Python...")
    try:
        exec_globals = {}
        exec(python_code, exec_globals)
        print("✓ Original executes successfully")
        original_works = True
    except Exception as e:
        print(f"✗ Original failed: {e}")
        original_works = False
    
    # Convert to VL
    try:
        vl_code = convert_python_to_vl(python_code)
    except Exception as e:
        print(f"✗ Conversion failed: {e}")
        return False
    
    # Compile back to Python
    try:
        compiler = Compiler(vl_code, TargetLanguage.PYTHON)
        generated_python = compiler.compile()
    except Exception as e:
        print(f"✗ Compilation failed: {e}")
        return False
    
    # Execute generated
    print("Executing generated Python...")
    try:
        exec_globals = {}
        exec(generated_python, exec_globals)
        print("✓ Generated executes successfully")
        generated_works = True
    except Exception as e:
        print(f"✗ Generated failed: {e}")
        print(f"\nGenerated code:")
        print(generated_python)
        traceback.print_exc()
        generated_works = False
    
    return original_works and generated_works

# Test real-world Python code patterns
tests = [
    ("Simple assignment", "x = 1\ny = 2\nz = x + y"),
    
    ("Function definition", """
def add(a, b):
    return a + b
result = add(5, 3)
"""),
    
    ("Dict subscript assignment", """
settings = {"downlink": {}}
settings["downlink"]["delay"] = 100
"""),
    
    ("If statement", """
x = 10
if x > 5:
    result = "large"
else:
    result = "small"
"""),
    
    ("For loop", """
total = 0
for i in range(5):
    total += i
"""),
    
    ("List comprehension", """
numbers = [1, 2, 3, 4, 5]
squares = [x * x for x in numbers]
"""),
    
    ("Try-except", """
try:
    x = 1 / 1
    result = "ok"
except:
    result = "error"
"""),
]

results = []
for name, code in tests:
    success = test_execution(name, code)
    results.append((name, success))

print(f"\n\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")
passed = sum(1 for _, success in results if success)
total = len(results)
print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
print()
for name, success in results:
    status = "✓" if success else "✗"
    print(f"{status} {name}")
