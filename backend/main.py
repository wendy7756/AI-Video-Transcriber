# =============================================================================
# backend/main.py - AI影片轉錄器主應用程式
# =============================================================================
# 此檔案包含FastAPI主應用程式，負責處理影片轉錄、摘要和翻譯的Web服務。
# 主要功能包括影片處理任務管理、實時狀態更新、檔案下載等。
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

from video_processor import VideoProcessor
from transcriber import Transcriber
from summarizer import Summarizer
from translator import Translator

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI影片轉錄器", version="1.0.0")

# CORS中介軟體配置
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

# 創建臨時目錄
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

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
    向所有連接的SSE客戶端廣播任務狀態更新。

    Args:
        task_id (str): 任務ID。
        task_data (dict): 任務狀態資料。

    Note:
        此函數會清理斷開的連接以維持效能。
    """
    logger.info(f"廣播任務更新: {task_id}, 狀態: {task_data.get('status')}, 連接數: {len(sse_connections.get(task_id, []))}")
    if task_id in sse_connections:
        connections_to_remove = []
        for queue in sse_connections[task_id]:
            try:
                await queue.put(json.dumps(task_data, ensure_ascii=False))
                logger.debug(f"訊息已發送到隊列: {task_id}")
            except Exception as e:
                logger.warning(f"發送訊息到隊列失敗: {e}")
                connections_to_remove.append(queue)

        # 移除斷開的連接
        for queue in connections_to_remove:
            sse_connections[task_id].remove(queue)

        # 如果沒有連接了，清理該任務的連接列表
        if not sse_connections[task_id]:
            del sse_connections[task_id]

# 啟動時載入任務狀態
tasks = load_tasks()
# 儲存正在處理的URL，防止重複處理
processing_urls = set()
# 儲存活躍的任務物件，用於控制和取消
active_tasks = {}
# 儲存SSE連接，用於實時推送狀態更新
sse_connections = {}

def generate_task_id() -> str:
    """
    生成8碼唯一任務ID。

    格式：HHMMSSXX（時分秒6碼 + 隨機2碼）
    範例：110730A3, 110731K7, 110732B2

    Returns:
        str: 8碼唯一任務ID。
    """
    # 字符集：數字 + 大寫字母（62種可能）
    chars = string.digits + string.ascii_uppercase

    # 生成唯一ID（最多重試100次）
    max_attempts = 100
    for _ in range(max_attempts):
        # 獲取當前時間 HHMMSS 格式
        now = datetime.now().strftime("%H%M%S")

        # 隨機生成2碼
        random_part = ''.join(random.choices(chars, k=2))
        task_id = f"{now}{random_part}"

        # 檢查是否重複
        if task_id not in tasks:
            return task_id

    # 如果重試次數用完，使用UUID作為fallback
    logger.warning("無法生成唯一8碼ID，使用UUID fallback")
    return str(uuid.uuid4())[:8].upper()

def _sanitize_title_for_filename(title: str) -> str:
    """
    將影片標題清洗為安全的檔案名片段。

    Args:
        title (str): 原始影片標題。

    Returns:
        str: 安全的檔案名片段。
    """
    if not title:
        return "untitled"
    # 僅保留字母數字、下劃線、連字符與空格
    safe = re.sub(r"[^\w\-\s]", "", title)
    # 壓縮空白並轉為下劃線
    safe = re.sub(r"\s+", "_", safe).strip("._-")
    # 最長限制，避免過長檔案名問題
    return safe[:80] or "untitled"

@app.get("/")
async def read_root():
    """
    返回前端頁面。

    Returns:
        FileResponse: 前端HTML頁面。
    """
    return FileResponse(str(PROJECT_ROOT / "static" / "index.html"))

@app.post("/api/process-video")
async def process_video(
    url: str = Form(...),
    summary_language: str = Form(default="zh")
):
    """
    處理影片鏈接，返回任務ID。

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
            # 查找現有任務
            for tid, task in tasks.items():
                if task.get("url") == url:
                    return {"task_id": tid, "message": "該影片正在處理中，請等待..."}
            
        # 生成唯一任務ID
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
            "url": url  # 保存URL用于去重
        }
        save_tasks(tasks)
        
        # 創建並跟踪非同步任務
        task = asyncio.create_task(process_video_task(task_id, url, summary_language))
        active_tasks[task_id] = task
        
        return {"task_id": task_id, "message": "任務已創建，正在處理中..."}
        
    except Exception as e:
        logger.error(f"處理影片時出錯: {str(e)}")
        raise HTTPException(status_code=500, detail=f"處理失敗: {str(e)}")

