"""VideoProcessor unit tests (no network)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from video_processor import VideoProcessor, _resolve_ffmpeg_dir


class TestResolveFfmpegDir:
    def test_prefers_which_when_available(self):
        with patch("video_processor.shutil.which", return_value="/opt/homebrew/bin/ffmpeg"):
            assert _resolve_ffmpeg_dir() == "/opt/homebrew/bin"

    def test_falls_back_to_homebrew_path(self):
        with patch("video_processor.shutil.which", return_value=None):
            with patch("video_processor.Path.exists", return_value=True):
                assert _resolve_ffmpeg_dir() == "/opt/homebrew/bin"


class TestVideoProcessorConfig:
    def test_video_format_prefers_mp4_up_to_720p(self):
        vp = VideoProcessor()
        assert "height<=720" in vp.video_format
        assert "mp4" in vp.video_format

    def test_base_ydl_opts_includes_ffmpeg_location_when_set(self):
        vp = VideoProcessor()
        vp.ydl_opts["ffmpeg_location"] = "/opt/homebrew/bin"
        opts = vp._base_ydl_opts("/tmp/video_%(ext)s")
        assert opts["ffmpeg_location"] == "/opt/homebrew/bin"
        assert opts["outtmpl"] == "/tmp/video_%(ext)s"
        assert opts["noplaylist"] is True


@pytest.mark.asyncio
async def test_extract_whisper_audio_invokes_ffmpeg(tmp_path, monkeypatch):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    out_dir = tmp_path / "out"

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        out = Path(cmd[-1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"audio")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr("video_processor.subprocess.run", fake_run)
    monkeypatch.setattr("video_processor.shutil.which", lambda _: "/usr/bin/ffmpeg")

    vp = VideoProcessor()
    result = await vp.extract_whisper_audio(video, out_dir, "abcd1234")

    assert result.endswith("audio_abcd1234.m4a")
    assert calls
    assert calls[0][0] == "/usr/bin/ffmpeg"
    assert "-ar" in calls[0] and "16000" in calls[0]
