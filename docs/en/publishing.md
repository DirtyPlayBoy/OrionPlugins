# Publishing to the catalogue

```bash
orion-plugin check . --strict
orion-plugin test . --call
orion-plugin init-ci .
orion-plugin pack .
orion-plugin submit . --repo Owner/your-plugin
```

1. Create a GitHub Release with the tag from `submit` (or the printed `gh release create …`).
2. Upload `.dist/<id>-<ver>-windows-x64.orionplugin`.
3. Copy `submit/plugins/<id>/` into a fork of [orion-registry](https://github.com/DirtyPlayBoy/orion-registry).
4. In the registry: `python tools/build-index.py && python tools/validate.py`.
5. Open a PR — first submission is human-reviewed.

Never invent digests. Never put binaries inside orion-registry.
