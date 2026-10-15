"""Orion plugin: color conversion helpers."""
from __future__ import annotations

import re

from orion_plugin_sdk import Plugin, run, tool


def _parse_hex(value: str) -> tuple[int, int, int]:
    s = str(value or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{3}", s):
        s = "".join(ch * 2 for ch in s)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        raise ValueError("expected #RGB or #RRGGBB")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


@tool(
    name="hex_to_rgb",
    description="Convert HEX color to RGB.",
    parameters={
        "type": "object",
        "properties": {"hex": {"type": "string"}},
        "required": ["hex"],
    },
)
def hex_to_rgb(hex: str = ""):
    try:
        r, g, b = _parse_hex(hex)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "hex": f"#{r:02X}{g:02X}{b:02X}", "r": r, "g": g, "b": b, "rgb": f"rgb({r}, {g}, {b})"}


@tool(
    name="rgb_to_hex",
    description="Convert RGB channels to HEX.",
    parameters={
        "type": "object",
        "properties": {
            "r": {"type": "integer"},
            "g": {"type": "integer"},
            "b": {"type": "integer"},
        },
        "required": ["r", "g", "b"],
    },
)
def rgb_to_hex(r: int = 0, g: int = 0, b: int = 0):
    rr = max(0, min(255, int(r or 0)))
    gg = max(0, min(255, int(g or 0)))
    bb = max(0, min(255, int(b or 0)))
    return {"ok": True, "hex": f"#{rr:02X}{gg:02X}{bb:02X}", "r": rr, "g": gg, "b": bb}


@tool(
    name="contrast_text",
    description="Suggest black or white text for a HEX background.",
    parameters={
        "type": "object",
        "properties": {"hex": {"type": "string"}},
        "required": ["hex"],
    },
)
def contrast_text(hex: str = ""):
    try:
        r, g, b = _parse_hex(hex)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    # Perceived luminance
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    text = "#111111" if lum > 0.55 else "#FFFFFF"
    return {"ok": True, "background": f"#{r:02X}{g:02X}{b:02X}", "text": text, "luminance": round(lum, 3)}


if __name__ == "__main__":
    run(Plugin(tools=[hex_to_rgb, rgb_to_hex, contrast_text]))
