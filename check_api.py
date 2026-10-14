"""Sanity-check the API in .env: one plain chat, then one call that should come back as a tool call."""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["BASE_URL"], api_key=os.environ["API_KEY"])
model = os.environ["MODEL"]

r = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "Say hi in five words."}])
print("plain reply:", r.choices[0].message.content)
print("usage:", r.usage)

tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    },
}
r = client.chat.completions.create(
    model=model, tools=[tool], messages=[{"role": "user", "content": "List the files in the current folder."}]
)
calls = r.choices[0].message.tool_calls
if calls:
    print("tool call:", calls[0].function.name, calls[0].function.arguments)
else:
    print("NO tool call came back - pick a different model. Reply was:", r.choices[0].message.content)
