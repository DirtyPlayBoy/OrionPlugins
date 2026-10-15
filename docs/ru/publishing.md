# Публикация в каталог

```bash
python cli/orion_plugin.py check . --strict
python cli/orion_plugin.py test . --call
python cli/orion_plugin.py pack .
python cli/orion_plugin.py submit . --repo Owner/your-plugin
```

1. Создайте GitHub Release с тегом из вывода `submit`.
2. Загрузите `.dist/<id>-<ver>-windows-x64.orionplugin`.
3. Скопируйте `submit/plugins/<id>/` в fork [orion-registry](https://github.com/DirtyPlayBoy/orion-registry).
4. В registry: `python tools/build-index.py && python tools/validate.py`.
5. Откройте PR. Первая заявка — ручная модерация.

Не выдумывайте SHA-256. Не кладите бинарники в orion-registry.
