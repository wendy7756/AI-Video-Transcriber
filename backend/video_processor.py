import os
import yt_dlp
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器，使用yt-dlp下载和转换视频"""
    
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'extractaudio': True,
            'audioformat': 'm4a',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }
    
    async def download_and_convert(self, url: str, output_dir: Path) -> tuple[str, str]:
        """
        下载视频并转换为m4a格式
        
        Args:
            url: 视频链接
            output_dir: 输出目录
            
        Returns:
            转换后的音频文件路径
        """
        try:
            # 创建输出目录
            output_dir.mkdir(exist_ok=True)
            
            # 生成唯一的文件名
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            output_template = str(output_dir / f"audio_{unique_id}.%(ext)s")
            
            # 更新yt-dlp选项
            ydl_opts = self.ydl_opts.copy()
            ydl_opts['outtmpl'] = output_template
            
            logger.info(f"开始下载视频: {url}")
            
            # 直接同步执行，不使用线程池
            # 在FastAPI中，IO密集型操作可以直接await
            import asyncio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 获取视频信息（放到线程池避免阻塞事件循环）
                info = await asyncio.to_thread(ydl.extract_info, url, False)
                video_title = info.get('title', 'unknown')
                logger.info(f"视频标题: {video_title}")
                
                # 下载视频（放到线程池避免阻塞事件循环）
                await asyncio.to_thread(ydl.download, [url])
            
            # 查找生成的m4a文件
            audio_file = str(output_dir / f"audio_{unique_id}.m4a")
            
            if not os.path.exists(audio_file):
                # 如果m4a文件不存在，查找其他音频格式
                for ext in ['webm', 'mp4', 'mp3', 'wav']:
                    potential_file = str(output_dir / f"audio_{unique_id}.{ext}")
                    if os.path.exists(potential_file):
                        audio_file = potential_file
                        break
                else:
                    raise Exception("未找到下载的音频文件")
            
            logger.info(f"音频文件已保存: {audio_file}")
            return audio_file, video_title
            
        except Exception as e:
            logger.error(f"下载视频失败: {str(e)}")
            raise Exception(f"下载视频失败: {str(e)}")
    
    def get_video_info(self, url: str) -> dict:
        """
        获取视频信息
        
        Args:
            url: 视频链接
            
        Returns:
            视频信息字典
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
            logger.error(f"获取视频信息失败: {str(e)}")
            raise Exception(f"获取视频信息失败: {str(e)}")
