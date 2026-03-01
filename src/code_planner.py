"""
code_planner.py — InsightX Code Generation Engine
===================================================
Uses Gemini to generate pandas code that answers user queries
about the transaction dataset.

This replaces the old query_parser.py + analytics_engine.py combo.
Instead of parsing into fixed intents, the LLM writes actual pandas
code that gets executed in sandbox.py.

Pipeline:
    user_query + schema + context
        → Gemini generates pandas code
        → code executed in sandbox
        → if error: Gemini fixes the code (up to MAX_RETRIES)
        → if misaligned: Gemini writes new code
        → final result returned

Usage:
    from src.code_planner import generate_analysis_code, fix_code, validate_and_refine
"""

import os
import json
import time
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

MAX_RETRIES = 3


def _call_gemini(prompt: str, retries: int = 2) -> str:
    """
    Call Gemini with automatic retry on rate limit (429) errors.
    Waits 10s then 20s before retrying.
    """
    for attempt in range(retries + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str) and attempt < retries:
                wait = 12 * (attempt + 1)  # 12s, 24s
                print(f"[code_planner] Rate limited, waiting {wait}s... (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            raise


# ---------------------------------------------------------------------------
# SCHEMA DESCRIPTION (injected into every prompt)
# ---------------------------------------------------------------------------

def get_schema_prompt(df) -> str:
    """
    Build a comprehensive schema description for the LLM.
    Includes column names, dtypes, valid values, and sample rows.
    """
    # Get basic info
    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        nunique = df[col].nunique()
        nulls = df[col].isnull().sum()

        # Get sample values for categorical columns
        if df[col].dtype == "object" or nunique <= 20:
            unique_vals = sorted(df[col].dropna().unique().tolist())
            if len(unique_vals) > 15:
                vals_str = str(unique_vals[:15]) + f" ... ({nunique} unique)"
            else:
                vals_str = str(unique_vals)
        else:
            vals_str = f"range: {df[col].min()} to {df[col].max()}"
            if dtype.startswith("float") or dtype.startswith("int"):
                vals_str += f", mean: {df[col].mean():.2f}"

        null_str = f", {nulls} nulls" if nulls > 0 else ""
        col_info.append(f"  - {col} ({dtype}): {vals_str}{null_str}")

    columns_desc = "\n".join(col_info)

    # Sample rows
    sample = df.head(5).to_string(index=False)

    return f"""DATASET: UPI Digital Payment Transactions (India)
Total rows: {len(df):,}
Total columns: {len(df.columns)}

COLUMNS:
{columns_desc}

IMPORTANT NOTES:
- merchant_category is NULL for P2P transactions (only applies to P2M)
- receiver_age_group is NULL for non-P2P transactions
- fraud_flag: 0 = not flagged, 1 = flagged for review (NOT confirmed fraud)
- is_failed: derived column, 1 = FAILED, 0 = SUCCESS
- is_weekend: 0 = weekday, 1 = weekend
- hour_of_day: 0-23
- The DataFrame is available as `df` (pandas DataFrame)

SAMPLE ROWS:
{sample}
"""


# ---------------------------------------------------------------------------
# CODE GENERATION PROMPT
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are BRAIN-DS, an expert data analyst. Your job is to write Python pandas code
to answer questions about a UPI digital payments dataset.

RULES:
1. You MUST assign your final answer to a variable called `result`.
2. `result` MUST strictly follow this dictionary structure:
    {{
        "answer": "A brief text answer to the question (1-2 sentences)",
        "data": [{{"col1": val1, "col2": val2}}], # The actual computed data points
        "chart": {{ # CRITICAL: You MUST include this chart object for ANY comparison, breakdown, trend, or distribution. Omit ONLY for single scalar answers.
            "type": "bar" | "line" | "pie", # Use 'pie' for share/proportions/percentages, 'line' for time trends (e.g., hour_of_day), and 'bar' for ranking/comparing distinct categories.
            "data": [{{"x": val1, "y": val2}}], # Data for the chart
            "xKey": "x", # Exact string key of the x-axis variable
            "yKey": "y", # Exact string key of the y-axis variable
            "title": "Chart Title Here"
        }}
    }}
3. CRITICAL REQUIREMENT: If the user asks for a 'breakdown', 'trend', 'comparison', 'relationship', or uses words like 'vs', you MUST include the 'chart' object inside the 'result' dictionary.
4. The DataFrame is pre-loaded as `df`. You have `pd`, `np`, `math`, and `datetime` available.
5. Do NOT import anything — all needed libraries are already available.
6. Do NOT try to access files, network, or any external resources.
7. Do NOT modify the original DataFrame in a way that would affect future queries.
   Work on copies if needed (e.g. `df_filtered = df[df["col"] == "val"]`).
8. Use `.copy()` when creating filtered subsets to avoid SettingWithCopyWarning.
9. Round percentages to 2 decimal places.
10. Include relevant counts/totals alongside percentages (e.g. "1,234 out of 50,000").
11. For comparative analyses, always compute ALL segments for fair comparison.
12. Return ONLY valid Python code. No markdown fences, no explanations outside comments.
13. OUT OF DOMAIN: If the user's query is completely unrelated or random regarding the digital payments dataset, just set `result = {{"answer": "This question is outside the scope of the digital payments transaction dataset.", "data": {{}}}}`

COMMON PATTERNS:
- Failure rate: `df["is_failed"].mean() * 100`
- Grouped failure rate: `df.groupby("col")["is_failed"].agg(["mean", "count"]).reset_index()`
- Fraud flag rate: `df["fraud_flag"].mean() * 100`
- Filter: `df_filtered = df[df["transaction_type"] == "P2P"].copy()`
"""


# ---------------------------------------------------------------------------
# CODE GENERATION
# ---------------------------------------------------------------------------

def generate_analysis_code(
    user_query: str,
    schema: str,
    conversation_context: str = "",
) -> str:
    """
    Ask Gemini to generate pandas analysis code for the user's query.

    Parameters
    ----------
    user_query : str
        The natural language question from the user.
    schema : str
        Dataset schema description (from get_schema_prompt).
    conversation_context : str
        Previous conversation turns for follow-up context.

    Returns
    -------
    str
        Python code string ready for sandbox execution.
    """
    context_block = ""
    if conversation_context:
        context_block = f"""
CONVERSATION CONTEXT (for follow-up questions):
{conversation_context}

If the user's question references previous analysis, use the context above to understand what they are referring to.
"""

    prompt = f"""{_SYSTEM_PROMPT}

{schema}
{context_block}
USER'S QUESTION: {user_query}

Write Python code to answer this question. Assign the final answer to `result`.
Return ONLY the Python code, nothing else."""

    try:
        raw = _call_gemini(prompt)
        code = _clean_code_response(raw)
        return code
    except Exception as e:
        raise RuntimeError(f"Failed to generate code: {e}")


# ---------------------------------------------------------------------------
# ERROR CORRECTION
# ---------------------------------------------------------------------------

def fix_code(
    original_code: str,
    error_message: str,
    user_query: str,
    schema: str,
) -> str:
    """
    Ask Gemini to fix code that produced an error.

    Parameters
    ----------
    original_code : str
        The code that failed.
    error_message : str
        The error traceback/message.
    user_query : str
        The original user question.
    schema : str
        Dataset schema description.

    Returns
    -------
    str
        Corrected Python code.
    """
    prompt = f"""{_SYSTEM_PROMPT}

{schema}

USER'S QUESTION: {user_query}

THE FOLLOWING CODE WAS GENERATED BUT PRODUCED AN ERROR:

```python
{original_code}
```

ERROR:
{error_message}

Fix the code to correctly answer the user's question. Make sure to assign the answer to `result`.
Return ONLY the corrected Python code, nothing else."""

    try:
        raw = _call_gemini(prompt)
        return _clean_code_response(raw)
    except Exception as e:
        raise RuntimeError(f"Failed to fix code: {e}")


# ---------------------------------------------------------------------------
# OUTPUT VALIDATION & REFINEMENT
# ---------------------------------------------------------------------------

def validate_and_refine(
    user_query: str,
    code: str,
    result_summary: str,
    schema: str,
) -> dict:
    """
    Ask Gemini whether the code output actually answers the user's question.

    Returns
    -------
    dict with keys:
        aligned : bool   — does the output answer the question?
        reason  : str    — why or why not
        new_code : str   — corrected code if not aligned (empty if aligned)
    """
    prompt = f"""You are a data analysis quality checker.

USER'S QUESTION: {user_query}

CODE THAT WAS EXECUTED:
```python
{code}
```

OUTPUT:
{result_summary}

DATASET SCHEMA:
{schema}

Does this output correctly and completely answer the user's question?

Return ONLY a JSON object (no markdown fences, no explanation):
{{
    "aligned": true/false,
    "reason": "brief explanation",
    "new_code": "corrected Python code if not aligned, empty string if aligned"
}}"""

    try:
        raw_text = _call_gemini(prompt)
        raw = _clean_json_response(raw_text)
        verdict = json.loads(raw)

        if not verdict.get("aligned") and verdict.get("new_code"):
            verdict["new_code"] = _clean_code_response(verdict["new_code"])

        return verdict
    except Exception:
        # If validation fails, assume the output is fine
        return {"aligned": True, "reason": "Validation skipped", "new_code": ""}


# ---------------------------------------------------------------------------
# FOLLOW-UP SUGGESTIONS
# ---------------------------------------------------------------------------

def generate_followups(user_query: str, result_summary: str) -> list[str]:
    """
    Generate 2-3 natural follow-up question suggestions.
    """
    prompt = f"""Based on this data analysis interaction, suggest exactly 3 natural follow-up questions
that a business leader might ask next. Keep them concise and specific.

USER'S QUESTION: {user_query}
ANALYSIS RESULT: {result_summary}

Return ONLY a JSON array of 3 strings, nothing else. Example:
["question 1", "question 2", "question 3"]"""

    try:
        raw_text = _call_gemini(prompt)
        raw = _clean_json_response(raw_text)
        followups = json.loads(raw)
        if isinstance(followups, list):
            return followups[:3]
        return []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# NARRATIVE GENERATION
# ---------------------------------------------------------------------------

def generate_narrative(
    user_query: str,
    code: str,
    result_summary: str,
    deep_dive_results: list[str] = None,
    stdout: str = "",
) -> str:
    """
    Generate a clear, executive-readable D-S-I-R narrative from code results.
    Weaves in deep dive insights if provided.
    """
    stdout_block = ""
    if stdout and stdout.strip():
        stdout_block = f"\nDEBUG OUTPUT:\n{stdout}"

    deep_dive_block = ""
    if deep_dive_results:
        joined_deep_dives = "\n\n".join(deep_dive_results)
        deep_dive_block = f"""
BACKGROUND DEEP-DIVE ANALYSIS:
Our background agents automatically ran related segmentations/correlations and found the following:
{joined_deep_dives}

IMPORTANT: Please weave these deeper insights into your 'Interpretation' and 'Supporting Metrics' sections naturally. Do not explicitly say 'a background agent found this', just present the insight as part of the overall data analysis.
"""

    current_time_str = datetime.now().strftime("%A, %B %d, %Y - %I:%M %p")
    prompt = f"""You are BRAIN-DS, a senior business analytics assistant for a digital payments platform.
You are tasked with presenting the results of a Python data analysis.

CURRENT SYSTEM TIME: {current_time_str}
(Use this to provide context-aware greetings if you choose to greet the user, e.g., "Good morning" vs "Good afternoon").

RULES:
1. You MUST output your response as valid, parseable JSON only. Do not wrap in markdown code blocks.
2. Follow this strict JSON schema:
{{
  "summary": "A 1-2 sentence high-level executive summary.",
  "narrative": "The full conversational D-S-I-R text response (using markdown).",
  "cards": [
    // Generate a FLEXIBLE number of cards (0 to 4+) depending on how much meaningful data is available.
    // Ensure the card count matches the complexity of the query. Do NOT create filler cards.
    // If a simple metric is requested, 1 card is enough. If a complex breakdown is provided, use multiple cards.
    // Option A: Metric Group
    {{
      "type": "metric_group",
      "title": "KEY PERFORMANCE INDICATORS",
      "metrics": [
        {{"label": "Metric Name", "value": "Value", "status": "success/warning/error/neutral"}}
      ]
    }},
    // Option B: Key-Value Table
    {{
      "type": "key_value",
      "title": "DATA BREAKDOWN",
      "sections": [
        {{"title": "Section Name", "items": [{{"label": "Key", "value": "Value"}}]}}
      ]
    }},
    // Option C: Insight List (for Deep Dives)
    {{
      "type": "insight_list",
      "title": "DEEP DIVE TRANSLATIONS",
      "items": [
        {{"title": "Insight", "description": "Details", "status": "success/warning/info"}}
      ]
    }}
  ]
}}
3. Use ONLY the numbers from the analysis output. NEVER invent statistics.
4. For the `narrative` field, naturally weave in the background deep dives if any. Be professional but conversational.

USER'S QUESTION: {user_query}

CODE EXECUTED:
```python
{code}
```

ANALYSIS OUTPUT:
{result_summary}
{stdout_block}
{deep_dive_block}

Output valid JSON:"""

    try:
        raw = _call_gemini(prompt)
        # Strip markdown fences if Gemini added them despite instructions
        clean_json = raw.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        
        # Verify it parses
        json.loads(clean_json.strip())
        return clean_json.strip()
    except Exception as e:
        fallback = {
            "summary": "Analysis completed, but I could not format the insights perfectly.",
            "narrative": f"Analysis complete. Raw result:\n{result_summary}",
            "cards": []
        }
        return json.dumps(fallback)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _clean_code_response(raw: str) -> str:
    """Strip markdown code fences and other non-code artifacts from LLM output."""
    code = raw.strip()

    # Remove markdown fence if present
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[3:].strip()

    if code.endswith("```"):
        code = code[:-3].strip()

    return code


def _clean_json_response(raw: str) -> str:
    """Strip markdown fences from JSON responses."""
    text = raw.strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def build_conversation_context(conversation_history: list[dict]) -> str:
    """
    Build a conversation context string from history for follow-up resolution.

    Parameters
    ----------
    conversation_history : list[dict]
        List of dicts with 'query', 'code', 'result_summary' keys.
    """
    if not conversation_history:
        return ""

    # Only include last 3 turns to keep context manageable
    recent = conversation_history[-3:]
    lines = []
    for i, turn in enumerate(recent, 1):
        lines.append(f"--- Turn {i} ---")
        lines.append(f"User asked: {turn.get('query', '')}")
        if turn.get("code"):
            lines.append(f"Code executed:\n{turn['code']}")
        if turn.get("result_summary"):
            lines.append(f"Result: {turn['result_summary']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("code_planner.py loaded successfully")
    print(f"Model: {MODEL}")
    print(f"Max retries: {MAX_RETRIES}")
