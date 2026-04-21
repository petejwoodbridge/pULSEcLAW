from __future__ import annotations

import json
import logging
from typing import Any

import ollama
from openai import OpenAI

from pulseclaw.core.config import env, get_models

log = logging.getLogger(__name__)


def _resolve_model(role: str) -> str:
    models = get_models().get("roles", {})
    model = models.get(role)
    if not model:
        raise ValueError(f"No model configured for role: {role}")
    if model.startswith("nim:") and not env("NVIDIA_NIM_API_KEY"):
        fb = get_models().get("fallback", {}).get("nim_fallback", "ollama:qwen2.5:14b")
        log.info("role=%s — NIM unavailable, falling back to %s", role, fb)
        return fb
    return model


def _ollama_chat(model: str, messages: list[dict[str, Any]], *,
                 json_mode: bool = False, temperature: float = 0.2) -> str:
    host = env("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    options = {"temperature": temperature}
    resp = client.chat(
        model=model,
        messages=messages,
        options=options,
        format="json" if json_mode else "",
    )
    return resp["message"]["content"]


def _nim_chat(model: str, messages: list[dict[str, Any]], *,
              json_mode: bool = False, temperature: float = 0.2) -> str:
    api_key = env("NVIDIA_NIM_API_KEY")
    base_url = env("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    client = OpenAI(api_key=api_key, base_url=base_url)
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def chat(role: str, messages: list[dict[str, Any]], *,
         json_mode: bool = False, temperature: float = 0.2) -> str:
    """Dispatch to the right provider based on the role→model mapping."""
    model = _resolve_model(role)
    provider, _, model_id = model.partition(":")
    if provider == "ollama":
        return _ollama_chat(model_id, messages, json_mode=json_mode, temperature=temperature)
    if provider == "nim":
        return _nim_chat(model_id, messages, json_mode=json_mode, temperature=temperature)
    raise ValueError(f"Unknown provider: {provider}")


def chat_json(role: str, messages: list[dict[str, Any]], *,
              temperature: float = 0.2) -> dict[str, Any]:
    """Chat with guaranteed JSON output. Parses and returns a dict."""
    raw = chat(role, messages, json_mode=True, temperature=temperature)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("JSON parse failed for role=%s: %s\nraw=%s", role, e, raw[:500])
        return {}


def health_check() -> dict[str, Any]:
    """Quick probe of all configured providers. Returns {provider: ok|error}."""
    out: dict[str, Any] = {}
    # Ollama
    try:
        host = env("OLLAMA_HOST", "http://localhost:11434")
        client = ollama.Client(host=host)
        client.list()
        out["ollama"] = "ok"
    except Exception as e:
        out["ollama"] = f"error: {e}"
    # NIM (optional)
    if env("NVIDIA_NIM_API_KEY"):
        try:
            _nim_chat(
                "nvidia/llama-3.1-nemotron-70b-instruct",
                [{"role": "user", "content": "ok"}],
                temperature=0.0,
            )
            out["nim"] = "ok"
        except Exception as e:
            out["nim"] = f"error: {e}"
    else:
        out["nim"] = "not configured"
    return out
