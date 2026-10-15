"""Orion plugin: secure password / PIN generator."""
from __future__ import annotations

import secrets
import string

from orion_plugin_sdk import Plugin, run, tool


@tool(
    name="generate_password",
    description="Generate a strong random password.",
    parameters={
        "type": "object",
        "properties": {
            "length": {"type": "integer", "default": 16, "description": "8–64"},
            "digits": {"type": "boolean", "default": True},
            "symbols": {"type": "boolean", "default": True},
            "uppercase": {"type": "boolean", "default": True},
        },
    },
)
def generate_password(
    length: int = 16,
    digits: bool = True,
    symbols: bool = True,
    uppercase: bool = True,
):
    n = max(8, min(int(length or 16), 64))
    alphabet = string.ascii_lowercase
    if uppercase:
        alphabet += string.ascii_uppercase
    if digits:
        alphabet += string.digits
    if symbols:
        alphabet += "!@#$%^&*_-+=?"
    if not alphabet:
        alphabet = string.ascii_letters
    pwd = "".join(secrets.choice(alphabet) for _ in range(n))
    return {"password": pwd, "length": n}


@tool(
    name="generate_pin",
    description="Generate a numeric PIN code.",
    parameters={
        "type": "object",
        "properties": {"length": {"type": "integer", "default": 4}},
    },
)
def generate_pin(length: int = 4):
    n = max(4, min(int(length or 4), 12))
    pin = "".join(secrets.choice(string.digits) for _ in range(n))
    return {"pin": pin, "length": n}


if __name__ == "__main__":
    run(Plugin(tools=[generate_password, generate_pin]))
