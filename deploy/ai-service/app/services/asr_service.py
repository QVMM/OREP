"""
ASR 语音转文字服务 — 基于 DashScope fun-asr-realtime-2026-02-28
"""
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from http import HTTPStatus
from dashscope.audio.asr import Recognition
import dashscope

from app.config import settings

logger = logging.getLogger(__name__)

# 设置 API Key
dashscope.api_key = settings.DASHSCOPE_API_KEY


class LongAudioTranscriptionError(RuntimeError):
    """A complete-recording ASR result cannot omit a failed chunk."""


def transcribe_audio(audio_path: str) -> dict:
    """
    调用 DashScope fun-asr-realtime-2026-02-28 进行语音转文字
    输入：wav 文件路径（16kHz, 单声道）
    输出：带时间戳的分段文本
    注意：供应商未返回说话人时保留为未知，不伪造 SPEAKER_0。
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    logger.info(f"开始 ASR 识别: {audio_path}")

    recognition = Recognition(
        model='fun-asr-realtime-2026-02-28',
        format='wav',
        sample_rate=16000,
        language_hints=['zh', 'en'],
        callback=None
    )

    # DashScope realtime call has hung indefinitely in production; bound each chunk.
    chunk_timeout = max(60, int(os.getenv("ASR_CHUNK_TIMEOUT_SECONDS", "300")))
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="asr-call") as pool:
        future = pool.submit(recognition.call, audio_path)
        try:
            result = future.result(timeout=chunk_timeout)
        except Exception as exc:
            future.cancel()
            error_msg = f"ASR 识别超时/失败: timeout={chunk_timeout}s path={audio_path} err={exc}"
            logger.error(error_msg)
            raise TimeoutError(error_msg) from exc

    if result.status_code == HTTPStatus.OK:
        parsed = _parse_asr_result(result)
        logger.info(f"ASR 识别完成: {len(parsed['segments'])} 段, 时长 {parsed['duration']:.1f}s")
        return parsed
    else:
        error_msg = f"ASR 识别失败: status={result.status_code}, message={result.message}"
        logger.error(error_msg)
        raise Exception(error_msg)


def _parse_asr_result(result) -> dict:
    """解析 DashScope 返回结果，转为统一格式"""
    sentences = result.get_sentence()
    if not sentences:
        return {
            'transcript': '',
            'segments': [],
            'duration': 0,
            'speakers': [],
            'request_id': result.get('request_id', '')
        }

    segments = []
    for sent in sentences:
        seg = {
            'text': sent.get('text', ''),
            'start': sent.get('begin_time', 0) / 1000,  # ms → s
            'end': sent.get('end_time', 0) / 1000,
        }
        confidence = sent.get('confidence')
        if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
            seg['confidence'] = float(confidence)
        # 只保存供应商真实返回的说话人簇。
        speaker_id = sent.get('speaker_id')
        if speaker_id is not None:
            seg['speaker'] = f"SPEAKER_{speaker_id}"

        segments.append(seg)

    full_text = ' '.join(s['text'] for s in segments)
    duration = segments[-1]['end'] if segments else 0
    speakers = sorted(list(set(s['speaker'] for s in segments if s.get('speaker'))))

    return {
        'transcript': full_text,
        'segments': segments,
        'duration': duration,
        'speakers': speakers,
        'request_id': result.get('request_id', '')
    }


def transcribe_long_audio(
    audio_path: str,
    chunk_duration: int = 300,
    max_workers: int | None = None,
) -> dict:
    """
    长音频分片处理，每片 5 分钟
    fun-asr-realtime-2026-02-28 单次建议不超过 10 分钟
    """
    from pydub import AudioSegment

    audio = AudioSegment.from_wav(audio_path)
    total_duration = len(audio) / 1000  # 秒

    # 如果音频不长，直接处理
    if total_duration <= chunk_duration:
        return transcribe_audio(audio_path)

    logger.info(f"长音频分片处理: 总时长 {total_duration:.0f}s, 每片 {chunk_duration}s")

    all_segments = []
    chunk_dir = os.path.join(os.path.dirname(audio_path), "_chunks")
    os.makedirs(chunk_dir, exist_ok=True)

    try:
        chunks = []
        for i, start_ms in enumerate(range(0, len(audio), chunk_duration * 1000)):
            chunk = audio[start_ms:start_ms + chunk_duration * 1000]
            chunk_path = os.path.join(chunk_dir, f"chunk_{i}.wav")
            chunk.export(chunk_path, format='wav')
            chunks.append((i, start_ms, len(chunk), chunk_path))

        worker_count = min(
            max(1, max_workers or settings.ASR_CHUNK_MAX_WORKERS),
            len(chunks),
        )
        logger.info("ASR分片有限并发: chunks=%s workers=%s", len(chunks), worker_count)
        results_by_index = {}
        failures_by_index = {}
        completed_count = 0
        total_chunks = len(chunks)

        def _emit_chunk_progress(done: int) -> None:
            # Map chunk completion into the ASR stage band (18% → 45%) so the UI
            # does not look frozen for long roadshows.
            try:
                from app.services.pipeline_service import _save_progress
                # audio_path is .../ai-score/<sessionId>/<file>.wav
                session_dir = os.path.basename(os.path.dirname(audio_path))
                meeting_id = session_dir if session_dir.isdigit() else None
                if meeting_id:
                    pct = 18 + int(27 * (done / max(1, total_chunks)))
                    _save_progress(
                        meeting_id,
                        "asr",
                        f"语音识别中... ({done}/{total_chunks})",
                        2,
                        9,
                        progress_percent=min(45, max(18, pct)),
                    )
            except Exception as exc:
                logger.debug("asr chunk progress emit skipped: %s", exc)

        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="asr-chunk") as executor:
            future_map = {}
            for index, start_ms, chunk_length, chunk_path in chunks:
                logger.info(
                    "提交分片 %s: %.0fs - %.0fs",
                    index + 1,
                    start_ms / 1000,
                    (start_ms + chunk_length) / 1000,
                )
                future_map[executor.submit(transcribe_audio, chunk_path)] = (index, start_ms)

            for future in as_completed(future_map):
                index, start_ms = future_map[future]
                try:
                    results_by_index[index] = (start_ms, future.result())
                    completed_count += 1
                    logger.info(
                        "ASR 分片完成: %s/%s (index=%s)",
                        completed_count,
                        total_chunks,
                        index + 1,
                    )
                    _emit_chunk_progress(completed_count)
                except Exception as e:
                    failures_by_index[index] = e
                    logger.error(f"分片 {index + 1} 识别失败: {e}")

        if failures_by_index:
            first_index = min(failures_by_index)
            failure = failures_by_index[first_index]
            raise LongAudioTranscriptionError(
                f"long_audio_chunk_failed:{first_index + 1}:{failure}"
            ) from failure

        for index in sorted(results_by_index):
            start_ms, result = results_by_index[index]
            offset = start_ms / 1000
            try:
                for seg in result['segments']:
                    adjusted = dict(seg)
                    adjusted['start'] += offset
                    adjusted['end'] += offset
                    all_segments.append(adjusted)
            except Exception as e:
                logger.warning(f"分片 {index + 1} 结果合并失败: {e}")
    finally:
        # 清理临时文件
        import shutil
        if os.path.exists(chunk_dir):
            shutil.rmtree(chunk_dir)

    full_text = ' '.join(s['text'] for s in all_segments)
    speakers = sorted(list(set(s['speaker'] for s in all_segments if s.get('speaker'))))

    return {
        'transcript': full_text,
        'segments': all_segments,
        'duration': total_duration,
        'speakers': speakers,
        'request_id': 'multi-chunk'
    }
