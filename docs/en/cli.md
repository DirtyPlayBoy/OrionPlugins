# CLI `orion-plugin`

```bash
python cli/orion_plugin.py new my-tool --author "You" --template tool
python cli/orion_plugin.py check . --strict
python cli/orion_plugin.py test . --call
python cli/orion_plugin.py pack .
python cli/orion_plugin.py submit . --repo Owner/Name
```

Inside the Orion tree:

```bash
python -m orion_backend.modules.plugins.devtools …
```

| Command | Purpose |
|---------|---------|
| `new` | Scaffold (`tool` / `ui-page` / `blank`) |
| `check` | Validate `plugin.toml` |
| `test` | Mock host conformance |
| `pack` | Build `.orionplugin` + sha256 |
| `submit` | Generate orion-registry PR files |
| `doctor` | Environment diagnostics |
