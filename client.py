"""Tiny stdlib-only MCP client: launches server.py and exercises it."""
import json
import subprocess
import sys

proc = subprocess.Popen(
    [sys.executable, "server.py"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
)
_next_id = 0


def request(method, params=None):
    global _next_id
    _next_id += 1
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": _next_id, "method": method, "params": params or {}}) + "\n")
    proc.stdin.flush()
    reply = json.loads(proc.stdout.readline())
    if "error" in reply:
        raise RuntimeError(reply["error"])
    return reply["result"]


def notify(method):
    proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
    proc.stdin.flush()


init = request("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "demo-client", "version": "0.1.0"},
})
notify("notifications/initialized")
print("Connected to:", init["serverInfo"]["name"], "| protocol", init["protocolVersion"])

print("Tools:", [t["name"] for t in request("tools/list")["tools"]])
print("add(2, 3) ->", request("tools/call", {"name": "add", "arguments": {"a": 2, "b": 3}})["content"][0]["text"])
print("word_count ->", request("tools/call", {"name": "word_count", "arguments": {"text": "hello MCP world"}})["content"][0]["text"])
print("resource ->", request("resources/read", {"uri": "demo://about"})["contents"][0]["text"])
print("prompt ->", request("prompts/get", {"name": "summarize", "arguments": {"text": "MCP is a protocol."}})["messages"][0]["content"]["text"])

proc.stdin.close()
proc.wait(timeout=5)
