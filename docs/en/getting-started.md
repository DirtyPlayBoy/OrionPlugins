# Getting started

## Option A — one-click example

In Orion: **Plugins → Catalog → Hello Orion → Install example**.

No developer mode needed.

## Option B — your own plugin in 5 minutes

```bash
pip install -e sdk/python
pip install -e cli
orion-plugin new hello --author "You" --dir ./hello
orion-plugin test ./hello --call
orion-plugin dev ./hello              # Orion running
```

Or manually: **Plugins → Development** → developer mode → load folder.

See [cli.md](cli.md), [manifest.md](manifest.md), [publishing.md](publishing.md).
