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
import queue
import json
import concurrent.futures

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

def _run_analysis_worker(task_id: str, is_main: bool, user_query: str, schema: str, conv_context_str: str, df, result_queue: queue.Queue):
    """
    Runs the generate -> execute -> fix loop for a single task.
    Puts status updates and final result into result_queue.
    """
    import json
    def _enqueue_event(event_type: str, data: dict):
        if is_main or event_type != "status" or data.get("step") == "deep_dive_start":
            if not is_main and event_type == "status":
                data["message"] = f"[Deep Dive] {data['message']}"
            result_queue.put({"task_id": task_id, "event_json": json.dumps({"type": event_type, "data": data})})

    steps = []
    last_code = ""
    last_result = None
    last_result_summary = "No output"

    if is_main:
        _enqueue_event("status", {"message": "Generating analysis code...", "step": "generate_code"})
    else:
        _enqueue_event("status", {"message": "Launching background deep-dive analysis...", "step": "deep_dive_start"})
        
    try:
        code = generate_analysis_code(user_query, schema, conv_context_str)
    except Exception as e:
        result_queue.put({"task_id": task_id, "error": str(e), "steps": steps})
        return

    for attempt in range(1, MAX_RETRIES + 1):
        if is_main:
            _enqueue_event("status", {"message": f"Executing code (Attempt {attempt})...", "step": "execute_code", "code": code})
        
        step = {
            "iteration": attempt,
            "phase": "execute",
            "code": code,
            "result": None,
            "error": None,
        }

        exec_result = execute_code(code, df)

        if exec_result["success"]:
            step["phase"] = "success"
            step["result"] = exec_result["result"]
            last_code = code
            last_result = exec_result["result"]
            last_result_summary = format_result_for_display(exec_result["result"])
            if exec_result.get("stdout"):
                step["stdout"] = exec_result["stdout"]
            steps.append(step)

            if attempt == 1 and last_result is not None:
                if is_main: _enqueue_event("status", {"message": "Validating output...", "step": "validate"})
                try:
                    validation = validate_and_refine(user_query, code, last_result_summary, schema)
                    if not validation.get("aligned") and validation.get("new_code"):
                        if is_main: _enqueue_event("status", {"message": "Output needed refinement. Regenerating...", "step": "refining"})
                        steps.append({
                            "iteration": attempt,
                            "phase": "refinement",
                            "reason": validation.get("reason", "Output misaligned"),
                            "code": validation["new_code"],
                        })
                        code = validation["new_code"]
                        continue
                except Exception:
                    pass
            break
        else:
            step["phase"] = "error"
            step["error"] = exec_result["error"]
            steps.append(step)

            if attempt < MAX_RETRIES:
                if is_main: _enqueue_event("status", {"message": f"Execution failed. Attempting to fix... ({attempt}/{MAX_RETRIES})", "step": "fix_code", "error": exec_result["error"]})
                try:
                    code = fix_code(code, exec_result["error"], user_query, schema)
                    steps.append({"iteration": attempt, "phase": "fix", "code": code})
                except Exception as fix_error:
                    result_queue.put({"task_id": task_id, "error": exec_result["error"], "steps": steps})
                    return
            else:
                result_queue.put({"task_id": task_id, "error": exec_result["error"], "steps": steps})
                return

    # Done
    result_queue.put({
        "task_id": task_id,
        "success": True,
        "last_code": last_code,
        "last_result": last_result,
        "last_result_summary": last_result_summary,
        "steps": steps
    })


