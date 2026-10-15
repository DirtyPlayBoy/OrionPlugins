"""Orion Plugin SDK (Python) — JSON-RPC loopback host for child-process plugins."""
from __future__ import annotations

import argparse
import inspect
import json
import socket
import sys
import threading
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional, get_args, get_origin

__version__ = "0.2.0"


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]


def _annotation_to_json_type(anno: Any) -> Dict[str, Any]:
    if anno is inspect.Parameter.empty or anno is None:
        return {"type": "string"}
    origin = get_origin(anno)
    if origin is list or anno is list:
        return {"type": "array", "items": {"type": "string"}}
    if origin is dict or anno is dict:
        return {"type": "object"}
    mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }
    if anno in mapping:
        return {"type": mapping[anno]}
    # Optional[T]
    args = get_args(anno)
    if args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _annotation_to_json_type(non_none[0])
    return {"type": "string"}


def schema_from_signature(fn: Callable[..., Any]) -> Dict[str, Any]:
    """Build a JSON Schema object from function type hints (best-effort)."""
    sig = inspect.signature(fn)
    props: Dict[str, Any] = {}
    required: List[str] = []
    for name, param in sig.parameters.items():
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        props[name] = _annotation_to_json_type(param.annotation)
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            props[name]["default"] = param.default
    out: Dict[str, Any] = {"type": "object", "properties": props}
    if required:
        out["required"] = required
    return out


def tool(
    name: str,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable[[Callable[..., Any]], ToolDef]:
    def deco(fn: Callable[..., Any]) -> ToolDef:
        params = parameters
        if params is None:
            try:
                params = schema_from_signature(fn)
            except Exception:
                params = {"type": "object", "properties": {}, "additionalProperties": True}
        return ToolDef(
            name=name,
            description=description or (fn.__doc__ or name).strip(),
            parameters=params,
            handler=fn,
        )

    return deco


class UiContrib:
    """Helpers for ui_contributions entries."""

    @staticmethod
    def host_page(
        contrib_id: str,
        label: str,
        host_page: str,
        *,
        icon: str = "puzzle",
        transparent: bool = True,
    ) -> Dict[str, Any]:
        return {
            "id": contrib_id,
            "slot": "page.custom",
            "label": label,
            "icon": icon,
            "host_page": host_page,
            "transparent": transparent,
        }

    @staticmethod
    def iframe_page(
        contrib_id: str,
        label: str,
        url: str,
        *,
        icon: str = "puzzle",
        transparent: bool = True,
    ) -> Dict[str, Any]:
        return {
            "id": contrib_id,
            "slot": "page.custom",
            "label": label,
            "icon": icon,
            "url": url,
            "transparent": transparent,
        }


@dataclass
class Plugin:
    tools: List[ToolDef] = field(default_factory=list)
    ui_contributions: List[Dict[str, Any]] = field(default_factory=list)


def parse_argv(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host-addr", default="")
    parser.add_argument("--daemon-addr", default="")
    parser.add_argument("--plugin-id", default="")
    parser.add_argument("--auth-token", default="")
    args, _unknown = parser.parse_known_args(argv if argv is not None else sys.argv[1:])
    return args


def host_base_url(argv: Optional[List[str]] = None) -> str:
    """Return http://127.0.0.1:<port> of the Orion backend from spawn args."""
    args = parse_argv(argv)
    addr = (args.host_addr or args.daemon_addr or "127.0.0.1:4310").strip()
    if not addr.startswith("http"):
        addr = "http://" + addr
    return addr.rstrip("/")


def host_http(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    *,
    base: Optional[str] = None,
    timeout: float = 20.0,
) -> Any:
    """Call Orion backend HTTP API from inside a plugin (loopback)."""
    root = (base or host_base_url()).rstrip("/")
    data = None
    headers = {"Accept": "application/json", "User-Agent": f"orion-plugin-sdk/{__version__}"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(root + path, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise RuntimeError(f"host_http {method} {path} → HTTP {exc.code}: {detail[:400]}") from exc


def _call_tool(tdef: ToolDef, arguments: Dict[str, Any]) -> Any:
    args = dict(arguments or {})
    sig = inspect.signature(tdef.handler)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return tdef.handler(**args)
    allowed = set(sig.parameters.keys())
    return tdef.handler(**{k: v for k, v in args.items() if k in allowed})


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run(plugin: Plugin, argv: Optional[List[str]] = None) -> None:
    args = parse_argv(argv)
    token = str(args.auth_token or "").strip()
    plugin_id = str(args.plugin_id or "").strip()
    port = _pick_free_port()
    tools_by_name = {t.name: t for t in (plugin.tools or [])}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *a: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/rpc", "/"}:
                self.send_error(404)
                return
            got = self.headers.get("x-plugin-token") or ""
            if token and got != token:
                self._json(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "unauthorized"}},
                    401,
                )
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                req = json.loads(raw.decode("utf-8"))
            except Exception:
                self._json(
                    {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}},
                    400,
                )
                return
            req_id = req.get("id")
            method = str(req.get("method") or "")
            params = req.get("params") if isinstance(req.get("params"), dict) else {}
            try:
                result = self._dispatch(method, params)
                self._json({"jsonrpc": "2.0", "id": req_id, "result": result})
            except Exception as exc:
                sys.stderr.write(f"[plugin] {method} error: {exc}\n")
                sys.stderr.flush()
                self._json(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32000,
                            "message": str(exc),
                            "data": traceback.format_exc()[-800:],
                        },
                    }
                )

        def _dispatch(self, method: str, params: Dict[str, Any]) -> Any:
            if method == "health_check":
                return {
                    "ok": True,
                    "plugin_id": plugin_id,
                    "sdk": f"python/{__version__}",
                    "tools": list(tools_by_name.keys()),
                }
            if method == "shutdown":
                threading.Thread(target=lambda: (server.shutdown()), daemon=True).start()
                return {"ok": True}
            if method == "list_tools":
                return [
                    {"name": t.name, "description": t.description, "parameters": t.parameters}
                    for t in tools_by_name.values()
                ]
            if method == "call_tool":
                name = str(params.get("name") or "")
                tdef = tools_by_name.get(name)
                if not tdef:
                    raise RuntimeError(f"unknown tool: {name}")
                return _call_tool(
                    tdef,
                    params.get("arguments") if isinstance(params.get("arguments"), dict) else {},
                )
            if method == "list_ui_contributions":
                return list(plugin.ui_contributions or [])
            raise RuntimeError(f"UNIMPLEMENTED: {method}")

        def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    # Host parser keys on "ORION_PLUGIN_READY" + "port="; extra fields are ignored.
    ready = f"ORION_PLUGIN_READY port={port}"
    if plugin_id:
        ready += f" plugin_id={plugin_id}"
    ready += f" tools={len(tools_by_name)}\n"
    sys.stdout.write(ready)
    sys.stdout.flush()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = [
    "Plugin",
    "tool",
    "run",
    "ToolDef",
    "UiContrib",
    "host_http",
    "host_base_url",
    "parse_argv",
    "schema_from_signature",
    "__version__",
]
