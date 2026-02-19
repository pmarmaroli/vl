#!/usr/bin/env python3
"""
VL Robustness Testing - Complex Real-World Scenarios
Tests VL's ability to handle production-level code patterns
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from vl.compiler import Compiler, TargetLanguage

# Complex test scenarios
test_scenarios = {
    "Nested Conditionals": """
F:classify|I|S|
ret:if:op:>(i0,100)?'large':if:op:>(i0,50)?'medium':if:op:>(i0,10)?'small':'tiny'
""",
    
    "Multiple Variables & Operations": """
F:calculate|I,I,I|I|
v:sum=op:+(i0,i1)|
v:product=op:*(sum,i2)|
v:adjusted=op:-(product,10)|
ret:adjusted
""",
    
    "Nested Loops": """
F:matrix|I,I|A|
v:result=[]|
for:i,range(0,i0)|
  for:j,range(0,i1)|
    v:val=op:*(i,j)|
ret:result
""",
    
    "Complex Data Pipeline": """
F:analyze|A|A|
ret:data:i0|filter:age>18|filter:active==true|map:op:*(salary,1.1)|filter:op:>(item,50000)
""",

    "Chained Operations": """
F:transform|I|I|
v:x=op:+(i0,5)|
v:y=op:*(x,2)|
v:z=op:/(y,3)|
v:result=op:-(z,1)|
ret:result
""",

    "Mixed Statement Types": """
F:process|A,I|A|
v:threshold=i1|
v:filtered=data:i0|filter:op:>(value,threshold)|
for:item,filtered|
  v:adjusted=op:*(item,2)|
ret:filtered
""",

    "String Interpolation Complex": """
F:greet|S,I|S|
ret:'Hello ${i0}, you are ${i1} years old and ${if:op:>(i1,18)?'adult':'minor'}'
""",

    "Multiple Return Paths": """
F:divide|I,I|I|
if:op:==(i1,0)?ret:0:ret:op:/(i0,i1)
""",

    "Array Operations": """
F:process_array|A|A|
v:doubled=data:i0|map:op:*(item,2)|
v:filtered=data:doubled|filter:op:>(item,10)|
ret:filtered
""",

    "Boolean Logic": """
F:validate|I,I|B|
ret:if:op:&&(op:>(i0,0),op:<(i1,100))?true:false
""",

    "Deep Nesting": """
F:nested|I|I|
ret:if:op:>(i0,0)?op:+(op:*(i0,2),if:op:>(i0,10)?5:3):op:-(i0,1)
""",

    "API with Error Handling": """
F:fetchData|S|O|
v:response=api:GET,i0|
if:op:==(response.status,200)?ret:response.json:ret:{}
""",

    "Multiple Filters": """
F:filterUsers|A|A|
ret:data:i0|filter:age>18|filter:active==true|filter:verified==true|filter:score>50
""",

    "Function Composition": """
F:compose|I|I|
v:step1=op:+(i0,5)|
v:step2=op:*(step1,2)|
v:step3=if:op:>(step2,20)?op:-(step2,10):step2|
ret:step3
""",

    "Edge Case - Empty Input": """
F:safe|A|I|
ret:if:op:==(i0,[])?0:op:+(i0[0],1)
""",
}

def test_scenario(name, code):
    """Test a single complex scenario"""
    print(f"\n{'='*70}")
    print(f"Test: {name}")
    print('='*70)
    print(f"VL Code:\n{code.strip()}")
    
    try:
        compiler = Compiler(code.strip(), TargetLanguage.PYTHON)
        py_code = compiler.compile()
        print(f"\n[PASS] Compilation successful!")
        print(f"\nGenerated Python:\n{py_code}")
        return True
    except Exception as e:
        print(f"\n[FAIL] {type(e).__name__}: {e}")
        return False

def main():
    print("VL ROBUSTNESS TEST SUITE")
    print("Testing complex real-world scenarios...")
    
    results = {}
    for name, code in test_scenarios.items():
        results[name] = test_scenario(name, code)
    
    print(f"\n{'='*70}")
    print("SUMMARY")
    print('='*70)
    
    passed = sum(results.values())
    total = len(results)
    
    for name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status:8} {name}")
    
    print(f"\nTotal: {passed}/{total} passed ({100*passed/total:.1f}%)")
    
    if passed < total:
        print(f"\n{total - passed} scenarios need language design improvements")
    else:
        print("\nVL handles all complex scenarios successfully!")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
