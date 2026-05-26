"""Subtitle parsing and rendering.

This module centralises everything that turns *segments* (a list of
``Segment`` instances with start/end seconds + text) into the various
output formats consumers expect — SRT, WebVTT, ASS, plain text and the
project's own Whisper-style Markdown — and the inverse: parsing VTT/SRT
files into ``Segment`` lists.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass
class Segment:
    """A single time-aligned transcript line."""

    start: float
    end: float
    text: str

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "text": self.text}

    @classmethod
    def from_dict(cls, data: dict) -> "Segment":
        return cls(
            start=float(data.get("start", 0.0)),
            end=float(data.get("end", 0.0)),
            text=str(data.get("text", "")),
        )


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _format_short(seconds: float) -> str:
    """Format seconds as ``MM:SS`` or ``HH:MM:SS``.

    Used by the Whisper-style Markdown output for human readability.
    """
    if seconds is None or seconds < 0:
        seconds = 0.0
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _format_srt_time(seconds: float) -> str:
    """``HH:MM:SS,mmm`` — SRT timestamp format."""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_vtt_time(seconds: float) -> str:
    """``HH:MM:SS.mmm`` — WebVTT timestamp format."""
    return _format_srt_time(seconds).replace(",", ".")


def _format_ass_time(seconds: float) -> str:
    """``H:MM:SS.cc`` — ASS timestamp format (centiseconds)."""
    if seconds is None or seconds < 0:
        seconds = 0.0
    total_cs = int(round(seconds * 100))
    cs = total_cs % 100
    total_s = total_cs // 100
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _parse_short_time(time_str: str) -> float:
    """Parse ``MM:SS`` / ``HH:MM:SS`` / ``HH:MM:SS.mmm`` to seconds."""
    if not time_str:
        return 0.0
    cleaned = re.sub(r"[.,](\d+)$", "", time_str)
    parts = cleaned.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return float(parts[0])
    except ValueError:
        return 0.0


def _parse_long_time(time_str: str) -> float:
    """Parse ``HH:MM:SS.mmm`` / ``HH:MM:SS,mmm`` to seconds."""
    if not time_str:
        return 0.0
    match = re.match(
        r"(?:(\d+):)?(\d+):(\d+)[.,](\d+)$",
        time_str.strip(),
    )
    if not match:
        return _parse_short_time(time_str)
    h = int(match.group(1) or 0)
    m = int(match.group(2))
    s = int(match.group(3))
    frac = match.group(4)
    # pad/truncate to milliseconds
    frac = (frac + "000")[:3]
    ms = int(frac)
    return h * 3600 + m * 60 + s + ms / 1000.0


# ---------------------------------------------------------------------------
# Parsers (VTT / SRT → list[Segment])
# ---------------------------------------------------------------------------

def parse_vtt(text_or_path: str | Path) -> List[Segment]:
    """Parse a WebVTT subtitle file or string into ``Segment`` objects.

    Handles YouTube's "rolling append" auto-caption format where the same
    sentence is split across many overlapping cues — only the longest /
    final version of each rolling group is kept.
    """
    content = _load_text(text_or_path)
    if not content:
        return []
    content = re.sub(r"^WEBVTT[^\n]*\n", "", content)
    blocks = re.split(r"\n{2,}", content.strip())

    raw_entries: List[Segment] = []
    seen: set[str] = set()
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        timing_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), -1)
        if timing_idx < 0:
            continue

        match = re.match(
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)\s*-->\s*"
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?)",
            lines[timing_idx],
        )
        if not match:
            continue
        start = _parse_long_time(match.group(1))
        end = _parse_long_time(match.group(2))

        raw_text = " ".join(lines[timing_idx + 1:])
        text = _strip_html_entities(raw_text)
        if not text or text in seen:
            continue
        seen.add(text)
        raw_entries.append(Segment(start=start, end=end, text=text))

    return _drop_rolling_intermediates(raw_entries)


def parse_srt(text_or_path: str | Path) -> List[Segment]:
    """Parse an SRT subtitle file or string into ``Segment`` objects."""
    content = _load_text(text_or_path)
    if not content:
        return []
    blocks = re.split(r"\n{2,}", content.strip())

    entries: List[Segment] = []
    seen: set[str] = set()
    for block in blocks:
        lines = block.strip().split("\n")
        timing_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), -1)
        if timing_idx < 0:
            continue
        match = re.match(
            r"(\d{1,2}:\d{2}:\d{2}[.,]\d+)\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d+)",
            lines[timing_idx],
        )
        if not match:
            continue
        start = _parse_long_time(match.group(1))
        end = _parse_long_time(match.group(2))
        text = _strip_html_entities(" ".join(lines[timing_idx + 1:]))
        if not text or text in seen:
            continue
        seen.add(text)
        entries.append(Segment(start=start, end=end, text=text))
    return entries


def _load_text(text_or_path: str | Path) -> str:
    if isinstance(text_or_path, Path):
        try:
            return text_or_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error(f"Failed to read subtitle file {text_or_path}: {e}")
            return ""
    return text_or_path or ""


def _strip_html_entities(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = (
        text.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&nbsp;", " ")
            .replace("&#39;", "'")
            .replace("&quot;", '"')
    )
    return re.sub(r"\s+", " ", text).strip()


def _drop_rolling_intermediates(entries: Sequence[Segment]) -> List[Segment]:
    if not entries:
        return []
    out: List[Segment] = []
    for i, entry in enumerate(entries):
        text = entry.text
        if len(text) < 2:
            continue
        is_intermediate = False
        for j in range(i + 1, min(i + 4, len(entries))):
            next_text = entries[j].text
            if next_text.startswith(text) and len(next_text) > len(text):
                is_intermediate = True
                break
        if not is_intermediate:
            out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Writers (list[Segment] → text)
# ---------------------------------------------------------------------------

def segments_to_srt(segments: Iterable[Segment]) -> str:
    out: List[str] = []
    for idx, seg in enumerate(segments, start=1):
        out.append(str(idx))
        out.append(f"{_format_srt_time(seg.start)} --> {_format_srt_time(seg.end)}")
        out.append(seg.text.strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def segments_to_vtt(segments: Iterable[Segment]) -> str:
    out: List[str] = ["WEBVTT", ""]
    for seg in segments:
        out.append(f"{_format_vtt_time(seg.start)} --> {_format_vtt_time(seg.end)}")
        out.append(seg.text.strip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


_ASS_HEADER = """[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayDepth: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,28,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,20,20,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def segments_to_ass(segments: Iterable[Segment]) -> str:
    lines = [_ASS_HEADER]
    for seg in segments:
        text = seg.text.replace("\n", " \\N ").strip()
        lines.append(
            f"Dialogue: 0,{_format_ass_time(seg.start)},{_format_ass_time(seg.end)},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines).rstrip() + "\n"


def segments_to_txt(segments: Iterable[Segment]) -> str:
    return "\n".join(seg.text.strip() for seg in segments if seg.text.strip()) + "\n"


def segments_to_markdown(
    segments: Sequence[Segment],
    language: Optional[str] = None,
    language_probability: Optional[float] = None,
) -> str:
    """Render segments as the Whisper-compatible Markdown the pipeline expects."""
    prob_repr = (
        f"{language_probability:.2f}" if isinstance(language_probability, (int, float)) else "—"
    )
    lines = [
        "# Video Transcription",
        "",
        f"**Detected Language:** {language or ''}",
        f"**Language Probability:** {prob_repr}",
        "",
        "## Transcription Content",
        "",
    ]
    for seg in segments:
        lines.append(f"**[{_format_short(seg.start)} - {_format_short(seg.end)}]**")
        lines.append("")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)


def parse_subtitle_file(path: str | Path) -> List[Segment]:
    """Dispatch to the correct parser based on extension."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".vtt":
        return parse_vtt(p)
    if suffix == ".srt":
        return parse_srt(p)
    raise ValueError(f"Unsupported subtitle extension: {suffix}")
