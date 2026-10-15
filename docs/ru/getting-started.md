# С чего начать

```bash
pip install -e sdk/python
python cli/orion_plugin.py new hello --author "Вы" --dir ./hello
python cli/orion_plugin.py test ./hello --call
```

В Orion: **Плагины → Разработка** → режим разработчика → путь к `./hello` → **Загрузить**.

См. [cli.md](cli.md), [manifest.md](manifest.md), [publishing.md](publishing.md).
