# BRAIN-DS — System Architecture

## 1. Overview

BRAIN-DS is a conversational analytics system that allows business leaders to query 250,000 UPI transactions using natural language and receive accurate, explainable insights. The system is built on a **Code Interpreter** paradigm — an LLM writes pandas code, which is executed in a secure sandbox, and the results are narrated back in executive-grade language.

**Core architectural principle:** The LLM generates code, never direct answers. All statistics are produced by pandas executing inside a sandboxed environment. An LLM-as-Judge validates every response before it reaches the user.

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI LAYER                      │
│   app/main.py               app/ui_components.py            │
│   • Chat interface          • Dark terminal theme           │
│   • Session state           • Glassmorphism cards           │
│   • Sample query chips      • Animated header & sidebar     │
│   • Follow-up buttons       • Data table expander           │
└──────────────────────────┬──────────────────────────────────┘
                           │ user query (str)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      AGENT                  [ORCHESTRATOR]  │
│   src/agent.py                                              │
│   • Entry point: run_agent()                                │
│   • Manages the generate → execute → validate loop          │
│   • Up to MAX_RETRIES iterations on execution errors        │
│   • Validates output alignment via code_planner             │
│   • Calls judge for final quality check                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ user_query + schema + context
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CODE PLANNER                   [LLM #1]    │
│   src/code_planner.py                                       │
│   • generate_analysis_code() — Gemini writes pandas code    │
│   • fix_code() — LLM corrects code that errored             │
│   • validate_and_refine() — checks output answers question  │
│   • generate_narrative() — D-S-I-R executive narrative      │
│   • generate_followups() — 2–3 follow-up suggestions        │
│   • get_schema_prompt() — builds full schema description     │
│   • build_conversation_context() — formats turn history     │
│   • Model: Gemini 2.5 Flash                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ generated Python code (str)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     SANDBOX                [RESTRICTED ENV] │
│   src/sandbox.py                                            │
│   • execute_code() — runs code against the DataFrame        │
│   • Restricted builtins (no open, exec, eval, import)       │
│   • Only pandas, numpy, math, datetime available            │
│   • 30-second timeout with thread-based enforcement         │
│   • Captures stdout + result + error                        │
│   • Handles DataFrame, Series, scalar, dict results         │
│   • format_result_for_display() — formats for LLM/UI       │
└──────────────────────────┬──────────────────────────────────┘
                           │ execution result (dict)
                           ▼
                  [If error → fix_code() → retry]
                  [If success → validate_and_refine()]
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│          NARRATIVE GENERATION                   [LLM #2]    │
│   src/code_planner.py → generate_narrative()                │
│   • Receives computed data + code + stdout                  │
│   • Produces D-S-I-R structured executive narrative         │
│   • Uses calibrated language for differences                │
│   • Model: Gemini 2.5 Flash                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ narrative response (str)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 JUDGE                        [LLM #3]       │
│   src/judge.py                                              │
│   • Evaluates: Relevance, Grounding, Calibration, Safety    │
│   • Scores 1–5 per dimension                                │
│   • Approves / corrects / appends caveat                    │
│   • Catches: hallucinated numbers, overclaimed significance,│
│     fraud language, irrelevant answers                      │
│   • Model: Gemini 3.1 Pro → falls back to 2.5 Pro          │
│   • Never blocks user if judge itself fails                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ validated response
                           ▼
                     Back to UI Layer
```

---

## 3. Module Descriptions

### `src/agent.py`
The orchestration layer and main entry point. Receives the user query, loads the DataFrame, builds schema and conversation context, then runs the generate → execute → validate loop. On execution errors, asks the code planner to fix the code (up to `MAX_RETRIES` attempts). On successful execution, validates that the output actually answers the question. Finally calls the narrator and judge before returning the complete result dict.

Key functions: `run_agent()`, `_error_result()`, `format_investigation_trace()`

### `src/code_planner.py`
The LLM interface layer. All Gemini API calls for code generation, error correction, output validation, narrative generation, and follow-up suggestion happen here. Injects a comprehensive schema description (column names, dtypes, valid values, sample rows) into every prompt to ground the LLM. Includes automatic retry logic for rate-limit (429) errors.

Key functions: `generate_analysis_code()`, `fix_code()`, `validate_and_refine()`, `generate_narrative()`, `generate_followups()`, `get_schema_prompt()`, `build_conversation_context()`

### `src/sandbox.py`
The security layer. Executes LLM-generated pandas code in a restricted environment. Only whitelisted builtins are available — no file I/O (`open`), no dynamic execution (`exec`, `eval`), no imports, no system access. Code must assign its answer to a `result` variable. Enforces a 30-second timeout using threads. Handles multiple result types (DataFrame, Series, scalar, dict) and converts numpy/pandas types to JSON-safe Python natives.

Key functions: `execute_code()`, `format_result_for_display()`, `_make_json_safe()`

### `src/judge.py`
The quality validation layer. Every response passes through the judge before reaching the user. Evaluates Relevance, Grounding, Calibration, and Safety on a 1–5 scale. Automatically corrects responses with critical issues or appends caveats for minor ones. Uses Gemini 3.1 Pro with automatic fallback to 2.5 Pro. Never blocks the user if the judge itself fails.

Key functions: `judge_response()`, `format_judge_badge()`, `get_judge_expander_content()`

### `src/data_loader.py`
The foundation layer. Loads the CSV once into memory and caches it for the session lifetime. Handles column renaming, timestamp parsing (`DD-MM-YYYY HH.MM`), and derives convenience columns like `is_failed`. Defines all EDA-derived constants (`HIGH_VALUE_THRESHOLD`, `OVERALL_FAILURE_RATE`, etc.) and valid categorical values used for entity validation.

Key functions: `get_dataframe()`, `get_subset()`, `sample_size_warning()`

### `src/conversation_manager.py`
The memory layer. Maintains conversation state as a `Turn` dataclass list. Tracks active filters, last metric, and code history across turns to enable follow-up queries. Provides context to the code planner so follow-up questions resolve correctly without the user repeating earlier constraints.

Key functions: `ConversationManager.add_turn()`, `.get_context()`, `.get_history()`, `.reset()`

### `src/query_parser.py`
Legacy intent parser. Sends the user's query to Gemini to extract structured JSON intent (intent type, entities, metrics, filters). Used by the analytics engine for structured computation. Retained in the codebase as a fallback path.

### `src/analytics_engine.py`
Legacy computation engine. Contains six deterministic compute functions dispatched by intent type (descriptive, comparative, temporal, segmentation, correlation, risk). All computation uses pandas. Retained in the codebase as a fallback path.

### `src/insight_generator.py`
Legacy narrative generator. Receives analytics results and produces D-S-I-R narratives via Gemini. Retained in the codebase as a fallback path.

### `app/main.py`
The application entry point. Initialises Streamlit session state, wires the pipeline through `run_agent()`, and manages the render loop. Handles prefilled queries from sample chips and follow-up buttons.

### `app/ui_components.py`
All visual components. Premium dark analytics dashboard with amber/gold accents using Bebas Neue (display), Space Mono (metrics), and DM Sans (body). Features animated gradient header, glassmorphism response cards, floating orb welcome screen, shimmer loading animation, and polished sidebar with session info, architecture badge, and dataset overview card.

---

## 4. Data Flow — Detailed Example

**Query:** *"Compare failure rates for HDFC vs SBI on weekends"*

```
1. agent.py → run_agent()
   - Loads DataFrame via data_loader.get_dataframe()
   - Builds schema prompt via code_planner.get_schema_prompt(df)
   - Builds conversation context from prior turns

2. code_planner.py → generate_analysis_code()
   - Sends query + schema + context to Gemini 2.5 Flash
   - Gemini generates pandas code:
     weekend_df = df[df['is_weekend'] == 1]
     banks = weekend_df[weekend_df['sender_bank'].isin(['HDFC', 'SBI'])]
     result = banks.groupby('sender_bank')['is_failed'].agg(['sum','count'])
     result['failure_rate'] = (result['sum'] / result['count'] * 100).round(2)

3. sandbox.py → execute_code()
   - Executes code in restricted environment with only pandas/numpy
   - Returns: {success: True, result: DataFrame, stdout: "", error: None}

4. code_planner.py → validate_and_refine()
   - Checks: does the output answer "Compare failure rates for HDFC vs SBI
     on weekends"?
   - If misaligned, generates corrected code and re-executes

5. code_planner.py → generate_narrative()
   - Receives computed DataFrame + code + stdout
   - Produces D-S-I-R narrative: "HDFC has a 5.01% failure rate on weekends
     (542 failed / 10,823 total), compared to SBI's 5.15% (919 / 17,829)..."

6. judge.py → judge_response()
   - Evaluates narrative against computed data
   - Checks calibration: 0.14pp spread → must use "marginal"
   - Approves or corrects

7. conversation_manager.py → add_turn()
   - Records query, code, result, and response
   - Updates active context for follow-up queries
```

---

## 5. Key Design Decisions

### Why Code Interpreter over Structured Intent Parsing?
The structured intent parser (query_parser → analytics_engine) required manually coding every possible query pattern into six intent types. The code interpreter approach lets the LLM write arbitrary pandas code, handling any question the user can think of — including novel multi-step analyses that don't fit neatly into predefined categories.

### Why a Sandbox?
LLM-generated code cannot be trusted to run unrestricted. The sandbox removes access to file I/O, network calls, imports, and system functions. Only data analysis builtins (pandas, numpy, math) are available, with a 30-second timeout to prevent infinite loops.

### Why a Validate-and-Refine Step?
LLMs sometimes generate code that runs without error but doesn't actually answer the question (e.g., computing total amount when asked for failure rate). The validation step catches these semantic mismatches and triggers a code correction before narrating.

### Why Separate Code Generation from Narrative?
Separating code generation (LLM #1) from narration (LLM #2) enforces the principle that all numbers come from deterministic pandas execution, not from the model's memory. The narrator only sees computed results.

### Why an LLM Judge?
Automated quality validation catches hallucinated numbers, overclaimed significance, and unsafe fraud language before they reach the user. The judge never blocks — if it fails, the original response passes through unchanged.

### Why Module-Level DataFrame Caching?
Streamlit reruns the entire script on every user interaction. Without caching, the 250k-row CSV would be re-read from disk on every query. The module-level cache in `data_loader.py` ensures it is read exactly once per session.

---

## 6. Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Data computation | Pandas | 2.x |
| LLM — Code Generation & Narration | Gemini 2.5 Flash | gemini-2.5-flash |
| LLM — Judge | Gemini 3.1 Pro | gemini-3.1-pro-preview |
| LLM — Judge Fallback | Gemini 2.5 Pro | gemini-2.5-pro |
| UI framework | Streamlit | Latest |
| API client | google-genai | Latest |
| Environment | python-dotenv | Latest |

---

## 7. Project Structure

```
insightx/
│
├── app/
│   ├── main.py                  # Streamlit entry point
│   └── ui_components.py         # All visual components & CSS
│
├── data/
│   └── raw/                     # Original CSV (gitignored)
│
├── docs/
│   ├── approach.md              # Query understanding methodology
│   └── architecture.md          # This document
│
├── notebooks/
│   ├── 01_eda.ipynb             # Exploratory data analysis
│   ├── 02_query_patterns.ipynb  # Parser testing
│   └── 03_insight_validation.ipynb # Output validation
│
├── src/
│   ├── __init__.py
│   ├── agent.py                 # Orchestrator: generate → execute → narrate
│   ├── code_planner.py          # LLM code generation & narrative (Gemini 2.5 Flash)
│   ├── sandbox.py               # Restricted code execution environment
│   ├── judge.py                 # LLM-as-Judge validation (Gemini 3.1 Pro)
│   ├── data_loader.py           # Data loading, caching, constants
│   ├── conversation_manager.py  # Conversation state & follow-up handling
│   ├── query_parser.py          # [Legacy] NL → intent (Gemini 2.5 Flash)
│   ├── analytics_engine.py      # [Legacy] Deterministic computation (pandas)
│   └── insight_generator.py     # [Legacy] Results → narrative (Gemini 2.5 Flash)
│
├── tests/
│   ├── sample_queries.json      # 15 sample queries + responses
│   ├── test_e2e.py              # End-to-end pipeline tests
│   ├── test_sandbox.py          # Sandbox security & execution tests
│   └── test_reproduce.py        # Reproducibility tests
│
├── .env                         # API keys (gitignored)
├── .env.example                 # Key template for teammates
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 8. Security Model

The sandbox enforces the following restrictions on LLM-generated code:

| Category | Allowed | Blocked |
|---|---|---|
| Builtins | `int`, `float`, `str`, `list`, `dict`, `len`, `range`, `sorted`, `min`, `max`, `sum`, `abs`, `round`, `enumerate`, `zip`, `map`, `filter`, `print` | `open`, `exec`, `eval`, `compile`, `__import__`, `globals`, `locals`, `exit`, `quit` |
| Libraries | `pandas` (as `pd`), `numpy` (as `np`), `math`, `datetime` | All other imports blocked |
| Execution | 30-second timeout | Infinite loops killed |
| File I/O | None | All file operations blocked |
| Network | None | All network access blocked |

---

## 9. Limitations

- **Synthetic data uniformity:** Failure rates differ by less than 0.5pp across most dimensions, limiting the drama of insights. The system reports this honestly.
- **No forecasting:** All insights are descriptive. No time-series modelling or predictive capability.
- **Fraud flag sparsity:** Only 480 flagged transactions (0.19%) means sub-segment fraud analysis has very small sample sizes.
- **10 states only:** The dataset covers 10 Indian states. Geographic insights are limited to this scope.
- **Code execution risk:** Despite sandbox restrictions, LLM-generated code carries inherent risk. The whitelist approach minimises this.
- **API rate limits:** Free-tier Gemini API has request quotas. The retry-with-backoff logic in `code_planner.py` mitigates transient 429 errors.