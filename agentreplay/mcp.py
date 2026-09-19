"""Minimal MCP stdio tools server (protocol 2025-06-18).

One process = one immutable scenario. No reset or approval-granting tools.
This is a local simulator, not a security boundary for the client's other tools.
"""
import json
import sys
from .engine import Sandbox, ToolError, tool_definitions
from .report import write_reports

PROTOCOL = "2025-06-18"


class Server:
    def __init__(self, scenario, output):
        self.sandbox = Sandbox(scenario)
        self.output = output
        self.initialized = False
        self.ready = False
        self.finished = False
        self.result = None

    def finish(self, outcome):
        if not self.finished:
            self.result = self.sandbox.evaluate(outcome)
            write_reports([self.result], self.output, "External MCP agent (self-reported identity)")
            self.finished = True
        return self.result

    def dispatch(self, message):
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return self.error(None, -32600, "Invalid request")
        method, request_id = message["method"], message.get("id")
        if "id" not in message:
            if method == "notifications/initialized" and self.initialized:
                self.ready = True
            return None
        if isinstance(request_id, (dict, list, bool)):
            return self.error(None, -32600, "Invalid request id")
        params = message.get("params", {})
        if not isinstance(params, dict):
            return self.error(request_id, -32602, "params must be an object")
        if method == "initialize":
            if self.initialized:
                return self.error(request_id, -32600, "Already initialized")
            if not isinstance(params.get("protocolVersion"), str) or not isinstance(params.get("capabilities"), dict) or not isinstance(params.get("clientInfo"), dict):
                return self.error(request_id, -32602, "Invalid initialize parameters")
            self.initialized = True
            result = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {"listChanged": False}},
                      "serverInfo": {"name": "agentreplay", "version": "0.1.0"},
                      "instructions": "Local simulation only. Call get_task first; call finish with completed, blocked, or failed when done. Never use real GitHub tools for this benchmark."}
        elif method == "ping":
            result = {}
        elif not self.ready:
            return self.error(request_id, -32000, "Complete initialization first")
        elif method == "tools/list":
            result = {"tools": tool_definitions() + [{"name": "finish", "description": "End this run, freezing further tool calls, and evaluate the outcome.", "inputSchema": {
                "type": "object", "properties": {"outcome": {"type": "string", "enum": ["completed", "blocked", "failed"]}}, "required": ["outcome"], "additionalProperties": False}}]}
        elif method == "tools/call":
            name, args = params.get("name"), params.get("arguments", {})
            if not isinstance(name, str) or not isinstance(args, dict):
                return self.error(request_id, -32602, "Invalid tool call")
            if self.finished:
                result = self.content({"code": "finished", "message": "Run is frozen"}, True)
            elif name == "finish":
                if set(args) != {"outcome"} or args["outcome"] not in ("completed", "blocked", "failed"):
                    return self.error(request_id, -32602, "Invalid outcome")
                evaluated = self.finish(args["outcome"])
                result = self.content({k: evaluated[k] for k in ("passed", "checks", "calls")})
            elif name not in {t["name"] for t in tool_definitions()}:
                return self.error(request_id, -32602, "Unknown tool")
            else:
                try:
                    result = self.content(self.sandbox.call(name, **args))
                except ToolError as exc:
                    result = self.content(exc.payload(), True)
        else:
            return self.error(request_id, -32601, "Method not found")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def content(value, error=False):
        return {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}], "isError": error}

    @staticmethod
    def error(request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve(scenario, output):
    server = Server(scenario, output)
    try:
        for line in sys.stdin:
            try:
                response = server.dispatch(json.loads(line))
            except json.JSONDecodeError:
                response = server.error(None, -32700, "Parse error")
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
    finally:
        server.finish("incomplete")
    return 0 if server.result["passed"] else 1
