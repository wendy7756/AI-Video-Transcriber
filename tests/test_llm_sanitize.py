"""Tests for LLM output sanitization."""

from llm_sanitize import strip_llm_artifacts


def test_strip_empty_input():
    assert strip_llm_artifacts("") == ""
    assert strip_llm_artifacts(None) == ""


def test_strip_trailing_english_meta_phrase():
    text = "Summary body here.\n\nLet me know if you need any changes."
    assert strip_llm_artifacts(text) == "Summary body here."


def test_strip_trailing_chinese_meta_phrase():
    text = "这是摘要正文。\n\n如有需要请告诉我。"
    assert strip_llm_artifacts(text) == "这是摘要正文。"


def test_preserves_substantive_content():
    text = "# Title\n\nImportant analysis about the video."
    assert strip_llm_artifacts(text) == text


def test_strip_feel_free_closing():
    text = "Key points listed.\n\nFeel free to ask if you want more detail."
    assert "Feel free" not in strip_llm_artifacts(text)
