"""
judge.py — InsightX LLM-as-Judge Validation Layer
===================================================
Implements a Gemini-powered judge that validates analytics responses
before they reach the user.

The judge evaluates four dimensions:
    1. Relevance    — does the response answer what was actually asked?
    2. Grounding    — are all cited numbers traceable to computed data?
    3. Calibration  — is language appropriately hedged for the data?
    4. Safety       — no unsupported causal claims or fraud confirmations?

The judge either:
    - Approves the response (passes through unchanged)
    - Corrects it automatically (replaces with a better version)
    - Appends a caveat (flags a specific concern inline)

IMPORTANT: The judge uses Gemini 3.1 Pro — the strongest available model
— because evaluation requires genuine reasoning about what the data
supports vs what the narrative claims.

Integration point: called by agent.py after _synthesise() or
generate_insight(), before returning to the user.

Usage:
    from src.judge import judge_response
    verdict = judge_response(query, response, observations, result)
    final_response = verdict["final_response"]
"""

import json
import re
import os
from google import genai
from dotenv import load_dotenv

try:
    from src.data_loader import CONSTANTS
except ModuleNotFoundError:
    from data_loader import CONSTANTS

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Best model for evaluation — needs strongest reasoning
JUDGE_MODEL = "gemini-3.1-pro-preview"

# Fallback if judge model is unavailable
FALLBACK_MODEL = "gemini-2.5-pro"


# ---------------------------------------------------------------------------
# JUDGE SYSTEM PROMPT
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM_PROMPT = f"""
You are a senior data quality judge for InsightX, an analytics system for
a digital payments platform. Your job is to evaluate whether a generated
insight response meets strict quality standards before it reaches
business leaders.

You evaluate responses on four dimensions:

1. RELEVANCE
   Does the response directly answer the user's original question?
   Is the answer clearly stated in the first sentence?
   Fail if: the response drifts, hedges the main point, or buries the answer.

2. GROUNDING
   Are all statistics in the response traceable to the computed data provided?
   No number should appear in the response that isn't in the observations.
   Fail if: any statistic appears that cannot be found in the computed data.

3. CALIBRATION
   Is the language appropriately scaled to the magnitude of differences?
   Guidelines (strictly enforced):
   - Spread < 0.5pp  → must use "marginal", "negligible", "slight"
   - Spread 0.5–2pp  → may use "notable", "meaningful"
   - Spread > 2pp    → may use "significant", "considerable"
   - Spread > 3pp    → may use "dramatic"
   Fail if: strong language is used for small differences, or vice versa.

4. SAFETY
   The response must never:
   - Confirm fraud (fraud_flag = 1 means flagged for review, NOT confirmed fraud)
   - Make causal claims ("X causes Y") without explicit data support
   - Claim statistical significance without a significance test
   - Reference data not in the provided observations
   Overall failure rate baseline is {CONSTANTS['OVERALL_FAILURE_RATE']}%.
   Fraud flag rate baseline is {CONSTANTS['OVERALL_FLAG_RATE']}% (flagged for review only).

RESPONSE FORMAT:
Return ONLY valid JSON. No explanation, no markdown fences.

{{
    "approved": true/false,
    "confidence": "high" | "medium" | "low",
    "scores": {{
        "relevance": 1-5,
        "grounding": 1-5,
        "calibration": 1-5,
        "safety": 1-5
    }},
    "issues": [
        // List of specific issues found. Empty list if approved.
        // Each issue: {{"dimension": "...", "description": "...", "severity": "critical"|"minor"}}
    ],
    "correction_needed": true/false,
    "corrected_response": null or "corrected response text if correction_needed is true",
    "caveat": null or "short caveat string to append if minor issues only"
}}

SCORING GUIDE:
5 = Excellent, no issues
4 = Good, minor imprecision
3 = Acceptable, needs caveat
2 = Poor, needs correction
1 = Fail, misleading or unsafe

If ALL scores are >= 4: approved = true, correction_needed = false
If ANY score is <= 2: approved = false, correction_needed = true, provide corrected_response
If scores are 3: approved = true, correction_needed = false, provide caveat
"""


# ---------------------------------------------------------------------------
# MAIN JUDGE FUNCTION
# ---------------------------------------------------------------------------

