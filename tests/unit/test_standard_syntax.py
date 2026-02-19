#!/usr/bin/env python3
"""
Test VL Standard Syntax (v0.1.2)
Tests the token-efficient syntax: F:, I/S/N/B/A/O types, M:/E:, etc.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from vl.compiler import Compiler, TargetLanguage

def test_standard_syntax():
    """Test all standard VL syntax patterns"""
    
    test_cases = [
        # (vl_code, description)
        
        # Basic functions with different types
        ("F:add|I,I|I|ret:i0+i1", "Function with int types"),
        ("F:concat|S,S|S|ret:i0+i1", "Function with string types"),
        ("F:scale|N,N|N|ret:i0*i1", "Function with float types"),
        ("F:check|B|B|ret:!i0", "Function with bool types"),
        ("F:process|A|A|ret:i0", "Function with array types"),
        ("F:transform|O|O|ret:i0", "Function with object types"),
        
        # Conditional
        ("F:max|I,I|I|ret:if:i0>i1?i0:i1", "Conditional function"),
        
        # Data pipeline
        ("F:double_all|A|A|ret:data:i0|map:item*2", "Data pipeline map"),
        
        # Loop with accumulator
        ("F:sum_range|I|I|v:total=0|for:idx,range(0,i0)|total+=idx|ret:total", "Loop with accumulator"),
        
        # Multiple parameters
        ("F:calc|I,I,N|N|ret:(i0+i1)*i2", "Mixed type parameters"),
        
        # Variables
        ("x=5", "Implicit variable"),
        ("name='Alice'", "String variable"),
        ("items=[1,2,3]", "Array variable"),
        
        # Meta and Export
        ("M:test,function,python\nF:add|I,I|I|ret:i0+i1\nE:add", "Full program structure"),
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 80)
    print("VL STANDARD SYNTAX TEST SUITE (v0.1.2)")
    print("=" * 80)
    print()
    
    for vl_code, description in test_cases:
        try:
            c = Compiler(vl_code, TargetLanguage.PYTHON)
            result = c.compile()
            print(f"[PASS] {description}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {description}")
            print(f"       Code: {vl_code}")
            print(f"       Error: {e}")
            failed += 1
    
    print()
    print("=" * 80)
    print(f"RESULTS: {passed}/{passed+failed} tests passed")
    print("=" * 80)
    
    return failed == 0


def test_all_targets():
    """Ensure syntax works for all code generation targets"""
    
    test_code = "F:add|I,I|I|ret:i0+i1"
    targets = [
        TargetLanguage.PYTHON,
        TargetLanguage.JAVASCRIPT,
        TargetLanguage.TYPESCRIPT,
        TargetLanguage.C,
        TargetLanguage.RUST,
    ]
    
    print()
    print("=" * 80)
    print("MULTI-TARGET TEST")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for target in targets:
        try:
            c = Compiler(test_code, target)
            result = c.compile()
            print(f"[PASS] {target.name}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {target.name}: {e}")
            failed += 1
    
    print()
    print(f"RESULTS: {passed}/{passed+failed} targets work")
    print("=" * 80)
    
    return failed == 0


def main():
    success = True
    success = test_standard_syntax() and success
    success = test_all_targets() and success
    
    if success:
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
