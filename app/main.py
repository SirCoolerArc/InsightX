"""
main.py — InsightX Streamlit Application
=========================================
Entry point for the InsightX conversational analytics system.

Run from project root:
    streamlit run app/main.py

Architecture (v3 — Code Interpreter):
    User Input
        → agent.run_agent()                [code interpreter loop]
             ├─ code_planner generates pandas code
             ├─ sandbox executes code safely
             ├─ self-correction loop (fix errors / refine)
             └─ narrative generation (D-S-I-R)
        → conversation_manager.add_turn()  [update state]
        → ui_components.*                  [render to screen]
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st

# ── Page config — must be first Streamlit call ──
st.set_page_config(
    page_title="BRAIN-DS — Leadership Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.agent import run_agent, format_investigation_trace
from src.conversation_manager import ConversationManager
from src.judge import format_judge_badge, get_judge_expander_content
from app.ui_components import (
    inject_global_css,
    render_header,
    render_welcome,
    render_user_message,
    render_assistant_response,
    render_metrics_strip,
    render_followup_suggestions,
    render_thinking,
    render_sidebar,
    render_error,
)


# ---------------------------------------------------------------------------
# SESSION STATE INITIALISATION
# ---------------------------------------------------------------------------

def init_session():
    """Initialise all session state variables on first load."""
    if "cm" not in st.session_state:
        st.session_state.cm = ConversationManager()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "prefilled_query" not in st.session_state:
        st.session_state.prefilled_query = None


# ---------------------------------------------------------------------------
# CORE PROCESSING PIPELINE
# ---------------------------------------------------------------------------

def process_query(user_input: str) -> tuple[str, dict, list[str], str, list, dict]:
    """
    Run the full code interpreter pipeline for a user query.

    Returns
    -------
    tuple of (response, primary_result, followups, mode, steps, agent_result)
    """
    cm = st.session_state.cm
    context = cm.get_context()

    agent_result = run_agent(user_input, conversation_context=context)

    response  = agent_result["response"]
    result    = agent_result["result"]
    followups = agent_result["followups"]
    mode      = agent_result["mode"]
    steps     = agent_result["steps"]

    # Record this turn with code history for follow-ups
    cm.add_turn(
        user_query=user_input,
        parsed_intent={},
        analytics_result=result,
        insight_response=response,
        code=agent_result.get("code", ""),
        result_summary=result.get("summary", "") if isinstance(result, dict) else "",
    )

    return response, result, followups, mode, steps, agent_result


# ---------------------------------------------------------------------------
# RENDER CONVERSATION HISTORY
# ---------------------------------------------------------------------------

def render_history():
    """Render all previous messages in the conversation."""
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            render_assistant_response(
                msg["content"],
                result=msg.get("result"),
            )

            # Show generated code in expander
            code = msg.get("code", "")
            if code:
                with st.expander("🐍 Generated Code", expanded=False):
                    st.code(code, language="python")

            # Show judge badge + expander if judge ran
            verdict = msg.get("verdict", {})
            if verdict and verdict.get("judge_ran"):
                badge_html = format_judge_badge(verdict)
                if badge_html:
                    st.markdown(
                        f"<div style='padding: 0 40px;'>{badge_html}</div>",
                        unsafe_allow_html=True
                    )
                with st.expander("⚖️ Quality verification", expanded=False):
                    st.markdown(get_judge_expander_content(verdict))

            # Show investigation trace if available
            if msg.get("steps"):
                trace = format_investigation_trace(msg["steps"])
                if trace:
                    with st.expander(
                        f"🔍 Execution trace ({len(msg['steps'])} steps)",
                        expanded=False
                    ):
                        st.markdown(trace)

            # Show follow-ups only for the last assistant message
            if msg == st.session_state.messages[-1] and msg.get("followups"):
                render_followup_suggestions(msg["followups"])


# ---------------------------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------------------------

def main():
    init_session()

    # ── Global styles ──
    inject_global_css()

    # ── Header ──
    render_header()

    # ── Sidebar ──
    render_sidebar(st.session_state.cm)

    # ── Main content area ──
    st.markdown("""
    <div style="
        max-width: 900px;
        margin: 0 auto;
        padding: 24px 0 120px;
        min-height: 80vh;
    ">
    """, unsafe_allow_html=True)

    # Show welcome screen or conversation history
    if not st.session_state.messages:
        render_welcome()
    else:
        render_history()

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chat Input ──
    prefilled = st.session_state.get("prefilled_query")
    if prefilled:
        st.session_state.prefilled_query = None
        user_input = prefilled
    else:
        user_input = None

    # Streamlit chat input
    chat_input = st.chat_input(
        placeholder="Ask anything about the transaction data...",
        key="chat_input",
    )

    # Determine final input
    final_input = chat_input or user_input

    if final_input and final_input.strip():
        query = final_input.strip()

        # Add user message to history immediately
        st.session_state.messages.append({
            "role": "user",
            "content": query,
        })

        # Process the query
        with st.spinner(""):
            render_thinking()
            try:
                response, result, followups, mode, steps, agent_result = process_query(query)

                # Add assistant response to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "result": result,
                    "followups": followups,
                    "mode": mode,
                    "steps": steps,
                    "verdict": agent_result.get("verdict", {}),
                    "code": agent_result.get("code", ""),
                })

            except Exception as e:
                import traceback
                traceback.print_exc()  # Print full traceback to terminal
                error_msg = f"Something went wrong: {str(e)}"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "result": None,
                    "followups": [],
                    "mode": "code_interpreter",
                    "steps": [],
                })

        st.rerun()


if __name__ == "__main__":
    main()