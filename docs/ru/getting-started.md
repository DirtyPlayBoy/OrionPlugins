# С чего начать

## Вариант A — пример одной кнопкой

В Orion: **Плагины → Каталог → Hello Orion → Установить пример**.

Режим разработчика не нужен.

## Вариант B — свой плагин за 5 минут

```bash
pip install -e sdk/python
pip install -e cli
orion-plugin new hello --author "Вы" --dir ./hello
orion-plugin test ./hello --call
orion-plugin dev ./hello              # Orion запущен
```

Или вручную: **Плагины → Разработка** → режим разработчика → путь → **Загрузить**.

См. [cli.md](cli.md), [manifest.md](manifest.md), [publishing.md](publishing.md).
