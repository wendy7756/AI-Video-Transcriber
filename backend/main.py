# =============================================================================
# backend/main.py - AI影片轉錄器主應用程式
# =============================================================================
# 此檔案包含FastAPI主應用程式，負責處理影片轉錄、摘要和翻譯的Web服務。
# 主要功能包括影片處理任務管理、即時狀態更新、檔案下載等。
# 依賴：FastAPI, yt-dlp, Faster-Whisper, OpenAI API等
# =============================================================================

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import tempfile
import asyncio
import logging
from pathlib import Path
from typing import Optional
import aiofiles
import uuid
import json
import re
import random
import string
from datetime import datetime
import shutil

from .video_processor import VideoProcessor
from .transcriber import Transcriber
from .summarizer import Summarizer
from .translator import Translator

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI影片轉錄器", version="1.0.0")

# CORS中介軟體設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 取得專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent

# 掛載靜態檔案
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")

# 建立檔案目錄結構
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# 根據任務創建目錄
def create_task_dir(task_id: str):
    from datetime import datetime
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    task_dir_name = f"{timestamp}_{task_id}"
    task_dir = TEMP_DIR / task_dir_name
    task_dir.mkdir(exist_ok=True)
    return task_dir

# 初始化處理器
video_processor = VideoProcessor()
transcriber = Transcriber(os.getenv('WHISPER_MODEL_SIZE', 'base'))
summarizer = Summarizer()
translator = Translator()

# 儲存任務狀態 - 使用檔案持久化
import json
import threading

TASKS_FILE = TEMP_DIR / "tasks.json"
tasks_lock = threading.Lock()

def load_tasks():
    """
    載入任務狀態。

    Returns:
        dict: 任務狀態字典，如果載入失敗則返回空字典。
    """
    try:
        if TASKS_FILE.exists():
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_tasks(tasks_data):
    """
    儲存任務狀態。

    Args:
        tasks_data (dict): 要儲存的任務狀態字典。

    Note:
        使用執行緒鎖確保檔案寫入的安全性。
    """
    try:
        with tasks_lock:
            with open(TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"儲存任務狀態失敗: {e}")

async def broadcast_task_update(task_id: str, task_data: dict):
    """
    向所有連線的SSE客戶端廣播任務狀態更新。

    Args:
        task_id (str): 任務ID。
        task_data (dict): 任務狀態資料。

    Note:
        此函式會清理斷開的連線以維持效能。
    """
    logger.info(f"廣播任務更新: {task_id}, 狀態: {task_data.get('status')}, 連線數: {len(sse_connections.get(task_id, []))}")
    if task_id in sse_connections:
        connections_to_remove = []
        for queue in sse_connections[task_id]:
            try:
                await queue.put(json.dumps(task_data, ensure_ascii=False))
                logger.debug(f"訊息已傳送到佇列: {task_id}")
            except Exception as e:
                logger.warning(f"傳送訊息到佇列失敗: {e}")
                connections_to_remove.append(queue)

        # 移除斷開的連線
        for queue in connections_to_remove:
            sse_connections[task_id].remove(queue)

        # 如果沒有連線了，清理該任務的連線列表
        if not sse_connections[task_id]:
            del sse_connections[task_id]

# 啟動時載入任務狀態
tasks = load_tasks()
# 儲存正在處理的URL，防止重複處理
processing_urls = set()
# 儲存活躍的任務物件，用於控制和取消
active_tasks = {}
# 儲存SSE連線，用於即時推播狀態更新
sse_connections = {}

def generate_task_id() -> str:
    """
    產生8碼唯一任務ID。

    格式：HHMMSSXX（時分秒6碼 + 隨機2碼）
    範例：110730A3, 110731K7, 110732B2

    Returns:
        str: 8碼唯一任務ID。
    """
    # 字元集：數字 + 大寫字母（62種可能）
    chars = string.digits + string.ascii_uppercase

    # 產生唯一ID（最多重試100次）
    max_attempts = 100
    for _ in range(max_attempts):
        # 獲取當前時間 HHMMSS 格式
        now = datetime.now().strftime("%H%M%S")

        # 隨機產生2碼
        random_part = ''.join(random.choices(chars, k=2))
        task_id = f"{now}{random_part}"

        # 檢查是否重複
        if task_id not in tasks:
            return task_id

    # 如果重試次數用完，使用UUID作為fallback
    logger.warning("無法產生唯一8碼ID，使用UUID fallback")
    return str(uuid.uuid4())[:8].upper()

