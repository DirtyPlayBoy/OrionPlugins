"""Example Orion plugin: dice roller."""
from __future__ import annotations

import random
import sys
from pathlib import Path

# Allow running without install: resolve sibling SDK
_SDK = Path(__file__).resolve().parents[2] / "sdk" / "python"
if _SDK.is_dir() and str(_SDK) not in sys.path:
    sys.path.insert(0, str(_SDK))

from orion_plugin_sdk import Plugin, run, tool  # noqa: E402


@tool(
    name="roll_dice",
    description="Roll an N-sided die and return the value.",
    parameters={
        "type": "object",
        "properties": {
            "sides": {
                "type": "integer",
                "default": 6,
                "description": "Number of sides (minimum 2).",
            },
            "count": {
                "type": "integer",
                "default": 1,
                "description": "How many dice to roll.",
            },
        },
    },
)
def roll_dice(sides: int = 6, count: int = 1):
    sides = max(2, int(sides or 6))
    count = max(1, min(int(count or 1), 40))
    rolls = [random.randint(1, sides) for _ in range(count)]
    return {"sides": sides, "rolls": rolls, "total": sum(rolls)}


@tool(
    name="flip_coin",
    description="Flip a coin — heads or tails.",
    parameters={"type": "object", "properties": {}},
)
def flip_coin():
    return {"result": random.choice(["heads", "tails"])}


if __name__ == "__main__":
    run(Plugin(tools=[roll_dice, flip_coin]))
