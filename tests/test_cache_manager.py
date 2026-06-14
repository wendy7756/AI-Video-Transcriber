"""Tests for local transcript cache."""

from __future__ import annotations

from pathlib import Path

from cache_manager import (
    TranscriptCache,
    normalize_url,
    source_key_from_file,
    source_key_from_url,
)


class TestNormalizeUrl:
    def test_youtube_watch_and_short_link_share_key(self):
        a = normalize_url("https://www.youtube.com/watch?v=abc123XYZ")
        b = normalize_url("https://youtu.be/abc123XYZ?si=foo")
        assert a == b == "youtube:abc123XYZ"

    def test_bilibili_normalizes_bv_id(self):
        url = "https://www.bilibili.com/video/BV1xx411c7mD/?spm_id_from=333.1007.top_right_bar_window"
        assert normalize_url(url) == "bilibili:BV1XX411C7MD"


class TestSourceKeys:
    def test_same_url_same_key(self):
        url = "https://example.com/video/1"
        assert source_key_from_url(url) == source_key_from_url(url)

    def test_file_key_is_content_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello", encoding="utf-8")
        f2.write_text("hello", encoding="utf-8")
        assert source_key_from_file(f1) == source_key_from_file(f2)


class TestTranscriptCache:
    def test_put_get_and_hydrate(self, tmp_path):
        cache = TranscriptCache(tmp_path / "cache")
        media = tmp_path / "clip.m4a"
        media.write_bytes(b"fake-audio")

        source_key = source_key_from_url("https://youtu.be/demo123")
        payload = {
            "source_ref": "https://youtu.be/demo123",
            "normalized_url": "youtube:demo123",
            "video_title": "Demo",
            "detected_language": "en",
            "script": "# Demo\n\nHello",
            "summary": "# Summary\n\nHi",
            "translation": None,
            "script_filename": "transcript_demo_ab12cd.md",
            "summary_filename": "summary_demo_ab12cd.md",
            "translation_filename": None,
            "media_filename": "media.m4a",
            "safe_title": "demo",
        }
        cache.put(source_key, "zh", payload, media_src=media)

        loaded = cache.get(source_key, "zh")
        assert loaded is not None
        assert loaded["from_cache"] is True
        assert loaded["script"].startswith("# Demo")

        task = cache.hydrate_task(loaded, "task-uuid-1234", "https://youtu.be/demo123")
        assert task["status"] == "completed"
        assert task["from_cache"] is True
        assert task["media_path"]
        assert Path(task["media_path"]).exists()

    def test_missing_variant_returns_none(self, tmp_path):
        cache = TranscriptCache(tmp_path / "cache")
        source_key = source_key_from_url("https://example.com/a")
        assert cache.get(source_key, "zh") is None

    def test_resolve_file_from_entry(self, tmp_path):
        cache = TranscriptCache(tmp_path / "cache")
        source_key = "url:abc123"
        entry_dir = cache._entry_dir(source_key)
        entry_dir.mkdir(parents=True)
        script_name = "transcript_x.md"
        (entry_dir / script_name).write_text("# x", encoding="utf-8")
        cache._index["entries"][source_key] = {"shared": {}, "variants": {}}
        assert cache.resolve_file(source_key, script_name) == entry_dir / script_name
