"""联网研究可观测指标：空结果率 / 附件命中 / 权威域 等（日志侧周报原料）。"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.assistant.domain_rank import soft_domain_boost
from app.services.assistant.query_anchors import extract_query_anchors

logger = logging.getLogger("orep.research_metrics")


def summarize_research_metrics(
    *,
    query: str,
    evidence: list[dict[str, Any]] | None,
    finish_reason: str = "",
    steps: list[Any] | None = None,
) -> dict[str, Any]:
    ev = [e for e in (evidence or []) if isinstance(e, dict)]
    anchors = extract_query_anchors(query or "")
    att_n = 0
    gov_edu = False
    for e in ev:
        url = str(e.get("url") or "")
        title = str(e.get("title") or "")
        if title.startswith("附件") or re.search(r"\.(pdf|xlsx?|docx?)(\?|$)", url, re.I):
            att_n += 1
        atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
        att_n += len(atts)
        if soft_domain_boost(url) >= 10:
            gov_edu = True
        if any(m in url.lower() for m in (".gov.cn", ".edu.cn")):
            gov_edu = True

    tools = []
    for s in steps or []:
        if isinstance(s, dict) and s.get("tool"):
            tools.append(str(s.get("tool")))
        elif hasattr(s, "tool"):
            tools.append(str(getattr(s, "tool")))

    metrics = {
        "queryLen": len(query or ""),
        "requiredCount": len(anchors.required),
        "hasRequired": bool(anchors.required),
        "evidenceCount": len(ev),
        "empty": len(ev) == 0,
        "attachmentCount": att_n,
        "hasAttachment": att_n > 0,
        "hasGovOrEdu": gov_edu,
        "finishReason": finish_reason or "",
        "stepCount": len(steps or []),
        "tools": tools[:12],
    }
    return metrics


def log_research_metrics(metrics: dict[str, Any]) -> None:
    """结构化一行日志，便于采集空结果率/附件命中率。"""
    try:
        logger.info("research_metrics %s", json.dumps(metrics, ensure_ascii=False))
    except Exception:
        logger.info("research_metrics %s", metrics)
