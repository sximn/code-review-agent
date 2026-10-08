"""Local, stateless Chat Completions simulator. Never contacts a model provider."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def simulate_completion(body: dict[str, Any], scenario: str) -> tuple[int, dict]:
    tool_results = [m for m in body["messages"] if m.get("role") == "tool"]
    if scenario == "api-error" or (scenario == "error-after-tool" and tool_results):
        return 429, {"error": {
            "message": "Simulated rate limit", "type": "rate_limit_error",
            "param": None, "code": "rate_limit_exceeded",
        }}

    message: dict[str, Any] = {"role": "assistant", "content": None}
    tool_call = not tool_results or scenario == "step-limit"
    if tool_call:
        message["tool_calls"] = [{
            "id": f"call_simulation_{len(tool_results)}", "type": "function",
            "function": {
                "name": "sandbox_exec",
                "arguments": json.dumps({
                    "command": ["git", "status", "--short"],
                    "cwd": "/workspace/repo",
                }),
            },
        }]
    else:
        findings = []
        if scenario == "findings":
            findings.append({
                "category": "quality", "severity": "medium",
                "title": "Simulated finding for development",
                "description": "Synthetic review data; this is not a real defect.",
                "file": "SIMULATION", "line_start": None, "line_end": None,
                "evidence": "The simulation exercised sandbox_exec.",
                "recommendation": "Use this fixture to inspect the findings UI.",
                "confidence": 1.0,
            })
        message["content"] = (
            "invalid JSON" if scenario == "invalid-output"
            else json.dumps({"findings": findings, "approval_granted": not findings})
        )

    response = {
        "id": f"chatcmpl-simulation-{len(tool_results)}",
        "object": "chat.completion", "created": 0,
        "model": body["model"],
        "choices": [{"index": 0, "message": message,
                     "finish_reason": "tool_calls" if tool_call else "stop"}],
        "usage": {
            "prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100,
            "prompt_tokens_details": {"cached_tokens": 200},
            "completion_tokens_details": {"reasoning_tokens": 20},
        },
    }
    if scenario == "missing-usage" and tool_results:
        response.pop("usage")
    return 200, response


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200 if self.path == "/health" else 404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            status, response = simulate_completion(
                body, self.headers.get("X-Simulation-Scenario", "success")
            )
        except (ValueError, KeyError, TypeError):
            status, response = 400, {"error": {"message": "Invalid simulation request"}}
        encoded = json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
