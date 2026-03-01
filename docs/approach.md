# BRAIN-DS — Query Understanding & Insight Generation Approach

## 1. Dataset Characteristics (EDA-Informed)

Before describing the approach, it is essential to understand what the data actually looks like, as this directly shapes design decisions.

**Scale & Coverage**
- 250,000 transactions across a full calendar year (2024-01-01 to 2024-12-30)
- 17 columns, zero duplicate transaction IDs, zero unexpected NULLs
- 10 Indian states, 8 banks, 4 transaction types, 4 network types, 3 device types

**Critical Observation — Uniformity of Failure Rates**
The most important finding from EDA is that failure rates are remarkably uniform across almost all dimensions:

| Dimension | Range of Failure Rates |
|---|---|
| Transaction Type | 4.88% – 5.09% |
| Sender Bank | 4.82% – 5.10% |
| Device Type | 4.93% – 5.15% |
| Network Type | 4.86% – 5.22% |
| Age Group | 4.84% – 5.13% |
| Merchant Category | 4.59% – 5.10% |
| Day of Week | 4.77% – 5.10% |

This is a synthetic dataset and this uniformity is a direct consequence of that. The system must report differences accurately and avoid exaggerating them.

**Amount Distribution**
- Heavily right-skewed: median ₹629, mean ₹1,312, max ₹42,099
- High-value threshold defined as P90 = ₹3,236 (used consistently throughout the system)
- Education transactions have by far the highest average (₹5,134), followed by Shopping (₹2,616)

**Fraud Flag Reality**
- Only 480 transactions flagged (0.19%) — extremely sparse
- Flagged transactions are actually *less* likely to fail (4.38%) than unflagged ones (4.95%)
- All differences are marginal — fraud flag analysis must always include sample size context

**Transaction Composition**
- P2P dominates at 45% of volume, P2M at 35%, Bill Payment at 15%, Recharge at 5%
- 26-35 age group is the largest sender segment (35% of volume)
- Android dominates device usage at 75% of all transactions
- Peak transaction hour is 19:00, with a sustained cluster from 17:00–20:00

---

## 2. Code Interpreter Approach

### 2.1 Why Code Interpreter?

Traditional NLP-to-analytics pipelines require:
1. Intent classification (mapping queries to predefined categories)
2. Entity extraction (pulling out specific column values)
3. Hardcoded computation functions (one per intent type)

This limits the system to a fixed set of question patterns. Any novel query that doesn't fit the predefined intents fails silently or returns irrelevant results.

BRAIN-DS uses a **Code Interpreter** approach instead:

```
User Query (natural language)
    ↓
LLM generates pandas code (arbitrary, unconstrained)
    ↓
Sandbox executes code safely against DataFrame
    ↓
LLM narrates the computed results
    ↓
LLM Judge validates quality
```

This handles any question the user can express — including multi-step analyses, cross-dimensional comparisons, and novel aggregations that don't fit into predefined categories.

### 2.2 Code Generation Strategy

The code planner (`src/code_planner.py`) sends the user query to Gemini 2.5 Flash along with:

- **Full schema description**: column names, dtypes, valid values, sample rows
- **Conversation context**: what was asked and computed in prior turns
- **Strict instructions**: assign the answer to `result`, use only pandas/numpy, include comments

The LLM generates executable Python code that directly computes the answer from the DataFrame.

### 2.3 Execution Safety

Generated code runs inside `sandbox.py` with:

- **Whitelisted builtins only** — no `open()`, `exec()`, `eval()`, `__import__()`, or system access
- **Only pandas, numpy, math, datetime** available as libraries
- **30-second timeout** — infinite loops are killed
- **Isolated namespace** — the code cannot access anything outside its restricted scope
- **Result capture** — code must assign to `result` for output

### 2.4 Self-Healing Loop

If code execution fails, the agent runs a retry loop:

