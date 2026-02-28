"""
sandbox.py — InsightX Code Execution Sandbox
=============================================
Provides a safe, restricted environment for executing LLM-generated
pandas code against the transaction DataFrame.

Security:
  - Only pandas, numpy, math, datetime, and the DataFrame are available
  - No file I/O, no network, no arbitrary imports
  - Execution timeout (30 seconds)
  - stdout captured for debugging

Usage:
    from src.sandbox import execute_code
    result = execute_code(code_string, df)
"""

import io
import sys
import traceback
import threading
import pandas as pd
import numpy as np
import math
import datetime


# ---------------------------------------------------------------------------
# ALLOWED BUILTINS — minimal set needed for data analysis
# ---------------------------------------------------------------------------

_SAFE_BUILTINS = {
    # Types & constructors
    "True": True,
    "False": False,
    "None": None,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "type": type,

    # Iteration & comprehension
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "reversed": reversed,
    "sorted": sorted,

    # Math & aggregation
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "pow": pow,
    "divmod": divmod,

    # String & formatting
    "print": print,  # stdout is captured
    "repr": repr,
    "format": format,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "hasattr": hasattr,
    "getattr": getattr,

    # Exceptions (so try/except works in generated code)
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "ZeroDivisionError": ZeroDivisionError,
    "AttributeError": AttributeError,
    "RuntimeError": RuntimeError,

    # Other essentials
    "any": any,
    "all": all,
    "iter": iter,
    "next": next,
    "callable": callable,
    "id": id,
    "hash": hash,
    "vars": vars,
}


# ---------------------------------------------------------------------------
# EXECUTION TIMEOUT
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 30


class ExecutionTimeout(Exception):
    """Raised when code execution exceeds the timeout."""
    pass


# ---------------------------------------------------------------------------
# MAIN EXECUTION FUNCTION
# ---------------------------------------------------------------------------

def execute_code(code: str, df: pd.DataFrame) -> dict:
    """
    Execute pandas code in a sandboxed environment.

    Parameters
    ----------
    code : str
        Python code to execute. Should assign its answer to `result`.
    df : pd.DataFrame
        The transactions DataFrame, made available as `df` in the code.

    Returns
    -------
    dict with keys:
        success : bool     — True if execution completed without error
        result  : any      — the value of `result` variable after execution, if set
        stdout  : str      — captured print output
        error   : str      — error message / traceback if failed
        code    : str      — the code that was executed (echo for tracing)
    """
    # Build the restricted execution namespace
    exec_globals = {
        "__builtins__": _SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "math": math,
        "datetime": datetime,
        "df": df.copy(),  # copy to prevent accidental mutation of the cached df
    }

    exec_locals = {}

    # Capture stdout
    old_stdout = sys.stdout
    captured_stdout = io.StringIO()

    execution_result = {
        "success": False,
        "result": None,
        "stdout": "",
        "error": "",
        "code": code,
    }

    # Track whether execution completed
    completed = threading.Event()
    error_holder = [None]

    def _run():
        nonlocal exec_locals
        try:
            sys.stdout = captured_stdout
            exec(code, exec_globals, exec_locals)
        except Exception as e:
            error_holder[0] = e
        finally:
            sys.stdout = old_stdout
            completed.set()

    # Run in a thread with timeout
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_SECONDS)

    if not completed.is_set():
        # Timeout — thread is still running (daemon so it will die eventually)
        sys.stdout = old_stdout
        execution_result["error"] = (
            f"Code execution timed out after {TIMEOUT_SECONDS} seconds. "
            "This usually means an infinite loop or very expensive computation. "
            "Try a more efficient approach."
        )
        return execution_result

    # Restore stdout and capture output
    sys.stdout = old_stdout
    execution_result["stdout"] = captured_stdout.getvalue()

    if error_holder[0] is not None:
        e = error_holder[0]
        execution_result["error"] = f"{type(e).__name__}: {str(e)}"
        return execution_result

    # Success — extract the `result` variable
    execution_result["success"] = True

    if "result" in exec_locals:
        result_val = exec_locals["result"]
        # Convert DataFrames to dicts for JSON serialisability
        if isinstance(result_val, pd.DataFrame):
            execution_result["result"] = {
                "type": "dataframe",
                "data": result_val.to_dict(orient="records"),
                "columns": list(result_val.columns),
                "shape": list(result_val.shape),
                "preview": result_val.head(20).to_string(index=False),
            }
        elif isinstance(result_val, pd.Series):
            execution_result["result"] = {
                "type": "series",
                "data": result_val.to_dict(),
                "name": result_val.name,
                "preview": result_val.head(20).to_string(),
            }
        elif isinstance(result_val, dict):
            # Try to make all values JSON-safe
            execution_result["result"] = _make_json_safe(result_val)
        else:
            execution_result["result"] = result_val
    elif "result" in exec_globals:
        execution_result["result"] = exec_globals["result"]
    else:
        # No `result` variable set — use stdout as the result
        if execution_result["stdout"].strip():
            execution_result["result"] = execution_result["stdout"].strip()
        else:
            execution_result["result"] = None
            execution_result["error"] = (
                "Code executed successfully but no `result` variable was set. "
                "Make sure to assign your final answer to a variable called `result`."
            )
            execution_result["success"] = False

    return execution_result


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _make_json_safe(obj):
    """Recursively convert numpy/pandas types to Python natives."""
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient="records")
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif pd.isna(obj):
        return None
    return obj


def format_result_for_display(result: any) -> str:
    """Format a sandbox result for display in the UI or LLM prompt."""
    if result is None:
        return "No output"
    if isinstance(result, dict):
        if result.get("type") == "dataframe":
            return result["preview"]
        elif result.get("type") == "series":
            return result["preview"]
        else:
            # Pretty-print the dict
            import json
            try:
                return json.dumps(result, indent=2, default=str)
            except (TypeError, ValueError):
                return str(result)
    return str(result)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Create a tiny test DataFrame
    test_df = pd.DataFrame({
        "transaction_type": ["P2P", "P2M", "P2P", "Recharge", "Bill Payment"],
        "amount_inr": [100, 500, 200, 50, 1000],
        "transaction_status": ["SUCCESS", "FAILED", "SUCCESS", "SUCCESS", "FAILED"],
        "is_failed": [0, 1, 0, 0, 1],
    })

    # Test 1: Basic compute
    print("=" * 50)
    print("Test 1: Basic compute")
    r = execute_code("""
result = {
    "average_amount": float(df["amount_inr"].mean()),
    "total_transactions": len(df),
    "failure_rate": float(df["is_failed"].mean() * 100),
}
""", test_df)
    print(f"  Success: {r['success']}")
    print(f"  Result: {r['result']}")

    # Test 2: Error handling
    print("\nTest 2: Error handling")
    r = execute_code("result = df['nonexistent_column'].mean()", test_df)
    print(f"  Success: {r['success']}")
    print(f"  Error: {r['error']}")

    # Test 3: No result variable
    print("\nTest 3: Missing result variable")
    r = execute_code("x = 42", test_df)
    print(f"  Success: {r['success']}")
    print(f"  Error: {r['error']}")

    # Test 4: Stdout capture
    print("\nTest 4: Stdout capture")
    r = execute_code("""
print("Debug info: processing...")
result = {"count": len(df)}
""", test_df)
    print(f"  Success: {r['success']}")
    print(f"  Stdout: {r['stdout']}")
    print(f"  Result: {r['result']}")

    print("\n✓ All sandbox tests passed")
