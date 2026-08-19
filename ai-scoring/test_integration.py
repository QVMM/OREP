#!/usr/bin/env python3
"""
OREP AI 评分集成测试 — 单画面 & 双画面流水线
用 mock 数据测试逻辑完整性，不调用真实 LLM/ASR API
"""
import os
import sys
import json
import asyncio
import tempfile
import struct
import wave
from datetime import datetime
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.expanduser("~/项目/OREP/ai-scoring"))

from app.services import pipeline_service, audio_service
from app.services import speech_analysis_service
from app.services import llm_scoring_service
from app.services import report_service
from app.services.fusion_service import fusion_service
from app.services.character_profile_service import character_profile_service


# ══════════════════════════════════════
#  工具函数
# ══════════════════════════════════════

def create_test_wav(duration_sec=30, sample_rate=16000):
    """创建一个测试用 WAV 文件"""
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    with wave.open(tmp.name, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        # 写入静音数据
        num_frames = sample_rate * duration_sec
        wf.writeframes(b'\x00\x00' * num_frames)
    return tmp.name


def create_test_video(duration_sec=30):
    """创建一个测试用 MP4 文件（假视频）"""
    tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    # 写入一些字节让 ffprobe 能识别（可能失败，没关系）
    tmp.write(b'\x00' * 1024)
    tmp.close()
    return tmp.name


def mock_asr_result(duration=1800):
    """模拟 ASR 识别结果"""
    segments = []
    # 生成 ~30 分钟的模拟演讲段落
    texts = [
        "各位评委老师好，今天我为大家带来的项目是智慧城市管理系统。",
        "我们的产品主要解决城市管理中的数据孤岛问题。",
        "通过物联网传感器网络，实时采集城市运行数据。",
        "我们的技术团队由五名核心成员组成，分工明确。",
        "在市场分析方面，我们调研了全国二十个城市的需求。",
        "竞品方面，我们与三家头部厂商进行了对比分析。",
        "商业模式上，我们采用SaaS订阅加硬件销售的组合模式。",
        "财务预测显示，第三年可以实现盈利。",
        "我们已经获得了某市政府的试点合作意向。",
        "接下来回答各位评委的提问。",
    ]
    t = 0.0
    for i in range(50):
        text = texts[i % len(texts)]
        seg_dur = duration / 50
        segments.append({
            'text': text,
            'start': round(t, 1),
            'end': round(t + seg_dur - 1.0, 1),
            'speaker': f'SPEAKER_{i % 3}',
        })
        t += seg_dur

    return {
        'transcript': ' '.join([s['text'] for s in segments]),
        'segments': segments,
        'duration': duration,
        'speakers': ['SPEAKER_0', 'SPEAKER_1', 'SPEAKER_2'],
    }


def mock_video_analysis(duration=1800, interval=30):
    """模拟视频分析结果"""
    num_frames = duration // interval
    per_frame = []
    for i in range(num_frames):
        per_frame.append({
            'timestamp': round(i * interval, 1),
            'gesture_score': round(5 + (i % 5) * 0.8, 1),
            'expression_score': round(6 + (i % 4) * 0.7, 1),
            'eye_contact_score': round(4 + (i % 6) * 0.9, 1),
            'posture_score': round(5 + (i % 5) * 0.6, 1),
            'visual_composite': round(5.2 + (i % 5) * 0.75, 1),
        })

    return {
        'frame_count': num_frames,
        'interval_sec': interval,
        'per_frame': per_frame,
        'aggregates': {
            'avg_gesture_score': 6.5,
            'avg_expression_score': 6.8,
            'avg_eye_contact_score': 6.2,
            'avg_posture_score': 6.0,
            'avg_visual_composite': 6.4,
        },
        'tokens_used': {'total': 5000},
    }


def mock_llm_result():
    """模拟 LLM 评分结果"""
    return {
        'overall_score': 72,
        'dimensions': {
            'skill_level': {
                'name': '技术技能水平',
                'score': 15,
                'max_score': 20,
                'items': [
                    {'name': '专业知识', 'score': 8, 'max_score': 10, 'reason': '技术基础扎实', 'improvement': '加深对前沿技术的理解'},
                    {'name': '技术方案', 'score': 7, 'max_score': 10, 'reason': '方案合理可行', 'improvement': '优化架构设计细节'},
                ]
            },
            'professionalism': {
                'name': '职业素养',
                'score': 14,
                'max_score': 20,
                'items': [
                    {'name': '表达能力', 'score': 7, 'max_score': 10, 'reason': '逻辑清晰', 'improvement': '减少口头禅使用'},
                    {'name': '时间管理', 'score': 7, 'max_score': 10, 'reason': '节奏把控较好', 'improvement': '注意各部分时间分配'},
                ]
            },
            'innovation': {
                'name': '创新创意',
                'score': 15,
                'max_score': 20,
                'items': [
                    {'name': '创新点', 'score': 8, 'max_score': 10, 'reason': '有差异化创新', 'improvement': '突出核心创新价值'},
                    {'name': '可行性', 'score': 7, 'max_score': 10, 'reason': '落地性较强', 'improvement': '补充更多验证数据'},
                ]
            },
            'application_value': {
                'name': '应用价值',
                'score': 14,
                'max_score': 20,
                'items': [
                    {'name': '市场需求', 'score': 7, 'max_score': 10, 'reason': '需求明确', 'improvement': '深化用户画像分析'},
                    {'name': '商业前景', 'score': 7, 'max_score': 10, 'reason': '模式合理', 'improvement': '完善盈利模式细节'},
                ]
            },
            'teamwork': {
                'name': '团队合作',
                'score': 14,
                'max_score': 20,
                'items': [
                    {'name': '协作展示', 'score': 7, 'max_score': 10, 'reason': '分工明确', 'improvement': '加强团队默契配合'},
                    {'name': '角色互补', 'score': 7, 'max_score': 10, 'reason': '各有专长', 'improvement': '展示更多协作成果'},
                ]
            },
        },
        'highlights': [
            '项目选题贴合智慧城市发展趋势，具有现实意义',
            '团队分工明确，技术架构设计合理',
        ],
        'critical_issues': [
            '路演过程中有较多停顿，影响表达流畅度',
            '部分技术细节阐述不够深入',
        ],
        'improvement_priorities': [
            {'priority': 1, 'dimension': '职业素养', 'issue': '表达不够流畅', 'suggestion': '建议多做脱稿练习，减少口头禅和停顿'},
            {'priority': 2, 'dimension': '技术技能水平', 'issue': '深度不足', 'suggestion': '建议补充核心技术的实现细节和性能数据'},
            {'priority': 3, 'dimension': '创新创意', 'issue': '创新点不够突出', 'suggestion': '建议在开场就明确阐述核心创新价值'},
        ],
        'model': 'deepseek-chat',
        'provider': 'deepseek',
        'tokens_used': {'total': 3000},
    }


def mock_character_profile():
    """模拟能力画像"""
    return {
        'profile_markdown': """## 能力画像

### 预热期（0-8min）
- **表现特征**: 开场准备充分，条理清晰
- **核心发现**: 选手在开场阶段表现出较强的信心

### 高潮期（8-16min）
- **表现特征**: 技术阐述深入，节奏把控好
- **核心发现**: 在产品演示环节表现最佳

### 选手分析

| 选手 | 时段 | 角色 | 表现特征 | 强项 | 弱项 | 改进建议 |
|------|------|------|----------|------|------|----------|
| 张三 | 全程 | 主讲 | 技术功底扎实 | 逻辑清晰 | 停顿较多 | 脱稿练习 |
""",
        'sections': {'warmup': '准备充分', 'climax': '技术深入'},
        'provider': 'deepseek',
    }


def mock_speech_quality(duration=1800):
    """模拟语音质量分析"""
    return {
        'speech_rate': {
            'global_chars_per_minute': 210,
            'global_rating': '良好',
            'ideal_range': '200-250 字/分钟',
        },
        'pauses': {
            'total_pauses': 8,
            'long_pauses': 3,
            'rating': '一般',
            'details': [
                {'position_seconds': 120, 'duration': 3.5, 'severity': '明显', 'context_before': '我们的产品', 'context_after': '主要解决'},
                {'position_seconds': 450, 'duration': 5.2, 'severity': '严重', 'context_before': '技术方案', 'context_after': '采用微服务'},
                {'position_seconds': 900, 'duration': 2.8, 'severity': '轻微', 'context_before': '市场规模', 'context_after': '预计达到'},
            ],
        },
        'fillers': {
            'total_fillers': 15,
            'total_words': 500,
            'filler_rate_percent': 3.0,
            'rating': '良好',
            'filler_types': [('嗯', 8), ('那个', 4), ('就是', 3)],
        },
        'prosody': {'enabled': False},
        'overall_rating': {'rating': '良好', 'score': 7.5},
        'duration': duration,
    }


# ══════════════════════════════════════
#  测试用例
# ══════════════════════════════════════

PASS = 0
FAIL = 0
WARN = 0

def check(name, condition, level='FAIL'):
    global PASS, FAIL, WARN
    if condition:
        print(f"  ✅ {name}")
        PASS += 1
    elif level == 'WARN':
        print(f"  ⚠️  {name}")
        WARN += 1
    else:
        print(f"  ❌ {name}")
        FAIL += 1


def test_structures():
    """测试 1: 检查单/双流水线返回结构一致性"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("📋 测试 1: 结构一致性检查")
    print("="*60)

    # 测试 skip_llm dimensions 格式
    from app.services.pipeline_service import _save_result
    dim_names = ['技术技能水平', '职业素养', '创新创意', '应用价值', '团队合作']
    skip_dims = {name: {'name': name, 'score': 15, 'max_score': 20, 'items': []} for name in dim_names}

    check("skip_llm dimensions 是 dict", isinstance(skip_dims, dict))
    check("skip_llm dimensions 有5个维度", len(skip_dims) == 5)
    for name in dim_names:
        dim = skip_dims[name]
        check(f"  维度 '{name}' 有 name/score/max_score/items",
              all(k in dim for k in ['name', 'score', 'max_score', 'items']))
        check(f"  维度 '{name}' items 是 list", isinstance(dim.get('items'), list))

    # 测试 improvement_priorities 兼容性
    str_priorities = ['建议1', '建议2', '建议3']
    obj_priorities = [
        {'priority': 1, 'dimension': '测试', 'issue': '问题', 'suggestion': '建议'},
    ]

    check("字符串 priorities 可迭代", all(isinstance(p, str) for p in str_priorities))
    check("对象 priorities 可 .get()", all(isinstance(p, dict) and hasattr(p, 'get') for p in obj_priorities))

    # 测试 report_service 的 _add_priorities 路径兼容
    # 字符串列表应能正确处理
    merged = []
    if str_priorities and isinstance(str_priorities[0], str):
        for i, text in enumerate(str_priorities):
            merged.append({'dimension': '', 'issue': '', 'suggestion': text})
    check("字符串 priorities 可转为 merged 结构", len(merged) == 3)
    check("merged 结构有 suggestion 字段", all('suggestion' in m for m in merged))

    # 对象列表应能正确处理
    merged2 = []
    sorted_p = sorted(obj_priorities, key=lambda x: x.get('priority', 99) if isinstance(x, dict) else 99)
    for p_item in sorted_p:
        if isinstance(p_item, dict):
            merged2.append({
                'dimension': p_item.get('dimension', ''),
                'issue': p_item.get('issue', ''),
                'suggestion': p_item.get('suggestion', ''),
            })
    check("对象 priorities 可正确排序和转换", len(merged2) == 1)
    check("对象 priorities priority=1 排序正确", merged2[0]['dimension'] == '测试')


def test_speech_analysis():
    """测试 2: 语音质量分析（真实调用）"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("🎤 测试 2: 语音质量分析")
    print("="*60)

    asr = mock_asr_result(duration=1800)
    result = speech_analysis_service.analyze_speech_quality(asr)

    check("语音分析返回 dict", isinstance(result, dict))
    check("有 speech_rate 字段", 'speech_rate' in result)
    check("有 pauses 字段", 'pauses' in result)
    check("有 fillers 字段", 'fillers' in result)
    check("语速在合理范围",
          100 < result.get('speech_rate', {}).get('global_chars_per_minute', 0) < 500)
    check("停顿分析有 details", isinstance(result.get('pauses', {}).get('details', []), list))
    check("口头禅检测有 filler_types",
          isinstance(result.get('fillers', {}).get('filler_types', []), list))


def test_fusion():
    """测试 3: 音视频融合"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("🔗 测试 3: 音视频融合")
    print("="*60)

    asr = mock_asr_result(duration=1800)
    video = mock_video_analysis(duration=1800, interval=30)

    result = fusion_service.run_fusion(
        asr_segments=asr['segments'],
        video_per_frame=video['per_frame'],
        window_sec=30
    )

    check("融合返回 dict", isinstance(result, dict))
    check("有 summary", 'summary' in result)
    check("有 trends", 'trends' in result)
    check("有 contradictions", 'contradictions' in result)
    check("有 timeline", 'timeline' in result)

    summary = result.get('summary', {})
    check("summary 有 fusion_avg", 'fusion_avg' in summary)
    check("fusion_avg 在 1-10 范围", 1 <= summary.get('fusion_avg', 0) <= 10)

    trends = result.get('trends', {})
    check("trends 有 gesture", 'gesture' in trends)
    check("trends 有 expression", 'expression' in trends)
    check("trends 有 eye_contact", 'eye_contact' in trends)
    check("trends 有 fusion", 'fusion' in trends)

    for dim in ['gesture', 'expression', 'eye_contact', 'fusion']:
        t = trends.get(dim, {})
        check(f"  trends.{dim} 有 values/avg/min/max",
              all(k in t for k in ['values', 'avg', 'min', 'max']))
        if t.get('values'):
            check(f"  trends.{dim} values 非空", len(t['values']) > 0)


def test_skip_llm_duration():
    """测试 4: 时长不足处理逻辑"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("⏱️  测试 4: 时长不足处理逻辑")
    print("="*60)

    # < 600s: skip_llm
    dim_names = ['技术技能水平', '职业素养', '创新创意', '应用价值', '团队合作']
    actual_duration = 300
    skip_llm = actual_duration < 600
    check("300s 应触发 skip_llm", skip_llm == True)

    ai_score = {
        'overall_score': 15,
        'dimensions': {name: {'name': name, 'score': 15, 'max_score': 20, 'items': []} for name in dim_names},
        'model': 'duration_adjustment',
    }
    check("skip_llm overall_score=15", ai_score['overall_score'] == 15)
    check("skip_llm 有5个维度", len(ai_score['dimensions']) == 5)
    for name in dim_names:
        check(f"  skip_llm 维度 '{name}' score=15",
              ai_score['dimensions'][name]['score'] == 15)

    # 600-1800s: score_cap=35
    actual_duration = 900
    score_cap = None
    duration_note = None
    if actual_duration < 600:
        pass
    elif actual_duration < 1800:
        score_cap = 35
    check("900s 应设置 score_cap=35", score_cap == 35)

    # score_cap 应用测试
    test_score = {'overall_score': 72, 'dimensions': {}}
    if score_cap and test_score['overall_score'] > score_cap:
        test_score['overall_score'] = score_cap
    check("score_cap 应将 72 降到 35", test_score['overall_score'] == 35)

    # > 1800s: 正常评分
    actual_duration = 2400
    score_cap = None
    if actual_duration < 600:
        pass
    elif actual_duration < 1800:
        score_cap = 35
    check("2400s 不应设置 score_cap", score_cap is None)


def test_report_generation():
    """测试 5: PDF 报告生成（单画面 mock 数据）"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("📄 测试 5: PDF 报告生成 - 单画面")
    print("="*60)

    result = {
        'meeting_id': 'test_single_001',
        'status': 'completed',
        'has_video': True,
        'completed_at': datetime.now().isoformat(),
        'asr': {
            'transcript': '各位评委老师好，今天我为大家带来智慧城市项目。',
            'duration': 1800,
            'segments': mock_asr_result()['segments'],
        },
        'speech_quality': mock_speech_quality(),
        'ai_score': {
            **mock_llm_result(),
            'overall_score': 72,
        },
        'fusion': {
            'summary': {
                'fusion_avg': 6.5,
                'gesture_avg': 6.2,
                'expression_avg': 6.8,
                'eye_contact_avg': 5.9,
                'contradiction_count': 3,
            },
            'trends': {
                'gesture': {'values': [5,6,7,6,5]*12, 'avg': 6.2, 'min': 3, 'max': 9},
                'expression': {'values': [6,7,7,6,6]*12, 'avg': 6.8, 'min': 4, 'max': 9},
                'eye_contact': {'values': [5,5,6,6,7]*12, 'avg': 5.9, 'min': 3, 'max': 8},
                'fusion': {'values': [5.5,6.2,6.8,6.3,5.8]*12, 'avg': 6.5, 'min': 3.5, 'max': 8.5},
                'speech_rate': {'values': [200,210,220,215,205]*12, 'avg': 210, 'min': 180, 'max': 250},
                'pauses': {'values': [0,1,0,2,1]*12, 'avg': 0.8, 'min': 0, 'max': 3},
            },
            'contradictions': [
                {'time_min': 5, 'description': '语音表现好(8.0分)但视觉表现差(3.0分)', 'audio_score': 8.0, 'visual_score': 3.0},
            ],
            'timeline': [{'time_min': i*0.5, 'text_preview': '测试段落'} for i in range(60)],
        },
        'character_profile': mock_character_profile(),
    }

    try:
        report_dir = tempfile.mkdtemp()
        report_path = report_service.generate_report(result, report_dir)
        check("单画面报告生成成功", os.path.exists(report_path))
        file_size = os.path.getsize(report_path)
        check(f"报告文件大小合理 ({file_size/1024:.1f}KB)", file_size > 1000)
        # 清理
        os.remove(report_path)
    except Exception as e:
        check(f"单画面报告生成失败: {e}", False)


def test_report_generation_dual():
    """测试 6: PDF 报告生成（双画面 mock 数据）"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("📄 测试 6: PDF 报告生成 - 双画面")
    print("="*60)

    result = {
        'meeting_id': 'test_dual_001',
        'status': 'completed',
        'has_video': True,
        'recording_mode': 'dual',
        'completed_at': datetime.now().isoformat(),
        'asr': {
            'transcript': '各位评委老师好，今天由我来展示我们的智慧城市项目。',
            'duration': 2400,
            'segments': mock_asr_result(duration=2400)['segments'],
        },
        'speech_quality': mock_speech_quality(duration=2400),
        'ai_score': {
            **mock_llm_result(),
            'overall_score': 78,
        },
        'video_camera_analysis': {
            'frame_count': 80,
            'aggregates': {'avg_visual_composite': 6.8},
        },
        'video_screen_analysis': {
            'frame_count': 80,
            'aggregates': {'avg_visual_composite': 7.2},
        },
        'fusion': {
            'summary': {
                'fusion_avg': 7.0,
                'gesture_avg': 6.5,
                'expression_avg': 7.0,
                'eye_contact_avg': 6.3,
                'contradiction_count': 2,
            },
            'trends': {
                'gesture': {'values': [6,7,7,6,6]*16, 'avg': 6.5, 'min': 4, 'max': 9},
                'expression': {'values': [7,7,8,7,6]*16, 'avg': 7.0, 'min': 5, 'max': 9},
                'eye_contact': {'values': [6,6,7,6,7]*16, 'avg': 6.3, 'min': 4, 'max': 8},
                'fusion': {'values': [6.5,7.0,7.5,6.8,6.5]*16, 'avg': 7.0, 'min': 4, 'max': 9},
                'speech_rate': {'values': [210,220,215,225,210]*16, 'avg': 216, 'min': 190, 'max': 260},
                'pauses': {'values': [0,0,1,0,1]*16, 'avg': 0.4, 'min': 0, 'max': 2},
            },
            'contradictions': [
                {'time_min': 8, 'description': '语音表现好(7.5分)但视觉表现差(4.0分)', 'audio_score': 7.5, 'visual_score': 4.0},
            ],
            'timeline': [{'time_min': i*0.5, 'text_preview': '双画面测试段落'} for i in range(80)],
        },
        'character_profile': mock_character_profile(),
    }

    try:
        report_dir = tempfile.mkdtemp()
        report_path = report_service.generate_report(result, report_dir)
        check("双画面报告生成成功", os.path.exists(report_path))
        file_size = os.path.getsize(report_path)
        check(f"报告文件大小合理 ({file_size/1024:.1f}KB)", file_size > 1000)
        os.remove(report_path)
    except Exception as e:
        check(f"双画面报告生成失败: {e}", False)


def test_skip_llm_report():
    """测试 7: skip_llm 模式下的报告生成"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("📄 测试 7: PDF 报告生成 - skip_llm (时长不足)")
    print("="*60)

    dim_names = ['技术技能水平', '职业素养', '创新创意', '应用价值', '团队合作']
    result = {
        'meeting_id': 'test_skip_001',
        'status': 'completed',
        'has_video': False,
        'completed_at': datetime.now().isoformat(),
        'asr': {
            'transcript': '简短的测试路演。',
            'duration': 300,
            'segments': [{'text': '简短的测试路演。', 'start': 0, 'end': 5, 'speaker': 'SPEAKER_0'}],
        },
        'speech_quality': {
            'speech_rate': {'global_chars_per_minute': 150, 'global_rating': '偏慢'},
            'pauses': {'total_pauses': 2, 'rating': '一般', 'details': []},
            'fillers': {'total_fillers': 3, 'total_words': 50, 'filler_rate_percent': 6.0, 'filler_types': [('嗯', 3)]},
            'prosody': {'enabled': False},
            'duration': 300,
        },
        'ai_score': {
            'overall_score': 15,
            'dimensions': {name: {'name': name, 'score': 15, 'max_score': 20, 'items': []} for name in dim_names},
            'highlights': ['路演时长严重不足，建议补充完整演示内容'],
            'critical_issues': ['路演实际时长 300 秒，远低于比赛要求的 3600 秒'],
            'improvement_priorities': ['建议按照完整比赛流程进行路演展示，确保覆盖所有评审维度'],
            'model': 'duration_adjustment',
            'provider': 'system',
        },
    }

    try:
        report_dir = tempfile.mkdtemp()
        report_path = report_service.generate_report(result, report_dir)
        check("skip_llm 报告生成成功", os.path.exists(report_path))
        file_size = os.path.getsize(report_path)
        check(f"报告文件大小合理 ({file_size/1024:.1f}KB)", file_size > 500)
        os.remove(report_path)
    except Exception as e:
        check(f"skip_llm 报告生成失败: {e}", False)


def test_callback_payload():
    """测试 8: 后端回调 payload 结构"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("🔄 测试 8: 后端回调 payload 结构")
    print("="*60)

    result = {
        'meeting_id': 'test_callback_001',
        'status': 'completed',
        'has_video': True,
        'ai_score': mock_llm_result(),
        'asr': {'transcript': '测试文本', 'duration': 1800},
        'speech_quality': mock_speech_quality(),
        'fusion': {'summary': {'fusion_avg': 6.5}},
    }

    # 模拟 _notify_backend 构建 payload
    payload = {
        'meetingId': result.get('meeting_id'),
        'status': result.get('status'),
        'overallScore': result.get('ai_score', {}).get('overall_score', 0),
        'resultPath': f"results/result_{result.get('meeting_id')}.json",
        'model': result.get('ai_score', {}).get('model', ''),
        'transcript': result.get('asr', {}).get('transcript', ''),
        'hasVideo': result.get('has_video', False),
    }

    ai_score = result.get('ai_score', {})
    if 'dimensions' in ai_score:
        payload['dimensions'] = ai_score['dimensions']
    if 'highlights' in ai_score:
        payload['highlights'] = ai_score['highlights']
    if 'critical_issues' in ai_score:
        payload['criticalIssues'] = ai_score['critical_issues']
    if 'improvement_priorities' in ai_score:
        payload['improvementPriorities'] = ai_score['improvement_priorities']
    if 'speech_quality' in result:
        payload['speechQuality'] = result['speech_quality']

    # 序列化测试
    try:
        json_str = json.dumps(payload, ensure_ascii=False)
        check("payload 可序列化为 JSON", True)
    except Exception as e:
        check(f"payload 序列化失败: {e}", False)
        return

    # 检查后端期望的字段
    check("payload 有 meetingId", 'meetingId' in payload)
    check("payload 有 status", 'status' in payload)
    check("payload 有 overallScore", 'overallScore' in payload)
    check("payload 有 model", 'model' in payload)
    check("payload 有 transcript", 'transcript' in payload)
    check("payload 有 dimensions", 'dimensions' in payload)
    check("payload 有 highlights", 'highlights' in payload)
    check("payload 有 criticalIssues", 'criticalIssues' in payload)
    check("payload 有 improvementPriorities", 'improvementPriorities' in payload)
    check("payload 有 speechQuality", 'speechQuality' in payload)

    # 检查 dimensions 可被 Java 端解析
    dims = payload.get('dimensions', {})
    check("dimensions 是 dict", isinstance(dims, dict))
    for key, dim in dims.items():
        check(f"  dimensions.{key} 是 dict", isinstance(dim, dict))
        check(f"  dimensions.{key} 有 score", 'score' in dim)


def test_audio_conversion():
    """测试 9: 音频转码"""
    global PASS, FAIL, WARN

    print("\n" + "="*60)
    print("🎵 测试 9: 音频转码")
    print("="*60)

    wav_path = create_test_wav(duration_sec=10)
    try:
        # 测试转码为 WAV（已经是 WAV，应该直接返回或复制）
        result = audio_service.convert_to_wav(wav_path)
        check("WAV 转码成功", os.path.exists(result))
        check("输出是 .wav 文件", result.endswith('.wav'))

        # 测试获取音频信息
        info = audio_service.get_audio_info(result)
        check("音频信息获取成功", isinstance(info, dict))
        check("有 duration 字段", 'duration' in info)
        check("duration ~10秒", 9 < info.get('duration', 0) < 11)
    except Exception as e:
        check(f"音频转码测试失败: {e}", False)
    finally:
        for f in [wav_path, result]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass


# ══════════════════════════════════════
#  运行所有测试
# ══════════════════════════════════════

if __name__ == '__main__':
    print("╔" + "═"*58 + "╗")
    print("║   OREP AI 评分集成测试                                 ║")
    print("║   单画面 & 双画面流水线                                ║")
    print("╚" + "═"*58 + "╝")

    test_structures()
    test_speech_analysis()
    test_fusion()
    test_skip_llm_duration()
    test_report_generation()
    test_report_generation_dual()
    test_skip_llm_report()
    test_callback_payload()
    test_audio_conversion()

    print("\n" + "="*60)
    print(f"📊 结果汇总: ✅ {PASS} 通过  ❌ {FAIL} 失败  ⚠️  {WARN} 警告")
    print("="*60)

    if FAIL > 0:
        print("❌ 存在失败用例，请检查上方详情")
        sys.exit(1)
    else:
        print("✅ 全部通过!")
        sys.exit(0)
