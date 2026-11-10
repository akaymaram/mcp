"""Minimal MCP server using only the Python standard library.

Speaks JSON-RPC 2.0 over stdio, one JSON message per line.
Never print() to stdout except protocol messages; log to stderr.
"""
import inspect
import json
import sys

SERVER_INFO = {"name": "stdlib-demo", "version": "0.1.0"}
SUPPORTED_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]

TOOLS, PROMPTS = {}, {}
RESOURCES = {}  # uri -> (description, function)

_JSON_TYPES = {int: "integer", float: "number", str: "string", bool: "boolean"}


def log(*args):
    print(*args, file=sys.stderr, flush=True)


# ---- registration decorators ------------------------------------------------
def tool(fn):
    """Register a function as a tool; schema is built from its type hints."""
    sig = inspect.signature(fn)
    props = {n: {"type": _JSON_TYPES.get(p.annotation, "string")} for n, p in sig.parameters.items()}
    required = [n for n, p in sig.parameters.items() if p.default is p.empty]
    TOOLS[fn.__name__] = {
        "fn": fn,
        "spec": {
            "name": fn.__name__,
            "description": inspect.getdoc(fn) or "",
            "inputSchema": {"type": "object", "properties": props, "required": required},
        },
    }
    return fn


def resource(uri, description=""):
    def wrap(fn):
        RESOURCES[uri] = (description, fn)
        return fn
    return wrap


def prompt(fn):
    sig = inspect.signature(fn)
    PROMPTS[fn.__name__] = {
        "fn": fn,
        "spec": {
            "name": fn.__name__,
            "description": inspect.getdoc(fn) or "",
            "arguments": [{"name": n, "required": True} for n in sig.parameters],
        },
    }
    return fn


# ---- your tools / resources / prompts --------------------------------------
@tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b


@tool
def word_count(text: str) -> dict:
    """Count the words and characters in a piece of text."""
    return {"words": len(text.split()), "characters": len(text)}


@resource("demo://about", "Information about this server")
def about():
    return "This is a dependency-free MCP server written in pure Python."


@prompt
def summarize(text: str) -> str:
    """Ask the model to summarize some text."""
    return f"Please summarize the following text in two sentences:\n\n{text}"


# ---- protocol handlers -------------------------------------------------------
class RpcError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def handle_initialize(params):
    requested = params.get("protocolVersion")
    version = requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        "serverInfo": SERVER_INFO,
    }


def handle_tools_call(params):
    entry = TOOLS.get(params.get("name"))
    if not entry:
        raise RpcError(-32602, f"Unknown tool: {params.get('name')}")
    try:
        result = entry["fn"](**params.get("arguments", {}))
        text = result if isinstance(result, str) else json.dumps(result)
        return {"content": [{"type": "text", "text": text}], "isError": False}
    except Exception as exc:  # tool failures are reported in-band, not as protocol errors
        return {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}


def handle_resources_read(params):
    uri = params.get("uri")
    if uri not in RESOURCES:
        raise RpcError(-32002, f"Resource not found: {uri}")
    return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": RESOURCES[uri][1]()}]}


def handle_prompts_get(params):
    entry = PROMPTS.get(params.get("name"))
    if not entry:
        raise RpcError(-32602, f"Unknown prompt: {params.get('name')}")
    text = entry["fn"](**params.get("arguments", {}))
    return {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]}


HANDLERS = {
    "initialize": handle_initialize,
    "ping": lambda p: {},
    "tools/list": lambda p: {"tools": [t["spec"] for t in TOOLS.values()]},
    "tools/call": handle_tools_call,
    "resources/list": lambda p: {
        "resources": [{"uri": u, "name": u, "description": d} for u, (d, _) in RESOURCES.items()]
    },
    "resources/read": handle_resources_read,
    "prompts/list": lambda p: {"prompts": [p_["spec"] for p_ in PROMPTS.values()]},
    "prompts/get": handle_prompts_get,
}


def send(message):
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def main():
    log("stdlib-demo MCP server started")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue

        method, msg_id = msg.get("method"), msg.get("id")
        if msg_id is None:  # notification (e.g. notifications/initialized): no reply
            continue
        try:
            handler = HANDLERS.get(method)
            if handler is None:
                raise RpcError(-32601, f"Method not found: {method}")
            send({"jsonrpc": "2.0", "id": msg_id, "result": handler(msg.get("params") or {})})
        except RpcError as e:
            send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": e.code, "message": e.message}})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}})


if __name__ == "__main__":
    main()
