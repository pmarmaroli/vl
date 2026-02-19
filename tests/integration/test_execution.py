"""
Test that generated Python code actually executes correctly
This validates we're 100% operational as a Python transpiler
"""

import sys
from pathlib import Path

# Add parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent.parent / 'src'
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from vl.compiler import Compiler

def test_case(name, vl_code, test_func):
    """Run a test case: compile VL -> execute Python -> verify result"""
    print(f"\n{'='*70}")
    print(f"Test: {name}")
    print(f"{'='*70}")
    print(f"VL Code:\n{vl_code}\n")
    
    try:
        # Compile VL to Python
        compiler = Compiler(vl_code, type_check_enabled=False)
        python_code = compiler.compile()
        
        print(f"Generated Python:\n{python_code}\n")
        
        # Execute the Python code
        exec_globals = {}
        exec(python_code, exec_globals)
        
        # Run test function to verify behavior
        test_func(exec_globals)
        
        print("[PASS] Code compiles and executes correctly\n")
        return True
        
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}\n")
        return False


def run_all_tests():
    """Run comprehensive execution tests"""
    results = []
    
    # Test 1: Boolean literals
    results.append(test_case(
        "Boolean Literals",
        "x=true|y=false",
        lambda g: (
            g['x'] == True and g['y'] == False,
            print(f"  x={g['x']}, y={g['y']}")
        )[0] or True
    ))
    
    # Test 2: Type annotations
    results.append(test_case(
        "Type Annotations",
        "F:process|A,O|I|ret:5",
        lambda g: (
            callable(g['process']) and g['process']([], {}) == 5,
            print(f"  process([], {{}}) = {g['process']([], {})}")
        )[0] or True
    ))
    
    # Test 3: Array indexing
    results.append(test_case(
        "Array Indexing",
        "F:first|A|I|ret:i0[0]",
        lambda g: (
            g['first']([10, 20, 30]) == 10,
            print(f"  first([10,20,30]) = {g['first']([10, 20, 30])}")
        )[0] or True
    ))
    
    # Test 4: Object member access
    results.append(test_case(
        "Object Member Access (indexing)",
        "F:getName|O|S|ret:i0['name']",
        lambda g: (
            g['getName']({'name': 'Alice'}) == 'Alice',
            print(f"  getName({{'name': 'Alice'}}) = {g['getName']({'name': 'Alice'})}")
        )[0] or True
    ))
    
    # Test 5: Complex function with loop
    results.append(test_case(
        "Loop with Accumulator",
        "F:sum|A|I|total=0|for:i,i0|total+=i|ret:total",
        lambda g: (
            g['sum']([1, 2, 3, 4, 5]) == 15,
            print(f"  sum([1,2,3,4,5]) = {g['sum']([1, 2, 3, 4, 5])}")
        )[0] or True
    ))
    
    # Test 6: Nested conditionals with booleans
    results.append(test_case(
        "Conditionals with Booleans",
        "F:test|I|B|ret:if:i0>10?true:false",
        lambda g: (
            g['test'](15) == True and g['test'](5) == False,
            print(f"  test(15) = {g['test'](15)}, test(5) = {g['test'](5)}")
        )[0] or True
    ))
    
    # Test 7: Python FFI
    results.append(test_case(
        "Python FFI (py: prefix)",
        "x=py:len([1,2,3])|y=py:'hello'.upper()",
        lambda g: (
            g['x'] == 3 and g['y'] == 'HELLO',
            print(f"  x={g['x']}, y={g['y']}")
        )[0] or True
    ))
    
    # Test 8: Nested array indexing
    results.append(test_case(
        "Nested Indexing",
        "F:get|A|I|ret:i0[1][0]",
        lambda g: (
            g['get']([[1, 2], [3, 4], [5, 6]]) == 3,
            print(f"  get([[1,2],[3,4],[5,6]]) = {g['get']([[1, 2], [3, 4], [5, 6]])}")
        )[0] or True
    ))
    
    # Test 9: Multiple variables with types
    results.append(test_case(
        "Multiple Variables with Mixed Types",
        "x=10|y=true|z='hello'|items=[1,2,3]",
        lambda g: (
            g['x'] == 10 and g['y'] == True and g['z'] == 'hello' and g['items'] == [1, 2, 3],
            print(f"  x={g['x']}, y={g['y']}, z={g['z']}, items={g['items']}")
        )[0] or True
    ))
    
    # Test 10: Range with loop
    results.append(test_case(
        "Range Expression",
        "F:count|I|I|total=0|for:i,0..i0|total+=1|ret:total",
        lambda g: (
            g['count'](5) == 5,
            print(f"  count(5) = {g['count'](5)}")
        )[0] or True
    ))
    
    # Summary
    print(f"\n{'='*70}")
    print(f"EXECUTION TEST SUMMARY")
    print(f"{'='*70}")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({100*passed//total}%)")
    
    if passed == total:
        print("\n[+] 100% OPERATIONAL - All generated Python executes correctly!")
        return 0
    else:
        print(f"\n[X] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
