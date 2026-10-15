#!/usr/bin/env python3
"""orion-plugin — scaffold, check, test, pack, submit for Orion plugins."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

__version__ = "0.4.0"
_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED = {"orion-stt", "orion-tts", "orion-core", "orion-agent", "orion-voice"}
KNOWN_CAPS = {
    "tools", "tts", "stt", "ai_provider", "client", "actions", "triggers",
    "ui_contributions", "event_handlers", "dom_access",
}

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES = {
    "tool": {
        "desc": "Assistant tools (default)",
        "caps": "tools = true\n",
        "main": '''\
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
''',
    },
    "ui-page": {
        "desc": "Unlock a host page (host_page) + optional tool",
        "caps": "tools = true\nui_contributions = true\n",
        "extra_toml": '''
[[ui.contributions]]
id = "{plugin_id}-page"
slot = "page.custom"
host_page = "pageCustom_{snake}"
label = "{name}"
icon = "puzzle"
transparent = true
''',
        "main": '''\
from orion_plugin_sdk import Plugin, tool, run

@tool(name="{tool_name}_ping", description="Ping {name}.", parameters={{"type":"object","properties":{{}}}})
def {fn_name}_ping():
    return {{"ok": True, "plugin": "{plugin_id}"}}

UI = [{{
    "id": "{plugin_id}-page",
    "slot": "page.custom",
    "host_page": "pageCustom_{snake}",
    "label": "{name}",
    "icon": "puzzle",
    "transparent": True,
}}]

if __name__ == "__main__":
    run(Plugin(tools=[{fn_name}_ping], ui_contributions=UI))
''',
    },
    "blank": {
        "desc": "Minimal process (health only)",
        "caps": "",
        "main": '''\
from orion_plugin_sdk import Plugin, run

if __name__ == "__main__":
    run(Plugin())
''',
    },
}

TOML_TMPL = '''\
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
{caps}
[permissions]
{extra_toml}'''

README_TMPL = '''\
# {name}

Orion plugin (`{plugin_id}`), template `{template}`.

## Develop

```bash
pip install -e <OrionPlugins>/sdk/python
orion-plugin check .
orion-plugin test .
```

## Load in Orion

One-shot (Orion must be running):

```bash
orion-plugin dev .
```

Or manually: **Плагины → Разработка** → режим разработчика → путь → **Загрузить**:

```
{folder}
```

## Publish

```bash
orion-plugin init-ci .
orion-plugin pack .
orion-plugin submit . --repo YourName/your-plugin --tag {plugin_id}-v0.1.0
```

Откройте PR в https://github.com/DirtyPlayBoy/orion-registry с файлами из `submit/`.
'''


def _die(msg: str, code: int = 1) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return code


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _slug(name: str) -> str:
    s = name.strip().lower().replace(" ", "-").replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _read_toml_simple(path: Path) -> Dict[str, Any]:
    """Minimal TOML read via tomllib when available."""
    try:
        import tomllib
    except ImportError:
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _find_sdk_path() -> Optional[Path]:
    here = Path(__file__).resolve()
    candidates: List[Path] = []
    # OrionPlugins/cli/orion_plugin.py → ../sdk/python
    candidates.append(here.parents[1] / "sdk" / "python")
    # Orion tree: …/modules/plugins/devtools → …/orion_backend/vendor
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "vendor")
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / "vendor")
    env = os.environ.get("ORION_PLUGIN_SDK", "").strip()
    if env:
        candidates.insert(0, Path(env))
    for cand in candidates:
        if (cand / "orion_plugin_sdk").is_dir():
            return cand
    return None


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _example_roots() -> List[Path]:
    roots: List[Path] = []
    here = Path(__file__).resolve()
    # OrionPlugins/cli → ../examples
    roots.append(here.parents[1] / "examples")
    # Orion tree: …/plugins/devtools → …/app/plugins-examples
    roots.append(here.parents[4] / "plugins-examples")
    for env_key in ("ORION_PLUGINS_ROOT", "ORIONPLUGINS"):
        val = os.environ.get(env_key, "").strip()
        if val:
            roots.append(Path(val) / "examples")
    sibling = Path.home() / "Scripts" / "GITHUB" / "OrionPlugins" / "examples"
    roots.append(sibling)
    out: List[Path] = []
    seen = set()
    for r in roots:
        try:
            key = str(r.resolve()).lower()
        except Exception:
            key = str(r).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _find_example(example_id: str) -> Optional[Path]:
    want = _slug(example_id)
    for root in _example_roots():
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if not child.is_dir() or not (child / "plugin.toml").is_file():
                continue
            if child.name == want or child.name == example_id:
                return child
            raw = _read_toml_simple(child / "plugin.toml")
            pid = str((raw.get("plugin") or {}).get("id") or "")
            if pid == want:
                return child
    return None


def cmd_new(args: argparse.Namespace) -> int:
    name = args.name.strip()
    plugin_id = _slug(args.id or name)
    if not _ID_RE.match(plugin_id):
        return _die("invalid id — lowercase letters, digits, hyphens")
    if plugin_id in RESERVED:
        return _die(f"id {plugin_id!r} is reserved")
    folder = Path(args.dir or plugin_id).expanduser().resolve()
    if folder.exists() and any(folder.iterdir()) and not args.force:
        return _die(f"folder not empty: {folder} (pass --force)")

    author = args.author or os.environ.get("ORION_PLUGIN_AUTHOR") or "Unknown"
    description = args.description or f"{name} — Orion plugin"
    from_example = (args.from_example or "").strip()

    if from_example:
        src = _find_example(from_example)
        if not src:
            known = []
            for root in _example_roots():
                if root.is_dir():
                    known.extend(c.name for c in root.iterdir() if (c / "plugin.toml").is_file())
            return _die(
                f"example {from_example!r} not found. Known: {', '.join(sorted(set(known)) or ['(none)'])}"
            )
        folder.mkdir(parents=True, exist_ok=True)
        skip = {".git", ".venv", "__pycache__", ".dist", "submit", "node_modules"}
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            if any(p in skip for p in path.parts):
                continue
            rel = path.relative_to(src)
            dest = folder / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = path.read_text(encoding="utf-8", errors="replace")
            # Best-effort rewrite of identity fields
            text = text.replace(from_example, plugin_id)
            src_raw = _read_toml_simple(src / "plugin.toml")
            src_id = str((src_raw.get("plugin") or {}).get("id") or from_example)
            src_name = str((src_raw.get("plugin") or {}).get("name") or "")
            if src_id and src_id != plugin_id:
                text = text.replace(src_id, plugin_id)
            if src_name and src_name != name:
                text = text.replace(src_name, name)
            dest.write_text(text, encoding="utf-8")
        # Force plugin.toml identity
        toml_path = folder / "plugin.toml"
        if toml_path.is_file():
            body = toml_path.read_text(encoding="utf-8")
            body = re.sub(r'(?m)^id\s*=\s*".*"', f'id = "{plugin_id}"', body, count=1)
            body = re.sub(r'(?m)^name\s*=\s*".*"', f'name = "{name}"', body, count=1)
            body = re.sub(r'(?m)^author\s*=\s*".*"', f'author = "{author.replace(chr(34), chr(39))}"', body, count=1)
            if args.description:
                body = re.sub(
                    r'(?m)^description\s*=\s*".*"',
                    f'description = "{description.replace(chr(34), chr(39))}"',
                    body,
                    count=1,
                )
            toml_path.write_text(body, encoding="utf-8")
        print(f"created {folder}")
        print(f"from={from_example}")
        print(folder)
        print("next: orion-plugin check . && orion-plugin test . --call && orion-plugin dev .")
        return 0

    template = (args.template or "tool").strip().lower()
    if template not in TEMPLATES:
        return _die(f"unknown template {template!r}; choose: {', '.join(TEMPLATES)}")
    folder.mkdir(parents=True, exist_ok=True)

    tool_name = plugin_id.replace("-", "_")
    snake = tool_name
    tmpl = TEMPLATES[template]
    caps = tmpl["caps"]
    extra = tmpl.get("extra_toml", "").format(
        plugin_id=plugin_id, name=name, snake=snake
    )
    (folder / "plugin.toml").write_text(
        TOML_TMPL.format(
            plugin_id=plugin_id,
            name=name,
            description=description.replace('"', "'"),
            author=author.replace('"', "'"),
            caps=caps,
            extra_toml=extra,
        ),
        encoding="utf-8",
    )
    (folder / "main.py").write_text(
        tmpl["main"].format(
            tool_name=tool_name,
            fn_name=tool_name,
            description=description.replace('"', "'"),
            plugin_id=plugin_id,
            name=name,
            snake=snake,
        ),
        encoding="utf-8",
    )
    (folder / "README.md").write_text(
        README_TMPL.format(
            name=name, plugin_id=plugin_id, template=template, folder=folder
        ),
        encoding="utf-8",
    )
    sdk = _find_sdk_path()
    req = "# Install Orion plugin SDK\n"
    if sdk:
        req += f"pip install -e \"{sdk}\"\n"
    else:
        req += "pip install -e <path-to-OrionPlugins>/sdk/python\n"
    (folder / "requirements.txt").write_text(req, encoding="utf-8")
    (folder / ".gitignore").write_text(
        ".venv/\n__pycache__/\n*.orionplugin\nsubmit/\n.dist/\n", encoding="utf-8"
    )
    print(f"created {folder}")
    print(f"template={template}")
    print(folder)
    print("next: orion-plugin check . && orion-plugin test . --call && orion-plugin dev .")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    toml_path = folder / "plugin.toml"
    if not toml_path.is_file():
        return _die("plugin.toml missing")
    try:
        import tomllib
    except ImportError:
        return _die("Python 3.11+ required (tomllib)")
    try:
        raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _die(f"plugin.toml parse error: {exc}")

    plugin = raw.get("plugin") if isinstance(raw.get("plugin"), dict) else {}
    entry = raw.get("entry") if isinstance(raw.get("entry"), dict) else {}
    caps = raw.get("capabilities") if isinstance(raw.get("capabilities"), dict) else {}
    errors: List[str] = []

    pid = str(plugin.get("id") or "").strip()
    if not _ID_RE.match(pid):
        errors.append("plugin.id invalid")
    if pid in RESERVED:
        errors.append(f"plugin.id {pid!r} reserved")
    if not str(plugin.get("name") or "").strip():
        errors.append("plugin.name required")
    if not str(plugin.get("version") or "").strip():
        errors.append("plugin.version required")
    if not str(entry.get("command") or "").strip():
        errors.append("entry.command required")
    for k in caps:
        if k not in KNOWN_CAPS:
            errors.append(f"unknown capability: {k}")
    ui = raw.get("ui") if isinstance(raw.get("ui"), dict) else {}
    contribs = ui.get("contributions") if isinstance(ui, dict) else None
    if isinstance(contribs, list) and contribs and not caps.get("ui_contributions"):
        errors.append("[[ui.contributions]] present but capabilities.ui_contributions is false")

    main = folder / "main.py"
    cmd = str(entry.get("command") or "")
    args_list = entry.get("args") if isinstance(entry.get("args"), list) else []
    if cmd == "python" and args_list and not (folder / str(args_list[0])).is_file():
        errors.append(f"entry file missing: {args_list[0]}")
    if not main.is_file() and cmd == "python":
        if not any((folder / str(a)).is_file() for a in args_list if isinstance(a, str)):
            errors.append("no entry .py found")

    warnings: List[str] = []
    runtimes = entry.get("runtimes") or []
    if not runtimes:
        warnings.append('entry.runtimes empty — declare ["python"] or ["node"]')
    if not (folder / "README.md").is_file():
        warnings.append("README.md missing — recommended for catalogue")
    if isinstance(contribs, list) and caps.get("ui_contributions"):
        for c in contribs:
            if isinstance(c, dict) and not (c.get("host_page") or c.get("url") or c.get("slot")):
                warnings.append(f"ui contribution {c.get('id')!r} has no host_page/url/slot")

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
        if args.strict and "runtimes" in w:
            return _die("strict: fix warnings above")
    _ok(f"{pid}@{plugin.get('version')} caps={sorted(k for k,v in caps.items() if v)}")
    return 0


def cmd_pack(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    if cmd_check(argparse.Namespace(path=str(folder), strict=False)) != 0:
        return 1
    raw = _read_toml_simple(folder / "plugin.toml")
    plugin = raw.get("plugin") or {}
    pid = str(plugin.get("id") or "plugin")
    ver = str(plugin.get("version") or "0.0.0")
    out_dir = Path(args.out or (folder / ".dist")).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pid}-{ver}-windows-x64.orionplugin"

    skip = {".git", ".venv", "__pycache__", "node_modules", ".dist", "submit"}
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip for part in path.parts):
                continue
            if path.suffix in {".orionplugin", ".pyc"}:
                continue
            zf.write(path, arcname=str(path.relative_to(folder)).replace("\\", "/"))

    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    size = out_path.stat().st_size
    meta = {"id": pid, "version": ver, "file": str(out_path), "sha256": digest, "size": size}
    (out_dir / f"{pid}-{ver}.sha256").write_text(f"{digest}  {out_path.name}\n", encoding="utf-8")
    (out_dir / f"{pid}-{ver}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _ok(f"packed {out_path}")
    print(f"sha256={digest}")
    print(f"size={size}")
    print(out_path)
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    if cmd_check(argparse.Namespace(path=str(folder), strict=True)) != 0:
        return 1
    raw = _read_toml_simple(folder / "plugin.toml")
    plugin = raw.get("plugin") or {}
    caps = raw.get("capabilities") or {}
    pid = str(plugin.get("id"))
    ver = str(plugin.get("version"))
    repo = (args.repo or "").strip()
    if not repo or "/" not in repo:
        return _die("--repo Owner/Name required (GitHub repository of the plugin)")
    tag = (args.tag or f"{pid}-v{ver}").strip()
    filename = f"{pid}-{ver}-windows-x64.orionplugin"
    url = args.url or f"https://github.com/{repo}/releases/download/{tag}/{filename}"

    # Prefer existing pack meta
    meta_path = folder / ".dist" / f"{pid}-{ver}.meta.json"
    sha256 = args.sha256 or ""
    size = args.size or 0
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        sha256 = sha256 or meta.get("sha256") or ""
        size = size or int(meta.get("size") or 0)
    if not sha256:
        pack_file = folder / ".dist" / filename
        if pack_file.is_file():
            sha256 = hashlib.sha256(pack_file.read_bytes()).hexdigest()
            size = pack_file.stat().st_size
        else:
            print("WARN: no sha256 — run `orion-plugin pack .` first; writing staging entry", file=sys.stderr)

    out = Path(args.out or (folder / "submit")).expanduser().resolve()
    plug_dir = out / "plugins" / pid
    ver_dir = plug_dir / "versions"
    plug_dir.mkdir(parents=True, exist_ok=True)
    ver_dir.mkdir(parents=True, exist_ok=True)

    plugin_json = {
        "id": pid,
        "name": plugin.get("name"),
        "summary": plugin.get("description") or "",
        "author": plugin.get("author") or "",
        "official": False,
        "license": plugin.get("license") or "MIT",
        "repository": f"https://github.com/{repo}",
        "homepage": f"https://github.com/{repo}",
        "capabilities": [k for k, v in caps.items() if v],
    }
    version_json: Dict[str, Any] = {
        "version": ver,
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "release": {
            "kind": "github_release",
            "repository": repo,
            "tag": tag,
        },
    }
    if sha256:
        version_json["artifacts"] = [
            {
                "platform": "windows-x64",
                "filename": filename,
                "url": url,
                "sha256": sha256,
                "size": size,
            }
        ]
        version_json["download_url"] = url
        version_json["sha256"] = sha256
        version_json["size"] = size
    else:
        version_json["staging"] = True
        version_json["staging_reason"] = "Run orion-plugin pack and re-submit with digests"
        version_json["artifacts"] = []

    (plug_dir / "plugin.json").write_text(
        json.dumps(plugin_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ver_dir / f"{ver}.json").write_text(
        json.dumps(version_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pr = out / "PULL_REQUEST.md"
    pr.write_text(
        f"""# Catalogue submission: `{pid}` {ver}

