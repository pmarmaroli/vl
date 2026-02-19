"""
Comprehensive Code Generation Test Suite
Tests all 5 targets (Python, JavaScript, TypeScript, C, Rust) for basic constructs

This ensures:
1. All targets can compile basic VL programs
2. Core language features work across targets
3. Regressions are caught early
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


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def record_pass(self, test_name):
        self.passed += 1
        print(f"  ✓ {test_name}")
    
    def record_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, str(error)))
        print(f"  ✗ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*70}")
        print(f"RESULTS: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"\nFailed tests:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")
        print(f"{'='*70}")
        return self.failed == 0


def test_target(target: TargetLanguage, vl_code: str, test_name: str, results: TestResults):
    """Test a specific target with given VL code"""
    try:
        compiler = Compiler(vl_code, target, type_check_enabled=False)
        output = compiler.compile()
        
        # Basic validation - just check we got some output
        if output and len(output) > 10:
            results.record_pass(f"{target.value}: {test_name}")
            return output
        else:
            results.record_fail(f"{target.value}: {test_name}", "Empty or too short output")
            return None
    except Exception as e:
        results.record_fail(f"{target.value}: {test_name}", str(e)[:100])
        return None


def run_test_suite():
    """Run comprehensive test suite"""
    results = TestResults()
    
    # Define test cases
    test_cases = [
        ("Simple function", "F:add|I,I|I|ret:i0+i1"),
        ("Variable assignment", "x=5\ny=10\nresult=x+y"),
        ("Boolean expression", "F:validate|I,I|B|ret:i0>0&&i1<100"),
        ("If statement", "F:max|I,I|I|ret:if:i0>i1?i0:i1"),
        ("Array literal", "nums=[1,2,3,4,5]"),
        ("Object literal", "user={name:'Alice',age:30}"),
        ("String template", "name='World'\nmsg='Hello ${name}!'"),
        ("Comparison", "F:compare|I,I|B|ret:i0==i1"),
        ("Arithmetic", "F:calc|I,I|I|ret:(i0+i1)*2"),
        ("Return constant", "F:get_five|I|I|ret:5"),
    ]
    
    # Test all targets
    targets = [
        TargetLanguage.PYTHON,
        TargetLanguage.JAVASCRIPT,
        TargetLanguage.TYPESCRIPT,
        TargetLanguage.C,
        TargetLanguage.RUST
    ]
    
    print("="*70)
    print("COMPREHENSIVE CODEGEN TEST SUITE")
    print("="*70)
    
    for test_name, vl_code in test_cases:
        print(f"\n{test_name}:")
        print(f"  VL: {vl_code[:50]}{'...' if len(vl_code) > 50 else ''}")
        
        for target in targets:
            test_target(target, vl_code, test_name, results)
    
    # Additional target-specific tests
    print(f"\n{'='*70}")
    print("TARGET-SPECIFIC FEATURES")
    print(f"{'='*70}")
    
    # Python-specific: Type annotations
    print(f"\nPython type annotations:")
    py_code = "F:typed|I,S,B|N|ret:3.14"
    test_target(TargetLanguage.PYTHON, py_code, "Type annotations", results)
    
    # TypeScript-specific: Full typing
    print(f"\nTypeScript full typing:")
    ts_code = "F:typed|I,S|S|ret:i1"
    test_target(TargetLanguage.TYPESCRIPT, ts_code, "Full typing", results)
    
    # JavaScript: No types
    print(f"\nJavaScript (no types):")
    js_code = "F:simple|I|I|ret:i0*2"
    test_target(TargetLanguage.JAVASCRIPT, js_code, "No types", results)
    
    return results.summary()


def test_boolean_optimization():
    """Verify boolean optimization works correctly"""
    print(f"\n{'='*70}")
    print("BOOLEAN OPTIMIZATION VERIFICATION")
    print(f"{'='*70}")
    
    results = TestResults()
    
    # Test case: 3+ conditions should use all() in Python
    vl_code = "F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2"
    
    print("\nTesting Python all() optimization:")
    compiler = Compiler(vl_code, TargetLanguage.PYTHON, type_check_enabled=False)
    output = compiler.compile()
    
    if "all([" in output:
        results.record_pass("Python uses all() for 3+ conditions")
    else:
        results.record_fail("Python uses all()", "Did not find all([")
    
    print("\nTesting JavaScript native &&:")
    compiler = Compiler(vl_code, TargetLanguage.JAVASCRIPT, type_check_enabled=False)
    output = compiler.compile()
    
    if "&&" in output and "all(" not in output:
        results.record_pass("JavaScript uses native &&")
    else:
        results.record_fail("JavaScript native &&", "Uses wrong operator")
    
    return results.summary()


def test_edge_cases():
    """Test edge cases and potential error conditions"""
    print(f"\n{'='*70}")
    print("EDGE CASE TESTING")
    print(f"{'='*70}")
    
    results = TestResults()
    
    edge_cases = [
        ("Single parameter", "F:identity|I|I|ret:i0"),
        ("Nested operations", "F:nested|I|I|ret:((i0+1)*2)-3"),
        ("Multiple returns", "F:abs|I|I|ret:if:i0<0?-i0:i0"),
    ]
    
    for test_name, vl_code in edge_cases:
        print(f"\n{test_name}:")
        # Test Python and JavaScript only for edge cases
        test_target(TargetLanguage.PYTHON, vl_code, test_name, results)
        test_target(TargetLanguage.JAVASCRIPT, vl_code, test_name, results)
    
    return results.summary()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("VL COMPREHENSIVE TEST SUITE")
    print("Testing all 5 targets with core language features")
    print("="*70)
    
    # Run all test suites
    suite1 = run_test_suite()
    suite2 = test_boolean_optimization()
    suite3 = test_edge_cases()
    
    # Final summary
    print(f"\n{'='*70}")
    print("FINAL RESULTS")
    print(f"{'='*70}")
    
    if suite1 and suite2 and suite3:
        print("✓ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        sys.exit(1)
