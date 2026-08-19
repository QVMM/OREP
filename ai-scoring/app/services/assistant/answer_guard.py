"""联网回答后处理：禁止「见附件」无链、禁止无相关 evidence 时硬凑答案。"""
from __future__ import annotations

import re
from typing import Any

_SEE_ATTACH = re.compile(
    r"(?is)"
    r"(见附件\s*[1-9一二三四五六七八九十0-9—\-到至及和与,，、]*)"
    r"|(附件\s*[1-9一二三四五六七八九十0-9—\-]+\s*(?:内容|如下|详见)?)"
    r"|(具体(?:获奖)?名单(?:为|在)附件[^\n。]{0,20})"
    r"|(请(?:在|于)?(?:上述)?官网下载查看)"
)

_MD_LINK = re.compile(r"\[[^\]]+\]\(https?://[^)]+\)")
_BARE_URL = re.compile(r"https?://[^\s\)\]>]+")

# researchBlock 标记：本轮未找到直接相关结果
_EMPTY_RESEARCH_MARK = re.compile(
    r"(?is)"
    r"(本轮判定：未找到直接相关|未命中与用户问题|"
    r"未检索到(?:直接)?相关公开|本轮联网检索未命中|"
    r"未能抓取用户给出的网页正文)"
)

# 答案侧已含诚实表述
_HONEST_EMPTY_ANSWER = re.compile(
    r"(?is)(未检索到|未找到|未命中|本轮未|查无|没有找到|未能(?:抓取|获取)|暂未找到)"
)

_FORCE_NOT_FOUND = (
    "本轮联网检索**未找到**与问题直接相关的公开结果。"
    "系统已执行检索，但命中页无法支撑原问题核心（可能为门户首页或跑题页）。"
    "建议换更具体的关键词，或到主管部门官网核验。"
)


def _has_download_urls(text: str) -> bool:
    if _MD_LINK.search(text or ""):
        return True
    if _BARE_URL.search(text or ""):
        return True
    return False


def research_block_is_empty(research_block: str) -> bool:
    """researchBlock 是否判定为未找到直接相关结果。"""
    b = research_block or ""
    if not b.strip():
        return False
    if _EMPTY_RESEARCH_MARK.search(b):
        return True
    if "写作硬约束" in b and "未找到" in b:
        return True
    return False


def force_not_found_if_no_related_evidence(
    answer: str,
    *,
    research_block: str = "",
    finish_reason: str = "",
) -> str:
    """无相关 evidence 时强制答案含「未找到」；禁止用跑题页硬凑。

    不做业务主题 if-else：只看 researchBlock / finish_reason 信号。
    """
    text = (answer or "").strip()
    fr = (finish_reason or "").strip().lower()
    empty = fr == "empty" or research_block_is_empty(research_block)
    if not empty:
        return text

    if text and _HONEST_EMPTY_ANSWER.search(text):
        # 已诚实：去掉可能的「见附件」凑数
        return text

    if not text or len(text) < 8:
        return _FORCE_NOT_FOUND

    # 模型仍在用无关页写长文：前置强制声明
    return (
        _FORCE_NOT_FOUND
        + "\n\n---\n"
        + "（以下原文可能混入了不相关命中，请以「未找到」结论为准，勿采信无出处编造。）\n\n"
        + text
    )


def guard_research_answer(
    answer: str,
    *,
    research_block: str = "",
    has_attachment_urls: bool | None = None,
    finish_reason: str = "",
) -> str:
    """无真实下载链时清理「见附件」；无相关 evidence 时强制未找到。"""
    text = (answer or "").strip()
    if not text and not research_block_is_empty(research_block) and (finish_reason or "") != "empty":
        return text

    block = research_block or ""
    if has_attachment_urls is None:
        has_attachment_urls = bool(
            "可下载附件" in block
            or re.search(r"\[.+?\]\(https?://", block)
            or re.search(r"https?://\S+\.(?:pdf|xlsx?|docx?)", block, re.I)
        )

    # 1) 无相关 → 强制未找到（优先于附件话术）
    text = force_not_found_if_no_related_evidence(
        text or "",
        research_block=block,
        finish_reason=finish_reason,
    )

    # 2) 正文已有可点链接：仅弱清理「见附件1—7」裸写
    if has_attachment_urls or _has_download_urls(text):
        cleaned = re.sub(
            r"见附件\s*[1-9一二三四五六七八九十0-9—\-到至及和与,，、]+",
            "见下方链接",
            text,
        )
        return cleaned.strip()

    if not _SEE_ATTACH.search(text) and "附件" not in text:
        return text

    cleaned = _SEE_ATTACH.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    note = (
        "\n\n---\n"
        "**说明：** 本轮未提供可点击的下载链接，"
        "本对话也不会上传文件。"
        "请以教育主管部门或大赛官网公示为准；"
        "勿将「附件」字样理解为聊天内已挂载文件。"
    )
    if len(cleaned) < 12:
        return (
            "本轮检索未拿到可直接下载的名单附件链接。"
            "请到对应行政区教育主管部门官网或大赛官网查阅公示。"
            + note
        )
    return cleaned + note


def research_has_attachment_urls(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    block = str(payload.get("researchBlock") or "")
    if "可下载附件" in block or re.search(r"\.(pdf|xlsx?|docx?)\)", block, re.I):
        return True
    cites = payload.get("researchCitations")
    if isinstance(cites, list):
        for c in cites:
            if not isinstance(c, dict):
                continue
            title = str(c.get("title") or "")
            url = str(c.get("url") or "")
            if title.startswith("附件") or re.search(r"\.(pdf|xlsx?|docx?)(\?|$)", url, re.I):
                return True
            atts = c.get("attachments")
            if isinstance(atts, list) and atts:
                return True
    return False
