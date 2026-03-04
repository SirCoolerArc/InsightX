# BRAIN-DS: Technical Architecture

## 1. System Overview
BRAIN-DS (Deterministic Systems for Digital Payments) is a high-depth AI analytics agent designed to provide business leaders with verifiable, executive-grade insights from large-scale digital payment datasets (e.g., UPI transactions). 

Unlike standard LLM chatbots, BRAIN-DS utilizes a **Code-Interpreter Paradigm** combined with a **7-LLM Parallel Orchestration Engine** to ensure 100% computational grounding and sub-second perceived latency.

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    NEXT.JS UI LAYER (Premium)               │
│   frontend/src/                frontend/components/         │
│   • Tailwind CSS styling       • ChartRenderer.tsx (Recharts)│
│   • Framer Motion              • Masonry KPI Grid           │
│   • Investigation Trace        • Dynamic Followups          │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /api/query
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND LAYER                    │
│   api/main.py                                               │
│   • CORS Middleware                                         │
│   • Session-based Thread Management                         │
│   • Streamed SSE Responses                                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ user_query (str)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              PARALLEL AGENTIC ORCHESTRATOR                  │
│   src/agent.py                                              │
│   • Multi-stage Parallel Execution (7+ Gemini API calls)    │
│   • Stage 1: Parallel Generation (Main + Proactive Deep Dive)│
│   • Stage 2: Narrative Synthesis                            │
│   • Stage 3: Parallel Validation (LLM Judge + Followups)    │
└────────┬───────────────────────────────┬────────────────────┘
         │                               │
         ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│ MAIN ANALYST (LLM #1) │       │ DEEP DIVE (LLM #3)    │
│ Code Generation       │       │ Proactive Research    │
└────────┬──────────────┘       └────────┬──────────────┘
         │                               │
         ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│ VALIDATOR (LLM #2)    │       │ VALIDATOR (LLM #4)    │
│ Semantic Check        │       │ Correlation Check     │
└────────┬──────────────┘       └────────┬──────────────┘
         │                               │
         └───────────────┬───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│             D-S-I-R NARRATIVE ARCHITECT (LLM #5)            │
│   src/code_planner.py -> generate_narrative()               │
│   • Weaves main data and research into executive insight    │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌───────────────┴───────────────┐
          ▼                               ▼
 ┌────────────────────────┐       ┌────────────────────────┐
 │   LLM-AS-JUDGE (LLM #6)│       │  FOLLOW-UP GEN (LLM #7)│
 │   5-Dimensional Audit  │       │  Contextual Prediction │
 └────────────────────────┘       └────────────────────────┘
                          │                 │
                          └────────┬────────┘
                                   ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                FINAL EXECUTIVE INSIGHT (UI)                 │
 │   • Calibrated D-S-I-R Narrative                            │
 │   • Insight Cards (Masonry) & Interaction Charts            │
 └─────────────────────────────────────────────────────────────┘
```

---

## 3. The 7-LLM Parallel Orchestration Engine
The core of BRAIN-DS is its multi-agent pipeline, which collapses a sequential reasoning process into three parallel stages to optimize both depth and speed.

### Stage 1: Parallel Discovery (Concurrency: 2)
*   **LLM #1: Primary Code Planner**: Generates deterministic Python/Pandas logic using dynamically injected schema metadata and P90 EDA benchmarks.
*   **LLM #2: Logic Validator**: Independently audits the Planner’s output to ensure semantic alignment with the user's intent before execution.
*   **LLM #3: Deep-Dive Researcher**: A context-aware agent that scans for anomalies or categorical correlations (e.g., State-wise or Network-wise disparities) in parallel with the main query.
*   **LLM #4: Research Auditor**: Validates the technical integrity of the Deep-Dive findings.

### Stage 2: Narrative Synthesis
*   **LLM #5: Narrative Architect**: Synthesizes the raw data from all discovery workers into a structured D-S-I-R (Direct, Support, Interpret, Recommend) response.

### Stage 3: Quality Audit (Concurrency: 2)
*   **LLM #6: Structural Judge**: A 5-Dimensional Auditor that enforces strict rules for Grounding (no uncomputed numbers), Calibration (adjective thresholds for 0.5pp/2pp deltas), and Logic Integrity.
*   **LLM #7: Contextual Predictor**: Anticipates the next three strategic follow-up questions to minimize user friction.

---

## 4. Final Executive Insight (The Output Layer)
This is the final terminal stage where the unified intelligence is delivered to the business leader:
*   **Narrative**: Executive-grade D-S-I-R text that is scientifically calibrated.
*   **KPI Masonry**: dynamic metrics, key-value tables, and insight lists.
*   **Interaction Charts**: Recharts-based visualizations tailored to the data.

---

## 4. The Secure Code Execution Sandbox
To ensure reliability and security, all generated code is executed within a **Zero-Trust Python Sandbox (`sandbox.py`)**.

*   **Isolation**: Uses a strict `_SAFE_BUILTINS` whitelist (blocking `eval`, `exec`, `open`, `__import__`, `globals`, `locals`).
*   **Data Integrity**: Injects a `df.copy()` of the 250k row dataset into memory to prevent accidental or malicious data mutation.
*   **Self-Healing Loop**: If execution fails, the system captures the Python Traceback, identifies the bug, and patches itself up to 3 times (`MAX_RETRIES: 3`).
*   **Resource Guard**: Thread-based 30-second timeout to prevent infinite loops or explosive computations.

---

## 5. Grounding & Data Science Layer
*   **EDA Anchors**: The system uses 14 pre-computed constants (e.g., `HIGH_VALUE_THRESHOLD: 3236.00`, `OVERALL_FAILURE_RATE: 4.95%`) for statistical anchoring.
*   **Scientific Calibration**: Insights are strictly calibrated based on percentage point (pp) deltas:
    *   Delta < 0.5pp → "Marginal"
    *   Delta 0.5 - 2pp → "Notable"
    *   Delta > 2pp → "Significant"

---

## 6. Visual & Interface Layer
*   **Next.js & Recharts**: Real-time rendering of Line, Bar, and Pie charts driven by LLM-generated JSON configurations.
*   **SSE Streaming**: Utilizes Server-Sent Events (SSE) to provide real-time updates of the agent’s reasoning steps (Progress Badges and Investigation Trace).
*   **Responsive Masonry**: A 2-column masonry grid for KPI cards (Metric Groups, Key-Value tables, and Insight Lists).

---

## 7. Data Flow — Detailed Example

**Query:** *"Compare failure rates for HDFC vs SBI on weekends"*

1.  **Orchestrator (`agent.py`)**: Receives query, loads Cached DataFrame, and injects Schema Context.
2.  **Code Planner (LLM #1)**: Generates Pandas code using `is_weekend` and `sender_bank` filters.
3.  **Sandbox (`sandbox.py`)**: Executes code in an isolated environment; returns a computed results dictionary.
4.  **Logic Validator (LLM #2)**: Verifies that the computed data semantically answers the weekend comparison.
5.  **Narrative Architect (LLM #5)**: Converts raw numbers into a D-S-I-R narrative (e.g., "HDFC failure rate is 5.01% vs SBI 5.15%").
6.  **Structural Judge (LLM #6)**: Cross-references the narrative against the computed result to ensure 100% grounding.
7.  **SSE Bridge**: Streams the final insight, cards, and Recharts config to the UI.

---

## 8. Key Design Decisions

*   **Code Interpreter Paradigm**: Eliminates the brittleness of intent-parsing by allowing the AI to write arbitrary, verifiable data-science logic.
*   **Module-Level Caching**: The 250k-row dataset is cached in `data_loader.py` memory, ensuring sub-second data access across API calls.
*   **Anti-Sycophancy Filter**: The Judge layer is instructed to challenge any leading questions or incorrect premises provided by the user.

---

## 9. Limitations & Guardrails
*   **Descriptive Focus**: The system is optimized for historical descriptive analytics; no predictive time-series modeling is implemented.
*   **Sample Size Guards**: Segments with `< 200` transactions trigger an automated "Low Confidence" warning.
*   **Deterministic Only**: If the LLM cannot generate valid code for a query, the system returns a graceful "Out of Domain" notification rather than hallucinating an answer.

---

## 10. Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Data computation | Pandas | 2.x |
| LLM — Code Generation & Narration | Gemini 2.5 Flash | gemini-2.5-flash |
| LLM — Judge | Gemini 2.5 Flash | gemini-2.5-flash |
| LLM — Judge Fallback | Gemini 2.5 Flash | gemini-2.5-flash |
| UI framework | Next.js (React) | 14.x |
| Backend API framework | FastAPI | Latest |
| API Server | Uvicorn | Latest |
| API client | google-genai | Latest |
| Environment | python-dotenv | Latest |

---

## 11. Project Structure

```
insightx/
│
├── api/
│   └── main.py                  # FastAPI backend entry point
│
├── frontend/                    # Next.js React Frontend App
│   ├── src/app/                 # Layouts and global CSS
│   ├── src/components/          # ChatInterface, MessageBubble
│   └── package.json             # NPM dependencies
│
├── data/
│   └── raw/                     # Original CSV (gitignored)
│
├── docs/
│   ├── approach.md              # Query understanding methodology
│   └── architecture.md          # This document
│
├── notebooks/
│   └── EDA.ipynb                # Exploratory data analysis
│
├── src/
│   ├── __init__.py
│   ├── agent.py                 # Orchestrator: parallelizes generate → execute → narrate
│   ├── code_planner.py          # LLM code generation & narrative (Gemini 2.5 Flash)
│   ├── sandbox.py               # Restricted code execution environment
│   ├── judge.py                 # LLM-as-Judge validation (Gemini 2.5 Flash)
│   ├── data_loader.py           # Data loading, caching, constants
│   └── conversation_manager.py  # Conversation state & follow-up handling
│
├── tests/
│   ├── sample_queries.json      # 15 sample queries + responses
│   ├── test_e2e.py              # End-to-end pipeline tests
│   └── test_sandbox.py          # Sandbox security & execution tests
│
├── .env                         # API keys
├── .gitignore
├── requirements.txt
└── README.md
```
