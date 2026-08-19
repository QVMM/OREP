"""音画证据对齐：内部 facts + 评分文案消歧。

对外 PDF / 学生可见文案不得出现抽帧数量、识别管道等实现细节。
"""

from __future__ import annotations

import copy
import re
from typing import Any


# 屏幕类型 / 内容类型中视为「开发者工具界面出现过」
_EDITOR_TYPES = ("代码编辑器", "IDE", "ide", "vscode", "VS Code", "编辑器")
_TERMINAL_TYPES = ("终端命令行", "终端", "命令行", "terminal", "shell")
_CODE_CONTENT = ("代码展示", "代码", "源码", "code")


# 与画面冲突的绝对否定（有开发者界面时禁止）
_ABSENT_IDE_CLAIM = re.compile(
    r"(?:"
    r"(?:全程未展示|完全未展示|未展示任何|没有任何|完全没有|完全无|缺少.{0,8}任何)"
    r".{0,24}"
    r"(?:IDE|ide|开发者工具|调试工具|代码编辑器?|vscode|VS\s*Code|命令行|终端)"
    r"|"
    r"(?:IDE|ide|开发者工具|调试工具|代码编辑器?).{0,12}(?:完全缺失|完全没有|完全未|全程未)"
    r"|"
    r"未展示.{0,8}(?:IDE|开发者工具|调试工具).{0,16}(?:任何|全部|完全)"
    r"|"
    r"缺少IDE界面截图"
    r"|"
    r"全程未展示IDE"
    r"|"
    r"未展示任何IDE界面"
    r")",
    re.IGNORECASE,
)

# 出口再清一次可能泄漏的内部措辞
_LEAK_PATTERNS = [
    re.compile(r"【?画面识别提示】?[^\n。]*[。]?", re.I),
    re.compile(r"本场抽帧已识别到[^。\n]*[。]?", re.I),
    re.compile(r"抽帧[^\n。]{0,40}帧", re.I),
    re.compile(r"代码编辑器约\s*\d+\s*帧", re.I),
]


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _screen_content_of_frame(frame: dict) -> dict:
    sc = frame.get("screen_content")
    if isinstance(sc, dict):
        return sc
    return {}


def build_visual_dev_tool_facts(
    result: dict | None = None,
    *,
    fusion_context: dict | None = None,
    video_analysis: dict | None = None,
) -> dict:
    """从 result / fusion / video_analysis 构建内部开发者界面 facts。"""
    result = result if isinstance(result, dict) else {}
    fusion = fusion_context if isinstance(fusion_context, dict) else _as_dict(result.get("fusion"))
    video = video_analysis if isinstance(video_analysis, dict) else _as_dict(result.get("video_analysis"))
    summary = _as_dict(fusion.get("screen_content_summary"))
    dist = _as_dict(summary.get("screen_type_distribution"))
    content_counts = _as_dict(summary.get("content_type_counts"))
    code_detections = summary.get("code_detections") if isinstance(summary.get("code_detections"), list) else []

    editor_count = 0
    terminal_count = 0
    for st, n in dist.items():
        st_s = str(st or "")
        try:
            n_i = int(n or 0)
        except Exception:
            n_i = 0
        if any(k.lower() in st_s.lower() for k in _EDITOR_TYPES if k.isascii()) or any(
            k in st_s for k in _EDITOR_TYPES if not k.isascii()
        ):
            editor_count += n_i
        if any(k.lower() in st_s.lower() for k in _TERMINAL_TYPES if k.isascii()) or any(
            k in st_s for k in _TERMINAL_TYPES if not k.isascii()
        ):
            terminal_count += n_i

    code_content_count = 0
    for ct, n in content_counts.items():
        ct_s = str(ct or "")
        try:
            n_i = int(n or 0)
        except Exception:
            n_i = 0
        if any(k in ct_s for k in _CODE_CONTENT):
            code_content_count += n_i

    # per_frame 兜底
    samples: list[float] = []
    if editor_count == 0 and terminal_count == 0:
        for frame in video.get("per_frame") or []:
            if not isinstance(frame, dict):
                continue
            sc = _screen_content_of_frame(frame)
            st = str(sc.get("screen_type") or "")
            try:
                ts = float(frame.get("timestamp_min") or 0)
            except Exception:
                ts = 0.0
            if any(k in st for k in ("代码编辑器", "编辑器")) or sc.get("has_code"):
                editor_count += 1
                if len(samples) < 5:
                    samples.append(ts)
            if any(k in st for k in ("终端", "命令行")):
                terminal_count += 1
                if len(samples) < 5:
                    samples.append(ts)

    for det in code_detections[:5]:
        if isinstance(det, dict):
            try:
                samples.append(float(det.get("timestamp_min") or 0))
            except Exception:
                pass
    samples = samples[:5]

    code_det_n = len(code_detections)
    has_code_editor_ui = editor_count > 0
    has_terminal_ui = terminal_count > 0
    has_code_content = code_content_count > 0 or code_det_n > 0 or has_code_editor_ui
    has_dev_tool_ui = has_code_editor_ui or has_terminal_ui or has_code_content

    return {
        "has_code_editor_ui": has_code_editor_ui,
        "has_terminal_ui": has_terminal_ui,
        "has_code_content": has_code_content,
        "has_dev_tool_ui": has_dev_tool_ui,
        "editor_count": editor_count,
        "terminal_count": terminal_count,
        "code_content_count": code_content_count,
        "code_detection_count": code_det_n,
        "screen_type_distribution": dist,
        "content_type_counts": content_counts,
        "sample_timestamps": samples,
    }


