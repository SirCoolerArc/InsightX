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
        audit_deep_dive,
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
        audit_deep_dive,
        get_schema_prompt,
        build_conversation_context,
        MAX_RETRIES,
    )
    from sandbox import execute_code, format_result_for_display
    from data_loader import get_dataframe
    from judge import judge_response


# Maximum number of judge-driven re-analyses. The judge runs once on the
# first narrative; if it returns approved=False with a critical issue we
# cannot patch in-place (see _judge_warrants_retry), we regenerate code
# with the judge's issues injected and re-run the pipeline.
#
# Default is 0: the audit loop is OFF unless the user opts into Deep Verify
# Mode. This avoids the ~50% latency hit on queries the judge would have
# (often spuriously) flagged. When Deep Verify is on, the budget bumps to
# DEEP_VERIFY_RETRY_BUDGET for stronger guarantees.
JUDGE_RETRY_BUDGET = 0
DEEP_VERIFY_RETRY_BUDGET = 2

# Only these dimensions warrant a full re-analysis. Calibration, safety, and
# relevance issues are already corrected in-place by the judge's
# final_response/caveat path — re-running the analysis for them just doubles
# latency without changing the underlying numbers. Grounding (made-up
# statistics) and logical_integrity (wrong premise / wrong question answered)
# require new code, so they go through the retry loop.
_RETRY_WORTHY_DIMENSIONS = {"grounding", "logical_integrity"}


_BREAKDOWN_KEYWORDS = {
    "compare", "vs", "versus", "breakdown", "break down", "by ",
    "across", "per ", "between", "each", "every", "trend", "distribution",
    "top ", "bottom ", "highest", "lowest", "rank", "ranked",
    "hourly", "daily", "weekly", "monthly", "yearly",
    "group", "segment", "category", "categories",
}


def _validation_likely_needed(user_query: str, result_summary: str) -> bool:
    """Cheap heuristic — decide whether validate_and_refine should run.

    Returns True only when the result looks suspect relative to the question:
      - empty / 'No output' result
      - user asked for a breakdown/comparison but got a single scalar
      - result is unusually short
    Otherwise validation is skipped (saves ~10s per query on the happy path).
    The semantic validator still runs whenever any of these heuristics fire.
    """
    if not result_summary or result_summary.strip() in ("", "No output", "None"):
        return True

    summary = result_summary.strip()
    query_lower = user_query.lower()
    asked_for_breakdown = any(kw in query_lower for kw in _BREAKDOWN_KEYWORDS)

    # Single scalar / single line when the user wanted a breakdown
    line_count = summary.count("\n") + 1
    if asked_for_breakdown and len(summary) < 120 and line_count <= 2:
        return True

    # Very short result — worth a sanity check regardless
    if len(summary) < 30:
        return True

    return False


def _judge_warrants_retry(verdict: dict) -> bool:
    """True only if the judge found a critical issue in a dimension that
    actually requires re-running the analysis."""
    if not verdict.get("judge_ran") or verdict.get("approved") is not False:
        return False
    for iss in (verdict.get("issues") or []):
        if iss.get("severity") != "critical":
            continue
        if iss.get("dimension", "").lower() in _RETRY_WORTHY_DIMENSIONS:
            return True
    return False


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

