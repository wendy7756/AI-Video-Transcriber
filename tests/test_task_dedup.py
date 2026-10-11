"""Regression tests for task dedup and zombie tasks left over from a restart.

Run: venv/bin/python -m unittest discover tests
"""
import asyncio
import json
import logging
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# main 在导入时读取 tasks.json，必须先把临时目录指过去，不能碰真实的 temp/
_TEMP = tempfile.mkdtemp(prefix="transcriber-test-")
os.environ["TRANSCRIBER_TEMP_DIR"] = _TEMP
Path(_TEMP, "tasks.json").write_text(json.dumps({
    "zombie": {"status": "processing", "progress": 80, "url": "https://example.com/v", "message": "正在生成摘要..."},
    "done": {"status": "completed", "progress": 100, "url": "https://example.com/old"},
}), encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
logging.disable(logging.CRITICAL)

import main  # noqa: E402

# TestClient 每个用例都会走一遍 lifespan，关闭看门狗否则会把测试进程直接退出
main.SHUTDOWN_FORCE_EXIT_SECONDS = None
from fastapi.testclient import TestClient  # noqa: E402

# 导入时的任务状态快照；DedupTests 会清空 main.tasks
TASKS_AT_STARTUP = json.loads(json.dumps(main.tasks))
DISK_AT_STARTUP = json.loads(Path(_TEMP, "tasks.json").read_text(encoding="utf-8"))

URL = "https://www.youtube.com/watch?v=test"


class StartupTests(unittest.TestCase):
    def test_processing_tasks_from_previous_run_are_marked_interrupted(self):
        self.assertEqual(TASKS_AT_STARTUP["zombie"]["status"], "error")
        self.assertEqual(TASKS_AT_STARTUP["zombie"]["error"], main.INTERRUPTED_MESSAGE)
        self.assertEqual(TASKS_AT_STARTUP["done"]["status"], "completed")

    def test_interrupted_status_is_persisted(self):
        self.assertEqual(DISK_AT_STARTUP["zombie"]["status"], "error")


class DedupTests(unittest.TestCase):
    def setUp(self):
        self.started = []
        self.cancelled = []

        async def fake_process_video_task(task_id, url, *args, **kwargs):
            self.started.append(task_id)
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                self.cancelled.append(task_id)
                raise

        self._orig_task = main.process_video_task
        main.process_video_task = fake_process_video_task
        main.tasks.clear()
        main.active_tasks.clear()
        main.processing_urls.clear()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        for job in list(main.active_tasks.values()):
            self.client.portal.call(self._cancel, job)
        self.client.__exit__(None, None, None)
        main.process_video_task = self._orig_task

    @staticmethod
    async def _cancel(job):
        job.cancel()

    def submit(self, url=URL, model="model-a", language="zh"):
        resp = self.client.post("/api/process-video", data={
            "url": url, "summary_language": language, "model_id": model,
            "api_key": "k", "model_base_url": "https://api.example.com/v1",
        })
        self.assertEqual(resp.status_code, 200)
        return resp.json()["task_id"]

    def wait_until(self, predicate):
        for _ in range(100):
            if predicate():
                return
            time.sleep(0.01)
        self.fail("condition not met")

    def test_same_settings_reuse_running_task(self):
        first = self.submit()
        second = self.submit()
        self.assertEqual(first, second)
        self.wait_until(lambda: self.started == [first])

    def test_finished_or_zombie_task_with_same_url_is_not_reused(self):
        main.tasks["zombie"] = {"status": "processing", "progress": 80, "url": URL,
                                "settings": main.task_settings("zh", "https://api.example.com/v1", "model-a")}
        new_id = self.submit()
        self.assertNotEqual(new_id, "zombie")
        self.wait_until(lambda: self.started == [new_id])

    def test_changed_model_supersedes_running_task(self):
        first = self.submit(model="model-a")
        self.wait_until(lambda: self.started == [first])
        second = self.submit(model="model-b")
        self.assertNotEqual(first, second)
        self.wait_until(lambda: self.cancelled == [first] and len(self.started) == 2)
        self.assertEqual(main.tasks[first]["status"], "error")
        self.assertEqual(main.tasks[first]["error"], main.SUPERSEDED_MESSAGE)
        self.assertNotIn(first, main.active_tasks)
        self.assertEqual(main.tasks[second]["status"], "processing")

    def test_changed_summary_language_supersedes_running_task(self):
        first = self.submit(language="zh")
        second = self.submit(language="en")
        self.assertNotEqual(first, second)
        self.wait_until(lambda: self.cancelled == [first])

    def test_different_urls_run_independently(self):
        first = self.submit(url=URL)
        second = self.submit(url=URL + "2")
        self.assertNotEqual(first, second)
        self.wait_until(lambda: len(self.started) == 2)
        self.assertEqual(self.cancelled, [])

    def test_superseded_task_notifies_its_subscribers(self):
        first = self.submit(model="model-a")
        queue = asyncio.Queue()
        main.sse_connections[first] = [queue]
        self.submit(model="model-b")
        message = json.loads(self.client.portal.call(queue.get))
        self.assertEqual(message["status"], "error")
        main.sse_connections.pop(first, None)


class ShutdownTests(unittest.TestCase):
    """热重载/停服不能被挂着的 SSE 连接或后台线程卡住。"""

    def test_stream_for_finished_task_closes_by_itself(self):
        main.tasks["finished"] = {"status": "completed", "progress": 100, "url": URL}
        result = {}

        def read_stream():
            with TestClient(main.app) as client:
                with client.stream("GET", "/api/task-stream/finished") as resp:
                    result["body"] = "".join(resp.iter_text())

        reader = threading.Thread(target=read_stream, daemon=True)
        reader.start()
        reader.join(timeout=5)
        self.assertFalse(reader.is_alive(), "SSE stream for a finished task never closed")
        self.assertIn('"status": "completed"', result["body"])

    def test_shutdown_forces_exit_when_threads_linger(self):
        exited = threading.Event()
        original_exit = main.os._exit
        main.os._exit = lambda code: exited.set()
        main.SHUTDOWN_FORCE_EXIT_SECONDS = 0.05
        try:
            with TestClient(main.app):
                pass
            self.assertTrue(exited.wait(timeout=2), "watchdog did not force exit")
        finally:
            main.SHUTDOWN_FORCE_EXIT_SECONDS = None
            main.os._exit = original_exit


class FrontendCacheTests(unittest.TestCase):
    def test_page_and_static_files_are_revalidated(self):
        with TestClient(main.app) as client:
            for path in ("/", "/static/app.js"):
                self.assertEqual(client.get(path).headers.get("cache-control"), "no-cache", path)


if __name__ == "__main__":
    unittest.main()
