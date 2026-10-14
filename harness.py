"""mini-harness: a minimal agent loop with one bash tool."""
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")
client = OpenAI(base_url=os.environ["BASE_URL"], api_key=os.environ["API_KEY"])
MODEL = os.environ["MODEL"]
SYSTEM_PROMPT = (HERE / "system_prompt.md").read_text()


TIMEOUT = 60  # seconds per command
MAX_OUTPUT = 10_000  # characters of output the model sees

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": (
            "Run a shell command (bash) on the user's computer, in the working folder, and return its "
            f"output and exit code. Commands time out after {TIMEOUT} s; long output is cut to the last "
            f"{MAX_OUTPUT} characters. The user must approve each command."
        ),
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "The shell command to run."}},
            "required": ["command"],
        },
    },
}


def run_bash(command):
    """Run one command; return what the model gets back as the tool result."""
    try:
        p = subprocess.run(command, shell=True, executable="/bin/bash" if os.name != "nt" else None,
                           capture_output=True, text=True, timeout=TIMEOUT)
        output, code = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        output, code = f"Command timed out after {TIMEOUT} s.", -1
    if len(output) > MAX_OUTPUT:
        output = f"[output cut: showing last {MAX_OUTPUT} of {len(output)} characters]\n" + output[-MAX_OUTPUT:]
    return f"exit code: {code}\n{output}"


def usage_line(usage):
    """Input, cached input (when the API reports it) and output tokens for one call."""
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) or 0
    return f"[tokens] in {usage.prompt_tokens} (cached {cached}) · out {usage.completion_tokens}"


MAX_ROUNDS = 20  # tool rounds per question, so a confused model can't loop forever


def agent_turn(messages, show, approve):
    """THE AGENT LOOP. Call the model; while it asks for tools, run them and call again; stop at text."""
    for _ in range(MAX_ROUNDS):
        reply = client.chat.completions.create(model=MODEL, messages=messages, tools=[BASH_TOOL])  # 1. call
        msg = reply.choices[0].message
        show("usage", usage_line(reply.usage))
        messages.append(msg.model_dump(exclude_none=True))  # 2. remember the reply (text and/or tool calls)
        if not msg.tool_calls:  # 3. plain text: the answer. Done until the user speaks again.
            show("text", msg.content)
            return
        for call in msg.tool_calls:  # 4. tool calls: run each, append its result, then loop
            command = json.loads(call.function.arguments)["command"]
            show("command", command)
            if approve(command):  # 5. the user decides; a "no" is itself a result the model sees
                result = run_bash(command)
            else:
                result = "The user declined to run this command."
            show("result", result)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    show("text", f"(Stopped after {MAX_ROUNDS} tool rounds.)")


def show_terminal(kind, data):
    print({"usage": f"  {data}", "text": f"\nagent> {data}", "command": f"\n$ {data}",
           "result": "  " + data.replace("\n", "\n  ")}[kind])


def approve_terminal(command):
    try:
        return input("  run it? [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main():
    auto = "--yes" in sys.argv  # approve everything; off unless you ask for it
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print(f"mini-harness · {MODEL} · Ctrl-D to quit" + (" · AUTO-APPROVE ON" if auto else ""))
    while True:
        try:
            user = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user:
            messages.append({"role": "user", "content": user})
            agent_turn(messages, show_terminal, (lambda c: True) if auto else approve_terminal)


if __name__ == "__main__":
    main()
