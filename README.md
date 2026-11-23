# SupplyShield

Hackathon prototype by Team Hackfusion.

SupplyShield demonstrates a supply disruption workflow using a SQLite database of fictional company data. The recorded demo run used a deterministic **PLACEHOLDER Sentinel** verdict. It did not perform live research or verify a real disruption.

## What the demo does

Given a disruption event, the pipeline:

1. Uses the labeled PLACEHOLDER Sentinel verdict in `test_pipeline.py`.
2. Calculates exposed orders from inventory, supplier lead times, and the disruption delay.
3. Finds alternative suppliers with a rule-based Planner. The Planner uses no LLM and has no retry loop.
4. Applies the configured Verifier checks for confidence, order size, maximum lead time, and price premium.
5. Writes draft purchase orders and draft email text files to `outbox/`. It sends no email and issues no real purchase order.

All company names, suppliers, products, customers, prices, inventory, orders, and disruption data are **MOCK** data.

## Verified limitation: arrival before stockout

The Verifier does not currently check whether an alternative supplier's lead time is shorter than the exposure's `stockout_days`. In the recorded run, the Hanoi alternative for product `CASE-IP67` was approved even though its lead time was 9 days and the reported stockout was in 2 days. The demo therefore must not be described as enforcing an arrival-before-stockout rule.

Other checks still run, but they do not prevent this timing mismatch. This is a known limitation in the submitted code.

## Setup on Windows

From PowerShell:

```powershell
cd C:\Hackfusion
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.seed
```

The end-to-end demo uses the PLACEHOLDER Sentinel and does not need an LLM API key:

```powershell
python test_pipeline.py
```

The separate live Sentinel runner requires a configured, reachable LLM provider and working news/weather network access:

```powershell
python test_sentinel.py
```

Keep real API keys only in the ignored `.env` file. Never commit `.env`.

## Other checks

```powershell
python test_impact.py
python test_alternatives.py
python test_verifier.py
```

## Demo result

The recorded PLACEHOLDER run completed with 4 approved draft POs, 0 escalations, and 0 rejections. The total approved value was INR 1,686,000. The same value was independently summed from the four PO files for the latest recorded job.

The output files are drafts for human review. No email was sent and no purchase order was issued to a supplier.

## Limitations

- **Sentinel:** the demo used a PLACEHOLDER verdict, not live research. The live LLM path has not been verified for this submission.
- **Company data:** all business data is MOCK data for a fictional company.
- **Planner:** it uses deterministic database lookup and rules; it has no LLM and no retry loop.
- **Verifier:** it checks confidence, order size, maximum lead time, and price premium, but does not enforce arrival before stockout. The Hanoi `CASE-IP67` approval described above demonstrates this gap.
- **Executor:** it writes draft files under `outbox/`; it sends no email and issues no real purchase order.
- **Dashboard:** neither `static/index.html` nor a FastAPI dashboard was built.
- **Response-time comparison:** the manual-response baseline is an assumption, not a measurement.

## Project files

- `app/agents/sentinel.py` - Sentinel and its news/weather evidence tools.
- `app/agents/impact.py` - deterministic exposure report.
- `app/agents/verifier.py` and `policies.yaml` - procurement policy checks.
- `app/pipeline.py` - alternative supplier lookup, verification, and execution flow.
- `app/executor.py` - writes PO and email draft files.
- `app/orchestrator.py` - stores jobs, runs stages, and records `job_events`.
- `app/db.py` and `app/seed.py` - SQLite schema and MOCK data.
- `test_pipeline.py` - deterministic end-to-end demonstration using the PLACEHOLDER Sentinel.
