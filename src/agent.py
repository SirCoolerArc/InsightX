"""
agent.py — InsightX Code Interpreter Agent (v3)
================================================
Orchestrates the code-interpreter pipeline:

    User Query
        → Code Planner (Gemini writes pandas code)
        → Sandbox (exec with restricted env)
        → Self-correction loop (fix errors / refine output)
        → Narrative Generator (D-S-I-R response)
        → Quality Judge (optional validation)

Returns the same interface as before:
    {response, result, followups, mode, steps, verdict}

Usage:
    from src.agent import run_agent
    result = run_agent("Which transaction type has the highest failure rate?")
"""

import traceback

try:
    from src.code_planner import (
        generate_analysis_code,
        fix_code,
        validate_and_refine,
        generate_narrative,
        generate_followups,
        get_schema_prompt,
        build_conversation_context,
        MAX_RETRIES,
    )
    from src.sandbox import execute_code, format_result_for_display
    from src.data_loader import get_dataframe
    from src.judge import judge_response
except ModuleNotFoundError:
    from code_planner import (
        generate_analysis_code,
        fix_code,
        validate_and_refine,
        generate_narrative,
        generate_followups,
        get_schema_prompt,
        build_conversation_context,
        MAX_RETRIES,
    )
    from sandbox import execute_code, format_result_for_display
    from data_loader import get_dataframe
    from judge import judge_response


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def run_agent(user_query: str, conversation_context: dict = None) -> dict:
    """
    Main entry point for the code interpreter agent.

    Parameters
    ----------
    user_query : str
        The user's natural language question.
    conversation_context : dict, optional
        Context from ConversationManager for follow-up queries.

    Returns
    -------
    dict with keys:
        response  : str   — final D-S-I-R narrative
        result    : dict  — execution result (data from sandbox)
        followups : list  — suggested follow-up questions
        mode      : str   — always "code_interpreter" in new arch
        steps     : list  — execution trace (code, output, errors per iteration)
        verdict   : dict  — judge verdict (if ran)
        code      : str   — final executed code
    """
    # Load the DataFrame and schema
    df = get_dataframe()
    schema = get_schema_prompt(df)

    # Build conversation context string for follow-ups
    conv_context_str = ""
    if conversation_context and conversation_context.get("history"):
        conv_context_str = build_conversation_context(
            conversation_context["history"]
        )

    # Track all steps for the investigation trace
    steps = []
    last_code = ""
    last_result = None
    last_result_summary = ""

    # -----------------------------------------------------------------------
    # STEP 1: Generate initial code
    # -----------------------------------------------------------------------
    try:
        code = generate_analysis_code(user_query, schema, conv_context_str)
    except Exception as e:
        return _error_result(
            f"I couldn't generate analysis code for your question. Please try rephrasing. ({e})",
            steps,
        )

    # -----------------------------------------------------------------------
    # STEP 2: Execute → Fix → Validate loop (up to MAX_RETRIES iterations)
    # -----------------------------------------------------------------------
    for attempt in range(1, MAX_RETRIES + 1):
        step = {
            "iteration": attempt,
            "phase": "execute",
            "code": code,
            "result": None,
            "error": None,
        }

        # Execute in sandbox
        exec_result = execute_code(code, df)

        if exec_result["success"]:
            step["phase"] = "success"
            step["result"] = exec_result["result"]
            last_code = code
            last_result = exec_result["result"]
            last_result_summary = format_result_for_display(exec_result["result"])

            # Add stdout to step for debugging visibility
            if exec_result.get("stdout"):
                step["stdout"] = exec_result["stdout"]

            steps.append(step)

            # Validate output alignment (only on first successful execution)
            if attempt == 1 and last_result is not None:
                try:
                    validation = validate_and_refine(
                        user_query, code, last_result_summary, schema
                    )
                    if not validation.get("aligned") and validation.get("new_code"):
                        # Output didn't answer the question — try refined code
                        steps.append({
                            "iteration": attempt,
                            "phase": "refinement",
                            "reason": validation.get("reason", "Output misaligned"),
                            "code": validation["new_code"],
                        })
                        code = validation["new_code"]
                        continue  # re-execute with refined code
                except Exception:
                    pass  # validation failed, proceed with current result

            break  # success and validated

        else:
            # Execution failed — try to fix
            step["phase"] = "error"
            step["error"] = exec_result["error"]
            steps.append(step)

            if attempt < MAX_RETRIES:
                try:
                    code = fix_code(code, exec_result["error"], user_query, schema)
                    steps.append({
                        "iteration": attempt,
                        "phase": "fix",
                        "code": code,
                    })
                except Exception as fix_error:
                    return _error_result(
                        f"I encountered an error analysing your question and couldn't fix it automatically. "
                        f"Error: {exec_result['error']}",
                        steps,
                    )
            else:
                return _error_result(
                    f"I tried {MAX_RETRIES} times but couldn't produce a working analysis. "
                    f"Last error: {exec_result['error']}. Please try rephrasing your question.",
                    steps,
                )

    # -----------------------------------------------------------------------
    # STEP 3: Generate narrative
    # -----------------------------------------------------------------------
    try:
        narrative = generate_narrative(
            user_query,
            last_code,
            last_result_summary,
            stdout=exec_result.get("stdout", ""),
        )
    except Exception:
        narrative = f"Analysis complete. Here are the results:\n\n{last_result_summary}"

    # -----------------------------------------------------------------------
    # STEP 4: Generate follow-up suggestions
    # -----------------------------------------------------------------------
    try:
        followups = generate_followups(user_query, last_result_summary)
    except Exception:
        followups = []

    # -----------------------------------------------------------------------
    # STEP 5: Quality judge (optional)
    # -----------------------------------------------------------------------
    verdict = {}
    try:
        verdict = judge_response(
            original_query=user_query,
            response=narrative,
            result={"success": True, "raw_output": last_result_summary},
        )
        if verdict.get("final_response"):
            narrative = verdict["final_response"]
    except Exception:
        verdict = {"judge_ran": False}

    return {
        "response": narrative,
        "result": {
            "success": True,
            "raw_output": last_result,
            "summary": last_result_summary,
            "code": last_code,
        },
        "followups": followups,
        "mode": "code_interpreter",
        "steps": steps,
        "verdict": verdict,
        "code": last_code,
    }


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _error_result(error_msg: str, steps: list) -> dict:
    """Return an error result dict with the standard interface."""
    return {
        "response": error_msg,
        "result": {"success": False, "error": error_msg},
        "followups": [],
        "mode": "code_interpreter",
        "steps": steps,
        "verdict": {"judge_ran": False},
        "code": "",
    }


