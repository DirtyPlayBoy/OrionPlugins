"""Orion Plugin SDK (Python) — JSON-RPC loopback host for child-process plugins."""
from __future__ import annotations

import argparse
import inspect
import json
import socket
import sys
import threading
import traceback
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional

__version__ = "0.1.0"


@dataclass
class ToolDef:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]


def tool(
    name: str,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Callable[[Callable[..., Any]], ToolDef]:
    def deco(fn: Callable[..., Any]) -> ToolDef:
        return ToolDef(
            name=name,
            description=description or (fn.__doc__ or name).strip(),
            parameters=parameters
            or {"type": "object", "properties": {}, "additionalProperties": True},
            handler=fn,
        )

    return deco


@dataclass
class Plugin:
    tools: List[ToolDef] = field(default_factory=list)


def _call_tool(tdef: ToolDef, arguments: Dict[str, Any]) -> Any:
    args = dict(arguments or {})
    sig = inspect.signature(tdef.handler)
    kwargs = {}
    for key, param in sig.parameters.items():
        if key in args:
            kwargs[key] = args[key]
        elif param.default is not inspect.Parameter.empty:
            continue
        elif param.kind in (inspect.Parameter.VAR_KEYWORD,):
            continue
        else:
            # missing required — still call and let TypeError surface
            pass
    # Pass remaining unknown keys only if **kwargs present
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return tdef.handler(**args)
    allowed = set(sig.parameters.keys())
    return tdef.handler(**{k: v for k, v in args.items() if k in allowed})


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def run(plugin: Plugin, argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host-addr", default="")
    parser.add_argument("--daemon-addr", default="")
    parser.add_argument("--plugin-id", default="")
    parser.add_argument("--auth-token", default="")
    args, _unknown = parser.parse_known_args(argv if argv is not None else sys.argv[1:])

    token = str(args.auth_token or "").strip()
    plugin_id = str(args.plugin_id or "").strip()
    port = _pick_free_port()
    tools_by_name = {t.name: t for t in (plugin.tools or [])}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *a: Any) -> None:  # silence
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path not in {"/rpc", "/"}:
                self.send_error(404)
                return
            got = self.headers.get("x-plugin-token") or ""
            if token and got != token:
                self._json({"jsonrpc": "2.0", "id": None, "error": {"code": -32001, "message": "unauthorized"}}, 401)
                return
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                req = json.loads(raw.decode("utf-8"))
            except Exception:
                self._json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}, 400)
                return
            req_id = req.get("id")
            method = str(req.get("method") or "")
            params = req.get("params") if isinstance(req.get("params"), dict) else {}
            try:
                result = self._dispatch(method, params)
                self._json({"jsonrpc": "2.0", "id": req_id, "result": result})
            except Exception as exc:
                self._json(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32000, "message": str(exc), "data": traceback.format_exc()[-800:]},
                    }
                )

        def _dispatch(self, method: str, params: Dict[str, Any]) -> Any:
            if method == "health_check":
                return {"ok": True, "plugin_id": plugin_id, "sdk": f"python/{__version__}"}
            if method == "shutdown":
                threading.Thread(target=lambda: (server.shutdown()), daemon=True).start()
                return {"ok": True}
            if method == "list_tools":
                return [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                    for t in tools_by_name.values()
                ]
            if method == "call_tool":
                name = str(params.get("name") or "")
                tdef = tools_by_name.get(name)
                if not tdef:
                    raise RuntimeError(f"unknown tool: {name}")
                return _call_tool(tdef, params.get("arguments") if isinstance(params.get("arguments"), dict) else {})
            raise RuntimeError(f"UNIMPLEMENTED: {method}")

        def _json(self, payload: Dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    # Ready line — must appear within 20s
    sys.stdout.write(f"ORION_PLUGIN_READY port={port}\n")
    sys.stdout.flush()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = ["Plugin", "tool", "run", "ToolDef", "__version__"]
