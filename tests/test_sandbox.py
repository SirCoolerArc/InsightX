"""Quick test for the sandbox module."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.sandbox import execute_code

# Create a tiny test DataFrame
test_df = pd.DataFrame({
    "transaction_type": ["P2P", "P2M", "P2P", "Recharge", "Bill Payment"],
    "amount_inr": [100, 500, 200, 50, 1000],
    "transaction_status": ["SUCCESS", "FAILED", "SUCCESS", "SUCCESS", "FAILED"],
    "is_failed": [0, 1, 0, 0, 1],
})

# Test 1: Basic compute
print("Test 1: Basic compute")
r = execute_code(
    'result = {"avg": float(df["amount_inr"].mean()), "count": len(df)}',
    test_df
)
print(f"  Success: {r['success']}")
print(f"  Result: {r['result']}")
assert r['success'], f"Expected success, got error: {r['error']}"
assert r['result']['avg'] == 370.0, f"Expected 370.0, got {r['result']['avg']}"
print("  PASSED")

# Test 2: Error handling
print("\nTest 2: Error handling")
r = execute_code('result = df["nonexistent"].mean()', test_df)
print(f"  Success: {r['success']}")
print(f"  Error: {r['error']}")
assert not r['success'], "Expected failure"
print("  PASSED")

# Test 3: No result variable
print("\nTest 3: Missing result variable")
r = execute_code("x = 42", test_df)
print(f"  Success: {r['success']}")
print(f"  Error: {r['error']}")
assert not r['success'], "Expected failure"
print("  PASSED")

# Test 4: DataFrame result
print("\nTest 4: DataFrame result")
r = execute_code(
    'result = df.groupby("transaction_type")["amount_inr"].mean().reset_index()',
    test_df
)
print(f"  Success: {r['success']}")
print(f"  Result type: {r['result'].get('type') if isinstance(r['result'], dict) else type(r['result'])}")
assert r['success'], f"Expected success, got error: {r['error']}"
print("  PASSED")

# Test 5: stdout capture
print("\nTest 5: Stdout capture")
code = '''
print("Debug output here")
result = {"status": "ok"}
'''
r = execute_code(code, test_df)
print(f"  Success: {r['success']}")
print(f"  Stdout: {repr(r['stdout'])}")
assert r['success']
assert "Debug output" in r['stdout']
print("  PASSED")

print("\n✓ All 5 sandbox tests passed!")
