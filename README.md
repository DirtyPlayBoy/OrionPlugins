# OrionPlugins

SDK, CLI и примеры плагинов для **Orion**.

| | |
|---|---|
| SDK | [`sdk/python`](sdk/python) (`orion-plugin-sdk` 0.2) |
| CLI | [`cli/`](cli/) 0.4 → `pip install -e cli` → `orion-plugin` |
| Examples | [`examples/`](examples) (`hello-orion`, `dice-roller`) |
| Docs | [`docs/en`](docs/en) · [`docs/ru`](docs/ru) |
| Catalogue | [orion-registry](https://github.com/DirtyPlayBoy/orion-registry) |
| AI map | [`AGENTS.md`](AGENTS.md) |

## 5-minute plugin

```bash
pip install -e sdk/python && pip install -e cli
orion-plugin new my-tool --author "You"
# or: orion-plugin new my-copy --from hello-orion --author "You"
orion-plugin test ./my-tool --call
orion-plugin dev ./my-tool
orion-plugin call hello --plugin my-tool
orion-plugin init-ci ./my-tool && orion-plugin pack ./my-tool
orion-plugin submit ./my-tool --repo You/my-tool
```

В Orion без CLI: **Плагины → Каталог → Hello Orion → Установить пример**, затем клик по tool ▶.

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
