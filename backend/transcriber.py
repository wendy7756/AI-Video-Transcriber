import os
import asyncio
import logging
import platform
from typing import Any, Optional

logger = logging.getLogger(__name__)

SPEED_PRESETS = {
    "fast": {
        "model_size": "tiny",
        "beam_size": 1,
        "best_of": 1,
        "temperature": [0.0],
    },
    "balanced": {
        "model_size": "base",
        "beam_size": 3,
        "best_of": 3,
        "temperature": [0.0, 0.2],
    },
    "quality": {
        "model_size": "small",
        "beam_size": 5,
        "best_of": 5,
        "temperature": [0.0, 0.2, 0.4],
    },
}

MLX_MODEL_REPOS = {
    "tiny": "mlx-community/whisper-tiny",
    "base": "mlx-community/whisper-base-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
    "large-v2": "mlx-community/whisper-large-v2-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
}


def _is_apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine().lower() in ("arm64", "aarch64")


def _mlx_importable() -> bool:
    if not _is_apple_silicon():
        return False
    try:
        import mlx_whisper  # noqa: F401

        return True
    except Exception:
        return False


def _faster_whisper_importable() -> bool:
    try:
        from faster_whisper import WhisperModel  # noqa: F401

        return True
    except Exception:
        return False


def detect_whisper_engines() -> dict[str, Any]:
    """Return runtime engine availability for diagnostics / UI."""
    mlx_ok = _mlx_importable()
    faster_ok = _faster_whisper_importable()
    return {
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "apple_silicon": _is_apple_silicon(),
        },
        "engines": {
            "mlx-whisper": {
                "available": mlx_ok,
                "reason": None
                if mlx_ok
                else (
                    "requires Apple Silicon + mlx-whisper package"
                    if _is_apple_silicon()
                    else "requires macOS Apple Silicon"
                ),
            },
            "faster-whisper": {
                "available": faster_ok,
                "reason": None if faster_ok else "faster-whisper not installed",
            },
        },
    }


def _resolve_device(device: str) -> tuple[str, str]:
    """Pick faster-whisper device/compute_type. CUDA when available, else CPU."""
    device = (device or "auto").lower()
    if device == "auto":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:
            pass
        return "cpu", "int8"
    if device == "cuda":
        return "cuda", "float16"
    return "cpu", "int8"


def _resolve_engine(requested: str) -> str:
    requested = (requested or "auto").strip().lower()
    aliases = {
        "mlx": "mlx-whisper",
        "mlx_whisper": "mlx-whisper",
        "faster": "faster-whisper",
        "faster_whisper": "faster-whisper",
        "fw": "faster-whisper",
    }
    requested = aliases.get(requested, requested)

    if requested == "auto":
        if _mlx_importable():
            return "mlx-whisper"
        return "faster-whisper"

    if requested == "mlx-whisper":
        if not _mlx_importable():
            raise RuntimeError(
                "WHISPER_ENGINE=mlx 不可用：需要 Apple Silicon 且已安装 mlx-whisper"
            )
        return "mlx-whisper"

    if requested == "faster-whisper":
        if not _faster_whisper_importable():
            raise RuntimeError("WHISPER_ENGINE=faster-whisper 不可用：未安装 faster-whisper")
        return "faster-whisper"

    raise RuntimeError(f"未知 WHISPER_ENGINE: {requested}")


def _mlx_repo_for_model(model_size: str) -> str:
    return MLX_MODEL_REPOS.get(model_size, f"mlx-community/whisper-{model_size}")


