# InsightX — System Architecture

## 1. Overview

InsightX is a conversational analytics system that allows business leaders to query 250,000 UPI transactions using natural language and receive accurate, explainable insights. The system is built around a strict separation between language understanding, deterministic computation, and narrative generation.

**Core architectural principle:** The LLM never computes numbers. All statistics are produced by pandas operating directly on the dataset. The LLM's role is limited to two tasks — parsing the user's intent into a structured format, and converting pre-computed numbers into readable narrative.

---

## 2. System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI LAYER                      │
│   app/main.py               app/ui_components.py            │
│   • Chat interface          • Dark terminal theme           │
│   • Session state           • Message bubbles               │
│   • Sample query chips      • Metrics strip                 │
│   • Follow-up buttons       • Data table expander           │
└──────────────────────────┬──────────────────────────────────┘
                           │ user query (str)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  CONVERSATION MANAGER                       │
│   src/conversation_manager.py                               │
│   • Turn history storage                                    │
│   • Active filter persistence across turns                  │
│   • Follow-up detection (phrase matching)                   │
│   • Context dict for query parser                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ (query, context)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    QUERY PARSER                  [LLM #1]   │
│   src/query_parser.py                                       │
│   • Gemini API call → structured JSON intent                │
│   • Intent classification (6 types)                         │
│   • Entity extraction (schema-bound)                        │
│   • Metric inference                                        │
│   • Entity normalisation against VALID_VALUES               │
│   • Fallback intent on parse failure                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ parsed_intent (dict)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  ANALYTICS ENGINE              [PANDAS ONLY]│
│   src/analytics_engine.py                                   │
│   • run_query() dispatch to 6 compute functions             │
│   • _compute_descriptive()                                  │
│   • _compute_comparative()                                  │
│   • _compute_temporal()                                     │
│   • _compute_segmentation()                                 │
│   • _compute_correlation()                                  │
│   • _compute_risk()                                         │
│   • Shared utilities: _apply_filters(), _failure_rate(),    │
│     _grouped_failure_rate(), _flag_rate(), etc.             │
│   • Sample size warnings (< 200 threshold)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │ analytics_result (dict)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 INSIGHT GENERATOR               [LLM #2]    │
│   src/insight_generator.py                                  │
│   • Gemini API call with pre-computed numbers only          │
│   • D-S-I-R narrative structure enforcement                 │
│   • Tone calibration (marginal / notable / significant)     │
│   • Assumption & warning appending                          │
│   • Fallback narrative if API unavailable                   │
│   • Follow-up suggestion generation                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ (response, followups)
                           ▼
                    Back to UI Layer
```

---

## 3. Module Descriptions

### `src/data_loader.py`
The foundation layer. Loads the CSV once into memory and caches it for the session lifetime. Handles all column renaming (raw CSV has spaces in headers), timestamp parsing (format: `DD-MM-YYYY HH.MM`), and derives the `is_failed` convenience column. Defines all EDA-derived constants (`HIGH_VALUE_THRESHOLD`, `OVERALL_FAILURE_RATE`, etc.) and valid categorical values used for entity validation downstream.

Key functions: `get_dataframe()`, `get_subset()`, `sample_size_warning()`

### `src/query_parser.py`
The language understanding layer. Sends the user's query to Gemini with a carefully engineered system prompt that includes the full schema, valid values, and system constants. Instructs the model to return only a structured JSON object — never an answer. Post-processes the response to correct capitalisation issues and remove unrecognised entities. Falls back to `intent: "unknown"` on complete parse failure.

Key functions: `parse_query()`, `explain_parse()`

### `src/analytics_engine.py`
The source of truth. All computation happens here via pandas. A single entry point `run_query()` dispatches to one of six compute functions based on intent type. Every function applies filters via `_apply_filters()`, runs the appropriate aggregation, checks for low sample sizes, and returns a standardised result dict with a `summary`, optional `data` DataFrame, `warning`, and `assumption`.

Key functions: `run_query()`, `_compute_*()`, `_apply_filters()`, `_grouped_failure_rate()`

### `src/insight_generator.py`
The narrative layer. Receives the analytics result and builds a prompt that passes only the pre-computed numbers to Gemini, instructing it to produce a D-S-I-R structured response. Tone guidelines in the system prompt ensure the model uses calibrated language (e.g. "marginally" for <0.5pp differences). Has a pure-Python fallback narrative if the API is unavailable.

Key functions: `generate_insight()`, `suggest_followups()`

### `src/conversation_manager.py`
The memory layer. Maintains conversation state as a Python dataclass (`Turn`) list. Merges active filters across follow-up turns so users don't need to repeat context. Detects follow-up queries via phrase matching. Provides a context dict to `query_parser` and a history list to the Streamlit UI.

Key functions: `ConversationManager.add_turn()`, `.get_context()`, `.get_history()`

### `app/main.py`
The application entry point. Initialises Streamlit session state, wires the full pipeline together, and manages the render loop. Handles prefilled queries from sample chips and follow-up buttons via `st.session_state.prefilled_query`.

### `app/ui_components.py`
All visual components. Dark terminal aesthetic with amber/gold accents using Bebas Neue (display), Space Mono (metrics), and DM Sans (body). Components include: header bar, welcome screen with sample query chips, user/assistant message bubbles, metrics strip, collapsible data table, follow-up suggestion chips, sidebar with session state display.

---

## 4. Data Flow — Detailed Example

**Query:** *"Compare failure rates for HDFC vs SBI on weekends"*

```
1. query_parser.py
   Input:  "Compare failure rates for HDFC vs SBI on weekends"
   Output: {
     "intent": "comparative",
     "metric": "failure_rate",
     "filters": {"sender_bank": ["HDFC", "SBI"], "is_weekend": 1},
     "group_by": "sender_bank",
     "comparison_values": ["HDFC", "SBI"]
   }

2. analytics_engine.py → _compute_comparative()
   - _apply_filters(): filters df to is_weekend=1, skips sender_bank list
   - df filtered to 71,337 weekend transactions
   - Further filtered to HDFC and SBI rows only
   - _grouped_failure_rate(df, "sender_bank") computes:
       SBI:  919 failed / 17,829 total = 5.15%
       HDFC: 542 failed / 10,823 total = 5.01%
   Output: result dict with summary + data DataFrame

3. insight_generator.py
   - Prompt contains ONLY the computed numbers above
   - Gemini produces D-S-I-R narrative using "marginally" (spread = 0.14pp)
   - Assumption appended: "sender_bank assumed for bank comparison"

4. conversation_manager.py
   - Turn recorded with full state
   - active_filters updated: {sender_bank: [HDFC, SBI], is_weekend: 1}
   - If next query is "now look at all banks", filters merge correctly
```

---

## 5. Key Design Decisions

### Why not Text-to-SQL?
Text-to-SQL would require maintaining a database layer and validating generated SQL for safety. Pandas operations on an in-memory 250k-row DataFrame are equivalent in speed, simpler to debug, and allow direct integration with Python-native validation logic.

### Why two separate LLM calls?
Separating parsing (LLM #1) from narration (LLM #2) enforces the core principle that computation is never LLM-dependent. If both calls were combined, there would be no clean boundary preventing the model from mixing recalled statistics with computed ones.

### Why simple phrase-matching for follow-up detection?
A classifier or embedding-based approach would introduce a third model call and new failure modes. The phrase list covers all realistic follow-up patterns for this domain with no latency overhead.

### Why module-level DataFrame caching?
Streamlit reruns the entire script on every user interaction. Without caching, the 250k-row CSV would be re-read from disk on every query. The module-level `_df_cache` in `data_loader.py` ensures it is read exactly once per session.

### Why hardcoded constants rather than computing baselines live?
The EDA-derived constants (`OVERALL_FAILURE_RATE = 4.95`, `HIGH_VALUE_THRESHOLD = 3236`, etc.) serve as ground truth anchors. Computing them fresh on each response would be marginally slower and, more importantly, would obscure the validation relationship between the analytics engine outputs and the EDA baselines.

---

## 6. Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12 |
| Data computation | Pandas | 2.x |
| LLM API | Google Gemini | gemini-2.5-flash |
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
│   ├── raw/                     # Original CSV (gitignored)
│   └── processed/               # Derived datasets if needed
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
│   ├── __init__.py              # Clean top-level imports
│   ├── data_loader.py           # Data loading, caching, constants
│   ├── query_parser.py          # NL → structured intent (LLM)
│   ├── analytics_engine.py      # Deterministic computation (pandas)
│   ├── insight_generator.py     # Results → narrative (LLM)
│   └── conversation_manager.py  # Conversation state management
│
├── tests/
│   └── sample_queries.json      # 15 sample queries + responses
│
├── .env                         # API keys (gitignored)
├── .env.example                 # Key template for teammates
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 8. Limitations

- **Synthetic data uniformity:** Failure rates differ by less than 0.5pp across most dimensions, limiting the drama of insights. The system reports this honestly rather than exaggerating differences.
- **No forecasting:** All insights are descriptive. No time-series modelling or predictive capability.
- **Fraud flag sparsity:** Only 480 flagged transactions (0.19%) means sub-segment fraud analysis has very small sample sizes. The system warns on segments below 200 transactions.
- **10 states only:** The dataset covers 10 Indian states. Geographic insights are limited to this scope.
- **No causal inference:** Near-zero correlations across all numeric fields mean no causal claims are made or warranted.