"""
重新分析 meeting_4 的语音数据，更新 result_4.json，再重新生成 PDF
"""
import sys, json, os
sys.path.insert(0, '.')

from app.services.asr_service import transcribe_long_audio
from app.services.speech_analysis_service import analyze_speech_quality
from app.services.report_service import generate_report

AUDIO_PATH = 'uploads/meeting_4_14132_converted.wav'
RESULT_PATH = 'uploads/results/result_4.json'

# 1. 加载现有结果
print("[1/4] 加载现有结果...")
with open(RESULT_PATH, 'r', encoding='utf-8') as f:
    result = json.load(f)

# 2. 重新 ASR（带时间戳分段）
print("[2/4] 重新 ASR 识别（分片处理，预计 2-5 分钟）...")
asr_result = transcribe_long_audio(AUDIO_PATH, chunk_duration=300)
print(f"  ASR 完成: {len(asr_result['segments'])} 段, 时长 {asr_result['duration']:.1f}s")

# 3. 重新语音质量分析
print("[3/4] 重新语音质量分析...")
speech_quality = analyze_speech_quality(asr_result, AUDIO_PATH)
pauses = speech_quality.get('pauses', {})
fillers = speech_quality.get('fillers', {})
print(f"  停顿: {pauses.get('total_pauses')} 次 (details: {len(pauses.get('details', []))} 条)")
print(f"  口头禅: {fillers.get('total_fillers')} 次 (types: {len(fillers.get('filler_types', []))} 种)")

# 4. 更新结果并保存
print("[4/4] 更新结果并重新生成 PDF...")
result['asr'] = {
    'transcript': asr_result['transcript'],
    'segments': asr_result['segments'],
    'segment_count': len(asr_result['segments']),
    'duration': asr_result['duration'],
    'speakers': asr_result['speakers'],
}
result['speech_quality'] = speech_quality

with open(RESULT_PATH, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"  结果已更新: {RESULT_PATH}")

# 5. 重新生成 PDF
pdf_path = generate_report(result, 'uploads/reports')
print(f"\n✅ PDF 已生成: {pdf_path}")