def format_investigation_trace(steps: list[dict]) -> str:
    """
    Format execution steps for the Streamlit UI expander.
    Shows the code, output, and any errors for each iteration.
    """
    if not steps:
        return ""

    lines = []
    for step in steps:
        iteration = step.get("iteration", "?")
        phase = step.get("phase", "unknown")

        if phase == "execute":
            lines.append(f"### Iteration {iteration}: Executing...")

        elif phase == "success":
            lines.append(f"### ✅ Iteration {iteration}: Success")
            if step.get("code"):
                lines.append(f"```python\n{step['code']}\n```")
            if step.get("result"):
                result_str = format_result_for_display(step["result"])
                if len(result_str) > 500:
                    result_str = result_str[:500] + "\n... (truncated)"
                lines.append(f"**Output:**\n```\n{result_str}\n```")

        elif phase == "error":
            lines.append(f"### ❌ Iteration {iteration}: Error")
            if step.get("code"):
                lines.append(f"```python\n{step['code']}\n```")
            lines.append(f"**Error:** `{step.get('error', 'Unknown error')}`")

        elif phase == "fix":
            lines.append(f"### 🔧 Iteration {iteration}: Fixing code...")

        elif phase == "refinement":
            lines.append(f"### 🔄 Iteration {iteration}: Refining")
            lines.append(f"**Reason:** {step.get('reason', 'Output needs adjustment')}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_queries = [
        "What is the average transaction amount?",
        "Which transaction type has the highest failure rate?",
    ]

    for q in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {q}")
        print("=" * 60)

        result = run_agent(q)

        print(f"\nMode: {result['mode']}")
        print(f"Steps: {len(result['steps'])}")
        print(f"\n--- Response ---\n{result['response']}")
        print(f"\n--- Code ---\n{result['code']}")

        if result["followups"]:
            print("\n--- Follow-ups ---")
            for f in result["followups"]:
                print(f"  → {f}")