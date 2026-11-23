import json
import re

from app import config


class LLMError(Exception):
    """Raised when no configured language model can return usable JSON."""


def _call_anthropic(prompt: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise LLMError("ANTHROPIC_API_KEY missing")
    from anthropic import Anthropic

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")


def _call_gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY missing")
    from google import genai

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    response = client.models.generate_content(model=config.GEMINI_MODEL, contents=prompt)
    return response.text or ""


def _call_ollama(prompt: str) -> str:
    import httpx

    response = httpx.post(
        f"{config.OLLAMA_BASE_URL}/api/generate",
        json={
            "model": config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def _extract_json(text: str) -> dict:
    """Extract a JSON object from plain text or a Markdown-fenced reply."""
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise LLMError(f"No JSON object in reply: {text[:200]}")
    try:
        result = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"Invalid JSON in reply: {exc}") from exc
    if not isinstance(result, dict):
        raise LLMError("LLM reply must be a JSON object")
    return result


def ask_json(prompt: str) -> dict:
    """Ask the configured provider first, then try the other providers."""
    provider_order = {
        "anthropic": [_call_anthropic, _call_gemini, _call_ollama],
        "gemini": [_call_gemini, _call_anthropic, _call_ollama],
        "ollama": [_call_ollama, _call_anthropic, _call_gemini],
    }
    providers = provider_order.get(config.PRIMARY_LLM, provider_order["anthropic"])
    errors = []
    for call in providers:
        try:
            return _extract_json(call(prompt))
        except Exception as exc:
            errors.append(f"{call.__name__}: {exc}")
    raise LLMError("All LLM providers failed. " + "; ".join(errors))
