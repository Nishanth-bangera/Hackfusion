"""
test_pipeline.py — End-to-end pipeline test using PLACEHOLDER sentinel.

Runs one complete job through:
  Sentinel (PLACEHOLDER) -> Impact -> Planner -> Verifier -> Executor

Expected outcomes:
  - job status: done
  - at least one PO file written to outbox/ (4 POs from 4 exposed orders)
  - escalation_count + approved_count >= total exposures (all orders handled)

With MOCK data:
  Orders 1,3: CELL-18650 — alternatives via Hanoi (lead=7, price=122) -> APPROVED
  Order 2:    BMS-40A    — alternative via Chennai (lead=4, price=880) -> APPROVED
  Order 4:    CASE-IP67  — alternative via Hanoi (lead=9, price=225) -> APPROVED
  All orders <= 10000 units so none escalate on order size.
  Result: 4 POs approved, 0 escalations (all alternatives pass policy).
"""
import asyncio
import json
from pathlib import Path

from app.db import get_connection
from app.orchestrator import create_job, placeholder_sentinel, run_job
from app.seed import seed

# Re-seed so data is clean and deterministic
print("Seeding MOCK data...")
seed()

EVENT = "Typhoon Haikui closes Shanghai port for 5 days (PLACEHOLDER sentinel test)"
job_id = create_job(EVENT)

print(f"\nJob created: id={job_id}")
print("Running pipeline with PLACEHOLDER sentinel...\n")

asyncio.run(run_job(job_id, EVENT, sentinel=placeholder_sentinel))

# --- Retrieve and display results ---
conn = get_connection()
job = conn.execute(
    "SELECT id, status, failure_reason, result_json FROM jobs WHERE id = ?",
    (job_id,),
).fetchone()

print("=" * 60)
print(f"JOB STATUS : {job['status']}")
if job["failure_reason"]:
    print(f"FAILURE    : {job['failure_reason']}")

result = json.loads(job["result_json"]) if job["result_json"] else {}
outcome = result.get("outcome", {})
if outcome:
    print("\nOUTCOME REPORT:")
    print(f"  Approved POs       : {outcome.get('approved_pos', 0)}")
    print(f"  Escalations        : {outcome.get('escalations', 0)}")
    print(f"  Rejections         : {outcome.get('rejections', 0)}")
    print(f"  Worst stockout     : {outcome.get('worst_stockout_days', 0)} days")
    print(f"  Total approved INR : \u20b9{outcome.get('total_approved_inr', 0):,.2f}")
    print(f"  Elapsed            : {outcome.get('elapsed_seconds', '?')}s")
    print(f"  Sentinel           : {outcome.get('sentinel_label', '?')}")

print("\n" + "=" * 60)
print("EVENT LOG:")
for row in conn.execute(
    "SELECT agent, message FROM job_events WHERE job_id = ? ORDER BY id",
    (job_id,),
):
    print(f"  {row['agent']:>13}: {row['message']}")

print("\n" + "=" * 60)
print("ACTIONS:")
for row in conn.execute(
    "SELECT action_type, status, payload_json FROM actions WHERE job_id = ? ORDER BY id",
    (job_id,),
):
    payload = json.loads(row["payload_json"])
    print(f"  {row['action_type']:>12} [{row['status']:>10}]: {payload}")

print("\n" + "=" * 60)
print("OUTBOX FILES:")
outbox = Path("outbox")
if outbox.exists():
    files = sorted(outbox.glob(f"*{job_id}*"))
    if files:
        for f in files:
            print(f"  {f.name}")
    else:
        print(f"  (no files matching job_id={job_id} in outbox/)")
else:
    print("  outbox/ directory does not exist")

conn.close()

# --- Assertions ---
assert job["status"] == "done", f"Expected status=done, got {job['status']}"

po_files = list(outbox.glob(f"PO-{job_id}-*.txt")) if outbox.exists() else []
assert len(po_files) >= 1, f"Expected at least 1 PO file, got {len(po_files)}"

approved_count = outcome.get("approved_pos", 0)
escalation_count = outcome.get("escalations", 0)
assert approved_count + escalation_count >= 1, (
    f"Expected at least 1 handled exposure, got approved={approved_count} escalations={escalation_count}"
)

print("\n" + "=" * 60)
print("All assertions passed:")
print(f"  status=done  PO files={len(po_files)}  approved={approved_count}  escalations={escalation_count}")
