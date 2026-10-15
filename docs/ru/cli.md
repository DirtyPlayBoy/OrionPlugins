# CLI `orion-plugin`

```bash
python cli/orion_plugin.py --version
python cli/orion_plugin.py templates
python cli/orion_plugin.py doctor
python cli/orion_plugin.py new my-tool --author "Вы" --template tool
python cli/orion_plugin.py check . --strict
python cli/orion_plugin.py test . --call
python cli/orion_plugin.py pack .
python cli/orion_plugin.py submit . --repo Owner/Name
```

Алиас внутри Orion:

```bash
python -m orion_backend.modules.plugins.devtools …
```

## Команды

| Команда | Назначение |
|---------|------------|
| `new` | Scaffold (`tool` / `ui-page` / `blank`) |
| `check` | Валидация `plugin.toml` |
| `test` | Mock-host: ready + health + tools |
| `pack` | `.orionplugin` + sha256 в `.dist/` |
| `submit` | Файлы PR для orion-registry в `submit/` |
| `doctor` | Диагностика окружения |
| `templates` | Список шаблонов |
