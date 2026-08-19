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
        # 顺句：避免「但虽出现」叠词
        out = out.replace("但虽出现", "虽出现").replace("，，", "，").replace("。。", "。")

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


def _score_num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _prefer_score_str(n: float) -> str:
    """展示用分数：整数去小数，否则保留一位。"""
    if abs(n - round(n)) < 1e-6:
        return str(int(round(n)))
    return f"{n:.1f}"


def _num_str_variants(n: float) -> list[str]:
    """用于文案替换的旧分数字面量集合（去重保序）。"""
    seen: list[str] = []
    for s in (
        _prefer_score_str(n),
        f"{n:.1f}",
        f"{n:.2f}",
        str(n),
        str(int(round(n))) if abs(n - round(n)) < 1e-6 else None,
    ):
        if s and s not in seen:
            seen.append(s)
    return seen


def _sync_rescore_numbers_in_text(
    text: str,
    *,
    old_overall: float,
    new_overall: float,
    old_skill: float,
    new_skill: float,
    skill_max: float,
) -> str:
    """把叙述中的旧总分/技能分改成校正后的数，避免 PDF 卡片与段落打架。"""
    if not text or not isinstance(text, str):
        return text
    if abs(old_overall - new_overall) < 1e-6 and abs(old_skill - new_skill) < 1e-6:
        return text
    out = text
    new_o = _prefer_score_str(new_overall)
    new_s = _prefer_score_str(new_skill)
    max_s = _prefer_score_str(skill_max)

    # 技能 X/60（先做更具体的）
    for old_s in _num_str_variants(old_skill):
        out = re.sub(
            rf"{re.escape(old_s)}\s*/\s*{re.escape(max_s)}",
            f"{new_s}/{max_s}",
            out,
        )
        out = re.sub(
            rf"((?:技能水平|技能熟练度|skill_level)[^0-9]{{0,24}}(?:仅得|得|为)?){re.escape(old_s)}(?![0-9.])",
            lambda m, ns=new_s: f"{m.group(1)}{ns}",
            out,
            flags=re.IGNORECASE,
        )

    # 总分 / 最终得分
    for old_o in _num_str_variants(old_overall):
        out = re.sub(
            rf"((?:本场|权威|AI\s*)?(?:总?分|基准总分|基准分)|最终得分|overall_score\s*[:=]?\s*)"
            rf"{re.escape(old_o)}(?![0-9.])",
            lambda m, no=new_o: f"{m.group(1)}{no}",
            out,
            flags=re.IGNORECASE,
        )
        out = re.sub(
            rf"(得分\s*){re.escape(old_o)}(?![0-9.])",
            lambda m, no=new_o: f"{m.group(1)}{no}",
            out,
        )
    return out


def _walk_sync_score_strings(
    value: Any,
    *,
    old_overall: float,
    new_overall: float,
    old_skill: float,
    new_skill: float,
    skill_max: float,
) -> Any:
    if isinstance(value, str):
        return _sync_rescore_numbers_in_text(
            value,
            old_overall=old_overall,
            new_overall=new_overall,
            old_skill=old_skill,
            new_skill=new_skill,
            skill_max=skill_max,
        )
    if isinstance(value, list):
        return [
            _walk_sync_score_strings(
                v,
                old_overall=old_overall,
                new_overall=new_overall,
                old_skill=old_skill,
                new_skill=new_skill,
                skill_max=skill_max,
            )
            for v in value
        ]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            # 跳过内部元数据与非叙述字段
            if k in ("_skill_visual_rescore", "items") and isinstance(v, list):
                # items 内 reason 仍要同步
                out[k] = _walk_sync_score_strings(
                    v,
                    old_overall=old_overall,
                    new_overall=new_overall,
                    old_skill=old_skill,
                    new_skill=new_skill,
                    skill_max=skill_max,
                )
            elif k == "_skill_visual_rescore":
                out[k] = v
            elif k in _TEXT_KEYS or isinstance(v, (dict, list, str)):
                out[k] = _walk_sync_score_strings(
                    v,
                    old_overall=old_overall,
                    new_overall=new_overall,
                    old_skill=old_skill,
                    new_skill=new_skill,
                    skill_max=skill_max,
                )
            else:
                out[k] = v
        return out
    return value