## Checklist
- [ ] `.orionplugin` uploaded to GitHub Release `{tag}`
- [ ] SHA-256 matches `plugins/{pid}/versions/{ver}.json`
- [ ] `plugin.id` is not reserved
- [ ] Capabilities match the package

## Files to copy into orion-registry
- `plugins/{pid}/plugin.json`
- `plugins/{pid}/versions/{ver}.json`

Then regenerate `registry/v1/index.json` (`python tools/build-index.py`) and open a PR.
""",
        encoding="utf-8",
    )
    _ok(f"submit bundle written to {out}")
    print(out)
    print(f"download_url={url}")
    if sha256:
        print(f"sha256={sha256}")
    print("")
    print("Next:")
    print(f"  1. gh release create {tag} .dist/{filename} --repo {repo} --title {tag}")
    print(f"  2. Copy {out / 'plugins' / pid} into a fork of DirtyPlayBoy/orion-registry")
    print("  3. In orion-registry: python tools/build-index.py && python tools/validate.py")
    print("  4. Open a PR to DirtyPlayBoy/orion-registry")
    return 0


def _rpc(port: int, token: str, method: str, params: Optional[dict] = None, timeout: float = 10.0) -> Any:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": "1", "method": method, "params": params or {}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = Request(
        f"http://127.0.0.1:{port}/rpc",
        data=body,
        headers={"Content-Type": "application/json", "x-plugin-token": token},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("error"):
        raise RuntimeError(payload["error"])
    return payload.get("result")


def cmd_test(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    if cmd_check(argparse.Namespace(path=str(folder), strict=False)) != 0:
        return 1
    raw = _read_toml_simple(folder / "plugin.toml")
    entry = raw.get("entry") or {}
    plugin = raw.get("plugin") or {}
    caps = raw.get("capabilities") or {}
    cmd = str(entry.get("command") or "python")
    entry_args = [str(a) for a in (entry.get("args") or ["main.py"])]

    # Fake host port (unused by MVP plugins except for --host-addr)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        host_port = s.getsockname()[1]

    token = "test-token-" + hashlib.sha1(str(time.time()).encode()).hexdigest()[:8]
    pid = str(plugin.get("id") or "plugin")
    env = os.environ.copy()
    sdk = _find_sdk_path()
    if sdk:
        env["PYTHONPATH"] = str(sdk) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    env["ORION_PLUGIN_CAPABILITIES"] = ",".join(k for k, v in caps.items() if v)

    if cmd in {"python", "python3"}:
        exe = sys.executable
        argv = [exe] + entry_args
    else:
        argv = [cmd] + entry_args
    argv += [
        f"--host-addr=127.0.0.1:{host_port}",
        f"--plugin-id={pid}",
        f"--auth-token={token}",
    ]

    proc = subprocess.Popen(
        argv,
        cwd=str(folder),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    port = 0
    lines: List[str] = []
    deadline = time.time() + 20

    def drain(stream, bucket: List[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                if not line:
                    break
                bucket.append(line.rstrip())
        except Exception:
            pass

    out_lines: List[str] = []
    err_lines: List[str] = []
    threading.Thread(target=drain, args=(proc.stdout, out_lines), daemon=True).start()
    threading.Thread(target=drain, args=(proc.stderr, err_lines), daemon=True).start()

    try:
        while time.time() < deadline:
            for line in list(out_lines):
                if line.startswith("ORION_PLUGIN_READY") and "port=" in line:
                    try:
                        port = int(line.split("port=", 1)[1].strip().split()[0])
                    except Exception:
                        pass
            if port:
                break
            if proc.poll() is not None:
                print("\n".join(out_lines[-10:] + err_lines[-10:]), file=sys.stderr)
                return _die(f"process exited before ready (code {proc.returncode})")
            time.sleep(0.05)
        else:
            proc.kill()
            return _die("ready timeout — need ORION_PLUGIN_READY port=N within 20s")

        health = _rpc(port, token, "health_check")
        _ok(f"health_check {health}")
        if caps.get("tools"):
            tools = _rpc(port, token, "list_tools")
            n = len(tools) if isinstance(tools, list) else 0
            _ok(f"list_tools count={n}")
            if n and args.call:
                name = tools[0].get("name") if isinstance(tools[0], dict) else None
                if name:
                    result = _rpc(port, token, "call_tool", {"name": name, "arguments": {}})
                    _ok(f"call_tool {name} -> {json.dumps(result, ensure_ascii=False)[:200]}")
        if caps.get("ui_contributions"):
            try:
                ui = _rpc(port, token, "list_ui_contributions")
                _ok(f"list_ui_contributions count={len(ui) if isinstance(ui, list) else 0}")
            except Exception as exc:
                print(f"WARN: list_ui_contributions: {exc}", file=sys.stderr)
        _ok("conformance passed")
        return 0
    finally:
        try:
            if port:
                _rpc(port, token, "shutdown", timeout=2)
        except Exception:
            pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()


def cmd_templates(_args: argparse.Namespace) -> int:
    for key, meta in TEMPLATES.items():
        print(f"{key:12} {meta['desc']}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"orion-plugin {__version__}")
    print(f"python {sys.version.split()[0]} ({sys.executable})")
    sdk = _find_sdk_path()
    print(f"sdk_path {sdk or '(not found next to cli)'}")
    if sdk:
        sys.path.insert(0, str(sdk))
        try:
            import orion_plugin_sdk

            print(f"sdk_version {orion_plugin_sdk.__version__}")
        except Exception as exc:
            print(f"sdk_import FAIL: {exc}")
    try:
        import tomllib  # noqa: F401

        print("tomllib ok")
    except ImportError:
        print("tomllib FAIL — need Python 3.11+")
    host = (args.host or os.environ.get("ORION_HOST") or "http://127.0.0.1:4310").rstrip("/")
    try:
        with urlopen(f"{host}/api/plugins/settings", timeout=2) as resp:
            print(f"orion_host {host} ok ({resp.status})")
    except Exception as exc:
        print(f"orion_host {host} unreachable ({exc})")
    if args.path:
        return cmd_check(argparse.Namespace(path=args.path, strict=True))
    return 0


def _orion_api(host: str, method: str, path: str, body: Optional[dict] = None, timeout: float = 30.0) -> Any:
    url = host.rstrip("/") + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def cmd_dev(args: argparse.Namespace) -> int:
    """Load (and optionally watch) a plugin folder into a running Orion."""
    folder = Path(args.path or ".").expanduser().resolve()
    if not (folder / "plugin.toml").is_file():
        return _die(f"plugin.toml missing in {folder}")
    if cmd_check(argparse.Namespace(path=str(folder), strict=False)) != 0:
        return 1
    host = (args.host or os.environ.get("ORION_HOST") or "http://127.0.0.1:4310").rstrip("/")
    try:
        result = _orion_api(
            host,
            "POST",
            "/api/plugins/dev/load",
            {
                "folder": str(folder),
                "enableDeveloperMode": True,
                "source": "sideloaded",
            },
        )
    except Exception as exc:
        return _die(
            f"cannot reach Orion at {host}: {exc}\n"
            "Start Orion (Запуск Orion.bat) and retry."
        )
    plugin = result.get("plugin") if isinstance(result, dict) else None
    pid = (plugin or {}).get("id") if isinstance(plugin, dict) else "?"
    _ok(f"loaded {pid} into {host}")
    if not args.watch:
        print(folder)
        return 0

    _ok(f"watching {folder} (Ctrl+C to stop)")
    mtimes: Dict[str, float] = {}

    def snapshot() -> Dict[str, float]:
        out: Dict[str, float] = {}
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            if any(p in {".git", ".venv", "__pycache__", ".dist", "submit"} for p in path.parts):
                continue
            if path.suffix in {".pyc", ".orionplugin"}:
                continue
            try:
                out[str(path)] = path.stat().st_mtime
            except OSError:
                pass
        return out

    mtimes = snapshot()
    try:
        while True:
            time.sleep(max(0.4, float(args.interval or 1.0)))
            now = snapshot()
            if now != mtimes:
                mtimes = now
                print("change detected — reloading…")
                try:
                    _orion_api(
                        host,
                        "POST",
                        "/api/plugins/dev/load",
                        {
                            "folder": str(folder),
                            "enableDeveloperMode": True,
                            "source": "sideloaded",
                        },
                    )
                    _ok(f"reloaded {pid}")
                except Exception as exc:
                    print(f"WARN: reload failed: {exc}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nstopped watching")
        return 0


def cmd_examples(_args: argparse.Namespace) -> int:
    rows: List[Tuple[str, str, str]] = []
    seen = set()
    for root in _example_roots():
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if not child.is_dir() or not (child / "plugin.toml").is_file():
                continue
            raw = _read_toml_simple(child / "plugin.toml")
            plugin = raw.get("plugin") or {}
            pid = str(plugin.get("id") or child.name)
            if pid in seen:
                continue
            seen.add(pid)
            rows.append((pid, str(plugin.get("name") or pid), str(child)))
    if not rows:
        print("(no examples found — clone DirtyPlayBoy/OrionPlugins or set ORION_PLUGINS_ROOT)")
        return 0
    for pid, name, path in rows:
        print(f"{pid:20} {name}")
        print(f"  {path}")
    print("")
    print("Install in Orion: Catalog -> Install example")
    print("Clone: orion-plugin new my-copy --from hello-orion --author You")
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    host = (args.host or os.environ.get("ORION_HOST") or "http://127.0.0.1:4310").rstrip("/")
    tool = (args.tool or "").strip()
    if not tool:
        return _die("tool name required (e.g. hello or plugin__hello-orion__hello)")
    arguments: Dict[str, Any] = {}
    if args.args_json:
        try:
            arguments = json.loads(args.args_json)
        except Exception as exc:
            return _die(f"invalid --args JSON: {exc}")
    if tool.startswith("plugin__"):
        body: Dict[str, Any] = {"fullName": tool, "arguments": arguments}
    else:
        pid = (args.plugin or "").strip()
        if not pid:
            # Infer from cwd plugin.toml
            folder = Path(args.path or ".").expanduser().resolve()
            raw = _read_toml_simple(folder / "plugin.toml") if (folder / "plugin.toml").is_file() else {}
            pid = str((raw.get("plugin") or {}).get("id") or "")
        if not pid:
            return _die("pass --plugin <id> or run inside a plugin folder / use full plugin__id__tool name")
        body = {"pluginId": pid, "tool": tool, "arguments": arguments}
    try:
        result = _orion_api(host, "POST", "/api/plugins/call-tool", body)
    except Exception as exc:
        return _die(f"call failed ({host}): {exc}\nIs Orion running? Did you `orion-plugin dev .`?")
    _ok(f"tool {result.get('tool')}")
    print(json.dumps(result.get("result"), ensure_ascii=False, indent=2))
    return 0


def cmd_init_ci(args: argparse.Namespace) -> int:
    folder = Path(args.path or ".").expanduser().resolve()
    if not (folder / "plugin.toml").is_file() and not args.force:
        return _die("plugin.toml missing — run from a plugin folder (or pass --force)")
    wf_dir = folder / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    target = wf_dir / "orion-plugin-release.yml"
    if target.exists() and not args.force:
        return _die(f"{target} exists (pass --force)")
    # Simpler, reliable workflow (no nested OrionPlugins assumption)
    content = '''\
name: Orion plugin release

on:
  push:
    tags:
      - "*-v*"
  workflow_dispatch:

jobs:
  pack:
    runs-on: windows-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Fetch Orion CLI
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path .ci | Out-Null
          Invoke-WebRequest -Uri "https://raw.githubusercontent.com/DirtyPlayBoy/OrionPlugins/main/cli/orion_plugin.py" -OutFile .ci/orion_plugin.py -UseBasicParsing
      - name: Pack
        run: python .ci/orion_plugin.py pack .
      - name: Upload release asset
        uses: softprops/action-gh-release@v2
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: .dist/*.orionplugin
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'''
    target.write_text(content, encoding="utf-8")
    _ok(f"wrote {target}")
    print("Tag a release: git tag <id>-v0.1.0 && git push --tags")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="orion-plugin",
        description="Scaffold, validate, test, pack and submit Orion plugins",
    )
    p.add_argument("--version", action="version", version=f"orion-plugin {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="scaffold a plugin")
    n.add_argument("name")
    n.add_argument("--id", default="")
    n.add_argument("--dir", default="")
    n.add_argument("--author", default="")
    n.add_argument("--description", default="")
    n.add_argument("--lang", default="python")
    n.add_argument("--template", default="tool", help="tool | ui-page | blank")
    n.add_argument("--from", dest="from_example", default="", help="clone an official example (hello-orion, dice-roller)")
    n.add_argument("--force", action="store_true")
    n.set_defaults(func=cmd_new)

    c = sub.add_parser("check", help="validate plugin.toml")
    c.add_argument("path", nargs="?", default=".")
    c.add_argument("--strict", action="store_true")
    c.set_defaults(func=cmd_check)

    t = sub.add_parser("test", help="spawn plugin against mock host")
    t.add_argument("path", nargs="?", default=".")
    t.add_argument("--call", action="store_true", help="call first tool")
    t.set_defaults(func=cmd_test)

    pk = sub.add_parser("pack", help="build .orionplugin zip + sha256")
    pk.add_argument("path", nargs="?", default=".")
    pk.add_argument("--out", default="")
    pk.set_defaults(func=cmd_pack)

    s = sub.add_parser("submit", help="generate orion-registry PR files")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--repo", required=True, help="Owner/Name of plugin GitHub repo")
    s.add_argument("--tag", default="")
    s.add_argument("--url", default="")
    s.add_argument("--sha256", default="")
    s.add_argument("--size", type=int, default=0)
    s.add_argument("--out", default="")
    s.set_defaults(func=cmd_submit)

    sub.add_parser("templates", help="list scaffold templates").set_defaults(func=cmd_templates)

    d = sub.add_parser("doctor", help="environment diagnostics")
    d.add_argument("path", nargs="?", default="")
    d.add_argument("--host", default="", help="Orion HTTP base (default http://127.0.0.1:4310)")
    d.set_defaults(func=cmd_doctor)

    dv = sub.add_parser("dev", help="load plugin into running Orion (optional --watch)")
    dv.add_argument("path", nargs="?", default=".")
    dv.add_argument("--host", default="", help="Orion HTTP base")
    dv.add_argument("--watch", action="store_true", help="reload on file changes")
    dv.add_argument("--interval", type=float, default=1.0, help="watch poll seconds")
    dv.set_defaults(func=cmd_dev)

    ic = sub.add_parser("init-ci", help="write GitHub Actions release workflow")
    ic.add_argument("path", nargs="?", default=".")
    ic.add_argument("--force", action="store_true")
    ic.set_defaults(func=cmd_init_ci)

    sub.add_parser("examples", help="list official example plugins").set_defaults(func=cmd_examples)

    ca = sub.add_parser("call", help="call a tool on a running Orion plugin")
    ca.add_argument("tool", help="tool name or plugin__id__tool")
    ca.add_argument("--plugin", default="", help="plugin id when tool is short name")
    ca.add_argument("--args", dest="args_json", default="{}", help='JSON arguments, default "{}"')
    ca.add_argument("--host", default="")
    ca.add_argument("--path", default=".", help="folder to infer plugin id from plugin.toml")
    ca.set_defaults(func=cmd_call)

    args = p.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
