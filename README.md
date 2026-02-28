# ⚡ BRAIN-DS — Leadership Analytics

> Conversational analytics for digital payments data.  
> Ask questions in plain English. Get executive-grade insights backed by real computation.

Built for **Techfest IIT Bombay 2025-26** — InsightX: Leadership Analytics challenge.

---

## What It Does

BRAIN-DS lets business leaders query 250,000 UPI transactions using natural language — no SQL, no dashboards, no analyst queues. The system **writes and executes pandas code** to compute accurate statistics, then narrates findings in clear, executive-ready language.

**Example queries the system handles:**
- *"Which transaction type has the highest failure rate?"*
- *"Compare failure rates for HDFC vs SBI on weekends"*
- *"What are the peak transaction hours for food delivery?"*
- *"Which age group uses P2P most frequently on weekends?"*
- *"What percentage of high-value transactions are flagged for review?"*
- *"Is there a relationship between network type and transaction success?"*

---

## Architecture

BRAIN-DS is built on a **Code Interpreter** paradigm — the LLM generates code, not answers.

```
User Query
    → Code Planner   [Gemini 2.5 Flash: writes pandas code]
    → Sandbox         [Executes code safely against DataFrame]
    → Narrative Gen   [Gemini 2.5 Flash: computed data → D-S-I-R narrative]
    → Judge           [Gemini 3.1 Pro: validates response quality]
    → Streamlit UI    [Chat interface with code trace & follow-ups]
```

All statistics come exclusively from pandas executing in a restricted sandbox — the LLM only writes the code and narrates the results.

For a full technical breakdown of every module, design decision, and data flow see **[docs/architecture.md](docs/architecture.md)**.  
For the query understanding methodology and EDA-derived baselines see **[docs/approach.md](docs/approach.md)**.

---

## Project Structure

```
insightx/
├── app/
│   ├── main.py                  # Streamlit entry point
│   └── ui_components.py         # UI components & styling
├── data/
│   └── raw/                     # Dataset (gitignored — add locally)
├── docs/
│   ├── approach.md              # Query understanding & methodology
│   └── architecture.md          # Full system architecture
├── notebooks/
│   ├── 01_eda.ipynb             # Exploratory data analysis
│   ├── 02_query_patterns.ipynb  # Parser testing
│   └── 03_insight_validation.ipynb
├── src/
│   ├── __init__.py
│   ├── agent.py                 # Orchestrator: generate → execute → narrate
│   ├── code_planner.py          # LLM code generation & narrative (Gemini 2.5 Flash)
│   ├── sandbox.py               # Restricted code execution environment
│   ├── judge.py                 # LLM-as-Judge validation (Gemini 3.1 Pro)
│   ├── data_loader.py           # Data loading, caching, constants
│   ├── conversation_manager.py  # Conversation state & follow-up handling
│   ├── query_parser.py          # [Legacy] NL → intent parser
│   ├── analytics_engine.py      # [Legacy] Deterministic computation
│   └── insight_generator.py     # [Legacy] Results → narrative
├── tests/
│   ├── sample_queries.json      # 15 sample queries + responses
│   ├── test_e2e.py              # End-to-end pipeline tests
│   ├── test_sandbox.py          # Sandbox security tests
│   └── test_reproduce.py        # Reproducibility tests
├── .env.example                 # API key template
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- A Google Gemini API key ([get one here](https://aistudio.google.com/app/apikey))
- The dataset CSV placed at `data/raw/upi_transactions_2024.csv`

### 1. Clone the repository
```bash
git clone https://github.com/<SirCoolerArc>/insightx.git
cd insightx
```

### 2. Create and activate a virtual environment
```bash
# Create
python -m venv venv

# Activate — Windows
venv\Scripts\Activate.ps1

# Activate — Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API key
```bash
# Copy the template
cp .env.example .env

# Open .env and add your key
GEMINI_API_KEY=your_actual_key_here
```

### 5. Add the dataset
Place the CSV file at:
```
data/raw/upi_transactions_2024.csv
```

Or override the path via environment variable:
```bash
INSIGHTX_DATA_PATH=/path/to/your/file.csv
```

### 6. Run the app
```bash
streamlit run app/main.py
```

The app will open at `http://localhost:8501`.

---

## How It Works

1. **You ask a question** in natural language
2. **Gemini writes pandas code** to answer your question
3. **Code executes in a sandbox** — restricted environment, no file/network access, 30s timeout
4. **If execution fails**, the LLM fixes the code and retries (up to 3 attempts)
5. **If output doesn't match the question**, the LLM regenerates corrected code
6. **Gemini narrates the results** in executive D-S-I-R format (Direct answer → Supporting metrics → Interpretation → Recommendation)
7. **An LLM Judge validates** the response for accuracy, calibration, and safety before displaying

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Data computation | Pandas (in-sandbox execution) |
| LLM — Code Generation & Narration | Google Gemini 2.5 Flash |
| LLM — Quality Judge | Google Gemini 3.1 Pro |
| UI | Streamlit |
| API client | google-genai |

---

## Key Dataset Facts

| Metric | Value |
|---|---|
| Total transactions | 250,000 |
| Date range | Jan–Dec 2024 |
| States covered | 10 |
| Banks | 8 |
| Overall failure rate | 4.95% |
| Fraud flag rate | 0.19% (flagged for review, not confirmed fraud) |
| High-value threshold (P90) | ₹3,236 |
| Peak transaction hour | 19:00 |

---

## Team

Built by: <br>
Rishabh Kumar | 24B2419 <br>
Subodh Patel | 24B2509 <br>
Dhruva Reddy | 24B2433 <br>
Abhijeet Singh | 24B2468 <br>

---

## Important Notes

- **Data privacy:** The dataset is synthetic and does not contain real user data.
- **Fraud flags:** `fraud_flag = 1` means flagged for automated review, not confirmed fraud.
- **API costs:** Standard queries make 3 Gemini API calls (code generation, narration, judge). The validate-and-refine step adds a 4th call when needed. Error retries add fix_code calls.
- **Rate limits:** If you hit API quota limits during development, the system has built-in retry-with-backoff logic for 429 errors.
- **Sandbox security:** LLM-generated code runs in a restricted environment with whitelisted builtins only — no file I/O, no network, no imports, 30-second timeout.