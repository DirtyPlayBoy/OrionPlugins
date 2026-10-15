"""Orion plugin: text utilities for the assistant."""
from __future__ import annotations

import re
import unicodedata

from orion_plugin_sdk import Plugin, run, tool


@tool(
    name="transform_case",
    description="Change text case: lower, upper, title, capitalize.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "mode": {
                "type": "string",
                "enum": ["lower", "upper", "title", "capitalize"],
                "default": "lower",
            },
        },
        "required": ["text"],
    },
)
def transform_case(text: str = "", mode: str = "lower"):
    raw = str(text or "")
    m = str(mode or "lower").lower()
    if m == "upper":
        out = raw.upper()
    elif m == "title":
        out = raw.title()
    elif m == "capitalize":
        out = raw.capitalize()
    else:
        out = raw.lower()
    return {"text": out, "mode": m}


@tool(
    name="slugify",
    description="Make a URL-friendly slug from text.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
def slugify(text: str = ""):
    raw = unicodedata.normalize("NFKD", str(text or ""))
    raw = raw.encode("ascii", "ignore").decode("ascii")
    raw = re.sub(r"[^a-zA-Z0-9]+", "-", raw).strip("-").lower()
    return {"slug": raw or "item"}


@tool(
    name="count_text",
    description="Count characters, words and lines.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
)
def count_text(text: str = ""):
    raw = str(text or "")
    words = re.findall(r"\S+", raw)
    return {
        "chars": len(raw),
        "chars_no_spaces": len(re.sub(r"\s+", "", raw)),
        "words": len(words),
        "lines": len(raw.splitlines()) if raw else 0,
    }


if __name__ == "__main__":
    run(Plugin(tools=[transform_case, slugify, count_text]))
