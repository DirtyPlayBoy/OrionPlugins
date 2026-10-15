# orion-plugin-sdk (Python)

Write an Orion plugin in a few lines.

```bash
pip install -e .
```

```python
from orion_plugin_sdk import Plugin, tool, run

@tool(name="hello", description="Say hello.", parameters={
    "type": "object",
    "properties": {"name": {"type": "string"}},
})
def hello(name: str = "world"):
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    run(Plugin(tools=[hello]))
```

See `docs/en/getting-started.md` and `examples/dice-roller`.
