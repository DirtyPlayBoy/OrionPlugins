"""Orion plugin: world clock / timezone helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from orion_plugin_sdk import Plugin, run, tool

ALIASES = {
    "moscow": "Europe/Moscow",
    "москва": "Europe/Moscow",
    "london": "Europe/London",
    "лондон": "Europe/London",
    "nyc": "America/New_York",
    "new_york": "America/New_York",
    "tokyo": "Asia/Tokyo",
    "токио": "Asia/Tokyo",
    "utc": "UTC",
    "berlin": "Europe/Berlin",
    "dubai": "Asia/Dubai",
}


def _zone(name: str) -> ZoneInfo:
    key = (name or "UTC").strip()
    key = ALIASES.get(key.lower().replace(" ", "_"), key)
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {name}") from exc


@tool(
    name="now_in",
    description="Current local time in a city or IANA timezone (e.g. Europe/Moscow, Tokyo).",
    parameters={
        "type": "object",
        "properties": {"timezone": {"type": "string", "default": "UTC"}},
    },
)
def now_in(timezone: str = "UTC"):
    try:
        z = _zone(timezone)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    now = datetime.now(z)
    return {
        "ok": True,
        "timezone": str(z),
        "iso": now.isoformat(timespec="seconds"),
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
        "utc_offset": now.strftime("%z"),
    }


@tool(
    name="time_diff",
    description="Hour difference between two timezones/cities.",
    parameters={
        "type": "object",
        "properties": {
            "from_tz": {"type": "string"},
            "to_tz": {"type": "string"},
        },
        "required": ["from_tz", "to_tz"],
    },
)
def time_diff(from_tz: str = "UTC", to_tz: str = "UTC"):
    try:
        a = _zone(from_tz)
        b = _zone(to_tz)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    now = datetime.now(timezone.utc)
    oa = now.astimezone(a).utcoffset()
    ob = now.astimezone(b).utcoffset()
    if oa is None or ob is None:
        return {"ok": False, "error": "offset unavailable"}
    hours = (ob - oa).total_seconds() / 3600.0
    return {"ok": True, "from": str(a), "to": str(b), "hours": hours}


if __name__ == "__main__":
    run(Plugin(tools=[now_in, time_diff]))
