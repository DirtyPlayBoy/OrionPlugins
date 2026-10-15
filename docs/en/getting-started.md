# Getting started

## Option A — one-click example

In Orion: **Plugins → Catalog → Hello Orion → Install example**.

No developer mode needed. Click the tool ▶ chip on the card to smoke-test.

## Option B — clone an example

```bash
pip install -e sdk/python && pip install -e cli
orion-plugin new my-copy --from hello-orion --author "You"
orion-plugin test ./my-copy --call
orion-plugin dev ./my-copy
orion-plugin call hello --plugin my-copy
```

## Option C — from scratch

```bash
orion-plugin new hello --author "You" --dir ./hello
orion-plugin test ./hello --call
orion-plugin dev ./hello --watch
```

See [cli.md](cli.md), [manifest.md](manifest.md), [publishing.md](publishing.md).
