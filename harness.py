"""mini-harness: a minimal agent loop with one bash tool."""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["BASE_URL"], api_key=os.environ["API_KEY"])
MODEL = os.environ["MODEL"]
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text()


def usage_line(usage):
    """Input, cached input (when the API reports it) and output tokens for one call."""
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", None) or 0
    return f"[tokens] in {usage.prompt_tokens} (cached {cached}) · out {usage.completion_tokens}"


messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "In one sentence, what are you?"},
]
reply = client.chat.completions.create(model=MODEL, messages=messages)
print(reply.choices[0].message.content)
print(usage_line(reply.usage))
