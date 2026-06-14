"""Tests for Whisper engine selection and Transcriber configuration."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from transcriber import (
    MLX_MODEL_REPOS,
    Transcriber,
    _mlx_repo_for_model,
    _resolve_device,
    _resolve_engine,
    detect_whisper_engines,
)


class TestResolveEngine:
    def test_auto_prefers_mlx_when_available(self, mlx_available):
        assert _resolve_engine("auto") == "mlx-whisper"

    def test_auto_falls_back_to_faster_whisper(self, faster_whisper_only):
        assert _resolve_engine("auto") == "faster-whisper"

    def test_faster_aliases_normalize(self, faster_whisper_only):
        assert _resolve_engine("fw") == "faster-whisper"

    def test_mlx_alias_when_available(self, mlx_available):
        assert _resolve_engine("mlx") == "mlx-whisper"

    def test_forced_mlx_raises_when_unavailable(self, faster_whisper_only):
        with pytest.raises(RuntimeError, match="mlx"):
            _resolve_engine("mlx-whisper")

    def test_forced_faster_raises_when_unavailable(self):
        with patch("transcriber._faster_whisper_importable", return_value=False):
            with pytest.raises(RuntimeError, match="faster-whisper"):
                _resolve_engine("faster-whisper")

    def test_unknown_engine_raises(self, faster_whisper_only):
        with pytest.raises(RuntimeError, match="未知"):
            _resolve_engine("unknown-engine")


class TestResolveDevice:
    def test_auto_without_cuda_uses_cpu_int8(self):
        with patch("transcriber._resolve_device.__module__", "transcriber"):
            device, compute = _resolve_device("auto")
        assert device == "cpu"
        assert compute == "int8"

    def test_explicit_cuda(self):
        device, compute = _resolve_device("cuda")
        assert device == "cuda"
        assert compute == "float16"

    def test_explicit_cpu(self):
        device, compute = _resolve_device("cpu")
        assert device == "cpu"
        assert compute == "int8"


class TestMlxRepoMapping:
    @pytest.mark.parametrize(
        "model_size,expected",
        [
            ("tiny", MLX_MODEL_REPOS["tiny"]),
            ("base", MLX_MODEL_REPOS["base"]),
            ("large-v3", MLX_MODEL_REPOS["large-v3"]),
        ],
    )
    def test_known_models_map_to_hf_repo(self, model_size, expected):
        assert _mlx_repo_for_model(model_size) == expected

    def test_unknown_model_uses_default_pattern(self):
        assert _mlx_repo_for_model("distil") == "mlx-community/whisper-distil"


class TestTranscriberConfig:
    def test_from_env_reads_whisper_variables(self, faster_whisper_only, monkeypatch):
        monkeypatch.setenv("WHISPER_MODEL_SIZE", "small")
        monkeypatch.setenv("WHISPER_DEVICE", "cpu")
        monkeypatch.setenv("WHISPER_SPEED_PRESET", "quality")
        monkeypatch.setenv("WHISPER_ENGINE", "faster-whisper")

        t = Transcriber.from_env()

        assert t.model_size == "small"
        assert t.device == "cpu"
        assert t.speed_preset == "quality"
        assert t.engine == "faster-whisper"

    def test_invalid_preset_falls_back_to_balanced(self, faster_whisper_only):
        t = Transcriber(speed_preset="not-a-preset")
        assert t.speed_preset == "balanced"
        assert t.model_size == "base"

    def test_fast_preset_uses_tiny_model(self, faster_whisper_only):
        t = Transcriber(speed_preset="fast")
        assert t.model_size == "tiny"
        assert t.beam_size == 1

    def test_describe_includes_engine_and_device(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper", speed_preset="fast", device="cpu")
        desc = t.describe()
        assert "faster-whisper" in desc
        assert "device=cpu" in desc

    def test_info_merges_detection_with_active_config(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper")
        info = t.info()
        assert "platform" in info
        assert "engines" in info
        assert info["active"]["engine"] == "faster-whisper"
        assert "describe" in info["active"]


class TestTranscriberHelpers:
    def test_format_time_under_one_hour(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper")
        assert t._format_time(65) == "01:05"

    def test_format_time_with_hours(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper")
        assert t._format_time(3661) == "01:01:01"

    def test_get_detected_language_from_transcript_markdown(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper")
        text = "# Video Transcription\n\n**Detected Language:** en\n"
        assert t.get_detected_language(text) == "en"

    @pytest.mark.asyncio
    async def test_transcribe_raises_when_audio_missing(self, faster_whisper_only):
        t = Transcriber(engine="faster-whisper")
        with pytest.raises(Exception, match="音频文件不存在"):
            await t.transcribe("/path/does/not/exist.wav")


class TestDetectWhisperEngines:
    def test_returns_platform_and_engine_availability(self):
        info = detect_whisper_engines()
        assert "platform" in info
        assert "engines" in info
        assert "mlx-whisper" in info["engines"]
        assert "faster-whisper" in info["engines"]
        assert isinstance(info["engines"]["faster-whisper"]["available"], bool)