def _sanitize_title_for_filename(title: str) -> str:
    """
    將影片標題清理為安全的檔名片段。

    Args:
        title (str): 原始影片標題。

    Returns:
        str: 安全的檔名片段。
    """
    if not title:
        return "untitled"
    # 僅保留字母數字、底線、連字號與空格
    safe = re.sub(r"[^\\w\\-\\s]", "", title)
    # 壓縮空白並轉為底線
    safe = re.sub(r"\\s+", "_", safe).strip("._-")
    # 最長限制，避免過長檔名問題
    return safe[:80] or "untitled"

@app.get("/")
async def read_root():
    """
    返回前端頁面。

    Returns:
        FileResponse: 前端HTML頁面。
    """
    return FileResponse(str(PROJECT_ROOT / "static" / "index.html"))

@app.get("/health")
async def health_check():
    """
    健康檢查端點。

    Returns:
        dict: 健康狀態資訊。
    """
    try:
        # 檢查基本服務狀態
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_tasks": len(active_tasks),
            "processing_urls": len(processing_urls)
        }
        
        # 檢查 GPU 狀態（如果可用）
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                memory_info = result.stdout.strip().split(',')
                status["gpu"] = {
                    "available": True,
                    "memory_used_mb": int(memory_info[0].strip()),
                    "memory_total_mb": int(memory_info[1].strip())
                }
            else:
                status["gpu"] = {"available": False, "error": "nvidia-smi failed"}
        except Exception as e:
            status["gpu"] = {"available": False, "error": str(e)}
        
        return status
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.post("/api/process-video")
async def process_video(
    url: str = Form(...),
    summary_language: str = Form(default="zh-tw")
):
    """
    處理影片連結，返回任務ID。

    Args:
        url (str): 影片URL。
        summary_language (str): 摘要語言，預設為"zh"。

    Returns:
        dict: 包含任務ID和訊息的字典。

    Raises:
        HTTPException: 處理失敗時拋出500錯誤。
    """
    try:
        # 檢查是否已經在處理相同的URL
        if url in processing_urls:
            # 尋找現有任務
            for tid, task in tasks.items():
                if task.get("url") == url:
                    return {"task_id": tid, "message": "該影片正在處理中，請等待..."}
            
        # 產生唯一任務ID
        task_id = generate_task_id()
        
        # 標記URL為正在處理
        processing_urls.add(url)
        
        # 初始化任務狀態
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "開始處理影片...",
            "script": None,
            "summary": None,
            "error": None,
            "url": url  # 儲存URL用於去重
        }
        save_tasks(tasks)
        
        # 建立並追蹤非同步任務
        task = asyncio.create_task(process_video_task(task_id, url, summary_language))
        active_tasks[task_id] = task
        
        return {"task_id": task_id, "message": "任務已建立，正在處理中..."}
        
    except Exception as e:
        logger.error(f"處理影片時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")

