# mini-harness

A minimal agent harness, written by hand for UCLA's *AI in Research* (EPSS 254, Fall 2026), week 2. It chats with a language model through any OpenAI-compatible API and gives it exactly one tool, `bash`. You approve every command before it runs.

No agent frameworks: the whole agent loop is `agent_turn()` in [`harness.py`](harness.py), about 20 lines.

## How it works

```
you ask ──▶ call the model (whole conversation + the bash tool)
              │
              ├─ reply is text?      ──▶ show it, wait for you
              └─ reply is tool calls ──▶ for each: show command, ask you,
                                          run it (or report "declined"),
                                          append the result ──▶ call again
```

- Every call resends the full conversation; the model has no memory of its own.
- `bash` runs in the folder you start the harness from, with a 60 s time limit, and returns the exit code plus the last 10,000 characters of output.
- At most 20 tool rounds per question.
- Each call prints its token usage: input, cached input (when the provider reports it) and output.

## Setup

Needs [uv](https://docs.astral.sh/uv/) and an OpenAI-compatible API key (e.g. [OpenRouter](https://openrouter.ai)).

```bash
git clone https://github.com/wvekhje/mini-harness.git
cd mini-harness
cp .env.example .env    # then put your key and model in .env
uv sync
uv run check_api.py     # optional: confirms the model answers and can call tools
```

`.env` holds three settings and is git-ignored:

```
BASE_URL=https://openrouter.ai/api/v1
API_KEY=...
MODEL=openai/gpt-4.1-mini
```

## Run

Web chat (recommended), at http://127.0.0.1:8765, reachable only from your computer:

```bash
uv run web.py
```

Or in the terminal (`--yes` approves every command automatically; off by default):

```bash
uv run harness.py
```

Commands run in the current folder, so start it where you want the agent to work, e.g. `uv run --project ~/mini-harness ~/mini-harness/web.py`. Set `PORT` to use another port.

## Files

| File | What it is |
|---|---|
| `harness.py` | The bash tool, the agent loop, and the terminal chat |
| `web.py` | Local web server: same loop, with Approve/Deny buttons |
| `index.html` | The chat page |
| `system_prompt.md` | The system prompt; edit freely. The harness appends the working folder, home folder and OS. |
| `check_api.py` | One plain call and one tool call, to test your `.env` |

## Platform notes

macOS and Linux run commands with `/bin/bash`. On Windows, use WSL, or commands run through the default `cmd` shell.

## License

MIT
