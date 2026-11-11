---
files:
  - "backend/**/*.py"
  - "transcribe.py"
  - "mcp_server.py"
  - "!backend/llm_client.py"
---

# Chat completions go through `llm_client.complete_text`

Every chat completion request must be made with
`await complete_text(client, model=..., messages=..., max_tokens=..., temperature=...)`
from `backend/llm_client.py`. Code outside `llm_client.py` must not call
`client.chat.completions.create(...)` (or `acreate`, `responses.create`, raw
HTTP to `/chat/completions`) directly, and must not read
`response.choices[0].message.content` itself.

## Why

Users bring their own OpenAI-compatible endpoint, including reasoning models
that can spend the whole `max_tokens` budget on thinking and return HTTP 200
with an empty `message.content`. An empty string is not an exception, so a
direct call slips past every `except` fallback in `Summarizer` and
`Translator` (local formatting, fallback summary, original text) and writes an
empty transcript, summary or translation to disk. `complete_text` retries once
(with a larger budget when `finish_reason == "length"`) and then raises
`EmptyLLMResponse`, so the existing fallbacks take over. It also runs the
synchronous OpenAI SDK in `asyncio.to_thread`, so a long call does not freeze
the event loop, the SSE progress stream and status requests. This was fixed in
#52 after both failures reached users.

## What to flag

- A new or changed call to `self.client.chat.completions.create(...)` or any
  other completion API outside `backend/llm_client.py`.
- Code that handles the result as if it could be empty
  (`message.content or ""`) instead of relying on `complete_text` raising.
- A caller of `complete_text` with no `try`/`except` or fallback where the
  surrounding code previously degraded gracefully, so `EmptyLLMResponse` now
  fails the whole task.
- Changes to `complete_text` itself that let an empty string return, drop the
  thread offload, or remove the retry.

## Example

Incorrect:

```python
response = self.client.chat.completions.create(
    model=self.fast_model,
    messages=[{"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}],
    max_tokens=4000,
    temperature=0.1,
)
optimized_text = strip_llm_artifacts(response.choices[0].message.content or "")
```

Correct:

```python
content = await complete_text(
    self.client,
    model=self.fast_model,
    messages=[{"role": "system", "content": system_prompt},
              {"role": "user", "content": user_prompt}],
    max_tokens=4000,
    temperature=0.1,
)
optimized_text = strip_llm_artifacts(content)
```
