"""Orion plugin: unit converter tools."""
from __future__ import annotations

from orion_plugin_sdk import Plugin, run, tool

# Base units: meter, kilogram, celsius, liter
LENGTH = {
    "m": 1.0,
    "km": 1000.0,
    "cm": 0.01,
    "mm": 0.001,
    "mi": 1609.344,
    "ft": 0.3048,
    "in": 0.0254,
    "yd": 0.9144,
}
MASS = {
    "kg": 1.0,
    "g": 0.001,
    "mg": 1e-6,
    "lb": 0.45359237,
    "oz": 0.028349523125,
    "t": 1000.0,
}
VOLUME = {
    "l": 1.0,
    "ml": 0.001,
    "m3": 1000.0,
    "gal": 3.785411784,
    "cup": 0.2365882365,
}


def _temp(value: float, fr: str, to: str) -> float:
    f = fr.lower()
    t = to.lower()
    if f == "c":
        c = value
    elif f == "f":
        c = (value - 32.0) * 5.0 / 9.0
    elif f == "k":
        c = value - 273.15
    else:
        raise ValueError("temperature from must be C/F/K")
    if t == "c":
        return c
    if t == "f":
        return c * 9.0 / 5.0 + 32.0
    if t == "k":
        return c + 273.15
    raise ValueError("temperature to must be C/F/K")


@tool(
    name="convert",
    description="Convert a value between units. Categories: length, mass, volume, temperature.",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "number"},
            "from_unit": {"type": "string", "description": "e.g. km, lb, C, gal"},
            "to_unit": {"type": "string"},
            "category": {
                "type": "string",
                "enum": ["length", "mass", "volume", "temperature", "auto"],
                "default": "auto",
            },
        },
        "required": ["value", "from_unit", "to_unit"],
    },
)
def convert(value: float = 0, from_unit: str = "", to_unit: str = "", category: str = "auto"):
    fr = str(from_unit or "").strip().lower()
    to = str(to_unit or "").strip().lower()
    cat = str(category or "auto").strip().lower()
    v = float(value or 0)

    if cat == "auto":
        if fr in LENGTH and to in LENGTH:
            cat = "length"
        elif fr in MASS and to in MASS:
            cat = "mass"
        elif fr in VOLUME and to in VOLUME:
            cat = "volume"
        elif fr in {"c", "f", "k"} and to in {"c", "f", "k"}:
            cat = "temperature"
        else:
            return {"ok": False, "error": f"cannot auto-detect category for {fr}→{to}"}

    try:
        if cat == "length":
            result = v * LENGTH[fr] / LENGTH[to]
        elif cat == "mass":
            result = v * MASS[fr] / MASS[to]
        elif cat == "volume":
            result = v * VOLUME[fr] / VOLUME[to]
        elif cat == "temperature":
            result = _temp(v, fr, to)
        else:
            return {"ok": False, "error": "unknown category"}
    except KeyError as exc:
        return {"ok": False, "error": f"unknown unit: {exc}"}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "value": v,
        "from": fr,
        "to": to,
        "category": cat,
        "result": round(float(result), 8),
    }


@tool(
    name="list_units",
    description="List supported units for a category.",
    parameters={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["length", "mass", "volume", "temperature"],
            }
        },
        "required": ["category"],
    },
)
def list_units(category: str = "length"):
    cat = str(category or "").lower()
    mapping = {
        "length": sorted(LENGTH.keys()),
        "mass": sorted(MASS.keys()),
        "volume": sorted(VOLUME.keys()),
        "temperature": ["c", "f", "k"],
    }
    return {"category": cat, "units": mapping.get(cat, [])}


if __name__ == "__main__":
    run(Plugin(tools=[convert, list_units]))
