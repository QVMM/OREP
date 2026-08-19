"""
语音质量分析服务
- 语速统计
- 停顿分析
- 填充词检测
- 语调韵律分析
"""
import logging
import numpy as np
import jieba

logger = logging.getLogger(__name__)

# 中文常见填充词
FILLER_WORDS = [
    '嗯', '呃', '啊', '额', '那个', '就是说', '然后呢',
    '这个', '对吧', '是不是', '怎么说呢', '就是', '反正',
    '就是那个', '其实呢', '所以说', '那么', '的话',
    '然后', '然后就是', '那个什么', '怎么说', '对不对',
    '嘛', '呀', '呢', '哦', '吧'
]


def analyze_speech_quality(asr_result: dict, audio_path: str = None) -> dict:
    """
    综合语音质量分析
    输入：ASR 结果 + 可选的音频文件路径
    输出：语音质量分析报告
    """
    segments = asr_result.get('segments', [])
    transcript = asr_result.get('transcript', '')
    duration = asr_result.get('duration', 0)

    if not segments and not transcript:
        return _empty_result()

    # 1. 语速分析
    speech_rate = _analyze_speech_rate(segments, duration)

    # 2. 停顿分析
    pauses = _analyze_pauses(segments, duration)

    # 3. 填充词检测
    fillers = _detect_fillers(segments, transcript)

    # 4. 语调分析（需要音频文件）
    prosody = {'enabled': False}
    if audio_path:
        try:
            prosody = _analyze_prosody(audio_path)
        except Exception as e:
            logger.warning(f"语调分析失败: {e}")
            prosody = {'enabled': False, 'error': str(e)}

    # 5. 综合评分
    overall = _calculate_overall_rating(speech_rate, pauses, fillers, prosody)

    return {
        'speech_rate': speech_rate,
        'pauses': pauses,
        'fillers': fillers,
        'prosody': prosody,
        'overall_rating': overall,
        'duration': duration
    }


def _analyze_speech_rate(segments: list, total_duration: float) -> dict:
    """按说话人分析语速"""
    speaker_data = {}

    for seg in segments:
        # Speaker evidence is allowed to be unresolved. Keep those segments in
        # an explicit diagnostic bucket instead of inventing SPEAKER_0.
        speaker = seg.get('speaker') or 'UNKNOWN'
        if speaker not in speaker_data:
            speaker_data[speaker] = {'chars': 0, 'seconds': 0.0}

        text = seg.get('text', '')
        speaker_data[speaker]['chars'] += len(text)
        speaker_data[speaker]['seconds'] += seg.get('end', 0) - seg.get('start', 0)

    results = []
    for speaker, data in sorted(speaker_data.items()):
        if data['seconds'] <= 0:
            continue
        rate = data['chars'] / (data['seconds'] / 60)  # 字/分钟

        if rate > 280:
            rating = '过快'
            rating_score = 30
        elif rate > 250:
            rating = '偏快'
            rating_score = 60
        elif rate >= 200:
            rating = '适中'
            rating_score = 100
        elif rate >= 160:
            rating = '偏慢'
            rating_score = 60
        else:
            rating = '过慢'
            rating_score = 30

        results.append({
            'speaker': speaker,
            'chars_per_minute': round(rate, 1),
            'total_chars': data['chars'],
            'speaking_seconds': round(data['seconds'], 1),
            'speaking_ratio': round(data['seconds'] / total_duration * 100, 1),
            'rating': rating,
            'rating_score': rating_score
        })

    # 全局语速
    total_chars = sum(r['total_chars'] for r in results)
    total_speaking = sum(r['speaking_seconds'] for r in results)
    global_rate = total_chars / (total_speaking / 60) if total_speaking > 0 else 0

    return {
        'per_speaker': results,
        'global_chars_per_minute': round(global_rate, 1),
        'global_rating': _rate_to_rating(global_rate),
        'ideal_range': '200-250 字/分钟'
    }


def _rate_to_rating(rate: float) -> str:
    if rate > 280: return '过快'
    if rate > 250: return '偏快'
    if rate >= 200: return '适中'
    if rate >= 160: return '偏慢'
    return '过慢'


def _analyze_pauses(segments: list, total_duration: float, threshold: float = 2.0) -> dict:
    """分析段间停顿"""
    if len(segments) < 2:
        return {
            'total_pauses': 0,
            'avg_pause_duration': 0,
            'longest_pause': 0,
            'pauses_per_minute': 0,
            'rating': '优秀',
            'details': []
        }

    pauses = []
    for i in range(len(segments) - 1):
        gap = segments[i + 1].get('start', 0) - segments[i].get('end', 0)
        if gap > threshold:
            severity = '严重' if gap > 5 else '明显' if gap > 3 else '轻微'
            pauses.append({
                'position_seconds': round(segments[i].get('end', 0), 1),
                'duration': round(gap, 2),
                'severity': severity,
                'context_before': segments[i].get('text', '')[-30:],
                'context_after': segments[i + 1].get('text', '')[:30]
            })

    total_pauses = len(pauses)
    avg_pause = round(sum(p['duration'] for p in pauses) / max(total_pauses, 1), 2)
    longest = max((p['duration'] for p in pauses), default=0)
    pauses_per_min = round(total_pauses / (total_duration / 60), 1) if total_duration > 0 else 0

    if total_pauses <= 3:
        rating = '优秀'
    elif total_pauses <= 8:
        rating = '良好'
    else:
        rating = '需改进'

    return {
        'total_pauses': total_pauses,
        'avg_pause_duration': avg_pause,
        'longest_pause': round(longest, 2),
        'pauses_per_minute': pauses_per_min,
        'rating': rating,
        'details': pauses  # 保留全部停顿数据
    }


