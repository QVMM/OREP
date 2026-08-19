"""
音频处理服务
- 格式转换（webm/ogg → wav 16kHz 单声道）
- 音频信息提取
"""
import os
import subprocess
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)


def convert_to_wav(input_path: str, output_path: str = None) -> str:
    """
    音频转码为 WAV（16kHz, 单声道, 16bit PCM）
    支持输入格式：webm, ogg, mp3, mp4, m4a, flac, wav
    如果输入已是 wav 且符合要求，直接返回
    返回输出文件路径
    """
    input_ext = os.path.splitext(input_path)[1].lower()

    # 如果输出路径未指定，生成新路径（避免同名覆盖问题）
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}_converted.wav"

    # 如果输入和输出相同，先写到临时文件再替换
    if os.path.abspath(input_path) == os.path.abspath(output_path):
        temp_output = f"{output_path}.tmp.wav"
    else:
        temp_output = output_path

    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-ar', '16000',        # 采样率 16kHz（paraformer 要求）
        '-ac', '1',             # 单声道
        '-f', 'wav',            # WAV 格式
        '-sample_fmt', 's16',   # 16bit PCM
        '-loglevel', 'error',   # 减少日志输出
        temp_output
    ]

    logger.info(f"音频转码: {input_path} → {output_path}")

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        if result.stderr:
            logger.warning(f"ffmpeg stderr: {result.stderr}")

        file_size = os.path.getsize(temp_output)
        logger.info(f"转码完成: {temp_output} ({file_size / 1024 / 1024:.2f} MB)")

        # 如果用了临时文件，重命名为最终输出
        if temp_output != output_path:
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(temp_output, output_path)

        return output_path

    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg 转码失败: {e.stderr}")
        # 清理临时文件
        if temp_output != output_path and os.path.exists(temp_output):
            os.remove(temp_output)
        raise Exception(f"音频转码失败: {e.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg 转码超时")
        if temp_output != output_path and os.path.exists(temp_output):
            os.remove(temp_output)
        raise Exception("音频转码超时（>5分钟）")


def get_audio_info(audio_path: str) -> dict:
    """获取音频文件信息"""
    cmd = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format', '-show_streams',
        audio_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        info = json.loads(result.stdout)

        audio_stream = next(
            (s for s in info.get('streams', []) if s.get('codec_type') == 'audio'),
            {}
        )

        return {
            'duration': float(info.get('format', {}).get('duration', 0)),
            'file_size': int(info.get('format', {}).get('size', 0)),
            'sample_rate': int(audio_stream.get('sample_rate', 0)),
            'channels': int(audio_stream.get('channels', 0)),
            'codec': audio_stream.get('codec_name', 'unknown'),
            'bit_rate': int(info.get('format', {}).get('bit_rate', 0))
        }
    except Exception as e:
        logger.error(f"获取音频信息失败: {e}")
        return {'error': str(e)}


def save_upload_file(upload_file, meeting_id: str, upload_dir: str) -> str:
    """
    保存上传的文件到本地
    返回保存的文件路径
    """
    os.makedirs(upload_dir, exist_ok=True)

    # 生成文件名
    ext = os.path.splitext(upload_file.filename)[1] if upload_file.filename else '.webm'
    filename = f"meeting_{meeting_id}_{os.getpid()}{ext}"
    file_path = os.path.join(upload_dir, filename)

    # 保存
    with open(file_path, "wb") as f:
        shutil.copyfileobj(upload_file.file, f)

    file_size = os.path.getsize(file_path)
    logger.info(f"文件已保存: {file_path} ({file_size / 1024 / 1024:.2f} MB)")

    return file_path
