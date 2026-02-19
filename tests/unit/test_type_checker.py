"""
Type Checker Test Script
"""

import sys
from pathlib import Path

# Add parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent.parent / 'src'
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from vl.compiler import Compiler

# Test 1: Correct type annotation
print("Test 1: v:x:int=42")
test1 = "v:x:int=42"
try:
    c1 = Compiler(test1)
    output = c1.compile()
    print(f"  PASSED: Generated: {output.strip()}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test 2: Type mismatch - string to int
print("\nTest 2: v:x:int='hello' (should detect type error)")
test2 = "v:x:int='hello'"
try:
    c2 = Compiler(test2)
    output = c2.compile()
    print(f"  UNEXPECTED: Should have type error, got: {output.strip()}")
except TypeError as e:
    print(f"  PASSED: Detected type error:")
    print(f"    {str(e)[:150]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Test 3: Float to int (should allow due to numeric compatibility)
print("\nTest 3: v:x:float=42 (int->float should be ok)")
test3 = "v:x:float=42"
try:
    c3 = Compiler(test3)
    output = c3.compile()
    print(f"  PASSED: {output.strip()}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test 4: Function return type mismatch
print("\nTest 4: Function returning wrong type")
test4 = """
F:add|I,I|S|ret:op:+(i0,i1)
"""
try:
    c4 = Compiler(test4)
    output = c4.compile()
    print(f"  UNEXPECTED: Should have type error")
except TypeError as e:
    print(f"  PASSED: Detected return type error")
    print(f"    {str(e)[:150]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Test 5: Compile with warnings instead of errors
print("\nTest 5: Compile with warnings (no raise)")
test5 = "v:x:int='hello'"
try:
    c5 = Compiler(test5)
    output, warnings = c5.compile_with_warnings()
    print(f"  Code generated: {output.strip()}")
    print(f"  Warnings: {len(warnings)}")
    for w in warnings:
        print(f"    - {w.message[:80]}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Test 6: No type annotation - should work
print("\nTest 6: v:x=42 (no type annotation)")
test6 = "v:x=42"
try:
    c6 = Compiler(test6)
    output = c6.compile()
    print(f"  PASSED: {output.strip()}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n--- Type Checker Tests Complete ---")
