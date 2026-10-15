# orion-plugin CLI

```bash
pip install -e .
orion-plugin new my-tool --author You
orion-plugin test ./my-tool --call
orion-plugin dev ./my-tool          # Orion must be running on :4310
orion-plugin init-ci ./my-tool
orion-plugin pack ./my-tool
orion-plugin submit ./my-tool --repo You/my-tool
```

Without install:

```bash
python orion_plugin.py doctor
```
