"""
Example: Debugging existing Python code with LLM using VL

This demonstrates the token-efficient workflow:
Python → VL → LLM debugging → VL → Python
"""

# Original Python code with a bug
buggy_code = """
def calculate_discount(price: float, discount_percent: int) -> float:
    # Bug: discount should be divided by 100
    discount = price * discount_percent
    final_price = price - discount
    return final_price

# Test
result = calculate_discount(100.0, 20)
print(f"Price after 20% discount: ${result}")
"""

print("=" * 60)
print("STEP 1: Original Python Code (with bug)")
print("=" * 60)
print(buggy_code)
print()

# Convert to VL
from vl.py_to_vl import convert_python_to_vl

vl_code = convert_python_to_vl(buggy_code)

print("=" * 60)
print("STEP 2: Converted to VL (40% fewer tokens)")
print("=" * 60)
print(vl_code)
print()

# Token count comparison
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
python_tokens = len(enc.encode(buggy_code))
vl_tokens = len(enc.encode(vl_code))
savings = ((python_tokens - vl_tokens) / python_tokens) * 100

print("=" * 60)
print("STEP 3: Token Analysis")
print("=" * 60)
print(f"Python tokens: {python_tokens}")
print(f"VL tokens: {vl_tokens}")
print(f"Savings: {savings:.1f}%")
print()

# Now an LLM would work with the VL version
# For this demo, let's manually fix the VL code
fixed_vl = """
F:calculate_discount|N,I|N|
  discount=i0*i1/100|
  final_price=i0-discount|
  ret:final_price|

result=calculate_discount(100.0,20)
@print('Price after 20% discount: $',result)
"""

print("=" * 60)
print("STEP 4: Fixed VL Code (from LLM)")
print("=" * 60)
print(fixed_vl)
print()

# Compile back to Python
from vl.compiler import Compiler, TargetLanguage

compiler = Compiler(fixed_vl, TargetLanguage.PYTHON)
fixed_python = compiler.compile()

print("=" * 60)
print("STEP 5: Compiled Back to Python")
print("=" * 60)
print(fixed_python)
print()

# Execute to verify fix
print("=" * 60)
print("STEP 6: Test Execution")
print("=" * 60)
exec(fixed_python)
print()

print("=" * 60)
print("COST SAVINGS ANALYSIS")
print("=" * 60)
print("For 3 iterations with LLM:")
print(f"  Input tokens: {python_tokens * 3} → {vl_tokens * 3} (saves {(python_tokens - vl_tokens) * 3})")
print(f"  Output tokens: ~{python_tokens // 2 * 3} → ~{vl_tokens // 2 * 3} (saves ~{(python_tokens - vl_tokens) // 2 * 3})")
print(f"  Total savings: ~{savings:.0f}% cheaper with VL!")