def _text_blob_for_skill(ai_score: dict) -> str:
    parts: list[str] = []
    for key in ("critical_issues", "highlights"):
        for item in ai_score.get(key) or []:
            parts.append(str(item))
    ov = ai_score.get("score_overview") if isinstance(ai_score.get("score_overview"), dict) else {}
    parts.append(str(ov.get("diagnosis") or ""))
    for item in ov.get("key_issues") or []:
        parts.append(str(item))
    fv = ai_score.get("final_verdict") if isinstance(ai_score.get("final_verdict"), dict) else {}
    for key in ("summary", "critical_deductions", "jury_summary"):
        val = fv.get(key)
        if isinstance(val, list):
            parts.extend(str(x) for x in val)
        elif val:
            parts.append(str(val))
    skill = (ai_score.get("dimensions") or {}).get("skill_level") or {}
    if isinstance(skill, dict):
        parts.append(str(skill.get("reason") or skill.get("summary") or ""))
        for it in skill.get("items") or []:
            if isinstance(it, dict):
                parts.append(str(it.get("reason") or ""))
                parts.append(str(it.get("improvement") or ""))
    return "\n".join(parts)


def apply_skill_visual_rescore(ai_score: dict, facts: dict | None) -> dict:
    """skill_level 局部重评：画面已有代码/终端界面时，纠正「当完全没工具」的过低分。

    规则（确定性，不调 LLM）：
    - 仅在 has_dev_tool_ui 时生效，只升不降
    - 加分 = 工具可见性信用（编辑器 > 终端 > 仅代码内容）
    - 上限：不超过 max_score 的 58%（仍保留「工程操作深度不足」空间）
    - 若存在分项 items，优先加在「技能熟练度」「操作规范性」
    - 重算 dimensions.skill_level.score 与 overall_score
    - 不把内部帧数写进文案
    - **幂等**：已有 `_skill_visual_rescore` 则不再叠加
    """
    if not isinstance(ai_score, dict):
        return ai_score if isinstance(ai_score, dict) else {}
    facts = facts or {}
    if not facts.get("has_dev_tool_ui"):
        return ai_score
    # 已校正过则不再加分（API 读路径 / PDF 生成可能多次调用）
    if isinstance(ai_score.get("_skill_visual_rescore"), dict):
        return ai_score

    dims = ai_score.get("dimensions")
    if not isinstance(dims, dict):
        return ai_score
    skill = dims.get("skill_level")
    if not isinstance(skill, dict):
        return ai_score

    max_score = _score_num(skill.get("max_score"), 60.0) or 60.0
    old_skill = _score_num(skill.get("score"), 0.0)
    if max_score <= 0:
        return ai_score

    # 可见性信用
    if facts.get("has_code_editor_ui"):
        credit = 7.0
    elif facts.get("has_terminal_ui"):
        credit = 5.0
    elif facts.get("has_code_content"):
        credit = 4.0
    else:
        credit = 0.0
    if credit <= 0:
        return ai_score

    ratio = old_skill / max_score
    blob = _text_blob_for_skill(ai_score)
    assumed_no_tools = bool(_ABSENT_IDE_CLAIM.search(blob)) or any(
        k in blob
        for k in (
            "全程未展示任何操作路径",
            "未展示任何IDE",
            "完全未展示",
            "技能展示无深度",
            "停留在用户操作层面",
        )
    )
    # 已较高且文案未按「无工具」扣 → 不抬
    if ratio >= 0.55 and not assumed_no_tools:
        return ai_score
    # 已接近可见性上限
    visibility_cap = round(max_score * 0.58, 2)  # 60 → 34.8
    if old_skill >= visibility_cap - 0.05:
        return ai_score

    target = min(visibility_cap, round(old_skill + credit, 2))
    if target <= old_skill:
        return ai_score

    delta = round(target - old_skill, 2)
    skill = dict(skill)
    items = skill.get("items")
    if isinstance(items, list) and items:
        # 按权重分配：熟练度 55% / 规范性 35% / 讲解 10%；溢出再扫一轮填有 room 的项
        note = (
            "共享屏幕中出现代码/终端类界面，工具可见性已计入；"
            "工程操作深度仍按演示过程评估。"
        )

        def _item_weight(name: str) -> float:
            if "熟练" in name:
                return 0.55
            if "规范" in name:
                return 0.35
            if "讲解" in name or "现场" in name:
                return 0.10
            return 0.0

        new_items: list = []
        rooms: list[float] = []
        weights: list[float] = []
        for it in items:
            if not isinstance(it, dict):
                new_items.append(it)
                rooms.append(0.0)
                weights.append(0.0)
                continue
            it2 = dict(it)
            new_items.append(it2)
            imax = _score_num(it2.get("max_score"), 0.0)
            isc = _score_num(it2.get("score"), 0.0)
            room = max(0.0, imax - isc) if imax > 0 else 0.0
            rooms.append(room)
            weights.append(_item_weight(str(it2.get("name") or "")) if room > 0 else 0.0)

        remain = delta
        wsum = sum(weights)
        if wsum > 0 and remain > 0.001:
            for i, it2 in enumerate(new_items):
                if remain <= 0.001 or not isinstance(it2, dict) or weights[i] <= 0:
                    continue
                planned = delta * (weights[i] / wsum)
                add = round(min(remain, rooms[i], planned), 2)
                if add <= 0:
                    continue
                isc = _score_num(it2.get("score"), 0.0)
                it2["score"] = round(isc + add, 2)
                rooms[i] = round(max(0.0, rooms[i] - add), 2)
                remain = round(remain - add, 2)
                reason = str(it2.get("reason") or "")
                if note not in reason:
                    it2["reason"] = (reason.rstrip("。") + "。" + note) if reason else note

        # 剩余均分到仍有 room 的项
        if remain > 0.001:
            for i, it2 in enumerate(new_items):
                if remain <= 0.001 or not isinstance(it2, dict) or rooms[i] <= 0:
                    continue
                add = round(min(remain, rooms[i]), 2)
                if add <= 0:
                    continue
                isc = _score_num(it2.get("score"), 0.0)
                it2["score"] = round(isc + add, 2)
                rooms[i] = round(max(0.0, rooms[i] - add), 2)
                remain = round(remain - add, 2)

        skill["items"] = new_items
        skill["score"] = round(
            sum(_score_num(it.get("score"), 0.0) for it in new_items if isinstance(it, dict)),
            2,
        )
        # 若 items 上限吃不下 target，以 items 和为准（不超过 visibility 目标）
        if skill["score"] > target:
            skill["score"] = target
    else:
        skill["score"] = target
        # 无细项时补一句 reason 级说明（若有字段）
        if not skill.get("reason") and not skill.get("summary"):
            skill["summary"] = (
                "共享屏幕中出现代码/终端类界面，已对技能水平做工具可见性校正；"
                "工程操作（调试/配置/异常）深度仍按现场演示评估。"
            )
    # 钳制
    skill["score"] = round(min(max_score, max(0.0, _score_num(skill.get("score"), target))), 2)
    skill["max_score"] = max_score
    new_skill = skill["score"]
    dims = dict(dims)
    dims["skill_level"] = skill
    ai_score = dict(ai_score)
    ai_score["dimensions"] = dims

    # 总分：按 skill 增量回写（避免维度缺失时 sum 失真）
    old_overall = _score_num(ai_score.get("overall_score"), 0.0)
    skill_delta = round(new_skill - old_skill, 2)
    new_overall = round(min(100.0, max(0.0, old_overall + skill_delta)), 2)
    ai_score["overall_score"] = new_overall

    # score_overview.total_score 等同数字段
    ov = ai_score.get("score_overview")
    if isinstance(ov, dict):
        ov = dict(ov)
        if "total_score" in ov:
            ov["total_score"] = new_overall
        ai_score["score_overview"] = ov
    if "raw_overall_score" in ai_score:
        try:
            ai_score["raw_overall_score"] = new_overall
        except Exception:
            pass

    # 文案中「-15分」等与校正后叙述不完全一致时，弱化绝对分值括号
    def _soften_point_tags(text: str) -> str:
        if not text:
            return text
        return re.sub(
            r"(技能展示无深度|技能熟练度失分|技能水平失分)（[+\-]?\d+(?:\.\d+)?分）",
            r"\1（主要失分项）",
            text,
        )

    for key in ("critical_issues",):
        val = ai_score.get(key)
        if isinstance(val, list):
            ai_score[key] = [
                _soften_point_tags(str(x)) if isinstance(x, str) else x for x in val
            ]
    fv = ai_score.get("final_verdict")
    if isinstance(fv, dict):
        fv = dict(fv)
        cd = fv.get("critical_deductions")
        if isinstance(cd, list):
            fv["critical_deductions"] = [
                _soften_point_tags(str(x)) if isinstance(x, str) else x for x in cd
            ]
        elif isinstance(cd, str):
            fv["critical_deductions"] = _soften_point_tags(cd)
        ai_score["final_verdict"] = fv

    # 同步叙述中的旧分数字面量（诊断/结论等）
    ai_score = _walk_sync_score_strings(
        ai_score,
        old_overall=old_overall,
        new_overall=new_overall,
        old_skill=old_skill,
        new_skill=new_skill,
        skill_max=max_score,
    )

    # 内部痕迹（默认不进 PDF；可供调试）
    ai_score["_skill_visual_rescore"] = {
        "before": old_skill,
        "after": new_skill,
        "delta": skill_delta,
        "overall_before": old_overall,
        "overall_after": new_overall,
        "visibility_cap": visibility_cap,
        "credit_rule": (
            "code_editor" if facts.get("has_code_editor_ui")
            else "terminal" if facts.get("has_terminal_ui")
            else "code_content"
        ),
    }
    return ai_score


