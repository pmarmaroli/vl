"""
Test VL Configuration System
Validates that configuration settings control behavior correctly
"""

import sys
from pathlib import Path

# Fix Windows Unicode encoding without replacing the file descriptor
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Add parent directory to sys.path for imports
parent_dir = Path(__file__).parent.parent.parent / 'src'
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from vl.compiler import Compiler, TargetLanguage
import vl.config as vl_config

print("Testing VL Configuration System")
print("=" * 70)

# Test 1: Boolean optimization threshold
print("\nTest 1: Boolean optimization threshold")
print("-" * 70)

vl_code = "F:test|I,I,I|B|ret:i0>0&&i1<100&&i2"

# Default behavior (threshold = 3)
compiler = Compiler(vl_code, target=TargetLanguage.PYTHON, type_check_enabled=False)
python_code = compiler.compile()
uses_all = 'all([' in python_code
print(f"Default (min_length={vl_config.BOOLEAN_CHAIN_MIN_LENGTH}): {'all()' if uses_all else 'native &&'}")
assert uses_all, "Expected all() optimization with 3 conditions"

# Change threshold to 4 (should not optimize)
original_threshold = vl_config.BOOLEAN_CHAIN_MIN_LENGTH
vl_config.BOOLEAN_CHAIN_MIN_LENGTH = 4
try:
    compiler2 = Compiler(vl_code, target=TargetLanguage.PYTHON, type_check_enabled=False)
    python_code2 = compiler2.compile()
    uses_all2 = 'all([' in python_code2
    print(f"Modified (min_length=4): {'all()' if uses_all2 else 'native &&'}")
    assert not uses_all2, "Should not optimize with threshold=4 and 3 conditions"
    print("✓ Threshold configuration works correctly")
finally:
    vl_config.BOOLEAN_CHAIN_MIN_LENGTH = original_threshold

# Test 2: Target-specific settings
print("\nTest 2: Target-specific settings")
print("-" * 70)

targets = ['python', 'javascript', 'typescript', 'c', 'rust']
for target in targets:
    ext = vl_config.get_target_extension(target)
    should_opt = vl_config.should_optimize_booleans(target)
    settings = vl_config.TARGET_SETTINGS.get(target, {})
    print(f"{target:12} → ext={ext:5} optimize_bool={should_opt:5} type_hints={settings.get('supports_type_hints', False)}")

print("✓ Target settings retrieved successfully")

# Test 3: Optimization flag control
print("\nTest 3: Optimization flag control")
print("-" * 70)

original_flag = vl_config.OPTIMIZE_BOOLEAN_CHAINS
vl_config.OPTIMIZE_BOOLEAN_CHAINS = False
try:
    compiler3 = Compiler(vl_code, target=TargetLanguage.PYTHON, type_check_enabled=False)
    python_code3 = compiler3.compile()
    uses_all3 = 'all([' in python_code3
    print(f"OPTIMIZE_BOOLEAN_CHAINS=False: {'all()' if uses_all3 else 'native &&'}")
    assert not uses_all3, "Should not optimize when flag is False"
    print("✓ Optimization flag controls behavior")
finally:
    vl_config.OPTIMIZE_BOOLEAN_CHAINS = original_flag

# Test 4: Config values are as expected
print("\nTest 4: Default configuration values")
print("-" * 70)

assert vl_config.BOOLEAN_CHAIN_MIN_LENGTH == 3, "Expected default threshold of 3"
assert vl_config.OPTIMIZE_BOOLEAN_CHAINS == True, "Expected optimization enabled by default"
assert vl_config.DEFAULT_TARGET == 'python', "Expected python as default target"
assert vl_config.TYPE_CHECK_ENABLED_DEFAULT == True, "Expected type checking enabled by default"

print(f"BOOLEAN_CHAIN_MIN_LENGTH: {vl_config.BOOLEAN_CHAIN_MIN_LENGTH}")
print(f"OPTIMIZE_BOOLEAN_CHAINS: {vl_config.OPTIMIZE_BOOLEAN_CHAINS}")
print(f"DEFAULT_TARGET: {vl_config.DEFAULT_TARGET}")
print(f"TYPE_CHECK_ENABLED_DEFAULT: {vl_config.TYPE_CHECK_ENABLED_DEFAULT}")
print("✓ All default values correct")

print("\n" + "=" * 70)
print("All configuration tests passed! ✓")
