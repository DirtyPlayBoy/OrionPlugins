# Справка по plugin.toml

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

`plugin.id` — строчные латиница, цифры, дефисы. Зарезервировано: `orion-stt`, `orion-tts`, `orion-core`, `orion-agent`, `orion-voice`.
