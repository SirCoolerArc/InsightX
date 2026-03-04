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
  → Next.js UI
  → FastAPI Backend
  → Parallel Stage 1: Discovery
      ├─ LLM #1: Code Planner (Deterministic Execution)
      ├─ LLM #2: Logic Validator
      ├─ LLM #3: Deep-Dive Researcher (Proactive Segmentation)
      └─ LLM #4: Research Auditor
  → Parallel Stage 2: Synthesis
      └─ LLM #5: Narrative Architect (D-S-I-R Logic)
  → Parallel Stage 3: Quality Audit
      ├─ LLM #6: Structural Judge (5-Dimensional Audit)
      └─ LLM #7: Contextual Predictor (Strategic Follow-ups)
  → Final Executive Insight (D-S-I-R Narrative + KPI Cards)
  → Next.js UI (Streaming SSE Updates)
```

All statistics come exclusively from pandas executing in a restricted sandbox — the LLM only writes the code and narrates the results.

For a full technical breakdown of every module, design decision, and data flow see **[docs/architecture.md](docs/architecture.md)**.  
For the query understanding methodology and EDA-derived baselines see **[docs/approach.md](docs/approach.md)**.

---

## Project Structure

```
insightx/
├── api/
│   └── main.py                  # FastAPI backend server
├── frontend/                    # Next.js React frontend
├── data/
│   └── raw/                     # Dataset (gitignored — add locally)
├── docs/
│   ├── approach.md              # Query understanding & methodology
│   └── architecture.md          # Full system architecture
├── notebooks/
│   └── EDA.ipynb                # Exploratory data analysis
├── src/
│   ├── __init__.py
│    ├── agent.py                 # Orchestrator: parallelizes generate → execute → narrate
    ├── code_planner.py          # LLM code generation & narrative (Gemini 2.5 Flash)
    ├── sandbox.py               # Restricted code execution environment
    ├── judge.py                 # LLM-as-Judge validation (Gemini 2.5 Flash)
│   ├── data_loader.py           # Data loading, caching, constants
│   └── conversation_manager.py  # Conversation state & follow-up handling
├── tests/
│   ├── sample_queries.json      # 15 sample queries + responses
│   ├── test_e2e.py              # End-to-end pipeline tests
│   └── test_sandbox.py          # Sandbox security tests
├── .env                         # API keys
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- The dataset CSV placed at `data/raw/upi_transactions_2024.csv`

### 1. Clone the repository
```bash
git clone https://github.com/SirCoolerArc/InsightX.git
cd InsightX
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

### 4. Configure Environment
A `.env` file is already provided in the root directory. To run the application, simply add your **Gemini API Key** to it:
```
GEMINI_API_KEY=your_key_here
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

### 6. Run the application locally (For Evaluators)

To run the application locally on an evaluation machine, you will need two separate terminal windows.

**Prerequisites:**
- Python 3.10+
- Node.js 18+ and npm

**Terminal 1: Start the Backend (FastAPI)**
```bash
# Ensure you are in the insightx directory with the virtual environment activated
# Windows
venv\Scripts\Activate.ps1
# Mac/Linux
source venv/bin/activate

# Run the server
python -m uvicorn api.main:app --port 8080
```
*The backend will boot up and load the dataset into memory. Wait until you see `Application startup complete`.*

**Terminal 2: Start the Frontend (Next.js)**
```bash
# Open a new terminal and navigate to the frontend folder
cd frontend

# Install Node dependencies (only needed the first time)
npm install

# Start the Next.js development server
npm run dev
```
*The application is now accessible at [http://localhost:3000](http://localhost:3000).*

---

## 🚀 Key Technological Breakthroughs

### 1. The 7-LLM Parallel Engine
A high-concurrency orchestration layer that collapses complex reasoning into three parallel stages:
*   **Discovery**: Concurrent Code Execution (Planner) + Proactive Research (Deep-Dive).
*   **Synthesis**: Narrative Architect weaving multiple data streams via D-S-I-R logic.
*   **Audit**: Concurrent Quality Judging (5-Dimensions) + Contextual Follow-up Prediction.

### 2. Zero-Trust Code Interpreter Sandbox
All insights are grounded in verified Python execution within a hardened sandbox:
*   **Isolated Builtins**: Blocking non-essential Python functions (`eval`, `exec`, `import`).
*   **Self-Healing**: Automated traceback reading and code patching (`MAX_RETRIES: 3`).
*   **Memory Integrity**: Non-mutable dataset injection using `df.copy()`.

### 3. Scientific Grounding (The Calibration Layer)
*   **EDA Baseline Anchors**: Every insight is anchored to 14 pre-computed statistical constants.
*   **Precision Adjectives**: Enforced adjective thresholds for deltas (Marginal < 0.5pp | Significant > 2pp).

### 4. Visual Excellence
*   **Real-time SSE Streaming**: Direct visibility into the agent's logic steps.
*   **Native Chart Rendering**: Dynamic Bar/Line/Pie charts built via Recharts.
*   **Masonry Insights Grid**: Context-rich UI cards for metrics, breakdowns, and anomalies.

---

##  Dataset Insights

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

## 👥 Team

Built by:  
Rishabh Kumar | 24B2419  
Subodh Patel | 24B2509  
Dhruva Reddy | 24B2433  
Abhijeet Singh | 24B2468  

---

## 📌 Important Notes

- **Data privacy:** The dataset is synthetic and does not contain real user data.
- **Fraud flags:** `fraud_flag = 1` means flagged for automated review, not confirmed fraud.
- **API costs:** Standard queries involve 3 parallel Gemini 2.5 Flash calls. The judge and follow-up steps add 4 more calls.
- **Rate limits:** Built-in retry-with-backoff logic handles 429 errors.
- **Sandbox security:** Generative code runs in a restricted environment with whitelisted builtins — no file I/O, no network, 30s timeout.