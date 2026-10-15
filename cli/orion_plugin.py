#!/usr/bin/env python3
"""Minimal orion-plugin CLI (scaffold + check)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEMPLATE_MAIN = '''\
from orion_plugin_sdk import Plugin, tool, run

@tool(
    name="{tool_name}",
    description="{description}",
    parameters={{
        "type": "object",
        "properties": {{
            "text": {{"type": "string", "description": "Input text"}},
        }},
    }},
)
def {fn_name}(text: str = ""):
    return {{"ok": True, "echo": text or "hello from {plugin_id}"}}

if __name__ == "__main__":
    run(Plugin(tools=[{fn_name}]))
'''

TEMPLATE_TOML = '''\
[plugin]
id = "{plugin_id}"
name = "{name}"
version = "0.1.0"
description = "{description}"
author = "{author}"
license = "MIT"

[entry]
command = "python"
args = ["main.py"]
cwd = "."
runtimes = ["python"]

[capabilities]
tools = true

[permissions]
'''

TEMPLATE_README = '''\
# {name}

Orion plugin scaffolded by `orion-plugin new`.

## Load in Orion

1. Enable developer mode: **Плагины → Разработка**
2. Load this folder path:
   `{folder}`
'''

_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def cmd_new(args: argparse.Namespace) -> int:
    name = args.name.strip()
    plugin_id = (args.id or name).strip().lower().replace(" ", "-").replace("_", "-")
    if not _ID_RE.match(plugin_id):
        print("invalid id — use lowercase letters, digits, hyphens", file=sys.stderr)
        return 2
    folder = Path(args.dir or plugin_id).expanduser().resolve()
    folder.mkdir(parents=True, exist_ok=True)
    author = args.author or "Unknown"
    description = args.description or f"{name} Orion plugin"
    tool_name = plugin_id.replace("-", "_")
    (folder / "plugin.toml").write_text(
        TEMPLATE_TOML.format(
            plugin_id=plugin_id,
            name=name,
            description=description,
            author=author,
        ),
        encoding="utf-8",
    )
    (folder / "main.py").write_text(
        TEMPLATE_MAIN.format(
            tool_name=tool_name,
            fn_name=tool_name,
            description=description,
            plugin_id=plugin_id,
        ),
        encoding="utf-8",
    )
    (folder / "README.md").write_text(
        TEMPLATE_README.format(name=name, folder=folder),
        encoding="utf-8",
    )
    # Drop a local copy hint for the SDK
    (folder / "REQUIREMENTS.txt").write_text(
        "# pip install -e <path-to-OrionPlugins>/sdk/python\norion-plugin-sdk>=0.1.0\n",
        encoding="utf-8",
    )
    print(f"created {folder}")
    print(folder)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    toml = folder / "plugin.toml"
    if not toml.is_file():
        print("FAIL: plugin.toml missing", file=sys.stderr)
        return 1
    text = toml.read_text(encoding="utf-8")
    if "id =" not in text or "name =" not in text or "command =" not in text:
        print("FAIL: plugin.toml missing required fields", file=sys.stderr)
        return 1
    print("OK: plugin.toml looks present")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="orion-plugin")
    p.add_argument("--version", action="version", version="orion-plugin 0.1.0")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="scaffold a plugin")
    n.add_argument("name")
    n.add_argument("--id", default="")
    n.add_argument("--dir", default="")
    n.add_argument("--author", default="")
    n.add_argument("--description", default="")
    n.add_argument("--lang", default="python")
    n.add_argument("--template", default="tool")
    n.set_defaults(func=cmd_new)

    c = sub.add_parser("check", help="validate plugin folder")
    c.add_argument("path", nargs="?", default=".")
    c.add_argument("--strict", action="store_true")
    c.set_defaults(func=cmd_check)

    args = p.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