```
1. Generate code → Execute
2. If error → fix_code(original_code, error_message) → Re-execute
3. If error again → fix_code again → Re-execute
4. After MAX_RETRIES failures → return error to user
```

Additionally, if code succeeds but `validate_and_refine()` determines the output doesn't answer the question, the LLM generates corrected code and re-executes.

---

## 3. Insight Generation Logic

### 3.1 Core Principle: Code-Computed Numbers Only

The LLM **never computes numbers from memory**. The pipeline is strictly:

```
Natural Language Query
        ↓
LLM → Python code
        ↓
Sandbox → Deterministic pandas execution → computed results
        ↓
LLM → Narrative wrapping of computed results ONLY
```

This ensures insight accuracy is never dependent on the model's memory or hallucination.

### 3.2 Computation Safeguards

The code planner's system prompt instructs Gemini to generate code that:

- **Reports with denominators**: "5.09% failure rate (638 failed out of 12,527)" not just "5.09%"
- **Uses rates for comparisons**: segment comparisons use rates, never absolute counts
- **Checks sample sizes**: segments with fewer than 200 transactions get explicit warnings
- **Anchors to baselines**: metrics are reported alongside overall averages

### 3.3 Response Structure — D-S-I-R Framework

Every narrative response follows this mandatory four-part structure:

| Component | Purpose | Example |
|---|---|---|
| **D**irect Answer | One sentence answering the question | "Recharge transactions have the highest failure rate at 5.09%." |
| **S**upporting Metrics | The numbers behind the answer with denominators | "638 failed out of 12,527 transactions. Bill Payment is lowest at 4.88% (1,824/37,368)." |
| **I**nterpretation | What the pattern means in business context | "The spread across all types is narrow (4.88%–5.09%), suggesting no transaction type is systematically more failure-prone." |
| **R**ecommendation | Actionable next step where appropriate | "Monitor Recharge integrations for marginal improvement." |

### 3.4 The Visual Layer (Dynamic UI)

Beyond text, the LLM is explicitly prompted to generate strictly typed JSON elements representing visual components:

- **Insight Cards:** A flexible array of metric groups displayed in a dynamic CSS Masonry layout. The LLM determines the optimal number of cards (0 to 4+) and highlights critical metrics dynamically (e.g., success, warning, error colors).
- **Native Charts:** For queries comparing dimensions or showing trends, the LLM generates a robust `<ChartRenderer>` config (Bar, Line, or Pie). The frontend intercepts this JSON schema and renders a flawless, interactive chart *before* the narrative begins.

### 3.4 Calibrated Language

The system uses calibrated language based on the magnitude of observed differences:

| Difference Magnitude | Required Language |
|---|---|
| < 0.5 percentage points | "marginal", "negligible", "slight" |
| 0.5 – 2 percentage points | "notable", "meaningful" |
| > 2 percentage points | "significant", "substantial" |

This prevents the system from dramatising the small differences inherent in the synthetic dataset.

### 3.5 LLM-as-Judge Validation

Every generated response passes through a Gemini 3.1 Pro judge before reaching the user. The judge evaluates four dimensions:

- **Relevance:** Does the response directly answer the question asked?
- **Grounding:** Are all cited statistics traceable to the computed data?
- **Calibration:** Is language scaled appropriately to the magnitude of differences?
- **Safety:** No causal claims unsupported by data, no fraud confirmation language

The judge either approves the response, automatically corrects it, or appends a caveat. It never blocks the user — if the judge itself fails, the original response passes through unchanged.

---

## 4. Pre-Computed Baselines (Data Loader Constants)

These baselines are established from EDA and used by the judge to validate live outputs and anchor all responses.

