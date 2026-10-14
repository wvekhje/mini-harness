"""Local web chat for mini-harness. Same agent loop as the terminal; only show() and approve() differ."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from harness import HERE, MODEL, SYSTEM_PROMPT, agent_turn

HOST, PORT = "127.0.0.1", int(os.environ.get("PORT", "8765"))  # 127.0.0.1: only this computer can connect

messages = [{"role": "system", "content": SYSTEM_PROMPT}]
events = []  # everything the page shows, in order; the page polls for new ones
pending = {}  # approval id -> [threading.Event, decision]
busy = threading.Lock()  # one question at a time


def show(kind, data):
    events.append({"kind": kind, "data": data})


def approve(command):
    """Called from the agent loop: post an approval request, then wait for the button click."""
    approval_id = str(len(events))
    pending[approval_id] = [threading.Event(), False]
    show("approve", {"id": approval_id, "command": command})
    pending[approval_id][0].wait()
    return pending.pop(approval_id)[1]


def run(text):
    try:
        messages.append({"role": "user", "content": text})
        agent_turn(messages, show, approve)
    except Exception as e:  # show API errors on the page instead of dying silently
        show("error", f"{type(e).__name__}: {e}")
    finally:
        show("done", None)
        busy.release()


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, content_type="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self.reply(200, (HERE / "index.html").read_text(), "text/html; charset=utf-8")
        elif self.path.startswith("/events"):
            since = int(self.path.partition("since=")[2] or 0)
            self.reply(200, {"events": events[since:], "model": MODEL})
        else:
            self.reply(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
        if self.path == "/send":
            if not busy.acquire(blocking=False):
                return self.reply(409, {"error": "still working on the last question"})
            show("user", body["text"])
            threading.Thread(target=run, args=(body["text"],), daemon=True).start()
            self.reply(200, {"ok": True})
        elif self.path == "/approve" and body.get("id") in pending:
            pending[body["id"]][1] = bool(body.get("ok"))
            pending[body["id"]][0].set()
            self.reply(200, {"ok": True})
        else:
            self.reply(400, {"error": "bad request"})

    def log_message(self, *args):  # keep the terminal quiet
        pass


if __name__ == "__main__":
    print(f"mini-harness web chat on http://{HOST}:{PORT}  ({MODEL}) - Ctrl-C to stop")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
