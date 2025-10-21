import os
import yt_dlp
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import uuid
import asyncio
import subprocess # 新增
import shlex # 新增
import math # 新增

logger = logging.getLogger(__name__)

class VideoProcessor:
    """视频处理器，使用yt-dlp下载和转换视频，或处理本地文件"""
    
    def __init__(self):
        self.ydl_opts = {
            'format': 'bestaudio/best',  # 优先下载最佳音频源
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                # 直接在提取阶段转换为单声道 16k（空间小且稳定）
                'preferredcodec': 'm4a',
                'preferredquality': '192'
            }],
            # 全局FFmpeg参数：单声道 + 16k 采样率 + faststart
            'postprocessor_args': ['-ac', '1', '-ar', '16000', '-movflags', '+faststart'],
            'prefer_ffmpeg': True,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,  # 强制只下载单个视频，不下载播放列表
        }
    
    async def download_and_convert(self, video_input: str, output_dir: Path) -> Tuple[List[str], str]:
        """
        下载视频或处理本地视频文件，并转换为m4a格式，如果视频过长则分块处理。
        
        Args:
            video_input: 视频链接或本地文件路径
            output_dir: 输出目录
            
        Returns:
            转换后的音频文件路径列表和视频标题
        """
        try:
            output_dir.mkdir(exist_ok=True)
            
            unique_id = str(uuid.uuid4())[:8]
            
            # 临时存储原始音频文件路径，可能需要分块
            raw_audio_file: Optional[str] = None
            video_title: str = "untitled"
            expected_duration: float = 0.0

            # 检查输入是URL还是本地文件 (确保是字符串进行判断)
            if isinstance(video_input, str) and (video_input.startswith("http://") or video_input.startswith("https://")):
                # 处理URL
                url = video_input
                output_template = str(output_dir / f"audio_{unique_id}.%(ext)s")
                
                ydl_opts = self.ydl_opts.copy()
                ydl_opts['outtmpl'] = output_template
                
                logger.info(f"开始下载视频: {url}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, False)
                    video_title = info.get('title', 'unknown')
                    expected_duration = info.get('duration') or 0
                    logger.info(f"视频标题: {video_title}")
                    
                    await asyncio.to_thread(ydl.download, [url])
                
                raw_audio_file = str(output_dir / f"audio_{unique_id}.m4a")
                
                if not os.path.exists(raw_audio_file):
                    for ext in ['webm', 'mp4', 'mp3', 'wav']:
                        potential_file = str(output_dir / f"audio_{unique_id}.{ext}")
                        if os.path.exists(potential_file):
                            raw_audio_file = potential_file
                            break
                    else:
                        raise Exception("未找到下载的音频文件")
            else:
                # 处理本地文件
                local_file_path = Path(video_input)
                logger.debug(f"检查本地文件是否存在: {local_file_path}, 结果: {local_file_path.exists()}")
                if not local_file_path.exists():
                    raise FileNotFoundError(f"本地视频文件不存在: {local_file_path}")
                
                video_title = local_file_path.stem # 使用文件名作为标题
                
                # 将本地视频文件转换为m4a音频
                raw_audio_file = str(output_dir / f"audio_{unique_id}.m4a")
                
                logger.info(f"开始转换本地视频文件: {local_file_path} 到 {raw_audio_file}")
                
                try:
                    # 获取视频时长
                    logger.debug(f"ffprobe input path: {local_file_path}")
                    probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(str(local_file_path))}"
                    logger.debug(f"ffprobe command: {probe_cmd}")
                    out = await asyncio.to_thread(subprocess.check_output, probe_cmd, shell=True)
                    out = out.decode().strip()
                    logger.debug(f"ffprobe output: {out}")
                    expected_duration = float(out) if out else 0.0

                    convert_cmd = f"ffmpeg -i {shlex.quote(str(local_file_path))} -vn -c:a aac -ac 1 -ar 16000 -b:a 192k -movflags +faststart {shlex.quote(raw_audio_file)}"
                    logger.debug(f"ffmpeg convert command: {convert_cmd}")
                    await asyncio.to_thread(subprocess.check_call, convert_cmd, shell=True)
                    logger.info(f"本地视频文件 '{local_file_path}' 已成功转换为音频: {raw_audio_file}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"转换本地视频文件失败: {e.output.decode()}") # 打印ffmpeg错误输出
                    raise Exception(f"转换本地视频文件失败: {e}")
                except Exception as e:
                    logger.error(f"处理本地视频文件失败: {e}")
                    raise Exception(f"处理本地视频文件失败: {e}")
            
            # 校验时长
            actual_duration = 0.0
            try:
                probe_cmd = f"ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 {shlex.quote(raw_audio_file)}"
                out = await asyncio.to_thread(subprocess.check_output, probe_cmd, shell=True)
                actual_duration = float(out.decode().strip()) if out else 0.0
            except Exception as _:
                actual_duration = 0.0
            
            if expected_duration and actual_duration and abs(actual_duration - expected_duration) / expected_duration > 0.1:
                logger.warning(
                    f"音频时长异常，期望{expected_duration}s，实际{actual_duration}s，尝试重封装修复…"
                )
                try:
                    fixed_path = str(output_dir / f"audio_{unique_id}_fixed.m4a")
                    fix_cmd = f"ffmpeg -y -i {shlex.quote(raw_audio_file)} -vn -c:a aac -b:a 160k -movflags +faststart {shlex.quote(fixed_path)}"
                    await asyncio.to_thread(subprocess.check_call, fix_cmd, shell=True)
                    # 用修复后的文件替换
                    raw_audio_file = fixed_path
                    # 重新探测
                    out2 = await asyncio.to_thread(subprocess.check_output, probe_cmd.replace(shlex.quote(raw_audio_file.rsplit('.',1)[0]+'.m4a'), shlex.quote(raw_audio_file)), shell=True)
                    actual_duration2 = float(out2.decode().strip()) if out2 else 0.0
                    logger.info(f"重封装完成，新时长≈{actual_duration2:.2f}s")
                except Exception as e:
                    logger.error(f"重封装失败：{e}")
            
            # --- 视频分块逻辑 ---
            segment_duration_s = 20 * 60 # 20分钟
            audio_segments: List[str] = []

            if actual_duration > segment_duration_s:
                num_segments = math.ceil(actual_duration / segment_duration_s)
                logger.info(f"视频时长 {actual_duration:.2f}s 超过 {segment_duration_s}s，将分割为 {num_segments} 段")
                
                for i in range(num_segments):
                    start_time = i * segment_duration_s
                    segment_file = str(output_dir / f"audio_{unique_id}_part{i+1}.m4a")
                    
                    segment_cmd = (
                        f"ffmpeg -i {shlex.quote(raw_audio_file)} -ss {start_time} -t {segment_duration_s} "
                        f"-c copy {shlex.quote(segment_file)}"
                    )
                    logger.debug(f"ffmpeg segment command: {segment_cmd}")
                    await asyncio.to_thread(subprocess.check_call, segment_cmd, shell=True)
                    audio_segments.append(segment_file)
                
                # 删除原始大文件，只保留片段
                os.remove(raw_audio_file)
                logger.info(f"原始音频文件 {raw_audio_file} 已删除")
            else:
                audio_segments.append(raw_audio_file)
            
            logger.info(f"音频文件已保存: {audio_segments}")
            return audio_segments, video_title
            
        except Exception as e:
            logger.error(f"处理视频失败: {str(e)}")
            raise Exception(f"处理视频失败: {str(e)}")
    
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
