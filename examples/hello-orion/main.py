"""Minimal Orion plugin — the five-minute hello world."""
from __future__ import annotations

from orion_plugin_sdk import Plugin, run, tool


@tool(name="hello", description="Greet someone by name.")
def hello(name: str = "Orion"):
    return {"message": f"Hello, {name}!", "plugin": "hello-orion"}


if __name__ == "__main__":
    run(Plugin(tools=[hello]))
