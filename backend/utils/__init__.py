"""Backend utility modules.

Mirrors the ``utils/`` layout used by sublyai for a clean separation of
concerns:

* ``downloader``  – yt-dlp wrapper (URL → media/subtitle on disk)
* ``media``       – ffmpeg helpers (normalize local media to whisper-ready audio)
* ``subtitle``    – ``Segment`` dataclass + VTT/SRT parsers + writers for
                    SRT/VTT/ASS/TXT/Markdown
* ``transcriber`` – Faster-Whisper wrapper
* ``summarizer``  – LLM-based transcript optimization + summarization
* ``translator``  – LLM-based translation
* ``llm_sanitize`` – Strip trailing LLM meta-phrases
* ``jobs``        – Task lifecycle persistence helpers
"""
