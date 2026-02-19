#!/usr/bin/env python3
"""
Test all VL example programs to ensure they compile correctly
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from vl.compiler import Compiler, TargetLanguage

def test_example(file_path):
    """Test a single VL example file"""
    print(f"\n{'='*70}")
    print(f"Testing: {file_path.name}")
    print('='*70)
    
    with open(file_path, 'r') as f:
        vl_code = f.read()
    
    print(f"VL Code:\n{vl_code}")
    
    try:
        compiler = Compiler(vl_code, TargetLanguage.PYTHON)
        py_code = compiler.compile()
        print(f"\n[OK] Compilation successful!")
        print(f"\nGenerated Python:\n{py_code}")
        return True
    except Exception as e:
        print(f"\n[FAIL] Compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    repo_root = Path(__file__).parent.parent.parent
    examples_dir = repo_root / 'examples'
    vl_files = sorted(examples_dir.rglob('*.vl'))
    
    print(f"Found {len(vl_files)} VL example files in {examples_dir}")
    
    results = {}
    for vl_file in vl_files:
        results[vl_file.name] = test_example(vl_file)
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    
    for filename, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status:8} {filename}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\nTotal: {passed}/{total} passed")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
