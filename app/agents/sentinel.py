import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from pydantic import ValidationError

from app.llm import ask_json
from app.schemas import SentinelVerdict
from app.tools.news import search_news
from app.tools.weather import get_weather

PORT_COORDS = {"Shanghai": (31.23, 121.47)}
_pool = ThreadPoolExecutor(max_workers=2)


async def _run_news(query: str):
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_pool, search_news, query)
    except Exception as exc:
        return {"error": str(exc)}


async def _run_weather(lat: float, lon: float):
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_pool, get_weather, lat, lon)
    except Exception as exc:
        return {"error": str(exc)}


async def run_sentinel(event_text: str, location: str = "Shanghai") -> SentinelVerdict:
    lat, lon = PORT_COORDS.get(location, PORT_COORDS["Shanghai"])

    news, weather = await asyncio.gather(
        _run_news(f"{location} port closure OR typhoon"),
        _run_weather(lat, lon),
    )

    if isinstance(news, dict) and "error" in news and isinstance(weather, dict) and "error" in weather:
        return SentinelVerdict(
            confirmed=False,
            severity="low",
            delay_days=0,
            location=location,
            confidence=0.2,
            evidence=["News and weather sources were unavailable; disruption could not be verified."],
        )

    prompt = f"""You are the Sentinel agent in a supply chain system.
Decide whether this disruption event is real and how serious it is.
Use only the evidence below. Do not invent facts.

EVENT: {event_text}

NEWS RESULTS (may contain errors or an error message):
{json.dumps(news, default=str)[:3000]}

WEATHER DATA (may contain an error message):
{json.dumps(weather, default=str)[:1500]}

Reply with ONLY a JSON object with these keys:
confirmed (bool), severity ("low"|"medium"|"high"), delay_days (int),
location (string), confidence (0 to 1), evidence (list of short strings).
If news and weather both failed, set confidence at or below 0.3."""

    raw = ask_json(prompt)
    try:
        return SentinelVerdict(**raw)
    except ValidationError as exc:
        raise RuntimeError(f"Sentinel output invalid: {exc}") from exc
