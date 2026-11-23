# SupplyShield — Hackfusion

**Hackathon project by Team Hackfusion**

A multi-agent AI system that detects supply chain disruptions and executes a verified, rule-based recovery plan in seconds.

---

## Problem

Global supply chains are fragile. When a port closes or a typhoon strikes, procurement teams spend hours manually identifying which orders are at risk, finding alternative suppliers, and raising emergency purchase orders. SupplyShield automates that entire response pipeline.

---

## Solution

SupplyShield runs a chain of autonomous agents on a natural-language disruption event:

1. **Sentinel** — verifies the event using live news and weather APIs, returns a confidence-scored verdict
2. **Impact Analyst** — queries the database to find which open orders are exposed, calculates stockout risk
3. **Planner** — rule-based (no LLM) finds alternative suppliers for each exposed order
4. **Verifier** — checks each candidate against procurement policies (lead time, price premium, order size)
5. **Executor** — writes draft purchase orders and email drafts to `outbox/`

---

## Architecture

```
Event (text)
    │
    ▼
[Sentinel Agent]  ←── news API + weather API
    │  confirmed verdict + confidence
    ▼
[Impact Analyst]  ←── DB: orders, inventory, supplier_products
    │  list of exposed orders + stockout days
    ▼
[Planner]         ←── DB: find_alternatives (rule-based, no LLM)
    │  candidate suppliers per exposure
    ▼
[Verifier]        ←── policies.yaml (lead time, price, order size)
    │  APPROVED / REJECTED / ESCALATE
    ▼
[Executor]        ──► outbox/PO-<job>-<n>.txt
                  ──► outbox/EMAIL-PO-<job>-<n>.txt
                  ──► actions table (DB)
```

All stages are logged to `job_events` and the final outcome is stored in `jobs.result_json`.

### Key files

| File | Purpose |
|------|---------|
| `app/agents/sentinel.py` | LLM agent — verifies disruption events |
| `app/agents/impact.py` | Deterministic — finds exposed orders |
| `app/agents/verifier.py` | Rule-based — checks procurement policies |
| `app/pipeline.py` | Planner + Verifier + Executor coordination |
| `app/executor.py` | Writes PO and email draft files to `outbox/` |
| `app/orchestrator.py` | Job management and pipeline sequencing |
| `app/tools/db_tools.py` | `find_exposures`, `find_alternatives` |
| `app/tools/news.py` | RSS news search tool |
| `app/tools/weather.py` | Open-Meteo weather tool |
| `policies.yaml` | Procurement policy thresholds |
| `app/db.py` | SQLite schema (8 tables) |
| `app/seed.py` | MOCK data loader |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Database | SQLite (via `sqlite3`) |
| Data models | Pydantic v2 |
| LLM clients | Anthropic Claude, Google Gemini, Ollama (fallback chain) |
| News tool | RSS / feedparser |
| Weather tool | Open-Meteo (free, no key required) |
| Policy engine | PyYAML + pure Python rules |
| Web API | FastAPI (optional dashboard — see Limitations) |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/Nishanth-bangera/Hackfusion.git
cd Hackfusion

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
# Edit .env and fill in your API keys (at least one LLM provider)

# 5. Seed the MOCK database
python -m app.seed

# 6. Run the end-to-end test
python test_pipeline.py
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PRIMARY_LLM` | Yes | `anthropic`, `gemini`, or `ollama` |
| `ANTHROPIC_API_KEY` | If using Anthropic | Your Anthropic API key |
| `ANTHROPIC_MODEL` | No | Defaults to `claude-haiku-5-5` |
| `GEMINI_API_KEY` | If using Gemini | Your Google Gemini API key |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `OLLAMA_MODEL` | If using Ollama | Local model name, e.g. `llama3.2` |
| `OLLAMA_BASE_URL` | No | Defaults to `http://localhost:11434` |

> **Never commit `.env` to version control.** It is listed in `.gitignore`.

---

## How to Run

```bash
# Full end-to-end pipeline test (PLACEHOLDER sentinel if LLM unavailable)
python test_pipeline.py

# Individual component tests
python test_impact.py        # Impact analyst (deterministic)
python test_verifier.py      # Verifier policy rules
python test_alternatives.py  # find_alternatives tool

# Existing orchestrator tests
python test_orchestrator.py
```

---

## Demo Workflow

1. `python -m app.seed` — loads MOCK suppliers, products, and open orders into SQLite
2. `python test_pipeline.py` — runs one full job end-to-end:
   - Creates a disruption event: *"Typhoon Haikui closes Shanghai port for 5 days"*
   - **Sentinel** verifies (or uses PLACEHOLDER if LLM unavailable)
   - **Impact** finds 4 exposed orders (all sourced via Shanghai port)
   - **Planner** finds alternative suppliers: Chennai, Hanoi/Haiphong
   - **Verifier** checks each against `policies.yaml` — all 4 pass (within lead-time and price limits)
   - **Executor** writes 4 draft POs + 4 draft emails to `outbox/`
   - Prints the full event log and outcome report

**Sample outcome (PLACEHOLDER sentinel):**
```
Approved POs       : 4
Escalations        : 0
Rejections         : 0
Worst stockout     : 4 days
Total approved INR : ₹1,686,000.00
Elapsed            : 0.6s
Sentinel           : PLACEHOLDER
```

**Sample outbox files:**
```
outbox/PO-6-1.txt          ← Draft PO for CELL-18650 via Hanoi Parts Co
outbox/EMAIL-PO-6-1.txt    ← Draft email to procurement team
outbox/PO-6-2.txt          ← Draft PO for CELL-18650 (order 1)
outbox/EMAIL-PO-6-2.txt
...
```

---

## Limitations

| Area | Detail |
|------|--------|
| **Company data** | All business data (suppliers, products, orders, prices) is **MOCK** data for a fictional company. No real company data is used. |
| **Sentinel** | May be **LIVE** (using the configured LLM provider — Anthropic, Gemini, or Ollama) or **PLACEHOLDER** (deterministic fallback if the LLM is unreachable or unconfigured). The job log and outcome report clearly label which was used. During hackathon testing, **PLACEHOLDER** was used. |
| **Planner** | Purely **rule-based** — no LLM reasoning in the planning stage. Picks the cheapest alternative that passes all verifier checks. |
| **Retry loop** | The Planner has **no retry loop**. If all candidates are rejected, the order is escalated rather than re-planned with a modified strategy. |
| **Executor** | Writes **draft files only** to `outbox/`. No real email is sent, no real purchase order is issued to any supplier. All files are labeled DRAFT. |
| **Dashboard** | The optional FastAPI dashboard (`static/index.html`) was **not completed** due to time constraints. The database (`supplyshield.db`) can be queried directly with any SQLite client. |
| **Baseline metric** | Any "manual response time" comparison would be an **assumption**, not a measured benchmark. No such comparison is claimed. |

---

*Built in one hour for the Hackfusion hackathon — November 2026.*
