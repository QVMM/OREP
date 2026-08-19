#!/usr/bin/env python3
"""Score XiaoQi 20-case evidence-layer results with 8-dim auto score (v3 scorer)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# allow import from ai-scoring root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.assistant.query_anchors import (  # noqa: E402
    evidence_has_list_notice_with_pdf,
    evidence_has_list_substance,
    is_comparison_query,
    is_full_list_demand,
    looks_like_portal_shell,
)

_EMPTY_STRUCT = re.compile(
    r"(本轮判定：未找到直接相关|未命中与用户问题|本轮联网检索未命中|未能抓取用户给出的网页正文)"
)
_BAIDU = re.compile(r"baidu\.com/link", re.I)
_GOV = re.compile(r"\.gov\.cn|\.edu\.cn|moe\.gov|miit\.gov|mohrss\.gov|stats\.gov", re.I)


def is_empty_block(block: str) -> bool:
    b = block or ""
    return bool(_EMPTY_STRUCT.search(b))


def score_case(case: dict, row: dict) -> dict:
    cid = case["id"]
    dim = case.get("dim") or ""
    q = case.get("q") or ""
    finish = str(row.get("finish") or "")
    block = str(row.get("block") or row.get("block_head") or "")
    cites = row.get("cites") if isinstance(row.get("cites"), list) else []
    tools = list(row.get("tools") or [])
    blob_parts = [block]
    for c in cites:
        if isinstance(c, dict):
            blob_parts += [str(c.get("title") or ""), str(c.get("url") or "")]
    blob = "\n".join(blob_parts)
    empty_block = is_empty_block(block)
    has_gov = bool(_GOV.search(blob))
    has_baidu = bool(_BAIDU.search(blob))
    n_ev = len(cites)
    fetched = sum(1 for c in cites if isinstance(c, dict) and c.get("fetched"))
    has_pdf = any(
        ".pdf" in str((c or {}).get("url") or "").lower() for c in cites if isinstance(c, dict)
    ) or evidence_has_list_notice_with_pdf(cites)
    has_open = "open_url" in tools
    has_batch = "web_search_batch" in tools
    has_search = has_batch or "web_search" in tools
    has_pdf_tool = "fetch_pdf" in tools
    multi = sum(1 for t in tools if t in ("web_search", "web_search_batch", "open_url", "fetch_pdf"))
    expect_empty = cid in ("N06", "N19", "V06", "V19", "C06", "C19") or dim in (
        "诚实空答",
        "应拒编造",
    )
    honesty_ok_empty = dim in (
        "诚实空答",
        "应拒编造",
        "地方名单",
        "附件PDF",
        "他省名单",
        "易混淆噪声",
    )
    is_cmp = is_comparison_query(q)
    shell_n = sum(1 for c in cites if isinstance(c, dict) and looks_like_portal_shell(c))

    # path
    path = 5.0
    if re.search(r"https?://", q):
        path = 9.5 if (tools[:1] == ["open_url"] or (has_open and not has_search)) else (
            7.0 if has_open else 2.0
        )
    else:
        path = 8.0 if has_batch else (6.5 if has_search else 3.0)
        if multi >= 3:
            path = min(10.0, path + 1.5)
        if is_cmp and multi >= 4:
            path = min(10.0, path + 0.5)

    # recall
    tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", q)
    stop = {
        "什么", "哪些", "如何", "请基", "官方", "来源", "如实", "说明", "告诉", "这个",
        "网页", "内容", "最近", "一年", "有没", "同时", "一下", "分别", "是否", "不是",
        "同一", "完整", "必须", "逐队", "不准", "概括", "当前", "国家", "层面", "推进",
        "查询", "查找", "给出", "标明",
    }
    tokens = [t for t in tokens if t not in stop and t not in ("https", "http", "www", "com", "shtml", "htm")][:12]
    hit_n = sum(1 for t in tokens if t in blob)
    if expect_empty:
        recall = 8.0 if (empty_block or finish == "empty") else 3.0
    elif empty_block and n_ev == 0:
        recall = 2.5
    else:
        ratio = hit_n / max(1, min(6, len(tokens)))
        recall = max(1.0, min(10.0, 2.0 + ratio * 8.0))
        if is_cmp and sum(
            1
            for g in (
                "广东",
                "浙江",
                "山东",
                "河南",
                "江苏",
                "四川",
                "河北",
                "湖北",
                "湖南",
                "安徽",
            )
            if g in blob
        ) >= 2:
            recall = max(recall, 8.5)

    # authority
    if expect_empty and (empty_block or finish == "empty"):
        authority = 9.0
    elif has_gov and n_ev > 0 and not empty_block:
        authority = 9.0 if fetched or has_pdf else 7.5
    elif has_gov and empty_block:
        authority = 4.0
    elif n_ev > 0:
        authority = 5.0
    else:
        authority = 2.0
    if shell_n >= n_ev and n_ev > 0 and not empty_block:
        authority = min(authority, 5.0)

    # multi_hop
    multi_hop = 4.0
    if has_batch and has_open:
        multi_hop = 7.5
    if has_batch and has_open and has_pdf_tool:
        multi_hop = 9.0
    if tools.count("web_search_batch") >= 2 or tools.count("open_url") >= 2:
        multi_hop = max(multi_hop, 8.5)
    if is_cmp and multi >= 4:
        multi_hop = max(multi_hop, 9.0)
    if multi <= 1 and not (re.search(r"https?://", q) and has_open):
        multi_hop = 3.0
    if finish == "empty" and multi >= 3:
        multi_hop = max(multi_hop, 7.0)

    # honesty
    if expect_empty:
        honesty = 9.5 if (finish == "empty" or empty_block) else (
            2.0 if n_ev > 0 and not empty_block else 6.0
        )
    else:
        if finish == "enough" and n_ev > 0 and not empty_block:
            honesty = 8.5
            if evidence_has_list_notice_with_pdf(cites) or (
                "名单" in q and has_pdf
            ):
                honesty = 9.0
        elif finish == "empty" and empty_block:
            honesty = 7.0 if honesty_ok_empty else 4.5
        elif finish == "enough" and empty_block:
            honesty = 3.0
        elif finish == "enough" and n_ev == 0:
            honesty = 2.0
        else:
            honesty = 5.0
        if shell_n >= 2 and finish == "enough" and "名单" in q:
            honesty = min(honesty, 5.0)

    # evidence
    if expect_empty and (empty_block or finish == "empty"):
        evidence = 9.0
    elif fetched >= 1 and len(block) > 200:
        evidence = 9.0
    elif n_ev >= 3 and has_gov:
        evidence = 7.5
    elif n_ev >= 1:
        evidence = 6.0
    elif empty_block:
        evidence = 3.0
    else:
        evidence = 2.0
    if has_pdf:
        evidence = max(evidence, 8.5)
    if evidence_has_list_substance(cites):
        evidence = max(evidence, 8.0)

    # cite
    if has_baidu:
        cite = 3.0
    elif n_ev == 0 and (empty_block or finish == "empty"):
        cite = 8.5
    elif n_ev > 0:
        cite = 9.0 if shell_n < max(1, n_ev // 2) else 6.5
    else:
        cite = 6.0

    # finish
    if expect_empty:
        finish_s = 9.5 if finish == "empty" else (4.0 if finish == "enough" else 6.0)
    else:
        if finish == "enough" and n_ev > 0 and not empty_block:
            finish_s = 9.0
        elif finish == "empty" and empty_block and n_ev == 0:
            finish_s = 6.5 if honesty_ok_empty else 4.0
        elif is_cmp and finish == "enough" and n_ev > 0:
            finish_s = 9.0
        else:
            finish_s = 5.5

    dims = {
        k: round(v, 1)
        for k, v in dict(
            path=path,
            recall=recall,
            authority=authority,
            multi_hop=multi_hop,
            honesty=honesty,
            evidence=evidence,
            cite=cite,
            finish=finish_s,
        ).items()
    }
    avg = round(sum(dims.values()) / len(dims), 2)
    return {
        "dims": dims,
        "avg": avg,
        "empty_block": empty_block,
        "has_gov": has_gov,
        "shell_n": shell_n,
        "has_pdf": has_pdf,
        "full_list_demand": is_full_list_demand(q),
    }


def main() -> int:
    raw_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else raw_path.with_name(
        raw_path.stem + "_scored.json"
    )
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    cases = {c["id"]: c for c in data} if isinstance(data, list) and data and "q" in data[0] else {}
    # if results only
    results = data
    scored = []
    for r in results:
        case = {"id": r["id"], "dim": r.get("dim"), "q": r.get("q")}
        if cases.get(r["id"]):
            case = cases[r["id"]]
        s = score_case(case, r)
        r2 = dict(r)
        r2["score"] = s
        scored.append(r2)
    avgs = [r["score"]["avg"] for r in scored]
    overall = round(sum(avgs) / len(avgs), 2) if avgs else 0.0
    dim_keys = ["path", "recall", "authority", "multi_hop", "honesty", "evidence", "cite", "finish"]
    dim_means = {
        k: round(sum(r["score"]["dims"][k] for r in scored) / len(scored), 2) for k in dim_keys
    }
    summary = {
        "n": len(scored),
        "overall_avg": overall,
        "dim_means": dim_means,
        "per_case": [
            {
                "id": r["id"],
                "dim": r.get("dim"),
                "finish": r.get("finish"),
                "ev": r.get("ev"),
                "sec": r.get("sec"),
                "avg": r["score"]["avg"],
                "dims": r["score"]["dims"],
                "tools": r.get("tools"),
            }
            for r in scored
        ],
    }
    out_path.write_text(json.dumps(scored, ensure_ascii=False, indent=2), encoding="utf-8")
    sum_path = out_path.with_name(out_path.stem + "_summary.json")
    sum_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("WROTE", out_path, sum_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