def format_visual_constraints_for_prompt(facts: dict) -> str:
    """写入评分 prompt 的约束段（可含内部计数；出口消毒会去掉泄漏句）。"""
    if not facts or not facts.get("has_dev_tool_ui"):
        return ""
    bits = []
    if facts.get("has_code_editor_ui"):
        bits.append("代码编辑器类界面（多次出现）")
    if facts.get("has_terminal_ui"):
        bits.append("终端/命令行界面")
    if facts.get("has_code_content") and not facts.get("has_code_editor_ui"):
        bits.append("代码展示类画面")
    ts = facts.get("sample_timestamps") or []
    ts_txt = ""
    if ts:
        ts_txt = "，示例时刻约 " + "、".join(f"{float(t):g}min" for t in ts[:4])
    joined = "、".join(bits) if bits else "开发相关屏幕内容"
    return (
        "\n### 硬约束（必须遵守）\n"
        f"- 视觉证据表明共享屏幕中出现过{joined}{ts_txt}。\n"
        "- **禁止**使用「全程未展示 IDE」「完全未展示开发者工具」「未展示任何 IDE 界面」等绝对否定表述。\n"
        "- 若技能深度不足，应写：「虽出现代码/终端类界面，但未演示调试、配置修改、异常处理等工程操作」或等价可核验表述。\n"
        "- 证据审计不得将 IDE 界面记为「完全无/E0 级缺失」；可记为「有界面、缺工程操作演示」。\n"
    )


def sanitize_scoring_text(text: str, facts: dict | None) -> str:
    """对单段评分文案做冲突消歧 + 去掉内部泄漏措辞。"""
    if not text or not isinstance(text, str):
        return text if isinstance(text, str) else ("" if text is None else str(text))
    out = text
    facts = facts or {}
    if facts.get("has_dev_tool_ui") and _ABSENT_IDE_CLAIM.search(out):
        # 整句级替换常见模板
        replacements = [
            (
                re.compile(
                    r"全程未展示(?:任何)?(?:IDE|ide|开发者工具|调试工具|代码编辑器?)[^。；;]*[。；;]?",
                    re.I,
                ),
                "虽出现代码/终端类界面，但未充分演示调试、配置修改或异常处理等工程操作，技能深度仍不足。",
            ),
            (
                re.compile(
                    r"完全未展示(?:任何)?(?:IDE|ide|开发者工具|调试工具)[^。；;]*[。；;]?",
                    re.I,
                ),
                "虽出现代码/终端类界面，但工程操作（调试/配置/异常处理）演示不足。",
            ),
            (
                re.compile(
                    r"未展示任何IDE界面[^。；;]*[。；;]?",
                    re.I,
                ),
                "代码界面有出现，但缺少面向评委的工程操作路径与调试过程展示。",
            ),
            (
                re.compile(
                    r"缺少IDE界面截图[^。；;]*[。；;]?",
                    re.I,
                ),
                "代码/终端类界面已有展示，仍缺少可核验的工程操作与配置/调试过程说明。",
            ),
            (
                re.compile(
                    r"未展示(?:任何)?(?:IDE|开发者工具|调试工具|配置文件、命令行)[^。；;]*[。；;]?",
                    re.I,
                ),
                "虽有代码或终端类界面，但未系统演示配置、命令行操作与调试闭环。",
            ),
        ]
        for pat, repl in replacements:
            out = pat.sub(repl, out)
        # 若仍残留绝对否定，追加一句纠正（不提抽帧）
        if _ABSENT_IDE_CLAIM.search(out):
            out = out.rstrip("。；; ") + "。补充：共享屏幕中已出现代码或终端类界面，扣分点应落在工程操作深度而非「界面完全未出现」。"

    for leak in _LEAK_PATTERNS:
        out = leak.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


