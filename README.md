# OrionPlugins

SDK, CLI и примеры плагинов для **Orion**.

| | |
|---|---|
| SDK | [`sdk/python`](sdk/python) (`orion-plugin-sdk` 0.2) |
| CLI | [`cli/orion_plugin.py`](cli/orion_plugin.py) |
| Examples | [`examples/`](examples) |
| Docs | [`docs/en`](docs/en) · [`docs/ru`](docs/ru) |
| Catalogue | [orion-registry](https://github.com/DirtyPlayBoy/orion-registry) |
| AI map | [`AGENTS.md`](AGENTS.md) |

## 5-minute plugin

```bash
pip install -e sdk/python
python cli/orion_plugin.py new my-tool --author "You"
python cli/orion_plugin.py test ./my-tool --call
# Orion → Plugins → Development → Load folder
python cli/orion_plugin.py pack ./my-tool
python cli/orion_plugin.py submit ./my-tool --repo You/my-tool
```

## Architecture

```
Orion backend ──spawn──► plugin process
       ▲                      │
       │   JSON-RPC /rpc      │
       └────── loopback ──────┘
```

Tools appear as `plugin__<id>__<tool>`. Host pages unlock via `[[ui.contributions]]` + `host_page`.

## License

MIT
