"""FastAPI endpoint tests."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import patch


class TestHealthAndInfo:
    def test_root_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Video Trans" in resp.text

    def test_transcriber_info_returns_active_engine(self, client):
        resp = client.get("/api/transcriber-info")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data
        assert "engine" in data["active"]
        assert "engines" in data

    def test_llm_presets_returns_providers_and_models(self, client):
        resp = client.get("/api/llm-presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert "recommended_models" in data
        assert any(p["id"] == "openrouter" for p in data["providers"])

    def test_health_returns_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "video-trans"
        assert "port" in data

    def test_health_reflects_port_env(self, client, monkeypatch):
        monkeypatch.setenv("PORT", "8777")
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["port"] == 8777


class TestProcessVideo:
    def test_missing_url_and_file_returns_400(self, client):
        resp = client.post("/api/process-video", data={"summary_language": "zh"})
        assert resp.status_code == 400
        assert "URL" in resp.json()["detail"] or "upload" in resp.json()["detail"].lower()

    def test_valid_url_creates_task_without_running_pipeline(self, client, isolated_tasks):
        main = isolated_tasks
        with patch.object(main.asyncio, "create_task") as mock_create:
            resp = client.post(
                "/api/process-video",
                data={
                    "url": "https://www.youtube.com/watch?v=test123",
                    "summary_language": "zh",
                },
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "task_id" in body
        assert body["task_id"] in main.tasks
        assert main.tasks[body["task_id"]]["url"].endswith("test123")
        mock_create.assert_called_once()

    def test_duplicate_url_returns_existing_task_id(self, client, isolated_tasks):
        main = isolated_tasks
        url = "https://example.com/video/duplicate"
        main.processing_urls.add(url)
        existing_id = "existing-task-id"
        main.tasks[existing_id] = {"status": "processing", "url": url}

        resp = client.post(
            "/api/process-video",
            data={"url": url, "summary_language": "zh"},
        )

        assert resp.status_code == 200
        assert resp.json()["task_id"] == existing_id


class TestTaskStatus:
    def test_unknown_task_returns_404(self, client):
        resp = client.get("/api/task-status/does-not-exist")
        assert resp.status_code == 404

    def test_existing_task_returns_snapshot(self, client, isolated_tasks):
        main = isolated_tasks
        main.tasks["abc"] = {
            "status": "completed",
            "progress": 100,
            "message": "done",
            "script": "text",
            "summary": None,
            "error": None,
            "url": "https://example.com",
        }

        resp = client.get("/api/task-status/abc")
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["progress"] == 100


class TestCacheAndExport:
    def test_url_cache_hit_skips_pipeline(self, client, isolated_tasks):
        main = isolated_tasks
        url = "https://www.youtube.com/watch?v=cachehit1"
        source_key = main.source_key_from_url(url)
        main.transcript_cache.put(
            source_key,
            "zh",
            {
                "source_ref": url,
                "normalized_url": main.normalize_url(url),
                "video_title": "Cached",
                "detected_language": "en",
                "script": "# Cached\n\nBody",
                "summary": "# Summary\n\nDone",
                "translation": None,
                "script_filename": "transcript_cached_ab12cd.md",
                "summary_filename": "summary_cached_ab12cd.md",
                "translation_filename": None,
                "media_filename": None,
                "safe_title": "cached",
            },
        )

        with patch.object(main.asyncio, "create_task") as mock_create:
            resp = client.post(
                "/api/process-video",
                data={"url": url, "summary_language": "zh"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("from_cache") is True
        mock_create.assert_called_once()

    def test_download_md_from_temp(self, client, isolated_tasks):
        main = isolated_tasks
        script_name = "transcript_demo_ab12cd.md"
        script_path = main.TEMP_DIR / script_name
        script_path.write_text("# demo", encoding="utf-8")

        resp = client.get(f"/api/download/{script_name}")
        assert resp.status_code == 200
        assert "demo" in resp.text

    def test_export_bundle_includes_transcript(self, client, isolated_tasks):
        main = isolated_tasks
        script_name = "transcript_demo_ab12cd.md"
        (main.TEMP_DIR / script_name).write_text("# demo\n\nline", encoding="utf-8")
        task_id = "export-task"
        main.tasks[task_id] = {
            "status": "completed",
            "safe_title": "demo",
            "short_id": "ab12cd",
            "script_filename": script_name,
        }

        resp = client.get(f"/api/export/{task_id}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/zip")

    def test_download_mp4_from_temp(self, client, isolated_tasks):
        main = isolated_tasks
        media_name = "video_demo_ab12cd.mp4"
        (main.TEMP_DIR / media_name).write_bytes(b"\x00\x00\x00\x18ftypmp42")

        resp = client.get(f"/api/download/{media_name}")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("video/")

    def test_export_bundle_includes_video_mp4(self, client, isolated_tasks):
        main = isolated_tasks
        script_name = "transcript_demo_ab12cd.md"
        media_name = "video_demo_ab12cd.mp4"
        (main.TEMP_DIR / script_name).write_text("# demo\n\nline", encoding="utf-8")
        (main.TEMP_DIR / media_name).write_bytes(b"\x00\x00\x00\x18ftypmp42")
        task_id = "export-video-task"
        media_path = main.TEMP_DIR / media_name
        main.tasks[task_id] = {
            "status": "completed",
            "safe_title": "demo",
            "short_id": "ab12cd",
            "script_filename": script_name,
            "media_filename": media_name,
            "media_path": str(media_path),
        }

        resp = client.get(f"/api/export/{task_id}")
        assert resp.status_code == 200

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            names = zf.namelist()
            assert any(n.endswith("_transcript.md") for n in names)
            assert any(n.endswith("_video.mp4") for n in names)

