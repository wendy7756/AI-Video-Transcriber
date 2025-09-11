# =============================================================================
# backend/transcriber.py - 音頻轉錄器
# =============================================================================
# 此檔案包含音頻轉錄器類別，負責使用Faster-Whisper進行語音轉文字。
# 主要功能包括音頻檔案轉錄、語言檢測、時間戳格式化等。
# 依賴：faster-whisper, WhisperModel等
# =============================================================================

import os
from faster_whisper import WhisperModel
import logging
from typing import Optional

# 在模組層級導入 PyTorch，避免熱重載問題
try:
    import torch
    TORCH_AVAILABLE = True
    TORCH_VERSION = torch.__version__
    CUDA_AVAILABLE = torch.cuda.is_available()
    if CUDA_AVAILABLE:
        DEVICE_COUNT = torch.cuda.device_count()
        DEVICE_NAME = torch.cuda.get_device_name(0) if DEVICE_COUNT > 0 else "Unknown"
        CUDA_VERSION = torch.version.cuda
    else:
        DEVICE_COUNT = 0
        DEVICE_NAME = "None"
        CUDA_VERSION = "N/A"
except ImportError as e:
    TORCH_AVAILABLE = False
    TORCH_VERSION = "N/A"
    CUDA_AVAILABLE = False
    DEVICE_COUNT = 0
    DEVICE_NAME = "None"
    CUDA_VERSION = "N/A"

logger = logging.getLogger(__name__)

class Transcriber:
    """音頻轉錄器，使用Faster-Whisper進行語音轉文字"""

    def __init__(self, model_size: str = "base"):
        """
        初始化轉錄器。

        Args:
            model_size: Whisper模型大小 (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self.last_detected_language = None
        self.device = self._detect_device()

    def _detect_device(self) -> str:
        """
        自動檢測可用的運算裝置。

        Returns:
            str: "cuda" 如果有 GPU，否則 "cpu"
        """
        if TORCH_AVAILABLE:
            logger.info(f"PyTorch 版本: {TORCH_VERSION}")
            
            if CUDA_AVAILABLE and DEVICE_COUNT > 0:
                logger.info(f"檢測到 {DEVICE_COUNT} 個 GPU 裝置: {DEVICE_NAME}")
                logger.info(f"CUDA 版本: {CUDA_VERSION}")
                return "cuda"
            else:
                logger.warning("CUDA 不可用，使用 CPU 模式")
                return "cpu"
        else:
            logger.error("PyTorch 不可用，使用 CPU 模式")
            return "cpu"

    def _load_model(self):
        """
        延遲載入模型。

        當需要時才載入Whisper模型以節省記憶體。
        """
        if self.model is None:
            logger.info(f"正在載入Whisper模型: {self.model_size} (使用 {self.device})")
            try:
                # 根據裝置選擇最佳的運算類型
                compute_type = "float16" if self.device == "cuda" else "int8"

                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=compute_type
                )
                logger.info("模型載入完成")
            except Exception as e:
                logger.error(f"模型載入失敗: {str(e)}")
                raise Exception(f"模型載入失敗: {str(e)}")
    
    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        轉錄音頻檔案。

        Args:
            audio_path: 音頻檔案路徑
            language: 指定語言（可選，如果不指定則自動檢測）

        Returns:
            轉錄文字（Markdown格式）
        """
        try:
            # 檢查檔案是否存在
            if not os.path.exists(audio_path):
                raise Exception(f"音頻檔案不存在: {audio_path}")

            # 載入模型
            self._load_model()

            logger.info(f"開始轉錄音頻: {audio_path}")

            # 直接調用會阻塞事件循環；放入執行緒避免阻塞
            import asyncio
            def _do_transcribe():
                return self.model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=5,
                    best_of=5,
                    temperature=[0.0, 0.2, 0.4],  # 使用溫度遞增策略
                    # 更穩健：開啟VAD與閾值，降低靜音/噪音導致的重複
                    vad_filter=True,
                    vad_parameters={
                        "min_silence_duration_ms": 900,  # 靜音檢測時長
                        "speech_pad_ms": 300  # 語音填充
                    },
                    no_speech_threshold=0.7,  # 無語音閾值
                    compression_ratio_threshold=2.3,  # 壓縮比閾值，檢測重複
                    log_prob_threshold=-1.0,  # 日誌概率閾值
                    # 避免錯誤累積導致的連環重複
                    condition_on_previous_text=False
                )
            segments, info = await asyncio.to_thread(_do_transcribe)

            detected_language = info.language
            self.last_detected_language = detected_language  # 保存檢測到的語言
            logger.info(f"檢測到的語言: {detected_language}")
            logger.info(f"語言檢測概率: {info.language_probability:.2f}")

            # 組裝轉錄結果
            transcript_lines = []
            transcript_lines.append("# Video Transcription")
            transcript_lines.append("")
            transcript_lines.append(f"**Detected Language:** {detected_language}")
            transcript_lines.append(f"**Language Probability:** {info.language_probability:.2f}")
            transcript_lines.append("")
            transcript_lines.append("## Transcription Content")
            transcript_lines.append("")

            # 添加時間戳和文字
            for segment in segments:
                start_time = self._format_time(segment.start)
                end_time = self._format_time(segment.end)
                text = segment.text.strip()

                transcript_lines.append(f"**[{start_time} - {end_time}]**")
                transcript_lines.append("")
                transcript_lines.append(text)
                transcript_lines.append("")

            transcript_text = "\n".join(transcript_lines)
            logger.info("轉錄完成")

            return transcript_text

        except Exception as e:
            logger.error(f"轉錄失敗: {str(e)}")
            raise Exception(f"轉錄失敗: {str(e)}")
    
    def _format_time(self, seconds: float) -> str:
        """
        將秒數轉換為時分秒格式。

        Args:
            seconds: 秒數

        Returns:
            格式化的時間字串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def get_supported_languages(self) -> list:
        """
        獲取支援的語言列表。

        Returns:
            list: 支援的語言代碼列表
        """
        return [
            "zh", "en", "ja", "ko", "es", "fr", "de", "it", "pt", "ru",
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no"
        ]

    def get_detected_language(self, transcript_text: Optional[str] = None) -> Optional[str]:
        """
        獲取檢測到的語言。

        Args:
            transcript_text: 轉錄文字（可選，用於從文字中提取語言資訊）

        Returns:
            檢測到的語言代碼
        """
        # 如果有保存的語言，直接返回
        if self.last_detected_language:
            return self.last_detected_language

        # 如果提供了轉錄文字，嘗試從中提取語言資訊
        if transcript_text and "**Detected Language:**" in transcript_text:
            lines = transcript_text.split('\n')
            for line in lines:
                if "**Detected Language:**" in line:
                    lang = line.split(":")[-1].strip()
                    return lang

        return None
