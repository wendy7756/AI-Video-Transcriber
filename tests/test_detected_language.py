"""Regression tests: .txt input reported detected_language "**".

Run: venv/bin/python -m unittest discover tests
"""
import logging
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
logging.disable(logging.CRITICAL)

from pipeline import txt_to_raw_transcript_markdown  # noqa: E402
from transcriber import Transcriber  # noqa: E402
from translator import Translator  # noqa: E402

EN_TEXT = "Hello everyone, today I want to talk about teleprompters and how to read naturally."
ZH_TEXT = "大家好，今天我想聊聊为什么刚开始看提词器读稿会觉得不自然，以及怎么练习。"


def detect(header_value: str):
    transcript = f"# Video Transcription\n\n**Detected Language:**{header_value}\n\n## Transcription Content\n\nhi\n"
    return Transcriber().get_detected_language(transcript)


def resolve_language(raw_script: str) -> str:
    """Mirrors the detection step in transcribe.py / main.py."""
    translator = Translator()
    detected = (Transcriber().get_detected_language(raw_script) or "").strip()
    if not detected:
        detected = translator.infer_language_code(raw_script)
    return translator.normalize_lang_code(detected) or detected


class DetectedLanguageTests(unittest.TestCase):
    def test_whisper_header(self):
        self.assertEqual(detect(" en"), "en")

    def test_subtitle_header_with_region(self):
        self.assertEqual(detect(" zh-Hans"), "zh-Hans")

    def test_three_letter_code(self):
        self.assertEqual(detect(" yue"), "yue")

    def test_empty_header_from_text_file_is_none(self):
        self.assertIsNone(detect(""))
        self.assertIsNone(detect("   "))

    def test_garbage_value_is_none(self):
        self.assertIsNone(detect(" —"))
        self.assertIsNone(detect(" **"))

    def test_saved_language_still_wins(self):
        transcriber = Transcriber()
        transcriber.last_detected_language = "ja"
        self.assertEqual(transcriber.get_detected_language("**Detected Language:**\n"), "ja")


class TextFileInputTests(unittest.TestCase):
    def test_english_txt_is_inferred_from_content(self):
        self.assertEqual(resolve_language(txt_to_raw_transcript_markdown(EN_TEXT)), "en")

    def test_chinese_txt_is_inferred_from_content(self):
        self.assertEqual(resolve_language(txt_to_raw_transcript_markdown(ZH_TEXT)), "zh")

    def test_chinese_txt_with_chinese_summary_is_not_translated(self):
        detected = resolve_language(txt_to_raw_transcript_markdown(ZH_TEXT))
        self.assertFalse(Translator().languages_differ_for_translation(detected, "zh"))


if __name__ == "__main__":
    unittest.main()