def judge_response(
    original_query: str,
    response: str,
    observations: list[dict] = None,
    result: dict = None,
) -> dict:
    """
    Evaluate a generated response before it reaches the user.

    Parameters
    ----------
    original_query : str
        The user's original question
    response : str
        The generated narrative response to evaluate
    observations : list[dict], optional
        Investigation steps from agentic loop (each with data_summary)
    result : dict, optional
        Primary analytics result from analytics_engine

    Returns
    -------
    dict with keys:
        - approved: bool
        - confidence: str
        - scores: dict
        - issues: list
        - final_response: str  (corrected/caveated/original)
        - judge_ran: bool
        - verdict_summary: str  (human-readable one-liner)
    """
    # Build the data context for the judge
    data_context = _build_data_context(observations, result)

    prompt = _build_judge_prompt(original_query, response, data_context)

    try:
        raw = _call_judge(prompt)
        verdict = _parse_verdict(raw)
        final_response = _apply_verdict(response, verdict)

        return {
            "approved": verdict.get("approved", True),
            "confidence": verdict.get("confidence", "medium"),
            "scores": verdict.get("scores", {}),
            "issues": verdict.get("issues", []),
            "final_response": final_response,
            "judge_ran": True,
            "verdict_summary": _summarise_verdict(verdict),
        }

    except Exception as e:
        # If judge fails for any reason, pass through original response
        # Never block the user because of a judge failure
        return {
            "approved": True,
            "confidence": "low",
            "scores": {},
            "issues": [],
            "final_response": response,
            "judge_ran": False,
            "verdict_summary": f"Judge unavailable ({str(e)[:50]}) — response passed through.",
        }


# ---------------------------------------------------------------------------
# PROMPT BUILDER
# ---------------------------------------------------------------------------

def _build_data_context(
    observations: list[dict] = None,
    result: dict = None,
) -> str:
    """Build a concise data context string for the judge."""
    lines = ["COMPUTED DATA (only these numbers are valid to cite):"]

    # From agentic observations
    if observations:
        for obs in observations:
            lines.append(f"\nStep {obs.get('step_num', '?')}: {obs.get('query_desc', '')}")
            lines.append(obs.get("data_summary", "No data"))

    # From code interpreter result (new pipeline)
    elif result and result.get("raw_output"):
        lines.append("\nCode interpreter output:")
        raw = result["raw_output"]
        if isinstance(raw, str):
            lines.append(raw[:2000])
        else:
            lines.append(json.dumps(raw, indent=2, default=str)[:2000])

    # From single-pass result (legacy)
    elif result and result.get("summary"):
        summary = result["summary"]
        if isinstance(summary, str):
            lines.append(f"\nAnalytics result summary:\n{summary}")
        else:
            lines.append("\nAnalytics result summary:")
            lines.append(json.dumps(summary, indent=2))
        if result.get("data") is not None and hasattr(result["data"], "to_string"):
            lines.append("\nData table:")
            lines.append(result["data"].head(10).to_string(index=False))

    else:
        lines.append("No structured data available.")

    return "\n".join(lines)


def _build_judge_prompt(
    original_query: str,
    response: str,
    data_context: str,
) -> str:
    return f"""{_JUDGE_SYSTEM_PROMPT}

ORIGINAL USER QUESTION:
{original_query}

GENERATED RESPONSE TO EVALUATE:
{response}

{data_context}

Evaluate the response against all four dimensions and return your verdict as JSON.
"""


# ---------------------------------------------------------------------------
# GEMINI CALL
# ---------------------------------------------------------------------------

def _call_judge(prompt: str) -> str:
    """Call the judge model with retry logic."""
    import time
    
    for model in [JUDGE_MODEL, FALLBACK_MODEL]:
        for attempt in range(2):  # 2 attempts per model
            try:
                response = _client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    if attempt == 0:
                        time.sleep(15)  # Wait 15s then retry
                        continue
                    else:
                        break  # Try fallback model
                elif "NOT_FOUND" in error_str or "404" in error_str:
                    break  # Try fallback model
                else:
                    raise  # Re-raise unexpected errors
    
    raise RuntimeError("All judge models rate limited or unavailable")


# ---------------------------------------------------------------------------
# RESPONSE PARSING & APPLICATION
# ---------------------------------------------------------------------------

def _parse_verdict(raw: str) -> dict:
    """Parse the JSON verdict from the judge model."""
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Return a safe default if parsing fails
        return {
            "approved": True,
            "confidence": "low",
            "scores": {},
            "issues": [],
            "correction_needed": False,
            "corrected_response": None,
            "caveat": None,
        }


def _apply_verdict(original_response: str, verdict: dict) -> str:
    """
    Apply the judge's verdict to produce the final response.

    Priority:
    1. If correction_needed → use corrected_response
    2. If caveat → append caveat to original
    3. Otherwise → return original unchanged
    """
    if verdict.get("correction_needed") and verdict.get("corrected_response"):
        return verdict["corrected_response"]

    if verdict.get("caveat"):
        caveat = verdict["caveat"].strip()
        return f"{original_response}\n\n*{caveat}*"

    return original_response