def sanitize_ai_score_payload(ai_score: dict | None, facts: dict | None) -> dict:
    """消毒 ai_score 文案，并在需要时做 skill 局部重评。

    顺序：先按**原始文案**校正 skill 分（assumed_no_tools 依赖「全程未展示 IDE」等原文），
    再做文案消歧与泄密剥离。
    """
    if not isinstance(ai_score, dict):
        return {}
    facts = facts or {}
    has_leak = any(
        ("抽帧" in s or "画面识别" in s or "代码编辑器约" in s)
        for s in _walk_strings(ai_score)
    )
    if not facts.get("has_dev_tool_ui") and not has_leak:
        return ai_score
    working = copy.deepcopy(ai_score)
    if facts.get("has_dev_tool_ui"):
        working = apply_skill_visual_rescore(working, facts)
    return _sanitize_value(working, facts)


def _walk_strings(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, list):
        for i in obj:
            yield from _walk_strings(i)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)


def _sync_score_calibration(result: dict, ai_score: dict) -> None:
    """把 score_calibration / 规则快照里的官方分与 ai_score 对齐（Web 端会读 calibration）。"""
    if not isinstance(result, dict) or not isinstance(ai_score, dict):
        return
    overall = ai_score.get("overall_score")
    dims = ai_score.get("dimensions") if isinstance(ai_score.get("dimensions"), dict) else {}
    skill = dims.get("skill_level") if isinstance(dims.get("skill_level"), dict) else {}
    cal = result.get("score_calibration")
    if not isinstance(cal, dict):
        return
    cal = dict(cal)
    if overall is not None:
        cal["original_score"] = overall
        cal["official_rubric_score"] = overall
        cal["final_score"] = overall
    if skill.get("score") is not None:
        cal["skill_score"] = skill.get("score")
    if skill.get("max_score") is not None:
        cal["skill_max_score"] = skill.get("max_score")
    orub = cal.get("official_rubric")
    if isinstance(orub, dict):
        orub = dict(orub)
        if overall is not None:
            orub["total_score"] = overall
        od = orub.get("dimensions")
        if isinstance(od, dict) and dims:
            od2 = dict(od)
            for k, v in dims.items():
                if not isinstance(v, dict):
                    continue
                prev = dict(od2.get(k) or {}) if isinstance(od2.get(k), dict) else {}
                prev["score"] = v.get("score")
                if v.get("max_score") is not None:
                    prev["max_score"] = v.get("max_score")
                od2[k] = prev
            orub["dimensions"] = od2
        cal["official_rubric"] = orub
    result["score_calibration"] = cal


def sanitize_result_for_report(result: dict | None) -> dict:
    """报告生成前：深拷贝 result，消毒文案 + skill 局部重评。"""
    if not isinstance(result, dict):
        return {}
    out = copy.deepcopy(result)
    fusion = out.get("fusion") if isinstance(out.get("fusion"), dict) else None
    video = out.get("video_analysis") if isinstance(out.get("video_analysis"), dict) else None
    facts = build_visual_dev_tool_facts(out, fusion_context=fusion, video_analysis=video)
    ai = out.get("ai_score")
    if isinstance(ai, dict):
        out["ai_score"] = sanitize_ai_score_payload(ai, facts)
        _sync_score_calibration(out, out["ai_score"])
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
