"""Job lifecycle helpers.

The FastAPI layer keeps a dict of in-flight task metadata that's
persisted to ``tasks.json`` so a restart doesn't lose progress. The
plumbing is small but appears in many places, so it lives here.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class JobStore:
    """Thread-safe JSON-backed task store.

    Not an async API on purpose — the writes are tiny and synchronous I/O
    keeps the rest of the pipeline simpler.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> Dict[str, Dict[str, Any]]:
        try:
            if self._path.exists():
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"读取任务状态失败（重置为空）: {e}")
        return {}

    def save(self) -> None:
        try:
            with self._lock:
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")

    # ------------------------------------------------------------------
    # Dict-style accessors (keeps existing call-sites idiomatic)
    # ------------------------------------------------------------------

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __getitem__(self, key: str) -> Dict[str, Any]:
        return self._data[key]

    def __setitem__(self, key: str, value: Dict[str, Any]) -> None:
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def items(self):
        return self._data.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def setdefault(self, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
        return self._data.setdefault(key, default)

    @property
    def data(self) -> Dict[str, Dict[str, Any]]:
        return self._data
