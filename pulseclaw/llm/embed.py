from __future__ import annotations

import ollama

from pulseclaw.core.config import env, get_models


def _embed_model() -> str:
    role = get_models().get("roles", {}).get("embed", "ollama:nomic-embed-text")
    return role.split(":", 1)[1] if ":" in role else role


def embed(text: str) -> list[float]:
    host = env("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    resp = client.embeddings(model=_embed_model(), prompt=text[:8000])
    return list(resp["embedding"])


def embed_many(texts: list[str]) -> list[list[float]]:
    return [embed(t) for t in texts]