def _run_analysis_worker(task_id: str, is_main: bool, user_query: str, schema: str, conv_context_str: str, df, result_queue: queue.Queue, persona: str = "executive_analyst", judge_feedback: str = "", economy: bool = False, force_validate: bool = False):
    """
    Runs the generate -> execute -> fix loop for a single task.
    Puts status updates and final result into result_queue.

    persona: which analytical persona this lane adopts (executive_analyst |
             forensic_segmenter). Routed through to generate_analysis_code so
             the two parallel lanes produce genuinely different angles.
    judge_feedback: if non-empty, prepended to the user query so a re-run
                    triggered by the Quality Auditor can address specific
                    issues raised by the previous judge verdict.
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

    effective_query = user_query
    if judge_feedback:
        effective_query = (
            f"{user_query}\n\n"
            f"PRIOR-RUN JUDGE FEEDBACK (must be addressed in the new analysis):\n"
            f"{judge_feedback}"
        )

    if is_main:
        _enqueue_event("status", {"message": "Generating analysis code...", "step": "generate_code"})
    else:
        _enqueue_event("status", {"message": "Launching background deep-dive analysis...", "step": "deep_dive_start"})

    try:
        code = generate_analysis_code(effective_query, schema, conv_context_str, persona=persona)
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
                # Smart-gate: skip the validator LLM call on the happy path
                # (saves ~10s/query). Always runs in Deep Verify Mode
                # (force_validate=True) or when heuristics flag a suspect result.
                should_validate = force_validate or _validation_likely_needed(effective_query, last_result_summary)
                if should_validate:
                    if is_main: _enqueue_event("status", {"message": "Validating output...", "step": "validate"})
                    try:
                        validation = validate_and_refine(effective_query, code, last_result_summary, schema, economy=economy)
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
                    code = fix_code(code, exec_result["error"], effective_query, schema)
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


def run_agent_stream(
    user_query: str,
    conversation_context: dict = None,
    quick_mode: bool = False,
    economy_mode: bool = False,
    deep_verify_mode: bool = False,
):
    """
    Generator version of run_agent that yields progress updates
    as SSE JSON events. Runs tasks in parallel using ThreadPoolExecutor.

    quick_mode: if True, skips the deep-dive lane (and therefore the Research
        Auditor too). Faster (~30s saved), at the cost of forensic-segmentation
        insight in the narrative.
    economy_mode: if True, routes the low-risk auxiliary calls (validate,
        audit, followups) to gemini-2.5-flash-lite. Critical-path calls
        (code generation, narrative, judge) stay on gemini-2.5-flash.
    deep_verify_mode: if True, enables the judge-driven audit loop with
        DEEP_VERIFY_RETRY_BUDGET retries. The judge can re-trigger code
        generation when it finds critical grounding or logical-integrity
        issues. Off by default to keep latency tight on the happy path.
    """
    retry_budget = DEEP_VERIFY_RETRY_BUDGET if deep_verify_mode else JUDGE_RETRY_BUDGET
    import json
    def _yield_event(event_type: str, data: dict):
        return json.dumps({"type": event_type, "data": data})

    yield _yield_event("status", {"message": "Initializing...", "step": "init"})

    df = get_dataframe()
    schema = get_schema_prompt(df)
    conv_context_str = build_conversation_context(conversation_context.get("history", [])) if conversation_context else ""

    # Two parallel lanes — each with a distinct analytical persona so the
    # outputs are genuinely complementary (executive headline vs. forensic
    # segmentation) rather than redundant.
    deep_dive_query = (
        f"DEEP DIVE CONTEXT: Original query was '{user_query}'. Task: Without explicitly "
        f"repeating the answer to the main query, break the data down by a relevant "
        f"categorical segment (e.g., network, merchant_category, age_group, state) to "
        f"find interesting deeper insights or correlations. If the original query is "
        f"already a breakdown, find an anomaly instead."
    )

    def _run_lanes(judge_feedback: str = ""):
        """Run the analysis lane(s) and collect worker_results.

        In Quick Mode, only the main lane runs — the deep-dive lane (and
        therefore the Research Auditor) is skipped entirely.
        """
        q = queue.Queue()
        tasks = [
            {"id": "main", "query": user_query, "is_main": True, "persona": "executive_analyst"},
        ]
        if not quick_mode:
            tasks.append(
                {"id": "deep_dive_1", "query": deep_dive_query, "is_main": False, "persona": "forensic_segmenter"}
            )
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(tasks))) as executor:
            futures = {
                executor.submit(
                    _run_analysis_worker,
                    t["id"], t["is_main"], t["query"], schema, conv_context_str, df, q,
                    t["persona"], judge_feedback, economy_mode, deep_verify_mode,
                ): t["id"]
                for t in tasks
            }
            completed = 0
            while completed < len(tasks):
                try:
                    msg = q.get(timeout=0.1)
                    if "event_json" in msg:
                        yield ("event", msg["event_json"])
                    else:
                        results[msg["task_id"]] = msg
                        completed += 1
                except queue.Empty:
                    if all(f.done() for f in futures):
                        while not q.empty():
                            msg = q.get()
                            if "event_json" in msg:
                                yield ("event", msg["event_json"])
                            else:
                                results[msg["task_id"]] = msg
                        break
        yield ("results", results)

    # ----- Lane execution (initial pass) -----
    worker_results = {}
    for kind, payload in _run_lanes():
        if kind == "event":
            yield payload
        else:
            worker_results = payload

    main_res = worker_results.get("main", {})
    if not main_res.get("success"):
        error_msg = main_res.get("error", "Unknown error")
        yield _yield_event("final", {
            "response": f"I couldn't produce a working analysis. Last error: {error_msg}",
            "result": {"success": False, "raw_output": error_msg, "code": ""},
            "steps": main_res.get("steps", [])
        })
        return

    # ----- Agent #4: Research Auditor -----
    # Audits each deep-dive lane's output for statistical meaningfulness,
    # consistency with the main result, and relevance. Invalid findings are
    # dropped; weak-but-valid ones are surfaced with a caveat.
    # Trivial deep-dives (very short or single-row outputs) skip the LLM
    # auditor — there is nothing meaningful to audit, and the round-trip
    # adds ~10s for no gain.
    def _is_trivial_deep_dive(summary: str) -> bool:
        s = (summary or "").strip()
        if len(s) < 80:
            return True
        if s.count("\n") < 2 and len(s) < 200:
            return True
        return False

    def _collect_audited_deep_dives(results):
        accepted = []
        for t_id, res in results.items():
            if t_id == "main" or not res.get("success"):
                continue
            summary = res.get("last_result_summary")
            if not summary or summary == "No output":
                continue
            if _is_trivial_deep_dive(summary):
                continue  # skip auditor entirely; trivial finding dropped
            audit = audit_deep_dive(
                user_query,
                main_res.get("last_result_summary", ""),
                summary,
                economy=economy_mode,
            )
            if audit["valid"]:
                if audit["caveat"]:
                    accepted.append(f"{summary}\n\n[Auditor caveat: {audit['caveat']}]")
                else:
                    accepted.append(summary)
        return accepted

    yield _yield_event("status", {"message": "Auditing deep-dive findings...", "step": "audit_deep_dive"})
    deep_dive_outputs = _collect_audited_deep_dives(worker_results)

    # ----- Narrative + Judge with retry loop -----
    # The Quality Auditor (Agent #6) runs once on the first narrative. If it
    # rejects the response with a critical issue, we re-run the analysis lanes
    # with the judge's issues injected as feedback (capped at JUDGE_RETRY_BUDGET
    # extra passes). This is the "auto-patch logic traces" path on the diagram.
    def _build_narrative(main_result, deep_dives):
        try:
            raw = generate_narrative(
                user_query,
                main_result.get("last_code", ""),
                main_result.get("last_result_summary", ""),
                deep_dive_results=deep_dives,
                stdout="",
            )
            try:
                return json.loads(raw)
            except Exception:
                return {
                    "summary": "Analysis generated but failed to parse into UI cards.",
                    "narrative": raw,
                    "cards": [],
                }
        except Exception:
            return {
                "summary": "Analysis generated but formatting failed.",
                "narrative": f"Analysis complete.\n\n{main_result.get('last_result_summary', '')}",
                "cards": [],
            }

    def _format_judge_feedback(v):
        issues = v.get("issues") or []
        if not issues:
            return v.get("verdict_summary", "Judge requested re-analysis.")
        lines = []
        for iss in issues:
            dim = iss.get("dimension", "issue")
            desc = iss.get("description", "")
            lines.append(f"- [{dim}] {desc}")
        return "The previous analysis was rejected by the Quality Auditor for these reasons:\n" + "\n".join(lines)

    yield _yield_event("status", {"message": "Synthesizing final insights...", "step": "narrative"})
    parsed_narrative = _build_narrative(main_res, deep_dive_outputs)

    yield _yield_event("status", {"message": "Finalizing insights & running quality review...", "step": "judge"})

    def _get_followups():
        try:
            return generate_followups(user_query, main_res.get("last_result_summary", ""), economy=economy_mode)
        except Exception:
            return []

    def _run_judge(narrative_text, summary):
        try:
            return judge_response(
                user_query,
                narrative_text,
                result={"success": True, "raw_output": summary},
            )
        except Exception:
            import traceback
            with open("crash_debug.txt", "w") as f:
                f.write(traceback.format_exc())
            return {"judge_ran": False, "confidence": "low"}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_followups = executor.submit(_get_followups)
        future_judge = executor.submit(_run_judge, parsed_narrative["narrative"], main_res.get("last_result_summary", ""))
        followups = future_followups.result()
        verdict = future_judge.result()

    retries_used = 0
    while retries_used < retry_budget and _judge_warrants_retry(verdict):
        retries_used += 1
        feedback = _format_judge_feedback(verdict)
        yield _yield_event("status", {
            "message": f"Quality Auditor flagged a critical issue. Re-running analysis (retry {retries_used}/{retry_budget})...",
            "step": "judge_retry",
        })
        for kind, payload in _run_lanes(judge_feedback=feedback):
            if kind == "event":
                yield payload
            else:
                worker_results = payload
        new_main = worker_results.get("main", {})
        if not new_main.get("success"):
            break
        main_res = new_main
        deep_dive_outputs = _collect_audited_deep_dives(worker_results)
        parsed_narrative = _build_narrative(main_res, deep_dive_outputs)
        verdict = _run_judge(parsed_narrative["narrative"], main_res.get("last_result_summary", ""))

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


def run_agent(
    user_query: str,
    conversation_context: dict = None,
    quick_mode: bool = False,
    economy_mode: bool = False,
    deep_verify_mode: bool = False,
) -> dict:
    """Main entry point for the code interpreter agent.

    quick_mode is accepted for API parity but has no effect here — this
    single-lane path never runs a deep-dive in the first place.
    economy_mode routes auxiliary calls (validate, followups) through
    gemini-2.5-flash-lite.
    deep_verify_mode enables the judge-driven audit loop with
    DEEP_VERIFY_RETRY_BUDGET retries (off by default).
    """
    del quick_mode  # accepted for API parity, no effect in single-lane path
    retry_budget = DEEP_VERIFY_RETRY_BUDGET if deep_verify_mode else JUDGE_RETRY_BUDGET
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
    judge_feedback = ""
    judge_retries_used = 0

    # Effective query carries judge feedback on subsequent passes.
    def _build_effective_query():
        if judge_feedback:
            return (
                f"{user_query}\n\n"
                f"PRIOR-RUN JUDGE FEEDBACK (must be addressed in the new analysis):\n"
                f"{judge_feedback}"
            )
        return user_query

    # -----------------------------------------------------------------------
    # STEP 1: Generate initial code
    # -----------------------------------------------------------------------
    try:
        code = generate_analysis_code(_build_effective_query(), schema, conv_context_str)
    except Exception as e:
        return _error_result(
            f"I couldn't generate analysis code for your question. Please try rephrasing. ({e})",
            steps,
        )

    # -----------------------------------------------------------------------
    # STEPS 2-4: Execute -> Narrate -> Judge, with judge-driven re-analysis
    # -----------------------------------------------------------------------
    # The Quality Auditor runs once per pass. If it rejects the response with a
    # critical issue, we regenerate code with its issues injected as feedback
    # and re-run the whole analysis. Capped at JUDGE_RETRY_BUDGET extra passes.
    def _format_judge_feedback(v):
        issues = v.get("issues") or []
        if not issues:
            return v.get("verdict_summary", "Judge requested re-analysis.")
        lines = [f"- [{iss.get('dimension', 'issue')}] {iss.get('description', '')}" for iss in issues]
        return "The previous analysis was rejected by the Quality Auditor for these reasons:\n" + "\n".join(lines)

    narrative = ""
    followups = []
    verdict = {"judge_ran": False}
    exec_result = {"success": False, "stdout": ""}

    while True:
        # ---- Execute -> Fix -> Validate inner loop ----
        for attempt in range(1, MAX_RETRIES + 1):
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
                    should_validate = deep_verify_mode or _validation_likely_needed(_build_effective_query(), last_result_summary)
                    if should_validate:
                        try:
                            validation = validate_and_refine(
                                _build_effective_query(), code, last_result_summary, schema, economy=economy_mode
                            )
                            if not validation.get("aligned") and validation.get("new_code"):
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
                    try:
                        code = fix_code(code, exec_result["error"], _build_effective_query(), schema)
                        steps.append({"iteration": attempt, "phase": "fix", "code": code})
                    except Exception:
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

        # ---- Narrative ----
        try:
            narrative = generate_narrative(
                user_query,
                last_code,
                last_result_summary,
                stdout=exec_result.get("stdout", ""),
            )
        except Exception:
            narrative = f"Analysis complete. Here are the results:\n\n{last_result_summary}"

        # ---- Followups + Judge in parallel ----
        def _gen_follow():
            try:
                return generate_followups(user_query, last_result_summary, economy=economy_mode)
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

        # ---- Judge-driven retry decision ----
        if judge_retries_used < retry_budget and _judge_warrants_retry(verdict):
            judge_retries_used += 1
            judge_feedback = _format_judge_feedback(verdict)
            try:
                code = generate_analysis_code(_build_effective_query(), schema, conv_context_str)
            except Exception:
                break  # give up gracefully if regeneration fails
            continue
        break

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