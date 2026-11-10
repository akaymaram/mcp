# mcp

A minimal Model Context Protocol (MCP) server and client in pure Python.
**No dependencies**: standard library only, Python 3.8+.

- `server.py` – MCP server (tools, resources, prompts) over stdio
- `client.py` – launches the server and calls each feature

## Run

```bash
python client.py
```

## Use with Claude Desktop

Add to `claude_desktop_config.json` (use absolute paths):

```json
{
  "mcpServers": {
    "stdlib-demo": {
      "command": "python3",
      "args": ["/absolute/path/to/mcp-stdlib/server.py"]
    }
  }
}
```

## Add your own tool

```python
@tool
def shout(text: str) -> str:
    """Uppercase some text."""
    return text.upper()
```

Type hints become the JSON input schema; the docstring becomes the description.

## Notes

- Transport is stdio with newline-delimited JSON-RPC 2.0. Never `print()` to
  stdout in the server (it would corrupt the stream); use `log()` (stderr).
- Implemented methods: `initialize`, `ping`, `tools/list`, `tools/call`,
  `resources/list`, `resources/read`, `prompts/list`, `prompts/get`.
- Not implemented: HTTP transport, resource templates, subscriptions,
  progress/cancellation, list-changed notifications. For production use, the
  official `mcp` SDK handles these.
