# eakso — EAKSO SDK

Consume marketplace skills in your own LLM calls.

```bash
pip install eakso
```

```python
from eakso import Client

client = Client(api_key="sk_live_...", base_url="https://your-eakso/api/v1")

skill = client.skill("<listing-id>")        # fetch a published skill
print(skill.title, skill.version)

# Bring your own model: any callable (system_prompt, user_input) -> str
def my_llm(system: str, user: str) -> str:
    ...  # call OpenAI / Anthropic / OpenRouter / local, your choice

answer = skill.apply(my_llm, "Summarise this invoice")   # usage auto-reported
```

`skill.system_prompt` is the skill body wrapped as a ready-to-use system prompt;
`skill.content` is the raw markdown. Create an API key in the EAKSO web app under
**Settings → API Keys**.
