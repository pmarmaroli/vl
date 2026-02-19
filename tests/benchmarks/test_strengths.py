#!/usr/bin/env python3
"""
VL Language - Comprehensive Strength & Weakness Analysis
Tests edge cases, performance patterns, and real-world complexity
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from vl.compiler import Compiler, TargetLanguage
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")

def count_tokens(text):
    return len(encoding.encode(text))

def compare_scenario(name, vl_code, py_code):
    """Compare VL vs Python for a specific scenario"""
    vl_tokens = count_tokens(vl_code)
    py_tokens = count_tokens(py_code)
    savings = (1 - (vl_tokens / py_tokens)) * 100 if py_tokens > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"Scenario: {name}")
    print('='*70)
    print(f"VL Code ({vl_tokens} tokens):\n{vl_code}")
    print(f"\nPython Code ({py_tokens} tokens):\n{py_code}")
    
    # Try to compile VL
    try:
        compiler = Compiler(vl_code, TargetLanguage.PYTHON)
        generated = compiler.compile()
        print(f"\n[PASS] VL Compiles Successfully")
        print(f"Generated Python:\n{generated}")
        verdict = "PASS"
    except Exception as e:
        print(f"\n[FAIL] VL Compilation Failed: {e}")
        verdict = "FAIL"
    
    print(f"\nToken Comparison: VL={vl_tokens}, Python={py_tokens}, Savings={savings:.1f}%")
    
    if savings > 20:
        strength = "STRONG"
    elif savings > 0:
        strength = "MODERATE"
    elif savings > -10:
        strength = "NEUTRAL"
    else:
        strength = "WEAK"
    
    return {
        'name': name,
        'vl_tokens': vl_tokens,
        'py_tokens': py_tokens,
        'savings': savings,
        'strength': strength,
        'verdict': verdict
    }

# Test scenarios covering different aspects
scenarios = [
    # STRENGTH TEST: Complex data transformations
    ("Complex Data Transformation", 
     "data:users|filter:age>18|filter:active==true|map:salary*1.1|filter:item>50000",
     "users_filtered = [u for u in users if u['age'] > 18]\nactive = [u for u in users_filtered if u['active'] == True]\nsalaries = [u['salary'] * 1.1 for u in active]\nresult = [s for s in salaries if s > 50000]"),
    
    # TEST: Simple variable declarations (using implicit vars)
    ("Multiple Simple Variables",
     "x=5|y=10|z=15|name='Alice'|active=true",
     "x = 5\ny = 10\nz = 15\nname = 'Alice'\nactive = True"),
    
    # STRENGTH TEST: Mathematical expressions
    ("Complex Math Expression",
     "F:calc|I,I,I|I|ret:(i0*i1)+(i2/2)",
     "def calc(a, b, c):\n    return (a * b) + (c / 2)"),
    
    # TEST: Object manipulation (using implicit vars)
    ("Object Creation and Access",
     "user={name:'Alice',age:30,city:'NYC'}|name=user.name",
     "user = {'name': 'Alice', 'age': 30, 'city': 'NYC'}\nname = user['name']"),
    
    # STRENGTH TEST: Conditional logic chains
    ("Nested Conditional Logic",
     "F:classify|I|S|ret:if:i0>1000?'huge':if:i0>100?'large':if:i0>10?'medium':'small'",
     "def classify(x):\n    if x > 1000:\n        return 'huge'\n    elif x > 100:\n        return 'large'\n    elif x > 10:\n        return 'medium'\n    else:\n        return 'small'"),
    
    # TEST: Error handling pattern
    ("Error Handling Pattern",
     "F:safeDivide|I,I|I|if:i1==0?ret:0:ret:i0/i1",
     "def safeDivide(a, b):\n    if b == 0:\n        return 0\n    else:\n        return a / b"),
    
    # TEST: Array literal creation (using implicit vars)
    ("Array Creation",
     "numbers=[1,2,3,4,5]|names=['Alice','Bob','Charlie']",
     "numbers = [1, 2, 3, 4, 5]\nnames = ['Alice', 'Bob', 'Charlie']"),
    
    # STRENGTH TEST: Loop with accumulator (using range shorthand and +=)
    ("Loop with Accumulator",
     "F:sumRange|I|I|total=0|for:idx,0..i0|total+=idx|ret:total",
     "def sumRange(n):\n    total = 0\n    for idx in range(0, n):\n        total = total + idx\n    return total"),
    
    # TEST: String interpolation complexity
    ("Complex String Interpolation",
     "F:describe|S,I,B|S|ret:'User ${i0} is ${i1} years old and is ${if:i2?'verified':'unverified'}'",
     "def describe(name, age, verified):\n    status = 'verified' if verified else 'unverified'\n    return f'User {name} is {age} years old and is {status}'"),
    
    # WEAKNESS TEST: Class definition (not supported)
    ("Class-like Structure",
     "v:Person={init:F:new|S,I|O|ret:{name:i0,age:i1}}",
     "class Person:\n    def __init__(self, name, age):\n        self.name = name\n        self.age = age"),
    
    # TEST: API with chaining (using implicit var)
    ("API Call with Processing",
     "F:fetchActive|S|A|result=api:GET,i0|ret:$result|filter:status=='active'",
     "def fetchActive(url):\n    import requests\n    response = requests.get(url)\n    data = response.json()\n    return [item for item in data if item['status'] == 'active']"),
    
    # TEST: Recursive pattern (if supported)
    ("Factorial Recursion",
     "F:fact|I|I|if:i0<=1?ret:1:ret:i0*@fact(i0-1)",
     "def fact(n):\n    if n <= 1:\n        return 1\n    else:\n        return n * fact(n - 1)"),
    
    # TEST: Dictionary operations (using implicit vars)
    ("Dictionary Merging",
     "a={x:1,y:2}|b={y:3,z:4}|c=op:merge(a,b)",
     "a = {'x': 1, 'y': 2}\nb = {'y': 3, 'z': 4}\nc = {**a, **b}"),
    
    # STRENGTH TEST: Pipeline with multiple operations
    ("Multi-stage Data Pipeline",
     "data:sales|filter:amount>100|groupBy:category|filter:count>5|map:total*1.2",
     "sales_filtered = [s for s in sales if s['amount'] > 100]\nby_category = {}\nfor s in sales_filtered:\n    cat = s['category']\n    if cat not in by_category:\n        by_category[cat] = []\n    by_category[cat].append(s)\nwith_count = {k: v for k, v in by_category.items() if len(v) > 5}\nresult = [{**v, 'total': v['total'] * 1.2} for v in with_count.values()]"),
    
    # TEST: Boolean operations
    ("Complex Boolean Logic",
     "F:validate|I,I,B|B|ret:i0>0&&i1<100&&i2",
     "def validate(a, b, c):\n    return a > 0 and b < 100 and c"),
]

print("VL LANGUAGE - COMPREHENSIVE STRENGTH & WEAKNESS ANALYSIS")
print("="*70)

results = []
for i, (name, vl, py) in enumerate(scenarios):
    print(f"\n[{i+1}/{len(scenarios)}] Starting: {name}")
    result = compare_scenario(name, vl, py)
    results.append(result)
    print(f"[{i+1}/{len(scenarios)}] Completed: {name}")

# Summary
print("\n\n" + "="*70)
print("SUMMARY - STRENGTH & WEAKNESS PROFILE")
print("="*70)
print(f"\n{'Scenario':<35} | {'Tokens':<12} | {'Savings':<8} | {'Verdict'}")
print("-"*70)

for r in results:
    tokens_str = f"{r['vl_tokens']:>3} vs {r['py_tokens']:>3}"
    savings_str = f"{r['savings']:>6.1f}%"
    strength_icon = {
        'STRONG': '[STRONG]',
        'MODERATE': '[GOOD]  ',
        'NEUTRAL': '[OK]    ',
        'WEAK': '[WEAK]  '
    }.get(r['strength'], '[?]')
    
    print(f"{r['name']:<35} | {tokens_str:<12} | {savings_str:<8} | {strength_icon} {r['verdict']}")

# Analysis
strong = [r for r in results if r['strength'] == 'STRONG']
weak = [r for r in results if r['strength'] == 'WEAK']
passed = [r for r in results if r['verdict'] == 'PASS']

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)
print(f"Total Scenarios: {len(results)}")
print(f"Compilation Success: {len(passed)}/{len(results)} ({100*len(passed)/len(results):.1f}%)")
print(f"\nStrength Profile:")
print(f"  [STRONG] Strong Areas (>20% savings): {len(strong)}")
print(f"  [WEAK] Weak Areas (<-10% savings): {len(weak)}")

print(f"\nVL EXCELS AT:")
for r in strong[:3]:
    print(f"   - {r['name']} ({r['savings']:.1f}% savings)")

print(f"\nVL STRUGGLES WITH:")
for r in sorted(results, key=lambda x: x['savings'])[:3]:
    print(f"   - {r['name']} ({r['savings']:.1f}% overhead)")

avg_savings = sum(r['savings'] for r in results) / len(results)
print(f"\nAverage Token Efficiency: {avg_savings:.1f}%")
