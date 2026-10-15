"""Orion plugin: local quick notes for the assistant."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from orion_plugin_sdk import Plugin, run, tool

DATA = Path(__file__).resolve().parent / "data" / "notes.json"


def _load() -> list:
    if not DATA.is_file():
        return []
    try:
        raw = json.loads(DATA.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    except Exception:
        return []


def _save(rows: list) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


@tool(
    name="add_note",
    description="Save a short local note for later recall.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "default": []},
        },
        "required": ["text"],
    },
)
def add_note(text: str = "", tags: list | None = None):
    body = str(text or "").strip()
    if not body:
        return {"ok": False, "error": "empty note"}
    rows = _load()
    note = {
        "id": uuid.uuid4().hex[:10],
        "text": body[:2000],
        "tags": [str(t).strip() for t in (tags or []) if str(t).strip()][:12],
        "createdAt": int(time.time()),
    }
    rows.insert(0, note)
    _save(rows[:200])
    return {"ok": True, "note": note, "total": len(rows)}


@tool(
    name="list_notes",
    description="List recent local notes.",
    parameters={
        "type": "object",
        "properties": {"limit": {"type": "integer", "default": 10}},
    },
)
def list_notes(limit: int = 10):
    n = max(1, min(int(limit or 10), 50))
    rows = _load()[:n]
    return {"ok": True, "notes": rows, "total": len(_load())}


@tool(
    name="search_notes",
    description="Search local notes by substring.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
        "required": ["query"],
    },
)
def search_notes(query: str = "", limit: int = 10):
    q = str(query or "").strip().lower()
    n = max(1, min(int(limit or 10), 50))
    if not q:
        return {"ok": False, "error": "empty query"}
    hits = []
    for row in _load():
        blob = f"{row.get('text', '')} {' '.join(row.get('tags') or [])}".lower()
        if q in blob:
            hits.append(row)
        if len(hits) >= n:
            break
    return {"ok": True, "query": query, "notes": hits}


@tool(
    name="delete_note",
    description="Delete a note by id.",
    parameters={
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
)
def delete_note(id: str = ""):
    nid = str(id or "").strip()
    rows = _load()
    next_rows = [r for r in rows if str(r.get("id")) != nid]
    if len(next_rows) == len(rows):
        return {"ok": False, "error": "not found"}
    _save(next_rows)
    return {"ok": True, "id": nid, "total": len(next_rows)}


if __name__ == "__main__":
    run(Plugin(tools=[add_note, list_notes, search_notes, delete_note]))
