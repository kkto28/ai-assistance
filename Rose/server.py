"""Python web server for the Rose React interface."""
from __future__ import annotations

import json
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
ROSE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "clawbot"))

from config import config  # noqa: E402
from core.agent import Agent  # noqa: E402


agent = Agent()
agent_lock = threading.Lock()
executor = ThreadPoolExecutor(max_workers=2)
jobs = {}
jobs_lock = threading.Lock()


def run_chat_job(job_id: str, text: str):
    try:
        with agent_lock:
            reply = agent.handle_message(
                channel="rose-web",
                user_text=text,
                approve_fn=lambda *_: config.auto_approve,
            )
        result = {"status": "complete", "reply": reply}
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    with jobs_lock:
        jobs[job_id] = result


class RoseHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self._send_json(404, {"error": "Not found"})
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(
                200,
                {
                    "name": config.name,
                    "provider": config.model_provider,
                    "model": config.model_name,
                    "ready": True,
                },
            )
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            with jobs_lock:
                result = jobs.get(job_id)
            if result is None:
                self._send_json(404, {"error": "Chat job not found."})
            else:
                self._send_json(200, result)
            return
        if path == "/":
            self._send_file(ROSE_DIR / "web" / "index.html", "text/html; charset=utf-8")
            return
        if path == "/assets/Rose.png":
            self._send_file(ROSE_DIR / "assets" / "Rose.png", "image/png")
            return
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/api/chat":
            self._send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            text = str(payload.get("message", "")).strip()
            if not text:
                raise ValueError("Message cannot be empty.")
            job_id = uuid.uuid4().hex
            with jobs_lock:
                jobs[job_id] = {"status": "running"}
            executor.submit(run_chat_job, job_id, text)
            self._send_json(202, {"job_id": job_id, "status": "running"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": str(exc)})

    def log_message(self, *_):
        return


def main():
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), RoseHandler)
    print(f"Rose is ready at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Rose.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
