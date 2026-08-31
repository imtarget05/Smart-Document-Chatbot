"""
Localhost end-to-end verification for top_p (LLM_TOP_P) sampling.

Runs the REAL llm-router FastAPI app over HTTP against a recording mock
Ollama provider — no Cloudflare credentials, no database, no UI clicking.

Chain verified:
  backend-shaped /api/chat payload -> LLMRouter -> LocalOllamaProvider
  -> mock Ollama (records the options it actually receives)

Checks:
  1. backend-shaped payload -> provider receives top_p == 0.95
  2. request without options -> provider still defaults top_p == 0.95
  3. explicit top_p override is forwarded untouched
  4. streaming request returns NDJSON tokens with top_p forwarded

Usage: cd llm-router && .venv/bin/python ../scripts/local_top_p_e2e.py
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "llm-router"))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.providers import CloudflareProvider, LocalOllamaProvider  # noqa: E402
from app.service import LLMRouter  # noqa: E402

DEFAULT_TOP_P = 0.95
RECEIVED = []


class MockOllamaHandler(BaseHTTPRequestHandler):
    def _reply(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Health probe used by LocalOllamaProvider.is_available().
        self._reply({"models": [{"name": "mock-model"}]})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        RECEIVED.append(json.loads(self.rfile.read(length) or b"{}"))
        if self.path == "/api/chat":
            self._reply({
                "model": "mock-model",
                "message": {"role": "assistant", "content": "e2e-ok"},
                "done": True,
                "done_reason": "stop",
                "eval_count": 7,
            })
        else:
            self._reply({"error": "unexpected path"}, status=404)

    def log_message(self, *args):
        pass


def start_mock():
    server = ThreadingHTTPServer(("127.0.0.1", 0), MockOllamaHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


def build_client(mock_url):
    settings = Settings(
        local_ollama_url=mock_url,
        local_ollama_model="mock-model",
        local_ollama_timeout_seconds=10.0,
        cloudflare_account_id="",
        cloudflare_api_token="",
        cloudflare_timeout_seconds=5.0,
        internal_token="",
    )
    router = LLMRouter(
        settings,
        CloudflareProvider(settings),
        local=LocalOllamaProvider(settings),
    )
    return TestClient(create_app(settings, router=router))


def backend_shaped_payload(**overrides):
    payload = {
        "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "messages": [
            {"role": "system", "content": "You are a helpful document assistant."},
            {"role": "user", "content": "Summarise the failure report."},
        ],
        "options": {"temperature": 0.3, "top_p": DEFAULT_TOP_P, "num_predict": 2048},
        "stream": False,
    }
    payload.update(overrides)
    return payload


CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append((name, bool(ok), detail))


def main():
    server, mock_url = start_mock()
    try:
        client = build_client(mock_url)

        # 1. Exact payload shape the Java backend (LlmClient) sends.
        RECEIVED.clear()
        r = client.post("/api/chat", json=backend_shaped_payload())
        check("backend-shaped /api/chat returns 200", r.status_code == 200, r.text[:120])
        check("...answer content returned", (r.json().get("message") or {}).get("content") == "e2e-ok")
        got = RECEIVED[0].get("options", {}) if RECEIVED else {}
        check("...provider received top_p == 0.95", got.get("top_p") == DEFAULT_TOP_P, "got %s" % got)
        check("...provider received temperature == 0.3", got.get("temperature") == 0.3, "got %s" % got)
        check("...provider received num_predict == 2048", got.get("num_predict") == 2048, "got %s" % got)

        # 2. Regression: options omitted entirely -> router/provider default.
        RECEIVED.clear()
        payload = backend_shaped_payload()
        payload.pop("options")
        r = client.post("/api/chat", json=payload)
        check("options-less /api/chat returns 200", r.status_code == 200)
        got = RECEIVED[0].get("options", {}) if RECEIVED else {}
        check("...provider defaulted top_p == 0.95", got.get("top_p") == DEFAULT_TOP_P, "got %s" % got)

        # 3. Explicit override is forwarded untouched.
        RECEIVED.clear()
        client.post("/api/chat", json=backend_shaped_payload(options={"top_p": 0.5}))
        got = RECEIVED[0].get("options", {}) if RECEIVED else {}
        check("override top_p == 0.5 forwarded untouched", got.get("top_p") == 0.5, "got %s" % got)

        # 4. Streaming path forwards top_p and yields NDJSON tokens.
        RECEIVED.clear()
        payload = backend_shaped_payload(stream=True)
        with client.stream("POST", "/api/chat", json=payload) as resp:
            lines = [ln for ln in resp.iter_lines() if ln.strip()]
        tokens = []
        for line in lines:
            try:
                chunk = json.loads(line)
            except ValueError:
                continue
            tokens.append((chunk.get("message") or {}).get("content", ""))
        check("streaming /api/chat yields tokens", any(tokens), "lines=%d" % len(lines))
        got = RECEIVED[0].get("options", {}) if RECEIVED else {}
        check("streaming provider received top_p == 0.95", got.get("top_p") == DEFAULT_TOP_P, "got %s" % got)
    finally:
        server.shutdown()

    width = max(len(n) for n, _, _ in CHECKS)
    failed = 0
    print("")
    print("=== top_p localhost E2E ===")
    for name, ok, detail in CHECKS:
        mark = "PASS" if ok else "FAIL"
        print("  [%s] %s  %s" % (mark, name.ljust(width), detail))
        failed += 0 if ok else 1
    total = len(CHECKS)
    print("  total: %d, passed: %d, failed: %d" % (total, total - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
