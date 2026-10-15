# С чего начать

## Вариант A — пример одной кнопкой

В Orion: **Плагины → Каталог → Hello Orion → Установить пример**.

Режим разработчика не нужен. На карточке кликните tool ▶ для проверки.

## Вариант B — клон примера

```bash
pip install -e sdk/python && pip install -e cli
orion-plugin new my-copy --from hello-orion --author "Вы"
orion-plugin test ./my-copy --call
orion-plugin dev ./my-copy
orion-plugin call hello --plugin my-copy
```

## Вариант C — свой плагин с нуля

```bash
orion-plugin new hello --author "Вы" --dir ./hello
orion-plugin test ./hello --call
orion-plugin dev ./hello --watch
```

См. [cli.md](cli.md), [manifest.md](manifest.md), [publishing.md](publishing.md).
