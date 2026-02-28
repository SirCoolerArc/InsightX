"""
ui_components.py — BRAIN-DS Streamlit UI Components (v2)
=========================================================
Reusable UI building blocks for the BRAIN-DS chat interface.
Handles all styling, custom HTML/CSS, and component rendering.

Design direction: Premium dark analytics dashboard with amber/gold accents.
Glassmorphism, micro-animations, and data-terminal DNA.
Professional, immersive, and trustworthy.
"""

import streamlit as st
import pandas as pd
import hashlib


# ---------------------------------------------------------------------------
# THEME & GLOBAL CSS
# ---------------------------------------------------------------------------

def inject_global_css():
    """Inject all global styles into the Streamlit app."""
    st.markdown("""
    <style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500;600;700&family=Bebas+Neue&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ── Root Variables ── */
    :root {
        --bg-primary:     #08080d;
        --bg-secondary:   #0e0e16;
        --bg-card:        #13131e;
        --bg-input:       #1a1a28;
        --bg-glass:       rgba(19, 19, 30, 0.7);
        --accent-gold:    #f0a500;
        --accent-amber:   #ff8c00;
        --accent-warm:    #e8952a;
        --accent-dim:     #7a5c00;
        --accent-glow:    #f0a50030;
        --text-primary:   #eaeaf4;
        --text-secondary: #9898b8;
        --text-muted:     #55557a;
        --success:        #00d4aa;
        --success-dim:    #00d4aa20;
        --danger:         #ff4757;
        --info:           #5b8def;
        --border:         #222238;
        --border-light:   #2e2e48;
        --border-accent:  #f0a50030;
        --radius-sm:      8px;
        --radius-md:      12px;
        --radius-lg:      16px;
        --radius-xl:      20px;
    }

    /* ── App Background ── */
    .stApp {
        background-color: var(--bg-primary);
        background-image:
            radial-gradient(ellipse 70% 40% at 50% -5%, #f0a50006 0%, transparent 60%),
            radial-gradient(ellipse 50% 30% at 80% 110%, #5b8def04 0%, transparent 60%),
            repeating-linear-gradient(0deg, transparent, transparent 60px, #ffffff02 60px, #ffffff02 61px),
            repeating-linear-gradient(90deg, transparent, transparent 60px, #ffffff01 60px, #ffffff01 61px);
        font-family: 'DM Sans', -apple-system, sans-serif;
        color: var(--text-primary);
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-dim);
    }

    /* ── Chat Input ── */
    .stChatInput,
    .stChatInput *,
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] *,
    [data-testid="stChatInputContainer"],
    [data-testid="stChatInputContainer"] * {
        background: #13131e !important;
        background-color: #13131e !important;
        border-color: #222238 !important;
        color: #eaeaf4 !important;
    }
    .stChatInput {
        border: 1px solid #222238 !important;
        border-radius: var(--radius-md) !important;
        transition: border-color 0.3s ease !important;
    }
    .stChatInput:focus-within {
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 2px var(--accent-glow) !important;
    }
    .stChatInput textarea {
        color: #eaeaf4 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 15px !important;
        background: transparent !important;
        caret-color: var(--accent-gold) !important;
        -webkit-text-fill-color: #eaeaf4 !important;
    }
    .stChatInput textarea::placeholder {
        color: #55557a !important;
        -webkit-text-fill-color: #55557a !important;
    }
    /* Force dark bottom bar */
    [data-testid="stBottom"],
    [data-testid="stBottom"] *,
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottomBlockContainer"] * {
        background: #08080d !important;
        background-color: #08080d !important;
    }
    /* Re-apply input box bg on top of bottom bar */
    [data-testid="stBottom"] .stChatInput,
    [data-testid="stBottom"] .stChatInput *,
    [data-testid="stBottom"] [data-testid="stChatInput"],
    [data-testid="stBottom"] [data-testid="stChatInput"] * {
        background: #13131e !important;
        background-color: #13131e !important;
    }
    /* Send button */
    .stChatInput button,
    [data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #f0a500, #ff8c00) !important;
        color: #08080d !important;
        border: none !important;
        border-radius: 8px !important;
    }

    /* ── Chat Messages ── */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 13px !important;
        border-radius: var(--radius-xl) !important;
        padding: 8px 16px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        white-space: nowrap !important;
        backdrop-filter: blur(8px) !important;
    }
    .stButton > button:hover {
        border-color: var(--accent-gold) !important;
        color: var(--accent-gold) !important;
        background: var(--accent-glow) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px var(--accent-glow) !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        color: var(--text-secondary) !important;
        font-size: 13px !important;
    }

    /* ── Dataframe / Tables ── */
    .stDataFrame {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ── Metric Cards ── */
    [data-testid="metric-container"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        padding: 14px !important;
        transition: border-color 0.2s ease !important;
    }
    [data-testid="metric-container"]:hover {
        border-color: var(--border-light) !important;
    }
    [data-testid="metric-container"] label {
        color: var(--text-muted) !important;
        font-size: 11px !important;
        font-family: 'Space Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: var(--accent-gold) !important;
        font-family: 'Space Mono', monospace !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        color: var(--text-secondary) !important;
        font-size: 13px !important;
        font-family: 'DM Sans', sans-serif !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        transition: all 0.2s ease !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: var(--border-light) !important;
        color: var(--text-primary) !important;
    }
    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-sm) var(--radius-sm) !important;
    }

    /* ── Code blocks inside expanders ── */
    .stCodeBlock {
        border-radius: var(--radius-sm) !important;
    }
    pre {
        background: #0c0c14 !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; }

    /* ── Select box ── */
    .stSelectbox select {
        background: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border) !important;
    }

    /* ── Animations ── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 1; box-shadow: 0 0 12px #f0a50020; }
        50% { opacity: 0.7; box-shadow: 0 0 24px #f0a50050; }
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    @keyframes spin-slow {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-4px); }
    }
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes typing-dots {
        0%   { content: '.'; }
        33%  { content: '..'; }
        66%  { content: '...'; }
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

def render_header():
    """Render the top header bar with animated gradient and status."""
    st.markdown("""<div style="background:linear-gradient(135deg,#0e0e16 0%,#13131e 50%,#0e0e16 100%);border-bottom:1px solid #222238;padding:16px 40px;display:flex;align-items:center;justify-content:space-between;position:relative;overflow:hidden;">
<div style="position:absolute;bottom:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent 0%,#f0a500 20%,#ff8c00 50%,#f0a500 80%,transparent 100%);background-size:200% 100%;animation:gradient-shift 4s ease-in-out infinite;"></div>
<div style="display:flex;align-items:center;gap:14px;">
<div style="width:40px;height:40px;background:linear-gradient(135deg,#f0a500,#ff8c00);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 0 24px #f0a50030,0 4px 12px #00000040;animation:float 3s ease-in-out infinite;">⚡</div>
<div>
<div style="font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:4px;color:#eaeaf4;line-height:1;text-shadow:0 0 20px #f0a50015;">BRAIN-DS</div>
<div style="font-family:'Space Mono',monospace;font-size:10px;color:#f0a500;letter-spacing:2px;margin-top:3px;opacity:0.85;">LEADERSHIP ANALYTICS &middot; TECHFEST IIT BOMBAY</div>
</div>
</div>
<div style="display:flex;align-items:center;gap:16px;font-family:'Space Mono',monospace;font-size:11px;">
<div style="display:flex;align-items:center;gap:6px;background:#00d4aa10;border:1px solid #00d4aa25;border-radius:20px;padding:4px 12px;">
<div style="width:6px;height:6px;background:#00d4aa;border-radius:50%;animation:pulse-dot 2s ease-in-out infinite;box-shadow:0 0 6px #00d4aa60;"></div>
<span style="color:#00d4aa;font-size:10px;letter-spacing:1px;">LIVE</span>
</div>
<div style="color:#55557a;text-align:right;">
<div style="color:#9898b8;">250K TRANSACTIONS</div>
<div style="font-size:9px;">JAN&ndash;DEC 2024</div>
</div>
</div>
</div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# WELCOME SCREEN
# ---------------------------------------------------------------------------

def render_welcome():
    """Render the welcome screen with animated hero and query cards."""
    st.markdown("""<div style="max-width:780px;margin:50px auto 0;padding:0 24px;text-align:center;animation:fadeInUp 0.6s ease-out;">
<div style="width:80px;height:80px;margin:0 auto 28px;background:linear-gradient(135deg,#f0a500,#ff8c00);border-radius:20px;display:flex;align-items:center;justify-content:center;font-size:36px;box-shadow:0 0 60px #f0a50025,0 8px 32px #00000040;animation:float 3s ease-in-out infinite;">⚡</div>
<div style="font-family:'Bebas Neue',sans-serif;font-size:56px;letter-spacing:5px;color:#eaeaf4;line-height:1;margin-bottom:16px;">ASK YOUR DATA</div>
<div style="font-family:'DM Sans',sans-serif;font-size:17px;color:#9898b8;font-weight:300;margin-bottom:12px;line-height:1.7;">
Conversational analytics for <b style="color:#f0a500;">250,000</b> UPI transactions.<br>
Ask questions in plain English. Get executive-grade insights.
</div>
<div style="display:inline-flex;align-items:center;gap:6px;background:#13131e;border:1px solid #222238;border-radius:20px;padding:5px 14px;margin-bottom:48px;font-family:'Space Mono',monospace;font-size:10px;color:#55557a;letter-spacing:1px;">
<span style="color:#5b8def;">&bull;</span> POWERED BY GEMINI &middot; CODE INTERPRETER
</div>
</div>""", unsafe_allow_html=True)

    # Section label
    st.markdown("""<div style="max-width:780px;margin:0 auto;padding:0 24px;">
<div style="font-family:'Space Mono',monospace;font-size:10px;color:#55557a;letter-spacing:2px;margin-bottom:14px;display:flex;align-items:center;gap:10px;">
<span>TRY ASKING</span>
<div style="flex:1;height:1px;background:linear-gradient(90deg,#222238,transparent);"></div>
</div>
</div>""", unsafe_allow_html=True)

    sample_questions = [
        ("📊", "Which transaction type has the highest failure rate?"),
        ("🏦", "Compare failure rates for HDFC vs SBI on weekends"),
        ("🕐", "What are the peak transaction hours?"),
        ("👥", "Which age group uses P2P most on weekends?"),
        ("⚠️", "What % of high-value transactions are flagged?"),
        ("📡", "Is there a relationship between network type and failures?"),
    ]

    cols = st.columns(2)
    for i, (icon, q) in enumerate(sample_questions):
        with cols[i % 2]:
            if st.button(f"{icon}  {q}", key=f"sample_{i}", use_container_width=True):
                st.session_state.prefilled_query = q
                st.rerun()


# ---------------------------------------------------------------------------
# USER MESSAGE BUBBLE
# ---------------------------------------------------------------------------

def render_user_message(message: str):
    """Render a user message bubble with subtle animation."""
    msg_hash = hashlib.md5(message.encode()).hexdigest()[:8]
    st.markdown(f"""
    <div style="
        display: flex;
        justify-content: flex-end;
        margin: 24px 0 8px;
        padding: 0 40px;
        animation: fadeIn 0.3s ease-out;
    ">
        <div style="
            background: linear-gradient(135deg, #1a1a2e, #22223a);
            border: 1px solid #2e2e48;
            border-radius: 16px 16px 4px 16px;
            padding: 14px 20px;
            max-width: 70%;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            color: #eaeaf4;
            line-height: 1.6;
            box-shadow: 0 2px 12px #00000020;
        ">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ASSISTANT RESPONSE
# ---------------------------------------------------------------------------

def render_assistant_response(response: str, result: dict = None):
    """
    Render the assistant's insight response with glassmorphism card.
    """
    # Convert newlines for HTML rendering
    formatted = response.replace("\n\n", "</p><p style='margin-top:12px'>").replace("\n", "<br>")

    st.markdown(f"""
    <div style="
        display: flex;
        justify-content: flex-start;
        margin: 8px 0;
        padding: 0 40px;
        gap: 12px;
        align-items: flex-start;
        animation: fadeInUp 0.4s ease-out;
    ">
        <div style="
            width: 34px; height: 34px; flex-shrink: 0;
            background: linear-gradient(135deg, #f0a500, #ff8c00);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px;
            box-shadow: 0 0 16px #f0a50020, 0 2px 8px #00000030;
            margin-top: 4px;
        ">⚡</div>
        <div style="
            background: linear-gradient(135deg, #11111c, #15152200);
            backdrop-filter: blur(12px);
            border: 1px solid #222238;
            border-left: 3px solid #f0a500;
            border-radius: 4px 16px 16px 16px;
            padding: 18px 22px;
            max-width: 80%;
            font-family: 'DM Sans', sans-serif;
            font-size: 15px;
            color: #d8d8ec;
            line-height: 1.75;
            box-shadow: 0 4px 24px #00000015;
        "><p style='margin:0'>{formatted}</p></div>
    </div>
    """, unsafe_allow_html=True)

    # Data table (if available)
    if result and isinstance(result, dict) and result.get("data") is not None:
        data = result["data"]
        if isinstance(data, pd.DataFrame) and not data.empty:
            with st.expander("📊 View Data Table", expanded=False):
                st.dataframe(
                    data,
                    use_container_width=True,
                    hide_index=True,
                )


# ---------------------------------------------------------------------------
# METRICS STRIP  (compatible with new result format)
# ---------------------------------------------------------------------------

def render_metrics_strip(result: dict):
    """
    Render a horizontal strip of key metric cards from the result summary.
    Only shown when there are clear numerical highlights.
    """
    summary = result.get("summary", {})
    if not summary or not isinstance(summary, dict):
        return

    metrics = []

    if "highest" in summary and isinstance(summary["highest"], dict):
        h = summary["highest"]
        val = h.get("value", h.get("failure_rate", ""))
        if val is not None:
            unit = "%" if isinstance(val, float) and val < 100 else ""
            metrics.append((str(h.get("segment", "Highest"))[:18], f"{val}{unit}", "▲ Max"))

    if "lowest" in summary and isinstance(summary["lowest"], dict):
        l = summary["lowest"]
        val = l.get("value", l.get("failure_rate", ""))
        if val is not None:
            unit = "%" if isinstance(val, float) and val < 100 else ""
            metrics.append((str(l.get("segment", "Lowest"))[:18], f"{val}{unit}", "▼ Min"))

    if "spread" in summary and isinstance(summary.get("spread"), (int, float)):
        spread = summary["spread"]
        if spread < 1000:
            metrics.append(("Spread", f"{spread}pp", "Range"))

    if "baseline_failure_rate" in summary:
        metrics.append(("Baseline", f"{summary['baseline_failure_rate']}%", "Overall Avg"))

    if "metric_value" in summary:
        unit = summary.get("unit", "")
        val = summary["metric_value"]
        label = summary.get("metric_label", "Value")
        if isinstance(val, float):
            val = f"{val:,.2f}"
        elif isinstance(val, int):
            val = f"{val:,}"
        metrics.append((label[:20], f"{val} {unit}".strip(), ""))

    if not metrics:
        return

    st.markdown("<div style='padding: 0 40px; margin: 4px 0;'>", unsafe_allow_html=True)
    cols = st.columns(min(len(metrics), 4))
    for i, (label, value, delta) in enumerate(metrics[:4]):
        with cols[i]:
            st.metric(label=label, value=value, delta=delta if delta else None)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# FOLLOW-UP SUGGESTIONS
# ---------------------------------------------------------------------------

def render_followup_suggestions(suggestions: list[str]):
    """Render clickable follow-up suggestion chips with hover effects."""
    if not suggestions:
        return

    st.markdown("""
    <div style="padding: 8px 40px 0; margin-top: 6px;">
        <div style="
            font-family: 'Space Mono', monospace;
            font-size: 10px;
            color: #55557a;
            letter-spacing: 2px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        ">
            <span>EXPLORE FURTHER</span>
            <div style="flex:1; height:1px; background: linear-gradient(90deg, #222238, transparent);"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(f"→ {suggestion}", key=f"followup_{suggestion[:20]}_{i}", use_container_width=True):
                st.session_state.prefilled_query = suggestion
                st.rerun()


# ---------------------------------------------------------------------------
# THINKING INDICATOR
# ---------------------------------------------------------------------------

def render_thinking():
    """Show a premium animated thinking indicator while processing."""
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 20px 40px;
        animation: fadeIn 0.3s ease-out;
    ">
        <div style="
            width: 34px; height: 34px;
            background: linear-gradient(135deg, #f0a500, #ff8c00);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px;
            animation: pulse-glow 1.8s ease-in-out infinite;
        ">⚡</div>
        <div style="display: flex; flex-direction: column; gap: 4px;">
            <div style="
                font-family: 'Space Mono', monospace;
                font-size: 12px;
                color: #f0a500;
                letter-spacing: 1px;
            ">ANALYSING DATA</div>
            <div style="display: flex; gap: 4px;">
                <div style="
                    width: 40px; height: 3px;
                    background: linear-gradient(90deg, #f0a500, #ff8c00, #f0a500);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s ease-in-out infinite;
                    border-radius: 2px;
                "></div>
                <div style="
                    width: 24px; height: 3px;
                    background: linear-gradient(90deg, #f0a500, #ff8c00, #f0a500);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s ease-in-out infinite 0.3s;
                    border-radius: 2px;
                    opacity: 0.6;
                "></div>
                <div style="
                    width: 16px; height: 3px;
                    background: linear-gradient(90deg, #f0a500, #ff8c00, #f0a500);
                    background-size: 200% 100%;
                    animation: shimmer 1.5s ease-in-out infinite 0.6s;
                    border-radius: 2px;
                    opacity: 0.3;
                "></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

def render_sidebar(cm):
    """Render the sidebar with session info, architecture badge, and controls."""
    with st.sidebar:
        # Brand section
        st.markdown("""
        <div style="
            font-family: 'Bebas Neue', sans-serif;
            font-size: 22px;
            letter-spacing: 4px;
            color: #eaeaf4;
            padding: 8px 0 6px;
        ">SESSION</div>
        <div style="
            width: 36px; height: 2px;
            background: linear-gradient(90deg, #f0a500, #ff8c00, transparent);
            margin-bottom: 18px;
            border-radius: 1px;
        "></div>
        """, unsafe_allow_html=True)

        # Turn counter — big and bold
        turns = cm.get_turn_count()
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #13131e, #18182a);
            border: 1px solid #222238;
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 14px;
            position: relative;
            overflow: hidden;
        ">
            <div style="
                position: absolute;
                top: 0; right: 0;
                width: 60px; height: 60px;
                background: radial-gradient(circle, #f0a50008, transparent 70%);
            "></div>
            <div style="font-family:'Space Mono',monospace; font-size:10px; color:#55557a; letter-spacing:2px;">QUERIES</div>
            <div style="font-family:'Space Mono',monospace; font-size:32px; color:#f0a500; margin-top:4px; text-shadow: 0 0 20px #f0a50020;">{turns:02d}</div>
        </div>
        """, unsafe_allow_html=True)

        # Architecture badge
        st.markdown("""
        <div style="
            background: #5b8def10;
            border: 1px solid #5b8def20;
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 14px;
        ">
            <div style="font-family:'Space Mono',monospace; font-size:9px; color:#5b8def; letter-spacing:1.5px; margin-bottom:6px;">ARCHITECTURE</div>
            <div style="font-family:'DM Sans',sans-serif; font-size:12px; color:#9898b8; line-height:1.6;">
                Code Interpreter Sandbox<br>
                <span style="color:#55557a; font-size:11px;">Generate → Execute → Validate → Narrate</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Active context
        context = cm.get_context()
        active_filters = {k: v for k, v in context.get("active_filters", {}).items() if v is not None}

        if active_filters:
            st.markdown("""
            <div style="font-family:'Space Mono',monospace; font-size:10px; color:#55557a; letter-spacing:2px; margin-bottom:8px;">ACTIVE CONTEXT</div>
            """, unsafe_allow_html=True)
            for k, v in active_filters.items():
                st.markdown(f"""
                <div style="
                    background: #f0a50008;
                    border: 1px solid #f0a50020;
                    border-left: 2px solid #f0a500;
                    border-radius: 6px;
                    padding: 7px 12px;
                    margin-bottom: 5px;
                    font-family: 'Space Mono', monospace;
                    font-size: 11px;
                    color: #f0a500;
                ">{k}: {v}</div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Reset button
        if st.button("↺  New Session", use_container_width=True):
            cm.reset()
            st.session_state.messages = []
            st.session_state.prefilled_query = None
            st.rerun()

        st.markdown("---")

        # Dataset info card
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #13131e, #18182a);
            border: 1px solid #222238;
            border-radius: 10px;
            padding: 14px 16px;
        ">
            <div style="font-family:'Space Mono',monospace; font-size:9px; color:#55557a; letter-spacing:2px; margin-bottom:10px;">DATASET OVERVIEW</div>
            <div style="font-family:'Space Mono',monospace; font-size:11px; line-height:2.2;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">Transactions</span>
                    <span style="color:#9898b8;">250,000</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">Period</span>
                    <span style="color:#9898b8;">Jan–Dec 2024</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">Coverage</span>
                    <span style="color:#9898b8;">10 states · 8 banks</span>
                </div>
                <div style="height:1px; background:#222238; margin:6px 0;"></div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">Failure Rate</span>
                    <span style="color:#f0a500;">4.95%</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">P90 Amount</span>
                    <span style="color:#f0a500;">₹3,236+</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#55557a;">Flag Rate</span>
                    <span style="color:#f0a500;">0.19%</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Footer
        st.markdown("""
        <div style="
            margin-top: 24px;
            padding-top: 12px;
            border-top: 1px solid #222238;
            text-align: center;
        ">
            <div style="font-family:'Space Mono',monospace; font-size:9px; color:#33334a; letter-spacing:1px;">
                BRAIN-DS v3.0 · CODE INTERPRETER
            </div>
        </div>
        """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# ERROR MESSAGE
# ---------------------------------------------------------------------------

def render_error(message: str):
    """Render an error message in the chat with warning styling."""
    st.markdown(f"""
    <div style="
        padding: 0 40px;
        margin: 8px 0;
        animation: fadeIn 0.3s ease-out;
    ">
        <div style="
            background: linear-gradient(135deg, #ff475708, #ff475712);
            border: 1px solid #ff475730;
            border-left: 3px solid #ff4757;
            border-radius: 8px;
            padding: 14px 18px;
            font-family: 'DM Sans', sans-serif;
            font-size: 14px;
            color: #ff7a85;
            display: flex;
            align-items: center;
            gap: 10px;
        "><span style="font-size:16px;">⚠</span> {message}</div>
    </div>
    """, unsafe_allow_html=True)