from app.agents.impact import run_impact
from app.schemas import SentinelVerdict

verdict = SentinelVerdict(
    confirmed=True,
    severity="high",
    delay_days=5,
    location="Shanghai",
    confidence=0.86,
    evidence=["test"],
)
print(run_impact(verdict).model_dump_json(indent=2))

weak_verdict = verdict.model_copy(update={"confidence": 0.3})
print(run_impact(weak_verdict).model_dump_json(indent=2))
