"""
Orchestrator — creates jobs and runs the full agent pipeline.

Pipeline: Sentinel -> Impact -> Planner -> Verifier -> Executor
"""
import asyncio
import json
import time
from collections.abc import Awaitable, Callable

from app.agents.impact import run_impact
from app.agents.sentinel import run_sentinel
from app.db import get_connection, init_db
from app.schemas import SentinelVerdict

SentinelRunner = Callable[[str], Awaitable[SentinelVerdict]]


def _record_event(job_id: int, agent: str, message: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO job_events (job_id, agent, message) VALUES (?, ?, ?)",
            (job_id, agent, message),
        )
        conn.commit()
    finally:
        conn.close()


def _update_job(
    job_id: int,
    *,
    status: str,
    failure_reason: str | None = None,
    result_json: str | None = None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET status = ?, failure_reason = ?, result_json = ? WHERE id = ?",
            (status, failure_reason, result_json, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def create_job(event_text: str) -> int:
    """Persist a queued disruption job and its planned agent sequence."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO jobs (event_text, status) VALUES (?, 'queued')",
            (event_text,),
        )
        job_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    _record_event(
        job_id,
        "orchestrator",
        "Job started. Plan: sentinel -> impact -> planner -> verifier -> executor",
    )
    return job_id


async def placeholder_sentinel(event_text: str) -> SentinelVerdict:
    """Return a deterministic PLACEHOLDER verdict for testing the pipeline flow."""
    return SentinelVerdict(
        confirmed=True,
        severity="high",
        delay_days=5,
        location="Shanghai",
        confidence=0.86,
        evidence=["PLACEHOLDER verdict — live Sentinel was not used"],
    )


async def run_job(
    job_id: int,
    event_text: str,
    sentinel: SentinelRunner | None = None,
    location: str = "Shanghai",
) -> None:
    """Run the full pipeline: Sentinel -> Impact -> Planner -> Verifier -> Executor."""
    start_time = time.monotonic()
    _update_job(job_id, status="running")

    try:
        # --- Stage 1: Sentinel ---
        _record_event(job_id, "sentinel", "Checking the event against news and weather.")
        if sentinel is None:
            async def live_sentinel(text: str) -> SentinelVerdict:
                return await run_sentinel(text, location)

            sentinel = live_sentinel

        verdict = await sentinel(event_text)

        # Detect whether the PLACEHOLDER was used
        is_placeholder = any("PLACEHOLDER" in e for e in verdict.evidence)
        sentinel_label = "PLACEHOLDER" if is_placeholder else "LIVE"

        _record_event(
            job_id,
            "sentinel",
            f"[{sentinel_label}] confirmed={verdict.confirmed}, severity={verdict.severity}, "
            f"delay_days={verdict.delay_days}, confidence={verdict.confidence:.2f}",
        )

        # Escalate if evidence is weak
        if not verdict.confirmed or verdict.confidence < 0.5:
            reason = "Sentinel evidence was unconfirmed or below the 0.5 confidence threshold."
            result_json = json.dumps({
                "sentinel": verdict.model_dump(),
                "sentinel_label": sentinel_label,
            })
            _record_event(job_id, "orchestrator", f"Escalated: {reason}")
            _update_job(
                job_id,
                status="escalated",
                failure_reason=reason,
                result_json=result_json,
            )
            return

        # --- Stage 2: Impact ---
        _record_event(
            job_id, "impact",
            "Calculating exposed orders from inventory and lead times.",
        )
        impact = run_impact(verdict)
        _record_event(
            job_id,
            "impact",
            f"{impact.total_orders_at_risk} orders at risk, "
            f"worst stockout {impact.worst_stockout_days} days",
        )

        if not impact.exposed:
            elapsed = round(time.monotonic() - start_time, 1)
            outcome = {
                "approved_pos": 0,
                "escalations": 0,
                "rejections": 0,
                "worst_stockout_days": 0,
                "total_approved_inr": 0.0,
                "elapsed_seconds": elapsed,
                "sentinel_label": sentinel_label,
                "note": "No exposures found — no procurement action needed.",
            }
            result_json = json.dumps({
                "sentinel": verdict.model_dump(),
                "sentinel_label": sentinel_label,
                "impact": impact.model_dump(),
                "outcome": outcome,
            })
            _update_job(job_id, status="done", result_json=result_json)
            _record_event(job_id, "orchestrator", "No exposures found — job complete.")
            return

        # --- Stages 3+4+5: Planner + Verifier + Executor ---
        _record_event(
            job_id, "planner",
            "Running rule-based planner (no LLM, no retry loop).",
        )
        from app.pipeline import run_pipeline

        pipeline_result = run_pipeline(
            job_id=job_id,
            impact=impact,
            confidence=verdict.confidence,
            disrupted_port=verdict.location,
        )

        elapsed = round(time.monotonic() - start_time, 1)
        outcome = {
            "approved_pos": pipeline_result["approved_pos"],
            "escalations": pipeline_result["escalations"],
            "rejections": pipeline_result["rejections"],
            "worst_stockout_days": impact.worst_stockout_days,
            "total_approved_inr": pipeline_result["total_approved_inr"],
            "elapsed_seconds": elapsed,
            "output_files": pipeline_result["output_files"],
            "sentinel_label": sentinel_label,
            "note": (
                "Baseline manual response time is an assumption, not a measurement."
            ),
        }
        result_json = json.dumps({
            "sentinel": verdict.model_dump(),
            "sentinel_label": sentinel_label,
            "impact": impact.model_dump(),
            "outcome": outcome,
        })
        _update_job(job_id, status="done", result_json=result_json)
        _record_event(
            job_id, "orchestrator",
            f"Done. POs={pipeline_result['approved_pos']}, "
            f"escalations={pipeline_result['escalations']}, "
            f"rejections={pipeline_result['rejections']}, "
            f"elapsed={elapsed}s",
        )

    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        _record_event(job_id, "orchestrator", f"Job failed: {reason}")
        _update_job(job_id, status="failed", failure_reason=reason)


async def run_disruption(event_text: str, location: str = "Shanghai") -> int:
    """Create a job and run the full pipeline."""
    job_id = create_job(event_text)
    await run_job(job_id, event_text, location=location)
    return job_id


def run_disruption_sync(event_text: str, location: str = "Shanghai") -> int:
    """Synchronous entry point for CLI scripts and background workers."""
    return asyncio.run(run_disruption(event_text, location))
