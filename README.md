# OrionPlugins

SDK, CLI и примеры плагинов для **Orion** — AI desktop assistant.

| | |
|---|---|
| SDK (Python) | [`sdk/python`](sdk/python) |
| CLI | [`cli/orion_plugin.py`](cli/orion_plugin.py) |
| Examples | [`examples/`](examples) |
| Docs EN | [`docs/en`](docs/en) |
| Docs RU | [`docs/ru`](docs/ru) |
| Catalogue | [orion-registry](https://github.com/DirtyPlayBoy/orion-registry) |

## 5-minute plugin

```bash
python cli/orion_plugin.py new my-tool --author "Your Name" --dir ./my-tool
pip install -e sdk/python
# In Orion: Plugins → Development → enable developer mode → Load folder
```

## Architecture

```
Orion backend ──spawn──► plugin process
       ▲                      │
       │   JSON-RPC /rpc      │
       └────── loopback ──────┘
```

Manifest: `plugin.toml`. Tools appear in the agent as `plugin__<id>__<tool>`.

## License

MIT — see individual packages.
