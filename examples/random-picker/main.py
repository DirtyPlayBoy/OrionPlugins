"""Orion plugin: random pick / number helpers."""
from __future__ import annotations

import random
import re

from orion_plugin_sdk import Plugin, run, tool


@tool(
    name="pick_one",
    description="Pick one random item from a list (comma/newline separated or JSON array).",
    parameters={
        "type": "object",
        "properties": {
            "items": {"type": "string", "description": "Options separated by comma or newline"},
            "count": {"type": "integer", "default": 1},
        },
        "required": ["items"],
    },
)
def pick_one(items: str = "", count: int = 1):
    raw = str(items or "").strip()
    parts = [p.strip() for p in re.split(r"[\n,;|]+", raw) if p.strip()]
    if not parts:
        return {"ok": False, "error": "empty list"}
    n = max(1, min(int(count or 1), len(parts)))
    chosen = random.sample(parts, n) if n > 1 else [random.choice(parts)]
    return {"ok": True, "picked": chosen[0] if n == 1 else chosen, "from": len(parts)}


@tool(
    name="random_int",
    description="Random integer in inclusive range [min, max].",
    parameters={
        "type": "object",
        "properties": {
            "min": {"type": "integer", "default": 1},
            "max": {"type": "integer", "default": 100},
        },
    },
)
def random_int(min: int = 1, max: int = 100):
    a = int(min if min is not None else 1)
    b = int(max if max is not None else 100)
    if a > b:
        a, b = b, a
    return {"ok": True, "value": random.randint(a, b), "min": a, "max": b}


if __name__ == "__main__":
    run(Plugin(tools=[pick_one, random_int]))