async def process_video_task(task_id: str, url: str, summary_language: str):
    """
    非同步處理影片任務
    """
    task_temp_dir = TEMP_DIR / task_id
    task_temp_dir.mkdir(exist_ok=True)
    try:
        # 立即更新狀態：開始處理
        tasks[task_id].update({
            "status": "processing",
            "progress": 5,
            "message": "正在解析影片資訊..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 加入短暫延遲確保狀態更新
        import asyncio
        await asyncio.sleep(0.1)

        # 更新狀態：開始下載
        tasks[task_id].update({
            "progress": 10,
            "message": "正在下載影片（這可能需要較長時間）..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 下載並轉換影片（這是最耗時的步驟）
        audio_path, video_title = await video_processor.download_and_convert(url, task_temp_dir)

        # 下載完成，更新狀態
        tasks[task_id].update({
            "progress": 30,
            "message": "影片下載完成，正在轉錄音訊..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])
        
        # 轉錄音訊
        raw_script = await transcriber.transcribe(audio_path)

        # 將Whisper原始轉錄儲存為Markdown檔案，供下載/封存
        try:
            short_id = task_id.replace("-", "")[:6]
            safe_title = _sanitize_title_for_filename(video_title)
            task_dir = create_task_dir(task_id)
            raw_md_filename = f"raw_{safe_title}_{short_id}.md"
            raw_md_path = task_dir / raw_md_filename
            with open(raw_md_path, "w", encoding="utf-8") as f:
                content_raw = (raw_script or "") + f"\n\nsource: {url}\n"
                f.write(content_raw)

            # 記錄原始轉錄檔案路徑（僅儲存檔名，實際路徑位於TEMP_DIR）
            tasks[task_id].update({
                "raw_script_file": raw_md_filename
            })
            save_tasks(tasks)
            await broadcast_task_update(task_id, tasks[task_id])
        except Exception as e:
            logger.error(f"儲存原始轉錄Markdown失敗: {e}")

        # 更新狀態：最佳化轉錄文字
        tasks[task_id].update({
            "progress": 45,
            "message": "正在最佳化轉錄文字..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 最佳化轉錄文字：修正錯別字，按語意分段，並轉換為繁體中文
        script = await summarizer.optimize_transcript(raw_script, target_language=summary_language)

        # 為轉錄文字加入標題，並在結尾加入來源連結
        script_with_title = f"# {video_title}\n\n{script}\n\nsource: {url}\n"

        # 檢查是否需要翻譯
        detected_language = transcriber.get_detected_language(raw_script)
        logger.info(f"偵測到的語言: {detected_language}, 摘要語言: {summary_language}")

        translation_content = None
        translation_filename = None
        translation_path = None

        if detected_language and translator.should_translate(detected_language, summary_language):
            logger.info(f"需要翻譯: {detected_language} -> {summary_language}")
            # 更新狀態：產生翻譯
            tasks[task_id].update({
                "progress": 65,
                "message": "正在產生翻譯..."
            })
            save_tasks(tasks)
            await broadcast_task_update(task_id, tasks[task_id])

            # 翻譯轉錄文字
            translation_content = await translator.translate_text(script, summary_language, detected_language)
            translation_with_title = f"# {video_title}\n\n{translation_content}\n\nsource: {url}\n"

            # 儲存翻譯到檔案
            translation_filename = f"translation_{safe_title}_{short_id}.md"
            translation_path = task_dir / translation_filename
            async with aiofiles.open(translation_path, "w", encoding="utf-8") as f:
                await f.write(translation_with_title)
        else:
            logger.info(f"不需要翻譯: detected_language={detected_language}, summary_language={summary_language}, should_translate={translator.should_translate(detected_language, summary_language) if detected_language else 'N/A'}")

        # 更新狀態：產生摘要
        tasks[task_id].update({
            "progress": 75,
            "message": "正在產生摘要..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])
        
        # 產生摘要
        summary = await summarizer.summarize(script, summary_language, video_title)
        summary_with_source = summary + f"\n\nsource: {url}\n"

        # 儲存最佳化後的轉錄文字到檔案
        script_filename = f"transcript_{safe_title}_{short_id}.md"
        script_path = task_dir / script_filename
        async with aiofiles.open(script_path, "w", encoding="utf-8") as f:
            await f.write(script_with_title)

        # 檔案已經使用正確命名，不需要重新命名

        # 儲存摘要到檔案（summary_標題_短ID.md）
        summary_filename = f"summary_{safe_title}_{short_id}.md"
        summary_path = task_dir / summary_filename
        async with aiofiles.open(summary_path, "w", encoding="utf-8") as f:
            await f.write(summary_with_source)

        # 更新狀態：完成
        task_result = {
            "status": "completed",
            "progress": 100,
            "message": "處理完成！",
            "video_title": video_title,
            "script": script_with_title,
            "summary": summary_with_source,
            "script_path": str(script_path),
            "summary_path": str(summary_path),
            "short_id": short_id,
            "safe_title": safe_title,
            "detected_language": detected_language,
            "summary_language": summary_language
        }

        # 如果有翻譯，加入翻譯資訊
        if translation_content and translation_path:
            task_result.update({
                "translation": translation_with_title,
                "translation_path": str(translation_path),
                "translation_filename": translation_filename
            })

        tasks[task_id].update(task_result)
        save_tasks(tasks)
        logger.info(f"任務完成，準備廣播最終狀態: {task_id}")
        await broadcast_task_update(task_id, tasks[task_id])
        logger.info(f"最終狀態已廣播: {task_id}")

        # 從處理列表中移除URL
        processing_urls.discard(url)

        # 從活躍任務列表中移除
        if task_id in active_tasks:
            del active_tasks[task_id]

        # 清理暫存目錄
        try:
            shutil.rmtree(task_temp_dir)
            logger.info(f"已清理暫存目錄: {task_temp_dir}")
        except Exception as e:
            logger.error(f"清理暫存目錄失敗: {e}")

    except Exception as e:
        logger.error(f"任務 {task_id} 處理失敗: {str(e)}")
        # 從處理列表中移除URL
        processing_urls.discard(url)

        # 從活躍任務列表中移除
        if task_id in active_tasks:
            del active_tasks[task_id]

        tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "message": f"處理失敗: {str(e)}"
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

@app.get("/api/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    獲取任務狀態。

    Args:
        task_id (str): 任務ID。

    Returns:
        dict: 任務狀態資訊。

    Raises:
        HTTPException: 當任務不存在時拋出404錯誤。
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任務不存在")

    return tasks[task_id]

@app.get("/api/task-stream/{task_id}")
async def task_stream(task_id: str):
    """
    SSE即時任務狀態流。

    Args:
        task_id (str): 任務ID。

    Returns:
        StreamingResponse: SSE串流回應。

    Raises:
        HTTPException: 當任務不存在時拋出404錯誤。
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任務不存在")

    async def event_generator():
        # 建立任務專用的佇列
        queue = asyncio.Queue()

        # 將佇列加入到連線列表
        if task_id not in sse_connections:
            sse_connections[task_id] = []
        sse_connections[task_id].append(queue)

        try:
            # 立即傳送目前狀態
            current_task = tasks.get(task_id, {})
            yield f"data: {json.dumps(current_task, ensure_ascii=False)}\n\n"

            # 持續監聽狀態更新
            while True:
                try:
                    # 等待狀態更新，逾時時間30秒傳送心跳
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"

                    # 如果任務完成或失敗，結束流
                    task_data = json.loads(data)
                    if task_data.get("status") in ["completed", "error"]:
                        break

                except asyncio.TimeoutError:
                    # 傳送心跳保持連線
                    yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE連線被取消: {task_id}")
        except Exception as e:
            logger.error(f"SSE流異常: {e}")
        finally:
            # 清理連線
            if task_id in sse_connections and queue in sse_connections[task_id]:
                sse_connections[task_id].remove(queue)
                if not sse_connections[task_id]:
                    del sse_connections[task_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    直接從temp目錄下載檔案（簡化方案）。

    Args:
        filename (str): 要下載的檔名。

    Returns:
        FileResponse: 檔案下載回應。

    Raises:
        HTTPException: 當檔案不存在或格式無效時拋出相應錯誤。
    """
    try:
        # 檢查檔案副檔名安全性
        if not filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="僅支援下載.md檔案")

        # 檢查檔名格式（防止路徑遍歷攻擊）
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="檔名格式無效")

        # 搜尋檔案：檢查所有任務目錄
        file_path = None
        
        # 檢查所有任務目錄
        for task_dir in TEMP_DIR.iterdir():
            if task_dir.is_dir():
                potential_path = task_dir / filename
                if potential_path.exists():
                    file_path = potential_path
                    break
        
        # 如果沒找到，檢查 temp 根目錄（相容性）
        if not file_path:
            temp_file_path = TEMP_DIR / filename
            if temp_file_path.exists():
                file_path = temp_file_path
        
        if not file_path:
            raise HTTPException(status_code=404, detail="檔案不存在")

        return FileResponse(
            file_path,
            filename=filename,
            media_type="text/markdown"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下載檔案失敗: {e}")
        raise HTTPException(status_code=500, detail=f"下載失敗: {str(e)}")


@app.delete("/api/task/{task_id}")
async def delete_task(task_id: str):
    """
    取消並刪除任務。

    Args:
        task_id (str): 要刪除的任務ID。

    Returns:
        dict: 包含成功訊息的字典。

    Raises:
        HTTPException: 當任務不存在時拋出404錯誤。
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任務不存在")

    # 如果任務還在執行，先取消它
    if task_id in active_tasks:
        task = active_tasks[task_id]
        if not task.done():
            task.cancel()
            logger.info(f"任務 {task_id} 已被取消")
        del active_tasks[task_id]

    # 從處理URL列表中移除
    task_url = tasks[task_id].get("url")
    if task_url:
        processing_urls.discard(task_url)

    # 刪除任務記錄
    del tasks[task_id]
    return {"message": "任務已取消並刪除"}

@app.get("/api/tasks/active")
async def get_active_tasks():
    """
    獲取目前活躍任務列表（用於除錯）。

    Returns:
        dict: 包含活躍任務統計資訊的字典。
    """
    active_count = len(active_tasks)
    processing_count = len(processing_urls)
    return {
        "active_tasks": active_count,
        "processing_urls": processing_count,
        "task_ids": list(active_tasks.keys())
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8893))
    uvicorn.run(app, host=host, port=port)