def _summarise_verdict(verdict: dict) -> str:
    """Produce a one-line human-readable verdict summary for logging."""
    if verdict.get("approved"):
        scores = verdict.get("scores", {})
        avg = sum(scores.values()) / len(scores) if scores else "?"
        return f"✓ Approved (avg score: {avg:.1f}/5)"
    else:
        issues = verdict.get("issues", [])
        critical = [i for i in issues if i.get("severity") == "critical"]
        return f"✗ Flagged — {len(critical)} critical issue(s): " + \
               ", ".join(i.get("dimension", "") for i in critical[:3])


# ---------------------------------------------------------------------------
# UI HELPERS
# ---------------------------------------------------------------------------

def format_judge_badge(verdict: dict) -> str:
    """
    Return a premium HTML badge for display in the Streamlit UI.
    Shows judge approval status with visual emphasis.
    """
    if not verdict.get("judge_ran"):
        return ""

    scores = verdict.get("scores", {})
    avg = sum(scores.values()) / len(scores) if scores else 0

    if verdict.get("approved") and avg >= 4:
        color = "#00d4aa"
        bg = "#00d4aa10"
        icon = "✓"
        label = f"Verified ({avg:.1f}/5)"
    elif verdict.get("approved"):
        color = "#f0a500"
        bg = "#f0a50010"
        icon = "~"
        label = f"Caveated ({avg:.1f}/5)"
    else:
        color = "#ff4757"
        bg = "#ff475710"
        icon = "✗"
        label = f"Corrected ({avg:.1f}/5)"

    return f"""
    <div style="
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'Space Mono', monospace;
        font-size: 11px;
        color: {color};
        background: {bg};
        border: 1px solid {color}30;
        border-radius: 20px;
        padding: 4px 14px;
        box-shadow: 0 0 12px {color}10;
    ">
        <span style="font-weight:700;">{icon}</span>
        <span>{label}</span>
    </div>
    """


def get_judge_expander_content(verdict: dict) -> str:
    """
    Return markdown content for a judge details expander in Streamlit.
    """
    if not verdict.get("judge_ran"):
        return "Judge did not run for this response."

    scores = verdict.get("scores", {})
    issues = verdict.get("issues", [])

    lines = ["**Quality Scores**\n"]
    for dim, score in scores.items():
        bar = "█" * score + "░" * (5 - score)
        lines.append(f"`{dim.capitalize():<12}` {bar} {score}/5")

    if issues:
        lines.append("\n**Issues Found**")
        for issue in issues:
            severity_icon = "🔴" if issue.get("severity") == "critical" else "🟡"
            lines.append(
                f"{severity_icon} **{issue.get('dimension', '').capitalize()}**: "
                f"{issue.get('description', '')}"
            )
    else:
        lines.append("\n✓ No issues found.")

    lines.append(f"\n**Verdict:** {verdict.get('verdict_summary', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Quick self-test — run from project root: python -m src.judge
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Use real analytics engine so judge receives actual computed data
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from src.analytics_engine import run_query
    from src.insight_generator import generate_insight

    test_cases = [
        {
            "name": "Good response — should approve",
            "query": "Which transaction type has the highest failure rate?",
            "parsed": {
                "intent": "comparative",
                "metric": "failure_rate",
                "filters": {},
                "group_by": "transaction_type",
                "comparison_values": ["P2P", "P2M", "Bill Payment", "Recharge"],
                "assumptions": [],
                "raw_query": "Which transaction type has the highest failure rate?",
            }
        },
        {
            "name": "Unsafe response — confirms fraud (injected)",
            "query": "Which bank has the highest fraud flag rate?",
            "parsed": {
                "intent": "risk",
                "metric": "fraud_flag_rate",
                "filters": {},
                "group_by": "sender_bank",
                "assumptions": [],
                "raw_query": "Which bank has the highest fraud flag rate?",
            },
            # Override the generated response with a bad one to test judge catches it
            "override_response": (
                "Kotak bank has the highest fraud rate at 0.25%, indicating confirmed "
                "fraudulent transactions that require immediate action."
            )
        },
    ]

    for tc in test_cases:
        print("\n" + "=" * 60)
        print(f"Test: {tc['name']}")
        print("=" * 60)

        result = run_query(tc["parsed"])
        response = tc.get("override_response") or generate_insight(result)

        verdict = judge_response(
            original_query=tc["query"],
            response=response,
            result=result,
        )

        print(f"Judge ran  : {verdict['judge_ran']}")
        print(f"Approved   : {verdict['approved']}")
        print(f"Scores     : {verdict['scores']}")
        print(f"Verdict    : {verdict['verdict_summary']}")
        if verdict["issues"]:
            for issue in verdict["issues"]:
                print(f"  [{issue.get('severity','?').upper()}] "
                      f"{issue.get('dimension')}: {issue.get('description')}")
        print(f"\nFinal response:\n{verdict['final_response']}")