async def process_video_task(task_id: str, url: str, summary_language: str):
    """
    异步处理视频任务
    """
    try:
        # 立即更新狀態：開始下載影片
        tasks[task_id].update({
            "status": "processing",
            "progress": 10,
            "message": "正在下載影片..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 添加短暫延遲確保狀態更新
        import asyncio
        await asyncio.sleep(0.1)

        # 更新狀態：正在解析影片資訊
        tasks[task_id].update({
            "progress": 15,
            "message": "正在解析影片資訊..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 下載並轉換影片
        audio_path, video_title = await video_processor.download_and_convert(url, TEMP_DIR)

        # 下載完成，更新狀態
        tasks[task_id].update({
            "progress": 35,
            "message": "影片下載完成，準備轉錄..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 更新狀態：轉錄中
        tasks[task_id].update({
            "progress": 40,
            "message": "正在轉錄音頻..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])
        
        # 轉錄音頻
        raw_script = await transcriber.transcribe(audio_path)

        # 將Whisper原始轉錄儲存為Markdown檔案，供下載/歸檔
        try:
            short_id = task_id.replace("-", "")[:6]
            safe_title = _sanitize_title_for_filename(video_title)
            raw_md_filename = f"raw_{safe_title}_{short_id}.md"
            raw_md_path = TEMP_DIR / raw_md_filename
            with open(raw_md_path, "w", encoding="utf-8") as f:
                content_raw = (raw_script or "") + f"\n\nsource: {url}\n"
                f.write(content_raw)

            # 記錄原始轉錄檔案路徑（僅儲存檔案名，實際路徑位於TEMP_DIR）
            tasks[task_id].update({
                "raw_script_file": raw_md_filename
            })
            save_tasks(tasks)
            await broadcast_task_update(task_id, tasks[task_id])
        except Exception as e:
            logger.error(f"儲存原始轉錄Markdown失敗: {e}")

        # 更新狀態：優化轉錄文字
        tasks[task_id].update({
            "progress": 55,
            "message": "正在優化轉錄文字..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])

        # 優化轉錄文字：修正錯別字，按含義分段
        script = await summarizer.optimize_transcript(raw_script)

        # 為轉錄文字添加標題，並在結尾添加來源鏈接
        script_with_title = f"# {video_title}\n\n{script}\n\nsource: {url}\n"

        # 檢查是否需要翻譯
        detected_language = transcriber.get_detected_language(raw_script)
        logger.info(f"檢測到的語言: {detected_language}, 摘要語言: {summary_language}")

        translation_content = None
        translation_filename = None
        translation_path = None

        if detected_language and translator.should_translate(detected_language, summary_language):
            logger.info(f"需要翻譯: {detected_language} -> {summary_language}")
            # 更新狀態：產生翻譯
            tasks[task_id].update({
                "progress": 70,
                "message": "正在產生翻譯..."
            })
            save_tasks(tasks)
            await broadcast_task_update(task_id, tasks[task_id])

            # 翻譯轉錄文字
            translation_content = await translator.translate_text(script, summary_language, detected_language)
            translation_with_title = f"# {video_title}\n\n{translation_content}\n\nsource: {url}\n"

            # 儲存翻譯到檔案
            translation_filename = f"translation_{safe_title}_{short_id}.md"
            translation_path = TEMP_DIR / translation_filename
            async with aiofiles.open(translation_path, "w", encoding="utf-8") as f:
                await f.write(translation_with_title)
        else:
            logger.info(f"不需要翻譯: detected_language={detected_language}, summary_language={summary_language}, should_translate={translator.should_translate(detected_language, summary_language) if detected_language else 'N/A'}")

        # 更新狀態：產生摘要
        tasks[task_id].update({
            "progress": 80,
            "message": "正在產生摘要..."
        })
        save_tasks(tasks)
        await broadcast_task_update(task_id, tasks[task_id])
        
        # 產生摘要
        summary = await summarizer.summarize(script, summary_language, video_title)
        summary_with_source = summary + f"\n\nsource: {url}\n"

        # 儲存優化後的轉錄文字到檔案
        script_filename = f"transcript_{task_id}.md"
        script_path = TEMP_DIR / script_filename
        async with aiofiles.open(script_path, "w", encoding="utf-8") as f:
            await f.write(script_with_title)

        # 重新命名為新規則：transcript_標題_短ID.md
        new_script_filename = f"transcript_{safe_title}_{short_id}.md"
        new_script_path = TEMP_DIR / new_script_filename
        try:
            if script_path.exists():
                script_path.rename(new_script_path)
                script_path = new_script_path
        except Exception as _:
            # 如重新命名失敗，繼續使用原路徑
            pass

        # 儲存摘要到檔案（summary_標題_短ID.md）
        summary_filename = f"summary_{safe_title}_{short_id}.md"
        summary_path = TEMP_DIR / summary_filename
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

        # 如果有翻譯，添加翻譯資訊
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

        # 不要立即刪除臨時檔案！保留給用戶下載
        # 檔案會在一定時間後自動清理或用戶手動清理

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
        # 創建任務專用的隊列
        queue = asyncio.Queue()

        # 將隊列添加到連接列表
        if task_id not in sse_connections:
            sse_connections[task_id] = []
        sse_connections[task_id].append(queue)

        try:
            # 立即發送目前狀態
            current_task = tasks.get(task_id, {})
            yield f"data: {json.dumps(current_task, ensure_ascii=False)}\n\n"

            # 持續監聽狀態更新
            while True:
                try:
                    # 等待狀態更新，逾時時間30秒發送心跳
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {data}\n\n"

                    # 如果任務完成或失敗，結束流
                    task_data = json.loads(data)
                    if task_data.get("status") in ["completed", "error"]:
                        break

                except asyncio.TimeoutError:
                    # 發送心跳保持連接
                    yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            logger.info(f"SSE連接被取消: {task_id}")
        except Exception as e:
            logger.error(f"SSE流異常: {e}")
        finally:
            # 清理連接
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
        filename (str): 要下載的檔案名稱。

    Returns:
        FileResponse: 檔案下載回應。

    Raises:
        HTTPException: 當檔案不存在或格式無效時拋出相應錯誤。
    """
    try:
        # 檢查檔案擴展名安全性
        if not filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="僅支援下載.md檔案")

        # 檢查檔案名格式（防止路徑遍歷攻擊）
        if '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="檔案名格式無效")

        file_path = TEMP_DIR / filename
        if not file_path.exists():
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

    # 如果任務還在運行，先取消它
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
