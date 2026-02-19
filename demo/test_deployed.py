"""
Quick test to verify the deployed website has the fixes
"""
import requests
import json

API_URL = "https://vl-demo-wine.vercel.app/api/convert"

# Test 1: Attribute assignment
test1 = """
class Counter:
    def __init__(self, start=0):
        self.value = start
"""

# Test 2: Tuple return
test2 = """
def get_coords():
    x = 10
    y = 20
    return x, y
"""

# Test 3: For loop with 'item'
test3 = """
def process_items(items):
    total = 0
    for item in items:
        total += item
    return total
"""

tests = [
    ("Attribute Assignment", test1),
    ("Tuple Return", test2),
    ("For Loop with 'item'", test3)
]

print("Testing deployed website API...\n")
print("=" * 80)

for name, code in tests:
    print(f"\nTest: {name}")
    print("-" * 80)
    
    try:
        response = requests.post(
            API_URL,
            json={"python_code": code.strip()},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Status: {response.status_code}")
            print(f"VL Output: {data.get('vl_code', 'N/A')[:100]}...")
            print(f"Token savings: {data.get('token_savings', 0):.1f}%")
        else:
            print(f"[FAIL] Status: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"[ERROR] {e}")

print("\n" + "=" * 80)
print("Testing complete!")
