"""Tests for main.py helper functions and task persistence."""

from __future__ import annotations

from main import _sanitize_title_for_filename, _txt_to_raw_transcript_markdown, load_tasks, save_tasks


class TestSanitizeTitle:
    def test_empty_title_becomes_untitled(self):
        assert _sanitize_title_for_filename("") == "untitled"

    def test_removes_unsafe_characters(self):
        assert _sanitize_title_for_filename('Hello <World>!') == "Hello_World"

    def test_truncates_long_titles(self):
        title = "a" * 120
        assert len(_sanitize_title_for_filename(title)) == 80


class TestTxtToMarkdown:
    def test_wraps_plain_text_in_transcript_template(self):
        md = _txt_to_raw_transcript_markdown("hello world")
        assert "# Video Transcription" in md
        assert "## Transcription Content" in md
        assert "hello world" in md

    def test_empty_body_becomes_placeholder(self):
        md = _txt_to_raw_transcript_markdown("   ")
        assert "(empty)" in md


class TestTaskPersistence:
    def test_save_and_load_roundtrip(self, isolated_tasks, tmp_path):
        main = isolated_tasks
        payload = {"task-1": {"status": "processing", "progress": 10}}
        main.tasks.clear()
        main.tasks.update(payload)
        save_tasks(main.tasks)

        loaded = load_tasks()
        assert loaded["task-1"]["status"] == "processing"

    def test_load_missing_file_returns_empty_dict(self, isolated_tasks):
        main = isolated_tasks
        assert main.TASKS_FILE.exists() is False
        assert load_tasks() == {}
