"""Faster-Whisper wrapper.

Exposes structured ``Segment`` lists in addition to the legacy
Markdown-shaped string so downstream code can render the transcript as
SRT / VTT / ASS / TXT without reparsing it.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional, Tuple

from faster_whisper import WhisperModel

from .subtitle import Segment, segments_to_markdown

logger = logging.getLogger(__name__)


class Transcriber:
    """Faster-Whisper based speech-to-text."""

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        self.last_detected_language: Optional[str] = None
        self.last_segments: List[Segment] = []
        self.last_language_probability: Optional[float] = None

    def _load_model(self) -> None:
        if self.model is None:
            logger.info(f"正在加载Whisper模型: {self.model_size}")
            try:
                self.model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
                logger.info("模型加载完成")
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                raise RuntimeError(f"模型加载失败: {e}") from e

    async def transcribe_segments(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> Tuple[List[Segment], str, float]:
        """Run Whisper and return ``(segments, detected_language, prob)``."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")

        self._load_model()
        logger.info(f"开始转录音频: {audio_path}")

        def _do_transcribe():
            return self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2, 0.4],
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 900,
                    "speech_pad_ms": 300,
                },
                no_speech_threshold=0.7,
                compression_ratio_threshold=2.3,
                log_prob_threshold=-1.0,
                condition_on_previous_text=False,
            )

        segments_iter, info = await asyncio.to_thread(_do_transcribe)

        segments: List[Segment] = []
        for seg in segments_iter:
            text = (seg.text or "").strip()
            if not text:
                continue
            segments.append(Segment(start=float(seg.start), end=float(seg.end), text=text))

        detected_language = info.language or ""
        language_probability = float(info.language_probability or 0.0)
        logger.info(
            f"检测到的语言: {detected_language}（{language_probability:.2f}）, "
            f"段落数: {len(segments)}"
        )

        self.last_detected_language = detected_language
        self.last_language_probability = language_probability
        self.last_segments = segments
        return segments, detected_language, language_probability

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """Backward-compatible Markdown-returning wrapper.

        Calls ``transcribe_segments`` and renders the result to the
        Markdown shape downstream code already consumes.
        """
        try:
            segments, detected, prob = await self.transcribe_segments(audio_path, language)
            return segments_to_markdown(segments, language=detected, language_probability=prob)
        except FileNotFoundError as e:
            raise RuntimeError(str(e)) from e
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise RuntimeError(f"转录失败: {e}") from e

    def get_supported_languages(self) -> list:
        return [
            "zh", "en", "ja", "ko", "es", "fr", "de", "it", "pt", "ru",
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no",
        ]

    def get_detected_language(self, transcript_text: Optional[str] = None) -> Optional[str]:
        if self.last_detected_language:
            return self.last_detected_language
        if transcript_text and "**Detected Language:**" in transcript_text:
            for line in transcript_text.split("\n"):
                if "**Detected Language:**" in line:
                    lang = line.split(":")[-1].strip()
                    return lang or None
        return None
