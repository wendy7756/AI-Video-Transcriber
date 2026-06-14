"""Local transcript cache: skip re-download / re-transcribe for the same source."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse, urlunparse

CACHE_VERSION = 2


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    """Normalize a video URL for stable cache keys."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    if "youtube.com" in netloc or "youtu.be" in netloc:
        video_id = None
        if "youtu.be" in netloc:
            video_id = parsed.path.strip("/").split("/")[0] or None
        else:
            qs = parse_qs(parsed.query)
            video_id = (qs.get("v") or [None])[0]
        if video_id:
            return f"youtube:{video_id}"

    if "bilibili.com" in netloc:
        m = re.search(r"/video/(BV[\w]+)", parsed.path, re.I)
        if m:
            return f"bilibili:{m.group(1).upper()}"

    path = parsed.path.rstrip("/") or "/"
    cleaned = urlunparse((scheme, netloc, path, "", "", ""))
    return cleaned


def source_key_from_url(url: str) -> str:
    normalized = normalize_url(url)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"url:{digest}"


def source_key_from_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return f"file:{h.hexdigest()}"


class TranscriptCache:
    """Persistent cache keyed by video URL / upload content hash."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._index: dict[str, Any] = self._load_index()

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"version": CACHE_VERSION, "entries": {}}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if (
                isinstance(data, dict)
                and isinstance(data.get("entries"), dict)
                and data.get("version") == CACHE_VERSION
            ):
                return data
        except Exception:
            pass
        return {"version": CACHE_VERSION, "entries": {}}

    def _save_index(self) -> None:
        self.index_path.write_text(
            json.dumps(self._index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _entry_dir(self, source_key: str) -> Path:
        safe = source_key.replace(":", "_")
        return self.root / "entries" / safe

    def get(self, source_key: str, summary_language: str) -> Optional[dict[str, Any]]:
        entry = self._index.get("entries", {}).get(source_key)
        if not entry:
            return None
        variants = entry.get("variants") or {}
        variant = variants.get(summary_language)
        if not variant:
            return None
        merged = {**entry.get("shared", {}), **variant}
        merged["source_key"] = source_key
        merged["summary_language"] = summary_language
        merged["from_cache"] = True
        if not self._variant_files_exist(merged):
            return None
        return merged

    def _variant_files_exist(self, data: dict[str, Any]) -> bool:
        script_name = data.get("script_filename")
        if not script_name:
            return False
        entry_dir = self._entry_dir(data["source_key"])
        if not (entry_dir / script_name).exists():
            return False
        media_name = data.get("media_filename")
        if media_name and not (entry_dir / media_name).exists():
            return False
        return True

    def put(
        self,
        source_key: str,
        summary_language: str,
        payload: dict[str, Any],
        media_src: Optional[Path] = None,
    ) -> dict[str, Any]:
        entry_dir = self._entry_dir(source_key)
        entry_dir.mkdir(parents=True, exist_ok=True)

        shared = self._index.setdefault("entries", {}).setdefault(source_key, {})
        shared.setdefault("shared", {})
        shared["shared"].update({
            "source_ref": payload.get("source_ref"),
            "video_title": payload.get("video_title"),
            "detected_language": payload.get("detected_language"),
            "normalized_url": payload.get("normalized_url"),
            "updated_at": _utc_now(),
        })

        script_filename = payload.get("script_filename")
        if script_filename and payload.get("script"):
            (entry_dir / script_filename).write_text(payload["script"], encoding="utf-8")

        summary_filename = payload.get("summary_filename")
        if summary_filename and payload.get("summary"):
            (entry_dir / summary_filename).write_text(payload["summary"], encoding="utf-8")

        translation_filename = payload.get("translation_filename")
        if translation_filename and payload.get("translation"):
            (entry_dir / translation_filename).write_text(payload["translation"], encoding="utf-8")

        media_filename = payload.get("media_filename")
        if media_src and media_src.exists() and media_filename:
            dest = entry_dir / media_filename
            if media_src.resolve() != dest.resolve():
                shutil.copy2(media_src, dest)

        variant = {
            "summary_language": summary_language,
            "script": payload.get("script"),
            "summary": payload.get("summary"),
            "translation": payload.get("translation"),
            "script_filename": script_filename,
            "summary_filename": summary_filename,
            "translation_filename": translation_filename,
            "media_filename": media_filename,
            "safe_title": payload.get("safe_title"),
            "cached_at": _utc_now(),
        }
        shared.setdefault("variants", {})[summary_language] = variant
        self._save_index()
        return variant

    def resolve_media_path(self, source_key: str, media_filename: str) -> Optional[Path]:
        if not media_filename:
            return None
        path = self._entry_dir(source_key) / media_filename
        return path if path.exists() else None

    def resolve_file(self, source_key: str, filename: str) -> Optional[Path]:
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            return None
        path = self._entry_dir(source_key) / filename
        return path if path.exists() else None

    def list_entries(self) -> list[dict[str, Any]]:
        out = []
        for key, entry in (self._index.get("entries") or {}).items():
            out.append({
                "source_key": key,
                "video_title": (entry.get("shared") or {}).get("video_title"),
                "source_ref": (entry.get("shared") or {}).get("source_ref"),
                "variants": list((entry.get("variants") or {}).keys()),
                "updated_at": (entry.get("shared") or {}).get("updated_at"),
            })
        return out

    def hydrate_task(self, cached: dict[str, Any], task_id: str, source_ref: str) -> dict[str, Any]:
        short_id = task_id.replace("-", "")[:6]
        entry_dir = self._entry_dir(cached["source_key"])
        script_path = entry_dir / cached["script_filename"]
        summary_path = entry_dir / cached["summary_filename"] if cached.get("summary_filename") else None
        translation_path = (
            entry_dir / cached["translation_filename"] if cached.get("translation_filename") else None
        )
        media_path = (
            entry_dir / cached["media_filename"] if cached.get("media_filename") else None
        )

        result = {
            "status": "completed",
            "progress": 100,
            "message": "已从本地缓存加载（跳过重复转写）",
            "url": source_ref,
            "video_title": cached.get("video_title"),
            "script": cached.get("script"),
            "summary": cached.get("summary"),
            "translation": cached.get("translation"),
            "script_path": str(script_path),
            "summary_path": str(summary_path) if summary_path else None,
            "translation_path": str(translation_path) if translation_path else None,
            "script_filename": cached.get("script_filename"),
            "summary_filename": cached.get("summary_filename"),
            "translation_filename": cached.get("translation_filename"),
            "media_filename": cached.get("media_filename"),
            "media_path": str(media_path) if media_path and media_path.exists() else None,
            "short_id": short_id,
            "safe_title": cached.get("safe_title"),
            "detected_language": cached.get("detected_language"),
            "summary_language": cached.get("summary_language"),
            "from_cache": True,
            "cache_source_key": cached.get("source_key"),
        }
        return result