class Transcriber:
    """音频转录器，支持 mlx-whisper（Apple Silicon）与 faster-whisper。"""

    def __init__(
        self,
        model_size: Optional[str] = None,
        device: str = "auto",
        speed_preset: str = "balanced",
        engine: str = "auto",
    ):
        preset_name = speed_preset if speed_preset in SPEED_PRESETS else "balanced"
        preset = SPEED_PRESETS[preset_name]
        self.speed_preset = preset_name
        self.model_size = (model_size or preset["model_size"]).strip()
        self.beam_size = preset["beam_size"]
        self.best_of = preset["best_of"]
        self.temperature = preset["temperature"]
        self.device, self.compute_type = _resolve_device(device)
        self.engine = _resolve_engine(engine)
        self.mlx_repo = _mlx_repo_for_model(self.model_size)
        self.model = None
        self.last_detected_language = None

    @classmethod
    def from_env(cls) -> "Transcriber":
        model_size = os.getenv("WHISPER_MODEL_SIZE", "").strip() or None
        device = os.getenv("WHISPER_DEVICE", "auto").strip()
        speed_preset = os.getenv("WHISPER_SPEED_PRESET", "balanced").strip()
        engine = os.getenv("WHISPER_ENGINE", "auto").strip()
        return cls(
            model_size=model_size,
            device=device,
            speed_preset=speed_preset,
            engine=engine,
        )

    def describe(self) -> str:
        if self.engine == "mlx-whisper":
            return (
                f"engine={self.engine}, preset={self.speed_preset}, "
                f"model={self.model_size}, repo={self.mlx_repo}"
            )
        return (
            f"engine={self.engine}, preset={self.speed_preset}, model={self.model_size}, "
            f"device={self.device}, compute={self.compute_type}"
        )

    def info(self) -> dict[str, Any]:
        data = detect_whisper_engines()
        data["active"] = {
            "engine": self.engine,
            "preset": self.speed_preset,
            "model_size": self.model_size,
            "describe": self.describe(),
        }
        return data

    def _load_faster_whisper_model(self):
        from faster_whisper import WhisperModel

        if self.model is None:
            logger.info(f"正在加载 faster-whisper 模型: {self.describe()}")
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("faster-whisper 模型加载完成")

    def _load_model(self):
        if self.engine == "mlx-whisper":
            if not _mlx_importable():
                raise RuntimeError("mlx-whisper 不可用")
            logger.info(f"mlx-whisper 就绪: {self.describe()}")
            return
        self._load_faster_whisper_model()

    def preload(self):
        """启动时预加载模型，避免首个任务冷启动。"""
        if self.engine == "mlx-whisper":
            logger.info(f"mlx-whisper 将在首次转录时加载权重: {self.mlx_repo}")
            return
        self._load_faster_whisper_model()

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        try:
            if not os.path.exists(audio_path):
                raise Exception(f"音频文件不存在: {audio_path}")

            self._load_model()
            logger.info(f"开始转录音频: {audio_path} ({self.describe()})")

            if self.engine == "mlx-whisper":
                transcript_text = await asyncio.to_thread(
                    self._transcribe_mlx, audio_path, language
                )
            else:
                transcript_text = await asyncio.to_thread(
                    self._transcribe_faster_whisper, audio_path, language
                )

            logger.info("转录完成")
            return transcript_text

        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise Exception(f"转录失败: {e}") from e

    def _transcribe_mlx(self, audio_path: str, language: Optional[str] = None) -> str:
        import mlx_whisper

        temperature = tuple(self.temperature)
        kwargs: dict[str, Any] = {
            "path_or_hf_repo": self.mlx_repo,
            "temperature": temperature,
            "condition_on_previous_text": False,
            "verbose": False,
        }
        if language:
            kwargs["language"] = language

        result = mlx_whisper.transcribe(audio_path, **kwargs)
        detected_language = result.get("language") or language or "unknown"
        self.last_detected_language = detected_language

        segments = result.get("segments") or []
        language_probability = result.get("language_probability")
        if language_probability is None:
            language_probability = 1.0 if language else 0.99

        logger.info(f"检测到的语言: {detected_language}")

        transcript_lines = [
            "# Video Transcription",
            "",
            f"**Detected Language:** {detected_language}",
            f"**Language Probability:** {language_probability:.2f}",
            "",
            "## Transcription Content",
            "",
        ]

        for segment in segments:
            start_time = self._format_time(float(segment.get("start", 0)))
            end_time = self._format_time(float(segment.get("end", 0)))
            text = str(segment.get("text", "")).strip()
            transcript_lines.extend([
                f"**[{start_time} - {end_time}]**",
                "",
                text,
                "",
            ])

        return "\n".join(transcript_lines)

    def _transcribe_faster_whisper(self, audio_path: str, language: Optional[str] = None) -> str:
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=self.beam_size,
            best_of=self.best_of,
            temperature=self.temperature,
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

        detected_language = info.language
        self.last_detected_language = detected_language
        logger.info(f"检测到的语言: {detected_language}")
        logger.info(f"语言检测概率: {info.language_probability:.2f}")

        transcript_lines = [
            "# Video Transcription",
            "",
            f"**Detected Language:** {detected_language}",
            f"**Language Probability:** {info.language_probability:.2f}",
            "",
            "## Transcription Content",
            "",
        ]

        for segment in segments:
            start_time = self._format_time(segment.start)
            end_time = self._format_time(segment.end)
            text = segment.text.strip()
            transcript_lines.extend([
                f"**[{start_time} - {end_time}]**",
                "",
                text,
                "",
            ])

        return "\n".join(transcript_lines)

    def _format_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

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
                    lang = line.split("**Detected Language:**", 1)[-1].strip()
                    return lang if lang else None
        return None
