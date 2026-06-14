"""Shared pytest fixtures."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

# Keep imports light: no Whisper preload during test collection.
os.environ.setdefault("WHISPER_PRELOAD", "false")
os.environ.setdefault("WHISPER_ENGINE", "faster-whisper")


@pytest.fixture
def faster_whisper_only():
    """Force engine resolution down the faster-whisper path."""
    with (
        patch("transcriber._mlx_importable", return_value=False),
        patch("transcriber._faster_whisper_importable", return_value=True),
    ):
        yield


@pytest.fixture
def mlx_available():
    with (
        patch("transcriber._mlx_importable", return_value=True),
        patch("transcriber._faster_whisper_importable", return_value=True),
    ):
        yield


@pytest.fixture
def isolated_tasks(tmp_path, monkeypatch):
    """Reset in-memory task state and use a temp tasks.json."""
    import main
    from cache_manager import TranscriptCache

    tasks_file = tmp_path / "tasks.json"
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(main, "TASKS_FILE", tasks_file)
    monkeypatch.setattr(main, "TEMP_DIR", tmp_path / "temp")
    main.TEMP_DIR.mkdir(exist_ok=True)
    monkeypatch.setattr(main, "CACHE_DIR", cache_dir)
    monkeypatch.setattr(main, "transcript_cache", TranscriptCache(cache_dir))
    monkeypatch.setattr(main, "tasks", {})
    monkeypatch.setattr(main, "processing_urls", set())
    monkeypatch.setattr(main, "active_tasks", {})
    monkeypatch.setattr(main, "sse_connections", {})
    yield main


@pytest.fixture
def client(isolated_tasks):
    from fastapi.testclient import TestClient

    with TestClient(isolated_tasks.app, raise_server_exceptions=False) as test_client:
        yield test_client