### Failure Rate Baselines
- **Overall:** 4.95% (12,376 / 250,000)
- **By type:** Recharge 5.09% > P2P 4.96% > P2M 4.95% > Bill Payment 4.88%
- **By bank:** Yes Bank 5.10% (highest) → HDFC 4.82% (lowest); spread: 0.28pp
- **By network:** 3G 5.22% (highest) → 5G/WiFi both 4.86% (lowest); spread: 0.36pp
- **By device:** Web 5.15% > Android 4.94% > iOS 4.93%
- **By age group:** 36-45 at 5.13% (highest) → 26-35 at 4.84% (lowest)
- **By state:** Uttar Pradesh 5.22% (highest) → Telangana 4.71% (lowest)
- **Bank pairs (P2P, notable outlier):** Yes Bank→Kotak 6.59% is the single largest observed differential

### Temporal Baselines
- **Peak hour:** 19:00 (21,232 transactions, 5.15% failure rate)
- **Peak cluster:** 17:00–20:00 sustained high volume
- **Weekend failure rate:** 5.09% vs weekday 4.89% (+0.20pp)
- **Highest failure day:** Sunday 5.10%, lowest: Friday 4.77%

### Fraud Flag Baselines
- **Overall flag rate:** 0.19% (480 / 250,000)
- **High-value (P90+) flag rate:** 0.25% — 1.31× overall concentration
- **Flagged transactions failure rate:** 4.38% (counterintuitively *lower* than unflagged 4.95%)

### Amount Baselines
- **Mean:** ₹1,312 | **Median:** ₹629 | **P90:** ₹3,236 | **P99:** ₹9,003
- **Highest avg category:** Education ₹5,134
- **Lowest avg category:** Transport ₹310

---

## 5. Conversational Context Management

### How Follow-Ups Work

The conversation manager (`src/conversation_manager.py`) maintains a history of prior turns including the query, generated code, and result summary. When a new query arrives:

1. The code planner receives the conversation history as context
2. Gemini can reference prior analyses when generating new code
3. Follow-up queries like "break that down by state" resolve correctly against the prior analysis

### Supported Follow-Up Patterns

| Follow-Up Type | Example | System Handling |
|---|---|---|
| Drill-down | "Break that down by state" | Code planner generates new code referencing prior result |
| Scope change | "Now look at only P2M" | New code adds filter, builds on prior analysis pattern |
| Why question | "Why is that happening?" | Code planner generates multi-dimensional exploration |
| Reset | "Start fresh" / "New question" | Conversation manager clears history |

### Guardrails
- Conversation history is passed to the LLM for code generation context — all numbers are always freshly computed from pandas, never recalled from prior turns
- Each follow-up triggers full code generation → sandbox execution → narration, ensuring result freshness

---

## 6. Limitations & Honest Non-Claims

| What We Do Not Claim | Reason |
|---|---|
| Causal relationships | Correlation matrix shows near-zero correlations; no causal inference warranted |
| Fraud detection capability | fraud_flag is an automated review flag, not confirmed fraud |
| Forecasting or prediction | No time-series modelling; all temporal insights are descriptive |
| External benchmarks | No real-world UPI data to benchmark against |
| User-level patterns | No user IDs in dataset; all analysis is aggregate only |
| Drama where none exists | Failure rate differences are small due to synthetic data uniformity |

---

## 7. Technology Decisions

| Component | Choice | Rationale |
|---|---|---|
| Code Interpreter | LLM-generated pandas code | Handles arbitrary queries without predefined intent categories |
| Sandbox | Restricted exec environment | Prevents unsafe operations from LLM-generated code |
| Data computation | Pandas | 250k rows fits in memory; all aggregations run in under 1 second |
| LLM | Gemini API | Strong instruction-following for code generation and structured output |
| Interface | Next.js (React) | Premium custom chat UI with animated responses |
| API Layer | FastAPI | Provides REST endpoint to connect Next.js to Python engine |
| State management | Python dataclass | Sufficient for conversation depth expected |
| No vector database | — | Structured tabular queries do not require semantic search |
| No SQL layer | — | Pandas operations are sufficient and easier to debug |
