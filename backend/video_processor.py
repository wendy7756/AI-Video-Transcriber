# =============================================================================
# backend/video_processor.py - 影片處理器
# =============================================================================
# 此檔案包含影片處理器類別，負責使用yt-dlp下載和轉換影片。
# 主要功能包括影片下載、音頻提取、格式轉換等。
# 依賴：yt-dlp, FFmpeg等
# =============================================================================

import os
import yt_dlp
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class VideoProcessor:
    """影片處理器，使用yt-dlp下載和轉換影片"""

    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',  # 優先下載最佳音頻源
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                # 直接在提取階段轉換為單聲道 16k（空間小且穩定）
                'preferredcodec': 'm4a',
                'preferredquality': '192'
            }],
            # 全域FFmpeg參數：單聲道 + 16k 取樣率 + faststart
            'postprocessor_args': ['-ac', '1', '-ar', '16000', '-movflags', '+faststart'],
            'prefer_ffmpeg': True,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # 強制只下載單個影片，不下載播放列表
        }
    
    async def download_and_convert(self, url: str, output_dir: Path) -> tuple[str, str]:
        """
        下載影片並轉換為m4a格式。

        Args:
            url: 影片鏈接
            output_dir: 輸出目錄

        Returns:
            tuple: (轉換後的音頻檔案路徑, 影片標題)
        """
        try:
            # 創建輸出目錄
            output_dir.mkdir(exist_ok=True)

            # 生成唯一的檔案名
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            output_template = str(output_dir / f"audio_{unique_id}.%(ext)s")

            # 更新yt-dlp選項
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = output_template

            logger.info(f"開始下載影片: {url}")

            # 直接同步執行，不使用執行緒池
            # 在FastAPI中，IO密集型操作可以直接await
            import asyncio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 獲取影片資訊（放到執行緒池避免阻塞事件循環）
                info = await asyncio.to_thread(ydl.extract_info, url, False)
                video_title = info.get('title', 'unknown')
                expected_duration = info.get('duration') or 0
                logger.info(f"影片標題: {video_title}")

                # 下載影片（放到執行緒池避免阻塞事件循環）
                await asyncio.to_thread(ydl.download, [url])

            # 查找生成的m4a檔案
            audio_file = str(output_dir / f"audio_{unique_id}.m4a")

            if not os.path.exists(audio_file):
                # 如果m4a檔案不存在，查找其他音頻格式
                for ext in ['webm', 'mp4', 'mp3', 'wav']:
                    potential_file = str(output_dir / f"audio_{unique_id}.{ext}")
                    if os.path.exists(potential_file):
                        audio_file = potential_file
                        break
                else:
                    raise Exception("未找到下載的音頻檔案")

            # 校驗時長，如果和源影片差異較大，嘗試一次ffmpeg規範化重封裝
            try:
                import subprocess, shlex
                probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(audio_file)}"
                out = subprocess.check_output(probe_cmd, shell=True).decode().strip()
                actual_duration = float(out) if out else 0.0
            except Exception as _:
                actual_duration = 0.0

            if expected_duration and actual_duration and abs(actual_duration - expected_duration) / expected_duration > 0.1:
                logger.warning(
                    f"音頻時長異常，期望{expected_duration}s，實際{actual_duration}s，嘗試重封裝修復…"
                )
                try:
                    fixed_path = str(output_dir / f"audio_{unique_id}_fixed.m4a")
                    fix_cmd = f"ffmpeg -y -i {shlex.quote(audio_file)} -vn -c:a aac -b:a 160k -movflags +faststart {shlex.quote(fixed_path)}"
                    subprocess.check_call(fix_cmd, shell=True)
                    # 用修復後的檔案替換
                    audio_file = fixed_path
                    # 重新探測
                    out2 = subprocess.check_output(probe_cmd.replace(shlex.quote(audio_file.rsplit('.',1)[0]+'.m4a'), shlex.quote(audio_file)), shell=True).decode().strip()
                    actual_duration2 = float(out2) if out2 else 0.0
                    logger.info(f"重封裝完成，新時長≈{actual_duration2:.2f}s")
                except Exception as e:
                    logger.error(f"重封裝失敗：{e}")

            logger.info(f"音頻檔案已保存: {audio_file}")
            return audio_file, video_title

        except Exception as e:
            logger.error(f"下載影片失敗: {str(e)}")
            raise Exception(f"下載影片失敗: {str(e)}")
    
    def get_video_info(self, url: str) -> dict:
        """
        獲取影片資訊。

        Args:
            url: 影片鏈接

        Returns:
            dict: 影片資訊字典
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                }
        except Exception as e:
            logger.error(f"獲取影片資訊失敗: {str(e)}")
            raise Exception(f"獲取影片資訊失敗: {str(e)}")
