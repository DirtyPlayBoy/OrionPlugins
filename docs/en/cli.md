# CLI `orion-plugin`

```bash
pip install -e cli          # → orion-plugin command
orion-plugin --version
orion-plugin templates
orion-plugin doctor
orion-plugin new my-tool --author "You" --template tool
orion-plugin check . --strict
orion-plugin test . --call
orion-plugin dev .                    # Orion on :4310
orion-plugin dev . --watch            # hot reload
orion-plugin init-ci .
orion-plugin pack .
orion-plugin submit . --repo Owner/Name
```

Without install: `python cli/orion_plugin.py …`

Inside the Orion tree:

```bash
python -m orion_backend.modules.plugins.devtools …
```

| Command | Purpose |
|---------|---------|
| `new` | Scaffold (`tool` / `ui-page` / `blank`) |
| `check` | Validate `plugin.toml` |
| `test` | Mock host conformance |
| `dev` | Load folder into running Orion (`--watch`) |
| `init-ci` | Write GitHub Actions release workflow |
| `pack` | Build `.orionplugin` + sha256 |
| `submit` | Generate orion-registry PR files |
| `doctor` | Environment diagnostics (+ Orion ping) |
| `templates` | List templates |
