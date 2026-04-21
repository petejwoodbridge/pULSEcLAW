"""Load SKILL.md prompts (YAML frontmatter + markdown body)."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"

_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER.match(raw)
    if not m:
        return {}, raw
    header, body = m.group(1), m.group(2)
    # Hand-parse simple YAML: key: value, no nesting.
    meta: dict[str, Any] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


@lru_cache(maxsize=64)
def load_skill(name: str) -> tuple[dict[str, Any], str]:
    """Return (metadata, body) for a skill."""
    path = SKILLS_DIR / name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"Skill not found: {path}")
    raw = path.read_text(encoding="utf-8")
    return _parse_frontmatter(raw)


def render(body: str, **context: Any) -> str:
    """Minimal template: {{var}} substitution only. No jinja for determinism."""
    out = body
    for k, v in context.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def load_rendered(name: str, **context: Any) -> tuple[dict[str, Any], str]:
    meta, body = load_skill(name)
    return meta, render(body, **context)