def _detect_fillers(segments: list, transcript: str = "") -> dict:
    """检测填充词使用频率"""
    filler_counts = {}
    total_words = 0

    # 优先用分段落数据，其次用完整文本
    if segments:
        for seg in segments:
            text = seg.get('text', '')
            words = list(jieba.cut(text))
            total_words += len(words)
            for word in words:
                word = word.strip()
                if word in FILLER_WORDS:
                    filler_counts[word] = filler_counts.get(word, 0) + 1
    elif transcript:
        words = list(jieba.cut(transcript))
        total_words = len(words)
        for word in words:
            word = word.strip()
            if word in FILLER_WORDS:
                filler_counts[word] = filler_counts.get(word, 0) + 1

    total_fillers = sum(filler_counts.values())
    filler_rate = round(total_fillers / max(total_words, 1) * 100, 2)

    if total_fillers <= 5:
        rating = '优秀'
    elif total_fillers <= 15:
        rating = '良好'
    elif total_fillers <= 30:
        rating = '一般'
    else:
        rating = '需改进'

    # 按频率排序
    sorted_fillers = sorted(filler_counts.items(), key=lambda x: -x[1])

    return {
        'total_fillers': total_fillers,
        'total_words': total_words,
        'filler_rate_percent': filler_rate,
        'filler_types': sorted_fillers[:10],
        'rating': rating
    }


def _analyze_prosody(audio_path: str) -> dict:
    """分析语调韵律（F0 基频起伏）"""
    import parselmouth

    snd = parselmouth.Sound(audio_path)
    pitch = snd.to_pitch()
    pitch_values = pitch.selected_array['frequency']

    # 过滤无声段（F0=0）
    voiced_pitch = pitch_values[pitch_values > 0]

    if len(voiced_pitch) == 0:
        return {'enabled': True, 'error': '未检测到有效语音'}

    mean_f0 = float(np.mean(voiced_pitch))
    f0_std = float(np.std(voiced_pitch))
    f0_min = float(np.min(voiced_pitch))
    f0_max = float(np.max(voiced_pitch))
    f0_range = f0_max - f0_min

    # 分段分析（按 10 秒切片）
    duration = snd.get_total_duration()
    segment_analysis = []
    for start in np.arange(0, duration, 10):
        end = min(start + 10, duration)
        part = snd.extract_part(from_time=start, to_time=end)
        part_pitch = part.to_pitch()
        part_values = part_pitch.selected_array['frequency']
        part_voiced = part_values[part_values > 0]
        if len(part_voiced) > 0:
            segment_analysis.append({
                'start': round(start, 1),
                'end': round(end, 1),
                'mean_f0': round(float(np.mean(part_voiced)), 1),
                'f0_std': round(float(np.std(part_voiced)), 1)
            })

    # 评分
    if f0_std > 40:
        rating = '起伏自然，表达力强'
    elif f0_std > 20:
        rating = '语调正常'
    else:
        rating = '语调偏平，可能在念稿'

    return {
        'enabled': True,
        'mean_f0_hz': round(mean_f0, 1),
        'f0_std_hz': round(f0_std, 1),
        'f0_range_hz': round(f0_range, 1),
        'f0_min_hz': round(f0_min, 1),
        'f0_max_hz': round(f0_max, 1),
        'rating': rating,
        'segment_analysis': segment_analysis[:60]  # 最多60段
    }


def _calculate_overall_rating(speech_rate, pauses, fillers, prosody) -> dict:
    """综合语音质量评分"""
    scores = []

    # 语速（30%）
    sr_score = 80  # 默认
    for speaker in speech_rate.get('per_speaker', []):
        sr_score = min(sr_score, speaker.get('rating_score', 80))
    scores.append(('语速', sr_score, 0.3))

    # 停顿（25%）
    pause_rating = pauses.get('rating', '良好')
    pause_score = {'优秀': 95, '良好': 75, '需改进': 45}.get(pause_rating, 60)
    scores.append(('停顿', pause_score, 0.25))

    # 填充词（25%）
    filler_rating = fillers.get('rating', '良好')
    filler_score = {'优秀': 95, '良好': 75, '一般': 55, '需改进': 35}.get(filler_rating, 60)
    scores.append(('填充词', filler_score, 0.25))

    # 语调（20%）
    if prosody.get('enabled'):
        prosody_rating = prosody.get('rating', '')
        if '表达力强' in prosody_rating:
            prosody_score = 95
        elif '正常' in prosody_rating:
            prosody_score = 75
        else:
            prosody_score = 45
    else:
        prosody_score = 70  # 未分析时给中等分
    scores.append(('语调', prosody_score, 0.2))

    total = sum(s * w for _, s, w in scores)

    return {
        'total_score': round(total, 1),
        'breakdown': [{'dimension': name, 'score': score, 'weight': weight} for name, score, weight in scores],
        'grade': '优秀' if total >= 85 else '良好' if total >= 70 else '一般' if total >= 55 else '需改进'
    }


def _empty_result() -> dict:
    return {
        'speech_rate': {'per_speaker': [], 'global_chars_per_minute': 0, 'global_rating': '无数据'},
        'pauses': {'total_pauses': 0, 'rating': '无数据', 'details': []},
        'fillers': {'total_fillers': 0, 'rating': '无数据', 'filler_types': []},
        'prosody': {'enabled': False},
        'overall_rating': {'total_score': 0, 'grade': '无数据', 'breakdown': []},
        'duration': 0
    }
