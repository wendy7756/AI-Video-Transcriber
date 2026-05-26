"""yt-dlp wrapper.

Everything in this module touches yt-dlp; nothing else should. Cookies
and timeout/retry settings come from environment variables (see
``build_network_opts``) because most VPS / datacenter IPs trigger YouTube's
"Sign in to confirm you're not a bot" check and need authenticated
cookies to make any progress.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

import yt_dlp

from . import media
from .subtitle import (
    Segment,
    parse_subtitle_file,
    segments_to_markdown,
)

logger = logging.getLogger(__name__)


def build_network_opts() -> dict:
    """Build cookie / timeout / retry / JS-solver options for yt-dlp from env.

    Environment variables:
        YT_DLP_COOKIES_FILE: path to a Netscape-format cookies.txt
            (passed as ``cookiefile``).
        YT_DLP_COOKIES_BROWSER: spec for ``--cookies-from-browser`` —
            e.g. ``chrome``, ``firefox``, ``chrome:Default`` or
            ``chrome:/path/to/profile``. Mutually exclusive with
            ``YT_DLP_COOKIES_FILE``; the file wins if both are set.
        YT_DLP_SOCKET_TIMEOUT: socket timeout seconds (default 60).
        YT_DLP_RETRIES: retries for transient errors (default 10).
        YT_DLP_FRAGMENT_RETRIES: retries per HLS/DASH fragment (default 10).
        YT_DLP_REMOTE_COMPONENTS: comma-separated list of remote component
            sources for yt-dlp's EJS JS-challenge solver (default
            ``ejs:github``). YouTube's `n` parameter is solved by player.js,
            and yt-dlp downloads a helper script on first use. Without this
            (or a pre-installed JS runtime + bundled solver), yt-dlp only
            sees storyboard formats and ``bestaudio/best`` raises
            ``Requested format is not available``. Set to empty string to
            disable.
    """
    opts: dict = {}

    cookies_file = os.getenv("YT_DLP_COOKIES_FILE", "").strip()
    cookies_browser = os.getenv("YT_DLP_COOKIES_BROWSER", "").strip()
    if cookies_file:
        if os.path.isfile(cookies_file):
            opts["cookiefile"] = cookies_file
        else:
            logger.warning(
                f"YT_DLP_COOKIES_FILE is set but file not found: {cookies_file}"
            )
    elif cookies_browser:
        if ":" in cookies_browser:
            name, profile = cookies_browser.split(":", 1)
            opts["cookiesfrombrowser"] = (name.strip(), profile.strip(), None, None)
        else:
            opts["cookiesfrombrowser"] = (cookies_browser, None, None, None)

    def _env_int(key: str, default: int) -> int:
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default

    opts["socket_timeout"] = _env_int("YT_DLP_SOCKET_TIMEOUT", 60)
    opts["retries"] = _env_int("YT_DLP_RETRIES", 10)
    opts["fragment_retries"] = _env_int("YT_DLP_FRAGMENT_RETRIES", 10)

    # Enable yt-dlp's EJS JS-challenge solver. Required since yt-dlp 2026.x
    # for any non-trivial YouTube video; otherwise bestaudio/best is rejected
    # with "Requested format is not available". A JS runtime (deno or node)
    # must be installed on the host; the Docker image installs deno.
    raw_components = os.getenv("YT_DLP_REMOTE_COMPONENTS", "ejs:github").strip()
    if raw_components:
        opts["remote_components"] = [
            c.strip() for c in raw_components.split(",") if c.strip()
        ]
    return opts


# Language preference fallback when the caller hasn't passed a preferred
# subtitle language (or the preferred language isn't available).
_DEFAULT_LANG_PRIORITY = [
    "id", "id-orig",
    "en", "en-orig",
    "zh-Hans", "zh-Hant", "zh",
    "ja", "ko", "fr", "de", "es",
]


class Downloader:
    """yt-dlp wrapper – probes info, fetches subtitles, downloads audio."""

    def __init__(self) -> None:
        self._base_dl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }],
            "postprocessor_args": [
                "-ac", str(media.AUDIO_CHANNELS),
                "-ar", str(media.AUDIO_SAMPLE_RATE),
                "-movflags", "+faststart",
            ],
            "prefer_ffmpeg": True,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def get_video_info(self, url: str) -> dict:
        info_opts = {"quiet": True, **build_network_opts()}
        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""),
                    "view_count": info.get("view_count", 0),
                    "upload_date": info.get("upload_date", ""),
                    "description": (info.get("description") or "")[:500],
                }
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {}

    async def fetch_subtitles(
        self,
        url: str,
        output_dir: Path,
        preferred_lang: Optional[str] = None,
    ) -> Tuple[Optional[List[Segment]], Optional[str], Optional[str], Optional[Tuple[str, str]]]:
        """Probe platform subtitles. Much faster than audio + Whisper.

        Returns ``(segments, video_title, language, raw_subtitle)`` where
        ``raw_subtitle`` is ``(content, ext_without_dot)`` for persisting
        the original file, or ``None`` if no subtitles are available.
        """
        output_dir.mkdir(exist_ok=True)
        sub_dir = output_dir / f"subs_{uuid.uuid4().hex[:8]}"

        try:
            check_opts = {
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                **build_network_opts(),
            }
            with yt_dlp.YoutubeDL(check_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, False)

            video_title = info.get("title", "unknown")
            manual_subs: dict = info.get("subtitles") or {}
            auto_caps: dict = info.get("automatic_captions") or {}

            manual_langs = [k for k in manual_subs if not k.startswith("live_chat")]
            auto_langs = [k for k in auto_caps if not k.startswith("live_chat")]
            if not manual_langs and not auto_langs:
                logger.info(f"视频无可用字幕: {url}")
                return None, video_title, None, None

            prefer_manual = bool(manual_langs)
            candidates = manual_langs if prefer_manual else auto_langs
            prefer_lang = self._pick_subtitle_lang(candidates, preferred_lang)
            logger.info(
                f"发现{'手动' if prefer_manual else '自动'}字幕，选用语言: {prefer_lang}"
                f"（候选 {len(candidates)} 种）"
            )

            sub_dir.mkdir(exist_ok=True)
            dl_opts = {
                "writesubtitles": prefer_manual,
                "writeautomaticsub": not prefer_manual,
                "subtitlesformat": "vtt/srt/best",
                "subtitleslangs": [prefer_lang],
                "skip_download": True,
                "outtmpl": str(sub_dir / "sub.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                **build_network_opts(),
            }
            with yt_dlp.YoutubeDL(dl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [url])

            sub_files = list(sub_dir.glob("*.vtt")) + list(sub_dir.glob("*.srt"))
            if not sub_files:
                logger.warning("字幕下载后未找到文件，回退音频模式")
                return None, video_title, None, None

            sub_file = sub_files[0]
            stem_parts = sub_file.stem.split(".")
            file_lang = stem_parts[-1] if len(stem_parts) > 1 else prefer_lang

            segments = parse_subtitle_file(sub_file)
            if not segments:
                logger.warning("字幕解析结果为空，回退音频模式")
                return None, video_title, None, None

            raw_payload: Optional[Tuple[str, str]] = None
            try:
                raw_text = sub_file.read_text(encoding="utf-8", errors="replace")
                raw_ext = sub_file.suffix.lstrip(".").lower() or "vtt"
                if raw_text.strip():
                    raw_payload = (raw_text, raw_ext)
            except Exception as e:
                logger.warning(f"读取原始字幕内容失败（仅影响下载，不阻断流程）: {e}")

            logger.info(f"字幕获取成功: lang={file_lang}, {len(segments)} 条目")
            return segments, video_title, file_lang, raw_payload

        except Exception as e:
            logger.warning(f"字幕获取失败（将回退至音频下载）: {e}")
            return None, None, None, None
        finally:
            if sub_dir.exists():
                shutil.rmtree(str(sub_dir), ignore_errors=True)

    async def download_audio(
        self,
        url: str,
        output_dir: Path,
        prefetched_title: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Download the best audio track and normalise to ``.m4a``.

        ``prefetched_title`` lets callers reuse the title from a prior
        ``fetch_subtitles`` probe to skip a redundant network round-trip.
        """
        output_dir.mkdir(exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        output_template = str(output_dir / f"audio_{unique_id}.%(ext)s")

        ydl_opts = {
            **self._base_dl_opts,
            "outtmpl": output_template,
            **build_network_opts(),
        }

        try:
            logger.info(f"开始下载视频: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if prefetched_title:
                    video_title = prefetched_title
                    expected_duration = 0
                    logger.info(f"复用预取标题，跳过 extract_info: {video_title}")
                else:
                    info = await asyncio.to_thread(ydl.extract_info, url, False)
                    video_title = info.get("title", "unknown")
                    expected_duration = info.get("duration") or 0
                    logger.info(f"视频标题: {video_title}")
                await asyncio.to_thread(ydl.download, [url])

            audio_file = str(output_dir / f"audio_{unique_id}.m4a")
            if not os.path.exists(audio_file):
                for ext in ("webm", "mp4", "mp3", "wav"):
                    cand = str(output_dir / f"audio_{unique_id}.{ext}")
                    if os.path.exists(cand):
                        audio_file = cand
                        break
                else:
                    raise RuntimeError("未找到下载的音频文件")

            audio_file = self._maybe_remux(audio_file, expected_duration, output_dir, unique_id)
            logger.info(f"音频文件已保存: {audio_file}")
            return audio_file, video_title

        except Exception as e:
            logger.error(f"下载视频失败: {e}")
            raise RuntimeError(f"下载视频失败: {e}") from e

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_subtitle_lang(
        self,
        candidates: List[str],
        preferred_lang: Optional[str],
    ) -> str:
        normalized = (preferred_lang or "").strip().lower()
        if normalized:
            for lang in candidates:
                if lang.lower() == normalized:
                    logger.info(f"按用户偏好选用字幕语言: {lang}")
                    return lang
            for lang in candidates:
                if lang.lower().split("-")[0] == normalized:
                    logger.info(f"按用户偏好（前缀匹配）选用字幕语言: {lang}")
                    return lang
        return next(
            (lang for lang in _DEFAULT_LANG_PRIORITY if lang in candidates),
            candidates[0],
        )

    def _maybe_remux(
        self,
        audio_file: str,
        expected_duration: float,
        output_dir: Path,
        unique_id: str,
    ) -> str:
        if not expected_duration:
            return audio_file
        actual = media.probe_duration(audio_file)
        if not actual:
            return audio_file
        drift = abs(actual - expected_duration) / expected_duration
        if drift <= 0.1:
            return audio_file

        logger.warning(
            f"音频时长异常，期望 {expected_duration}s，实际 {actual}s，尝试重封装修复…"
        )
        fixed_path = str(output_dir / f"audio_{unique_id}_fixed.m4a")
        ok, err = media.remux_audio(audio_file, fixed_path)
        if not ok:
            logger.error(f"重封装失败：{err}")
            return audio_file
        new_actual = media.probe_duration(fixed_path)
        logger.info(f"重封装完成，新时长≈{new_actual:.2f}s")
        return fixed_path


def render_segments_as_markdown(
    segments: List[Segment],
    language: Optional[str],
) -> str:
    """Compatibility shim: turn ``Segment`` list into the legacy Markdown shape."""
    return segments_to_markdown(segments, language=language, language_probability=1.0)
