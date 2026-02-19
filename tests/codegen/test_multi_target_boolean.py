"""
Test Multi-Target Boolean Logic Optimization

Verifies that:
1. Python codegen uses all()/any() for boolean chains (3+ conditions)
2. JavaScript codegen uses native &&/|| operators
3. TypeScript codegen uses native &&/|| operators
4. C codegen uses native &&/|| operators
5. Rust codegen uses native &&/|| operators
"""

import sys
from pathlib import Path

# Fix Unicode output on Windows without replacing file descriptors
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass

# Add interpreter directory to path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vl.compiler import Compiler, TargetLanguage


def test_boolean_optimization():
    """Test that boolean chains are optimized per target language"""
    
    # VL source with 3 boolean conditions (should trigger optimization)
    vl_source = """
F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2
"""
    
    print("Testing Boolean Logic Optimization Across Targets")
    print("=" * 60)
    print("\nVL Source:")
    print(vl_source.strip())
    print("\n" + "=" * 60)
    
    # Test Python target
    print("\n1. PYTHON TARGET (should use all()):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.PYTHON, type_check_enabled=False)
        python_output = compiler.compile()
        print(python_output)
        
        # Verify Python uses all()
        if "all([" in python_output:
            print("✅ PASS: Python correctly uses all() for token efficiency")
        else:
            print("❌ FAIL: Python should use all() for boolean chains")
            print("   (Found: uses 'and' operator instead)")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test JavaScript target
    print("\n2. JAVASCRIPT TARGET (should use native &&):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.JAVASCRIPT, type_check_enabled=False)
        js_output = compiler.compile()
        print(js_output)
        
        # Verify JavaScript uses &&
        if "&&" in js_output and "all(" not in js_output:
            print("✅ PASS: JavaScript correctly uses native && operator")
        else:
            print("❌ FAIL: JavaScript should use && operator")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test TypeScript target
    print("\n3. TYPESCRIPT TARGET (should use native &&):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.TYPESCRIPT, type_check_enabled=False)
        ts_output = compiler.compile()
        print(ts_output)
        
        # Verify TypeScript uses &&
        if "&&" in ts_output and "all(" not in ts_output:
            print("✅ PASS: TypeScript correctly uses native && operator")
        else:
            print("❌ FAIL: TypeScript should use && operator")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test C target
    print("\n4. C TARGET (should use native &&):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.C, type_check_enabled=False)
        c_output = compiler.compile()
        print(c_output)
        
        # Verify C uses &&
        if "&&" in c_output and "all(" not in c_output:
            print("✅ PASS: C correctly uses native && operator")
        else:
            print("❌ FAIL: C should use && operator")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test Rust target
    print("\n5. RUST TARGET (should use native &&):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.RUST, type_check_enabled=False)
        rust_output = compiler.compile()
        print(rust_output)
        
        # Verify Rust uses &&
        if "&&" in rust_output and "all(" not in rust_output:
            print("✅ PASS: Rust correctly uses native && operator")
        else:
            print("❌ FAIL: Rust should use && operator")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


def test_or_chain():
    """Test OR chain optimization"""
    
    vl_source = """
F:hasError|I,I,I|B|ret:i0<0||i1<0||i2<0
"""
    
    print("\n\nTesting OR Chain Optimization")
    print("=" * 60)
    print("\nVL Source:")
    print(vl_source.strip())
    print("\n" + "=" * 60)
    
    # Test Python target
    print("\nPYTHON TARGET (should use any()):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.PYTHON, type_check_enabled=False)
        python_output = compiler.compile()
        print(python_output)
        
        # Verify Python uses any()
        if "any([" in python_output:
            print("✅ PASS: Python correctly uses any() for OR chains")
        else:
            print("❌ FAIL: Python should use any() for OR chains")
    except Exception as e:
        print(f"❌ ERROR: {e}")


def test_short_chain():
    """Test that short chains (2 conditions) don't trigger optimization"""
    
    vl_source = """
F:check|I,I|B|ret:i0>0&&i1<100
"""
    
    print("\n\nTesting Short Chain (2 conditions - no optimization)")
    print("=" * 60)
    print("\nVL Source:")
    print(vl_source.strip())
    print("\n" + "=" * 60)
    
    # Test Python target
    print("\nPYTHON TARGET (should use 'and', not all()):")
    print("-" * 60)
    try:
        compiler = Compiler(vl_source, TargetLanguage.PYTHON, type_check_enabled=False)
        python_output = compiler.compile()
        print(python_output)
        
        # Verify Python uses 'and' for short chains
        if "all([" not in python_output and " and " in python_output:
            print("✅ PASS: Python correctly skips all() for short chains")
        else:
            print("❌ FAIL: Python should use 'and' for 2-condition chains")
    except Exception as e:
        print(f"❌ ERROR: {e}")


if __name__ == "__main__":
    test_boolean_optimization()
    test_or_chain()
    test_short_chain()
