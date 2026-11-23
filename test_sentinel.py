import asyncio

from app.agents.sentinel import run_sentinel

verdict = asyncio.run(run_sentinel("Typhoon closes Shanghai port for 5 days"))
print(verdict.model_dump_json(indent=2))
