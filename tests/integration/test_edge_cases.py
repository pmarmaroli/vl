"""Test edge cases and non-executable patterns"""
import sys
from pathlib import Path

if 'pytest' in sys.modules:
    import pytest
    pytest.skip("Edge case smoke test is manual-only", allow_module_level=True)

# Add parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent.parent / 'src'
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from vl.compiler import Compiler

print("Testing edge cases...\n")

# 1. UI Components (compile but don't execute - placeholder code)
try:
    c = Compiler('ui:Counter|state:count:int=0|render:div', type_check_enabled=False)
    code = c.compile()
    print("[1] UI Component: COMPILES")
    print("    (Generates placeholder - not executable)")
except Exception as e:
    print(f"[1] UI Component: FAILED - {e}")

# 2. Data pipeline in function return
try:
    c = Compiler('F:test|A|A|ret:data:i0|map:item*2', type_check_enabled=False)
    code = c.compile()
    exec(code)
    result = test([1, 2, 3])
    print(f"[2] Pipeline in return: COMPILES & EXECUTES")
    print(f"    test([1,2,3]) = {result}")
except Exception as e:
    print(f"[2] Pipeline in return: FAILED - {e}")

# 3. String literals in conditionals
try:
    c = Compiler('F:classify|I|S|ret:if:i0>0?\'positive\':\'negative\'', type_check_enabled=False)
    code = c.compile()
    exec(code)
    print(f"[3] Strings in conditionals: COMPILES & EXECUTES")
    print(f"    classify(5) = {classify(5)}, classify(-3) = {classify(-3)}")
except Exception as e:
    print(f"[3] Strings in conditionals: FAILED - {e}")

# 4. Nested data structures
try:
    c = Compiler('x={name:\'Alice\',age:30,items:[1,2,3]}', type_check_enabled=False)
    code = c.compile()
    exec(code)
    print(f"[4] Nested structures: COMPILES & EXECUTES")
    print(f"    x = {x}")
except Exception as e:
    print(f"[4] Nested structures: FAILED - {e}")

# 5. Complex boolean expressions
try:
    c = Compiler('F:validate|I,I,B|B|ret:(i0>0)&&(i1<100)&&i2', type_check_enabled=False)
    code = c.compile()
    exec(code)
    print(f"[5] Complex boolean: COMPILES & EXECUTES")
    print(f"    validate(5, 50, True) = {validate(5, 50, True)}")
except Exception as e:
    print(f"[5] Complex boolean: FAILED - {e}")

# 6. API calls (generates code but needs requests module)
try:
    c = Compiler('F:fetch|S|O|ret:api:GET,i0', type_check_enabled=False)
    code = c.compile()
    print(f"[6] API call: COMPILES")
    print(f"    (Requires requests module at runtime)")
except Exception as e:
    print(f"[6] API call: FAILED - {e}")

# 7. Member access chains
try:
    c = Compiler('F:getName|O|S|ret:i0.user.name', type_check_enabled=False)
    code = c.compile()
    exec(code)
    test_obj = type('obj', (), {'user': type('user', (), {'name': 'Bob'})()})()
    print(f"[7] Member access chain: COMPILES & EXECUTES")
    print(f"    getName(obj) = {getName(test_obj)}")
except Exception as e:
    print(f"[7] Member access chain: FAILED - {e}")

# 8. Array operations with filtering
try:
    c = Compiler('F:filterEvens|A|A|ret:data:i0|filter:item%2==0', type_check_enabled=False)
    code = c.compile()
    exec(code)
    print(f"[8] Array filter: COMPILES & EXECUTES")
    print(f"    filterEvens([1,2,3,4,5,6]) = {filterEvens([1,2,3,4,5,6])}")
except Exception as e:
    print(f"[8] Array filter: FAILED - {e}")

print("\nEDGE CASE SUMMARY:")
print("- Most patterns compile successfully")
print("- Executable Python generated for data processing, functions, conditionals")
print("- UI components and API calls compile but need runtime dependencies")
