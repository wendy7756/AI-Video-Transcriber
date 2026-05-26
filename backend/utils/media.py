"""FFmpeg helpers.

Pure media operations live here; no yt-dlp, no HTTP. The goal is to keep
the rest of the pipeline blissfully unaware of how audio actually gets
normalised to a Whisper-friendly format.
"""
from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Target audio profile expected by Faster-Whisper: mono 16 kHz AAC m4a.
AUDIO_CHANNELS = 1
AUDIO_SAMPLE_RATE = 16000


async def normalize_local_media_to_m4a(input_path: Path, output_dir: Path) -> str:
    """Re-encode any local audio/video to mono 16 kHz AAC ``.m4a``.

    Mirrors the yt-dlp post-processor args so behaviour is identical for
    uploaded files vs. downloaded URLs.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    unique_id = str(uuid.uuid4())[:8]
    out_path = output_dir / f"upload_norm_{unique_id}.m4a"

    cmd = [
        "ffmpeg", "-y", "-nostdin", "-i", str(input_path.resolve()),
        "-vn", "-ac", str(AUDIO_CHANNELS), "-ar", str(AUDIO_SAMPLE_RATE),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(out_path.resolve()),
    ]

    def _run() -> None:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()
            raise RuntimeError(f"FFmpeg 转换失败: {err[:800]}")
        if not out_path.exists():
            raise RuntimeError("FFmpeg 未生成输出文件")

    await asyncio.to_thread(_run)
    return str(out_path)


def probe_duration(audio_path: str) -> float:
    """Return media duration in seconds (best-effort, returns 0 on failure)."""
    cmd = (
        "ffprobe -v error -show_entries format=duration "
        f"-of default=noprint_wrappers=1:nokey=1 {shlex.quote(audio_path)}"
    )
    try:
        out = subprocess.check_output(cmd, shell=True).decode().strip()
        return float(out) if out else 0.0
    except Exception:
        return 0.0


def remux_audio(source_path: str, output_path: str) -> Tuple[bool, Optional[str]]:
    """Repackage an audio file via ffmpeg without re-encoding the codec.

    Returns ``(ok, error_message)``. Used as a "fix-up" step when the
    downloaded file has a broken duration header.
    """
    cmd = (
        f"ffmpeg -y -i {shlex.quote(source_path)} -vn -c:a aac -b:a 160k "
        f"-movflags +faststart {shlex.quote(output_path)}"
    )
    try:
        subprocess.check_call(cmd, shell=True)
        return True, None
    except Exception as e:
        return False, str(e)
