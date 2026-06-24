"""Tests for the optional TwelveLabs Pegasus transcription backend.

Runs with pytest if available, otherwise as a plain script:
    python tests/test_pegasus_transcriber.py

The live test against the TwelveLabs API only runs when TWELVELABS_API_KEY is set;
it is skipped otherwise so the no-network tests stay runnable everywhere.
"""

import os
import sys
import asyncio

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "backend")
)

from pegasus_transcriber import PegasusTranscriber  # noqa: E402

# 1 分钟以内的公网示例视频，TwelveLabs 服务端可直接拉取
SAMPLE_URL = (
    "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/"
    "Big_Buck_Bunny_360_10s_1MB.mp4"
)


def test_is_available_reflects_api_key():
    # 临时清除环境变量，验证未配置 key 时不可用
    saved = os.environ.pop("TWELVELABS_API_KEY", None)
    try:
        assert PegasusTranscriber(api_key=None).is_available() is False
    finally:
        if saved is not None:
            os.environ["TWELVELABS_API_KEY"] = saved
    assert PegasusTranscriber(api_key="dummy").is_available() is True


def test_format_transcript_matches_whisper_structure():
    t = PegasusTranscriber(api_key="dummy")
    md = t._format_transcript("hello world")
    # 与 Whisper / 字幕路径输出结构一致，供下游管线直接复用
    assert md.startswith("# Video Transcription")
    assert "## Transcription Content" in md
    assert "hello world" in md


def test_get_detected_language_default_none():
    assert PegasusTranscriber(api_key="dummy").get_detected_language() is None


def test_transcribe_url_live():
    """端到端 live 测试，仅在配置 TWELVELABS_API_KEY 时运行。"""
    api_key = os.getenv("TWELVELABS_API_KEY")
    if not api_key:
        print("SKIP test_transcribe_url_live: TWELVELABS_API_KEY not set")
        return

    t = PegasusTranscriber(api_key=api_key)
    md = asyncio.run(t.transcribe_url(SAMPLE_URL))
    assert md.startswith("# Video Transcription")
    assert "## Transcription Content" in md
    # 转录正文非空（去掉 Markdown 头部后仍有内容）
    body = md.split("## Transcription Content", 1)[1].strip()
    assert len(body) > 0


if __name__ == "__main__":
    test_is_available_reflects_api_key()
    test_format_transcript_matches_whisper_structure()
    test_get_detected_language_default_none()
    test_transcribe_url_live()
    print("All tests passed.")
