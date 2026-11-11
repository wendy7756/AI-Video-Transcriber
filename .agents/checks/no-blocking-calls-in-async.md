---
files:
  - "backend/**/*.py"
  - "transcribe.py"
  - "mcp_server.py"
---

# Blocking work in `async def` runs in a worker thread

The web server runs every task, the SSE progress stream and the status
endpoints on one asyncio event loop. Inside an `async def`, any call that can
take more than a moment must be offloaded with `await asyncio.to_thread(...)`
(or be a native async API such as `aiofiles`). This covers:

- yt-dlp: `ydl.extract_info(...)`, `ydl.download(...)`
- faster-whisper: `model.transcribe(...)` and iterating its segments
- FFmpeg/ffprobe: `subprocess.run`, `check_output`, `check_call`, `os.system`
- the synchronous OpenAI SDK, e.g. `client.models.list()`
  (chat completions are offloaded by `complete_text`, see
  `llm-calls-use-complete-text.md`)
- `time.sleep(...)` (use `await asyncio.sleep(...)`) and synchronous HTTP
  clients such as `requests`

## Why

A blocking call on the loop freezes every other task: live progress stops,
status polling hangs, cancellation and superseding a task (#52) cannot run
until the call returns, and a single Whisper run or video download can take
minutes. #52 fixed exactly this for LLM calls. Short, local file reads and
writes are acceptable.

## Example

Incorrect:

```python
async def extract_audio(self, url, output_dir):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        ydl.download([url])
    out = subprocess.check_output(probe_cmd, shell=True).decode().strip()
```

Correct:

```python
async def extract_audio(self, url, output_dir):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, False)
        await asyncio.to_thread(ydl.download, [url])
    out = (await asyncio.to_thread(
        subprocess.check_output, probe_cmd, shell=True
    )).decode().strip()
```

Only flag blocking calls that a pull request adds or moves into an `async def`;
code in plain `def` functions that are themselves called through
`asyncio.to_thread` is fine.
