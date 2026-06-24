import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Pegasus（pegasus1.5）单次 analyze 支持的视频上限为 1 小时，且直接接收视频 URL，
# 由 TwelveLabs 服务端拉取，无需本地下载音频或调用 Whisper。
PEGASUS_MAX_TOKENS = 4096
DEFAULT_MODEL = "pegasus1.5"

# 引导 Pegasus 输出逐句转录文本的提示词；要求纯转录，不要额外解说。
_TRANSCRIPT_PROMPT = (
    "Transcribe the spoken words in this video verbatim. "
    "Output only the transcript text, preserving the original spoken language. "
    "Do not add commentary, timestamps, speaker labels, or descriptions. "
    "If the video contains no speech, briefly describe what is shown instead."
)


class PegasusTranscriber:
    """基于 TwelveLabs Pegasus 的视频转录器（可选后端）。

    与 Transcriber 保持一致的接口契约：transcribe() 返回与 Whisper 输出结构
    相同的 Markdown，供下游 优化→翻译→摘要 管线直接复用。区别在于 Pegasus
    直接处理视频 URL（服务端原生支持长视频），不需要先下载音频。
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("TWELVELABS_API_KEY")
        self.model_name = model_name or os.getenv("TWELVELABS_MODEL", DEFAULT_MODEL)
        self.last_detected_language = None
        self._client = None

    def _load_client(self):
        """延迟加载 TwelveLabs 客户端，避免未启用时强制依赖该 SDK。"""
        if self._client is None:
            if not self.api_key:
                raise Exception("未设置 TWELVELABS_API_KEY，无法使用 Pegasus 转录")
            try:
                from twelvelabs import TwelveLabs
            except ImportError as e:
                raise Exception(
                    "未安装 twelvelabs SDK，请先 `pip install twelvelabs`"
                ) from e
            self._client = TwelveLabs(api_key=self.api_key)
        return self._client

    async def transcribe_url(self, url: str) -> str:
        """对视频 URL 执行 Pegasus 转录，返回 Markdown 文本。

        Args:
            url: 公网可访问的视频地址（TwelveLabs 服务端拉取）。

        Returns:
            与 Whisper 输出结构一致的 Markdown 转录文本。
        """
        from twelvelabs.types.video_context import VideoContext_Url

        client = self._load_client()
        logger.info(f"开始使用 Pegasus（{self.model_name}）转录视频: {url}")

        def _do_analyze():
            return client.analyze(
                model_name=self.model_name,
                video=VideoContext_Url(url=url),
                prompt=_TRANSCRIPT_PROMPT,
                max_tokens=PEGASUS_MAX_TOKENS,
            )

        try:
            res = await asyncio.to_thread(_do_analyze)
        except Exception as e:
            logger.error(f"Pegasus 转录失败: {str(e)}")
            raise Exception(f"Pegasus 转录失败: {str(e)}")

        text = (getattr(res, "data", None) or "").strip()
        if not text:
            raise Exception("Pegasus 返回空转录结果")

        logger.info("Pegasus 转录完成")
        return self._format_transcript(text)

    def _format_transcript(self, text: str) -> str:
        """包装为与 Whisper / 字幕路径一致的 Markdown 结构。

        Pegasus 不返回逐段时间戳，故省略时间戳行；下游管线（optimize_transcript）
        本就会移除时间戳，因此结构上完全兼容。
        """
        return "\n".join([
            "# Video Transcription",
            "",
            "**Detected Language:**",
            "**Language Probability:** —",
            "",
            "## Transcription Content",
            "",
            text,
        ])

    def get_detected_language(self, transcript_text: Optional[str] = None) -> Optional[str]:
        """与 Transcriber 接口一致：返回检测到的语言代码（Pegasus 暂不显式返回）。"""
        return self.last_detected_language

    def is_available(self) -> bool:
        """是否具备使用 Pegasus 的条件（已配置 API Key）。"""
        return bool(self.api_key)
