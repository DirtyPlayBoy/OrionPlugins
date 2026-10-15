# plugin.toml reference

Required:

```toml
[plugin]
id = "my-plugin"
name = "My Plugin"
version = "0.1.0"

[entry]
command = "python"
args = ["main.py"]
runtimes = ["python"]

[capabilities]
tools = true
```

`plugin.id` — lowercase, digits, hyphens. Reserved: `orion-stt`, `orion-tts`, `orion-core`, `orion-agent`, `orion-voice`.

Unknown capability keys fail the install.
