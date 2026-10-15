# CLI `orion-plugin`

```bash
pip install -e cli          # → команда orion-plugin
orion-plugin --version
orion-plugin templates
orion-plugin examples
orion-plugin doctor
orion-plugin new my-tool --author "Вы" --template tool
orion-plugin new my-copy --from hello-orion --author "Вы"
orion-plugin check . --strict
orion-plugin test . --call
orion-plugin dev .                    # Orion на :4310
orion-plugin dev . --watch            # hot reload
orion-plugin call hello --plugin my-tool
orion-plugin init-ci .
orion-plugin pack .
orion-plugin submit . --repo Owner/Name
```

Без установки: `python cli/orion_plugin.py …`

Алиас внутри Orion:

```bash
python -m orion_backend.modules.plugins.devtools …
```

## Команды

| Команда | Назначение |
|---------|------------|
| `new` | Scaffold (`tool` / `ui-page` / `blank`) или `--from <example>` |
| `examples` | Список официальных примеров |
| `check` | Валидация `plugin.toml` |
| `test` | Mock-host: ready + health + tools |
| `dev` | Загрузить папку в запущенный Orion (`--watch`) |
| `call` | Вызвать tool у running-плагина |
| `init-ci` | GitHub Actions workflow для релиза |
| `pack` | `.orionplugin` + sha256 в `.dist/` |
| `submit` | Файлы PR для orion-registry в `submit/` |
| `doctor` | Диагностика окружения (+ ping Orion) |
| `templates` | Список шаблонов |
