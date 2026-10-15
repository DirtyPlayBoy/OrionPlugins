# Publishing

```bash
python cli/orion_plugin.py pack .
python cli/orion_plugin.py submit . --repo Owner/your-plugin
```

1. GitHub Release + upload `.orionplugin`
2. Copy `submit/plugins/<id>/` into [orion-registry](https://github.com/DirtyPlayBoy/orion-registry)
3. `python tools/build-index.py && python tools/validate.py`
4. Open a PR

Never invent digests. Never commit binaries to the registry.