def run_agent_stream(user_query: str, conversation_context: dict = None):
    """
    Generator version of run_agent that yields progress updates
    as SSE JSON events. Runs tasks in parallel using ThreadPoolExecutor.
    """
    import json
    def _yield_event(event_type: str, data: dict):
        return json.dumps({"type": event_type, "data": data})

    yield _yield_event("status", {"message": "Initializing...", "step": "init"})

    df = get_dataframe()
    schema = get_schema_prompt(df)
    conv_context_str = build_conversation_context(conversation_context.get("history", [])) if conversation_context else ""

    q = queue.Queue()
    tasks = [
        {"id": "main", "query": user_query, "is_main": True},
        {"id": "deep_dive_1", "query": f"DEEP DIVE CONTEXT: Original query was '{user_query}'. Task: Without explicitly repeating the answer to the main query, break the data down by a relevant categorical segment (e.g., network, merchant_category, age_group, state) to find interesting deeper insights or correlations. If the original query is already a breakdown, find an anomaly instead.", "is_main": False}
    ]

    worker_results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(_run_analysis_worker, t["id"], t["is_main"], t["query"], schema, conv_context_str, df, q): t["id"]
            for t in tasks
        }
        
        # Consume queue
        completed = 0
        while completed < len(tasks):
            try:
                msg = q.get(timeout=0.1)
                if "event_json" in msg:
                    yield msg["event_json"]
                else:
                    worker_results[msg["task_id"]] = msg
                    completed += 1
            except queue.Empty:
                if all(f.done() for f in futures):
                    while not q.empty():
                        msg = q.get()
                        if "event_json" in msg:
                            yield msg["event_json"]
                        else:
                            worker_results[msg["task_id"]] = msg
                    break

    main_res = worker_results.get("main", {})
    if not main_res.get("success"):
        error_msg = main_res.get("error", "Unknown error")
        yield _yield_event("final", {
            "response": f"I couldn't produce a working analysis. Last error: {error_msg}",
            "result": {"success": False, "raw_output": error_msg, "code": ""},
            "steps": main_res.get("steps", [])
        })
        return

    yield _yield_event("status", {"message": "Synthesizing final insights...", "step": "narrative"})
    
    deep_dive_outputs = []
    for t_id, res in worker_results.items():
        if t_id != "main" and res.get("success") and res.get("last_result_summary") and res.get("last_result_summary") != "No output":
            deep_dive_outputs.append(res["last_result_summary"])
            
    try:
        narrative = generate_narrative(
            user_query,
            main_res.get("last_code", ""),
            main_res.get("last_result_summary", ""),
            deep_dive_results=deep_dive_outputs,
            stdout=""
        )
        try:
            parsed_narrative = json.loads(narrative)
        except:
            parsed_narrative = {
                "summary": "Analysis generated but failed to parse into UI cards.",
                "narrative": narrative,
                "cards": []
            }
    except Exception:
        fallback_text = f"Analysis complete.\n\n{main_res.get('last_result_summary', '')}"
        parsed_narrative = {
            "summary": "Analysis generated but formatting failed.",
            "narrative": fallback_text,
            "cards": []
        }

    yield _yield_event("status", {"message": "Finalizing insights & running quality review...", "step": "judge"})
    
    def _get_followups():
        try:
            return generate_followups(user_query, main_res.get("last_result_summary", ""))
        except Exception:
            return []

    def _run_judge():
        try:
            judge_result_arg = {"success": True, "raw_output": main_res.get("last_result_summary", "")}
            return judge_response(user_query, parsed_narrative["narrative"], result=judge_result_arg)
        except Exception as e:
            import traceback
            with open("crash_debug.txt", "w") as f:
                f.write(traceback.format_exc())
            return {"judge_ran": False, "confidence": "low"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_followups = executor.submit(_get_followups)
        future_judge = executor.submit(_run_judge)
        
        followups = future_followups.result()
        verdict = future_judge.result()

    if verdict.get("final_response"): 
        parsed_narrative["narrative"] = verdict["final_response"]

    # --- TRUNCATION LOGIC TO PREVENT FRONTEND JSON PARSE ERRORS (64KB LIMIT) ---
    raw_res = main_res.get("last_result")
    if isinstance(raw_res, list) and len(raw_res) > 100:
        raw_res = raw_res[:100] + [{"_INFO": f"... truncated {len(raw_res) - 100} more items to prevent session crash"}]
        
    final_steps = main_res.get("steps", [])
    for s in final_steps:
        if isinstance(s.get("result"), dict) and s["result"].get("data"):
            if isinstance(s["result"]["data"], list) and len(s["result"]["data"]) > 50:
                s["result"]["data"] = s["result"]["data"][:50] + [{"_INFO": "truncated"}]

    final_payload = {
        "response": parsed_narrative.get("narrative", ""),
        "insight_summary": parsed_narrative.get("summary", ""),
        "cards": parsed_narrative.get("cards", []),
        "result": {
            "success": True,
            "raw_output": raw_res,
            "summary": main_res.get("last_result_summary"),
            "code": main_res.get("last_code"),
        },
        "followups": followups,
        "mode": "code_interpreter",
        "steps": final_steps,
        "verdict": verdict,
        "code": main_res.get("last_code"),
    }
    
    event_json = _yield_event("final", final_payload)
    if len(event_json) > 60000:
        # Emergency truncation if still too large
        final_payload["result"]["raw_output"] = "Data too large for full preview. See summary."
        event_json = _yield_event("final", final_payload)
    
    
    yield event_json


def run_agent(user_query: str, conversation_context: dict = None) -> dict:
    """Main entry point for the code interpreter agent."""
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
    # STEP 4 & 5: Generate follow-up suggestions & Quality judge (Parallel)
    # -----------------------------------------------------------------------
    def _gen_follow():
        try:
            return generate_followups(user_query, last_result_summary)
        except Exception:
            return []
            
    def _run_jud():
        try:
            return judge_response(
                original_query=user_query,
                response=narrative,
                result={"success": True, "raw_output": last_result_summary},
            )
        except Exception:
            return {"judge_ran": False}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_follow = executor.submit(_gen_follow)
        f_jud = executor.submit(_run_jud)
        
        followups = f_follow.result()
        verdict = f_jud.result()

    if verdict.get("final_response"):
        narrative = verdict["final_response"]

    try:
        parsed_narrative = json.loads(narrative) # narrative is already JSON from generate_narrative
    except Exception:
        parsed_narrative = {"narrative": narrative, "summary": "Analysis generated.", "cards": []}

    return {
        "response": parsed_narrative.get("narrative", narrative),
        "insight_summary": parsed_narrative.get("summary", ""),
        "cards": parsed_narrative.get("cards", []),
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
    Format execution steps for the Frontend UI expander.
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