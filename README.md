# ⚡ InsightX — Leadership Analytics

> Conversational analytics for digital payments data.  
> Ask questions in plain English. Get executive-grade insights backed by real computation.

Built for **Techfest IIT Bombay 2025-26** — InsightX: Leadership Analytics challenge.

---

## What It Does

InsightX lets business leaders query 250,000 UPI transactions using natural language — no SQL, no dashboards, no analyst queues. The system understands diverse business questions, computes accurate statistics, and explains findings in clear, structured language.

**Example queries the system handles:**
- *"Which transaction type has the highest failure rate?"*
- *"Compare failure rates for HDFC vs SBI on weekends"*
- *"What are the peak transaction hours for food delivery?"*
- *"Which age group uses P2P most frequently on weekends?"*
- *"What percentage of high-value transactions are flagged for review?"*
- *"Is there a relationship between network type and transaction success?"*

---

## Architecture

InsightX is built around one core principle: **the LLM never computes numbers**.

```
User Query
    → Query Parser      [Gemini: NL → structured intent JSON]
    → Analytics Engine  [Pandas: deterministic computation]
    → Insight Generator [Gemini: numbers → D-S-I-R narrative]
    → Streamlit UI      [Chat interface with metrics & follow-ups]
```

The LLM is used twice — once to parse intent, once to narrate results. All statistics come exclusively from pandas operating on the raw dataset.

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
│   ├── raw/                     # Dataset (gitignored — add locally)
│   └── processed/
├── docs/
│   ├── approach.md              # Query understanding & methodology
│   └── architecture.md          # Full system architecture
├── notebooks/
│   ├── 01_eda.ipynb             # Exploratory data analysis
│   ├── 02_query_patterns.ipynb  # Parser testing
│   └── 03_insight_validation.ipynb
├── src/
│   ├── __init__.py
│   ├── data_loader.py           # Data loading, caching, constants
│   ├── query_parser.py          # NL → intent (Gemini)
│   ├── analytics_engine.py      # All computation (pandas)
│   ├── insight_generator.py     # Results → narrative (Gemini)
│   └── conversation_manager.py  # Conversation state
├── tests/
│   └── sample_queries.json      # 15 sample queries + responses
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
git clone https://github.com/<your-username>/insightx.git
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

## Running Individual Modules

Each core module has a self-test block. Run from the project root:

```bash
# Verify dataset loads correctly
python -m src.data_loader

# Test the analytics engine (no API calls needed)
python -m src.analytics_engine

# Test the full pipeline: parser → engine → narrative (uses API)
python -m src.insight_generator
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12 |
| Data computation | Pandas |
| LLM | Google Gemini 2.5 Flash |
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
- **API costs:** The system makes two Gemini API calls per query. Use `gemini-2.5-flash` to keep costs low.
- **Rate limits:** If you hit API quota limits during development, test `analytics_engine.py` directly — it requires no API calls.