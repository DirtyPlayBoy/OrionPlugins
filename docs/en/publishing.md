# Publishing

1. Package folder as `<id>-<version>-windows-x64.orionplugin` (zip, `plugin.toml` at root).
2. SHA-256 the artifact.
3. GitHub Release on your public repo.
4. PR to [orion-registry](https://github.com/DirtyPlayBoy/orion-registry):
   - `plugins/<id>/plugin.json`
   - `plugins/<id>/versions/<semver>.json` with `url`, `sha256`, `size`
5. CI rebuilds `registry/v1/index.json`. First submission is human-reviewed.