_TEXT_KEYS = {
    "reason", "improvement", "suggestion", "summary", "diagnosis", "comment",
    "issue", "problem", "method", "title", "actual", "gap", "fix", "claim",
    "source", "impact", "description", "gapDescription", "requiredEvidence",
    "jury_summary", "next_round_focus", "defensible_strengths", "critical_deductions",
    "highlights", "critical_issues", "key_issues", "text", "content",
}


def _sanitize_value(value: Any, facts: dict) -> Any:
    if isinstance(value, str):
        return sanitize_scoring_text(value, facts)
    if isinstance(value, list):
        return [_sanitize_value(v, facts) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in _TEXT_KEYS or isinstance(v, (dict, list, str)):
                out[k] = _sanitize_value(v, facts)
            else:
                out[k] = v
        return out
    return value


def sanitize_ai_score_payload(ai_score: dict | None, facts: dict | None) -> dict:
    """消毒 ai_score 全文案相关字段。"""
    if not isinstance(ai_score, dict):
        return {}
    facts = facts or {}
    has_leak = any(
        ("抽帧" in s or "画面识别" in s or "代码编辑器约" in s)
        for s in _walk_strings(ai_score)
    )
    if not facts.get("has_dev_tool_ui") and not has_leak:
        return ai_score
    return _sanitize_value(copy.deepcopy(ai_score), facts)


def _walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for i in obj:
            yield from _walk_strings(i)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)


def sanitize_result_for_report(result: dict | None) -> dict:
    """报告生成前：深拷贝 result 并消毒 ai_score（历史数据自愈）。"""
    if not isinstance(result, dict):
        return {}
    out = copy.deepcopy(result)
    fusion = out.get("fusion") if isinstance(out.get("fusion"), dict) else None
    video = out.get("video_analysis") if isinstance(out.get("video_analysis"), dict) else None
    facts = build_visual_dev_tool_facts(out, fusion_context=fusion, video_analysis=video)
    ai = out.get("ai_score")
    if isinstance(ai, dict):
        out["ai_score"] = sanitize_ai_score_payload(ai, facts)
    return out


def build_prompt_visual_block(
    fusion_context: dict | None,
    video_analysis: dict | None = None,
) -> str:
    """供 score_roadshow 使用的视觉证据 + 硬约束文本。"""
    facts = build_visual_dev_tool_facts(
        fusion_context=fusion_context or {},
        video_analysis=video_analysis,
    )
    lines: list[str] = []
    summary = _as_dict((fusion_context or {}).get("screen_content_summary"))
    dist = _as_dict(summary.get("screen_type_distribution") or facts.get("screen_type_distribution"))
    content_counts = _as_dict(summary.get("content_type_counts") or facts.get("content_type_counts"))

    if dist or content_counts or facts.get("has_dev_tool_ui"):
        lines.append("\n## 视觉证据（共享屏幕识别摘要，请作为评分依据）")
    if dist:
        lines.append("\n### 屏幕类型分布（摘要）")
        for st, n in sorted(dist.items(), key=lambda x: -int(x[1] or 0))[:8]:
            lines.append(f"- {st}: 多次出现" if int(n or 0) > 0 else f"- {st}")
    if content_counts:
        lines.append("\n### 内容类型分布（摘要）")
        for ct, n in sorted(content_counts.items(), key=lambda x: -int(x[1] or 0))[:8]:
            lines.append(f"- {ct}: 有出现")

    codes = summary.get("code_detections") if isinstance(summary.get("code_detections"), list) else []
    if codes:
        lines.append("\n### 代码相关画面时刻")
        for c in codes[:12]:
            if not isinstance(c, dict):
                continue
            ts = c.get("timestamp_min", "")
            desc = str(c.get("desc") or "")[:80]
            lines.append(f"- 约 {ts}min: {desc}" if desc else f"- 约 {ts}min: 代码相关画面")

    # 既有细类
    for title, key in (
        ("标准规范证据", "standard_detections"),
        ("数据图表证据", "chart_detections"),
        ("成本分析证据", "cost_detections"),
        ("安全方案证据", "security_detections"),
        ("团队协作画面", "collaboration_detections"),
    ):
        items = summary.get(key) if isinstance(summary.get(key), list) else []
        if not items:
            continue
        lines.append(f"\n### {title}")
        for it in items[:8]:
            if not isinstance(it, dict):
                continue
            ts = it.get("timestamp_min", "")
            text = it.get("text") or it.get("desc") or it.get("title") or ""
            lines.append(f"- 约 {ts}min: {str(text)[:80]}")

    constraints = format_visual_constraints_for_prompt(facts)
    if constraints:
        lines.append(constraints)

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)
