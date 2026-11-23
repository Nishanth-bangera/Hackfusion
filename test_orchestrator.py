import asyncio

from app.db import get_connection
from app.orchestrator import create_job, run_job, placeholder_sentinel


def show(job_id: int) -> None:
    conn = get_connection()
    job = conn.execute(
        "SELECT id, status, failure_reason FROM jobs WHERE id = ?", (job_id,)
    ).fetchone()
    print("JOB:", dict(job))
    for row in conn.execute(
        "SELECT agent, message FROM job_events WHERE job_id = ? ORDER BY id", (job_id,)
    ):
        print(f"{row['agent']:>13}: {row['message']}")
    conn.close()


async def low_confidence_sentinel(event_text):
    from app.schemas import SentinelVerdict

    return SentinelVerdict(
        confirmed=True,
        severity="high",
        delay_days=5,
        location="Shanghai",
        confidence=0.3,
        evidence=["TEST verdict, low confidence"],
    )


# Case 1: confident verdict goes through impact to done
job_ok = create_job("Typhoon closes Shanghai port for 5 days")
asyncio.run(
    run_job(
        job_ok,
        "Typhoon closes Shanghai port for 5 days",
        placeholder_sentinel,
    )
)
show(job_ok)

print("-" * 40)

# Case 2: low confidence must escalate, no impact run
job_low = create_job("Typhoon closes Shanghai port for 5 days")
asyncio.run(
    run_job(
        job_low,
        "Typhoon closes Shanghai port for 5 days",
        low_confidence_sentinel,
    )
)
show(job_low)
