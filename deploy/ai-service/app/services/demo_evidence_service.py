"""Infer on-site demo evidence strength from scoring result payloads."""

from __future__ import annotations


DEMO_KEYWORDS = ("现场演示", "演示", "实操", "操作", "运行", "系统界面", "设备", "功能")
RUNTIME_KEYWORDS = ("成功", "结果", "运行成功", "完成", "日志", "输出", "识别结果", "控制")
TEST_KEYWORDS = ("测试", "benchmark", "准确率", "响应时间", "性能", "并发", "错误率", "报告", "ms", "%")
FAILURE_KEYWORDS = ("报错", "失败", "中断", "卡顿", "崩溃", "无法打开", "超时")


def _collect_text(result: dict) -> str:
    parts = []
    asr = result.get("asr") or {}
    parts.append(str(asr.get("transcript") or ""))
    video = result.get("video_analysis") or {}
    for frame in video.get("per_frame") or []:
        screen = frame.get("screen_content") or {}
        parts.append(str(screen.get("screen_type") or ""))
        parts.append(str(screen.get("text") or screen.get("visible_text") or ""))
    fusion = result.get("fusion") or {}
    summary = fusion.get("screen_content_summary") or {}
    parts.append(str(summary.get("screen_type_distribution") or ""))
    return " ".join(parts)


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def analyze_demo_evidence(result: dict) -> dict:
    text = _collect_text(result or {})
    has_demo = _has_any(text, DEMO_KEYWORDS)
    has_runtime_result = _has_any(text, RUNTIME_KEYWORDS)
    has_test_data = _has_any(text, TEST_KEYWORDS)
    has_failure = _has_any(text, FAILURE_KEYWORDS)

    if has_demo and has_runtime_result and has_test_data:
        level = "full_channel"
        score_band = "95-100"
    elif has_demo and has_runtime_result:
        level = "demo_runtime"
        score_band = "80-95"
    elif has_demo:
        level = "demo_only"
        score_band = "60-80"
    else:
        level = "verbal_or_ppt_only"
        score_band = "40-60"

    return {
        "has_demo": has_demo,
        "has_runtime_result": has_runtime_result,
        "has_test_data": has_test_data,
        "has_failure": has_failure,
        "level": level,
        "score_band": score_band,
    }
