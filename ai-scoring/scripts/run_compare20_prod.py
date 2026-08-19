#!/usr/bin/env python3
"""线上 20 题 Research Agent 对标复测（证据层）。

用法（容器内）:
  PYTHONPATH=/app python /tmp/run_compare20_prod.py /tmp/tmp_compare20_cases.json /tmp/compare20_out.json
"""
from __future__ import annotations

import json
import re
import sys
import time
import traceback
from typing import Any

# --- scoring helpers ---------------------------------------------------------

_HONEST = re.compile(r"未找到|未检索到|未命中|本轮判定：未找到|查无")
_BAIDU_LINK = re.compile(r"baidu\.com/link", re.I)
_GOV = re.compile(r"\.gov\.cn|\.edu\.cn|moe\.gov", re.I)


def _tools(steps: list[dict[str, Any]]) -> list[str]:
    return [str(s.get("tool") or "") for s in steps if isinstance(s, dict)]


def _blob(cites: list[dict[str, Any]], block: str) -> str:
    parts = [block or ""]
    for c in cites or []:
        if not isinstance(c, dict):
            continue
        parts.append(str(c.get("title") or ""))
        parts.append(str(c.get("url") or ""))
        parts.append(str(c.get("snippet") or "")[:200])
        parts.append(str(c.get("pageText") or "")[:300])
    return "\n".join(parts)


def score_case(case: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    """多维 0–10 打分（证据层；与历史对标口径一致的可自动化部分）。

    维度：
    1 path     路径/意图（URL 直开、batch、多跳工具）
    2 recall   检索相关度（主题实体是否进证据）
    3 authority 权威域
    4 multi_hop 多跳（search→open→pdf / 再搜）
    5 honesty  诚实拒凑（应空则空，应有则不空）
    6 evidence 证据可用（fetched/正文/附件）
    7 cite     引用卫生（无 baidu link）
    8 finish   finish 与证据一致性
    """
    cid = case["id"]
    dim = case.get("dim") or ""
    q = case.get("q") or ""
    finish = str(row.get("finish") or "")
    block = str(row.get("block") or "")
    cites = row.get("cites") if isinstance(row.get("cites"), list) else []
    steps = row.get("steps") if isinstance(row.get("steps"), list) else []
    tools = _tools(steps)
    blob = _blob(cites, block)
    empty_block = bool(_HONEST.search(block)) or "未命中" in block
    has_gov = bool(_GOV.search(blob))
    has_baidu = bool(_BAIDU_LINK.search(blob))
    n_ev = len(cites)
    fetched = sum(1 for c in cites if isinstance(c, dict) and c.get("fetched"))
    has_pdf = any(
        ".pdf" in str((c or {}).get("url") or "").lower()
        or (isinstance((c or {}).get("attachments"), list) and (c or {}).get("attachments"))
        for c in cites
        if isinstance(c, dict)
    )
    has_open = "open_url" in tools
    has_batch = "web_search_batch" in tools
    has_search = has_batch or "web_search" in tools
    has_pdf_tool = "fetch_pdf" in tools
    multi = sum(1 for t in tools if t in ("web_search", "web_search_batch", "open_url", "fetch_pdf"))

    # --- expected class ---
    # expect_empty: 虚构/应拒编造完整名单
    expect_empty = cid in ("C06", "C19")
    # expect_useful: 应尽量 enough 且有实质证据
    expect_useful = cid not in ("C06", "C19")
    # honesty-heavy: 查不到也要 empty 诚实
    honesty_ok_empty = cid in ("C06", "C10", "C17", "C18", "C19", "C02", "C15")

    # 1 path
    path = 5.0
    if "http" in q and re.search(r"https?://", q):
        if tools[:1] == ["open_url"] or (has_open and not has_search):
            path = 9.5
        elif has_open:
            path = 7.0
        else:
            path = 2.0
    else:
        if has_batch:
            path = 8.0
        elif has_search:
            path = 6.5
        else:
            path = 3.0
        if multi >= 3:
            path = min(10.0, path + 1.5)
        if "tool_name" in tools or any(t and t not in ("web_search", "web_search_batch", "open_url", "fetch_pdf", "finish", "…") for t in tools):
            path = max(0.0, path - 2.0)

    # 2 recall — 主题碎片命中证据
    tokens = re.findall(r"[\u4e00-\u9fff]{2,6}|[A-Za-z]{3,}", q)
    stop = {"什么", "哪些", "如何", "请基", "官方", "来源", "如实", "说明", "告诉", "这个", "网页", "内容", "最近", "一年", "有没", "同时", "一下", "分别", "是否", "不是", "同一", "完整", "必须", "逐队", "不准", "概括", "当前", "国家", "层面", "推进"}
    tokens = [t for t in tokens if t not in stop and t not in ("https", "http", "www", "com", "shtml")][:12]
    hit_n = sum(1 for t in tokens if t in blob)
    if expect_empty:
        recall = 8.0 if (empty_block or finish == "empty") else 3.0
    elif empty_block and n_ev == 0:
        recall = 2.5
    else:
        ratio = hit_n / max(1, min(6, len(tokens)))
        recall = max(1.0, min(10.0, 2.0 + ratio * 8.0))
        if dim in ("地方名单", "省级通知", "附件PDF") and ("技能" in blob or "大赛" in blob) and ("河南" in blob or "河南" not in q):
            if "河南" in q and "河南" in blob:
                recall = max(recall, 7.5)
        if dim == "部委实体" and ("生态环境" in blob or "mee.gov" in blob.lower()):
            recall = max(recall, 8.5)
        if dim == "教育强国" and ("教育强国" in blob or "2035" in blob):
            recall = max(recall, 8.5)
        if dim == "国策文本" and ("人工智能" in blob or "政府工作报告" in blob):
            recall = max(recall, 8.0)

    # 3 authority
    if expect_empty and (empty_block or finish == "empty"):
        authority = 9.0  # 不滥引权威壳
    elif has_gov and n_ev > 0 and not empty_block:
        authority = 9.0 if fetched or has_pdf else 7.5
    elif has_gov and empty_block:
        authority = 4.0  # 有弱 gov 但判定未采用
    elif n_ev > 0:
        authority = 5.0
    else:
        authority = 2.0

    # 4 multi_hop
    multi_hop = 4.0
    if has_batch and has_open:
        multi_hop = 7.5
    if has_batch and has_open and has_pdf_tool:
        multi_hop = 9.0
    if tools.count("web_search_batch") >= 2 or (has_search and tools.count("open_url") >= 2):
        multi_hop = max(multi_hop, 8.5)
    if multi <= 1 and not ( "http" in q and has_open):
        multi_hop = 3.0
    if finish == "empty" and multi >= 3:
        multi_hop = max(multi_hop, 7.0)  # 多跳后仍 empty 算试过

    # 5 honesty
    honesty = 5.0
    if expect_empty:
        if finish == "empty" or empty_block:
            honesty = 9.5
        elif n_ev > 0 and not empty_block:
            # 凑数风险
            honesty = 2.0
        else:
            honesty = 6.0
    else:
        if finish == "enough" and n_ev > 0 and not empty_block:
            honesty = 8.5
        elif finish == "empty" and empty_block:
            honesty = 7.0 if honesty_ok_empty else 4.5  # 可答却 empty 扣分
        elif finish == "enough" and empty_block:
            honesty = 3.0  # 判 enough 但写作空
        elif finish == "enough" and n_ev == 0:
            honesty = 2.0
        else:
            honesty = 5.0
        # 门户壳冒充
        if any(k in blob for k in ("人民政府门户", "考试院", "首页导航")) and finish == "enough" and "名单" in q:
            honesty = min(honesty, 3.5)

    # 6 evidence
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
    if dim in ("附件PDF", "地方名单", "省级通知") and has_pdf:
        evidence = max(evidence, 9.0)

    # 7 cite hygiene
    if has_baidu:
        cite = 3.0
    elif n_ev == 0 and (empty_block or finish == "empty"):
        cite = 8.5
    elif n_ev > 0 and all(str(c.get("url") or "").startswith("http") for c in cites if isinstance(c, dict)):
        cite = 9.0
    else:
        cite = 6.0

    # 8 finish consistency
    if expect_empty:
        finish_s = 9.5 if finish == "empty" else (4.0 if finish == "enough" else 6.0)
    else:
        if finish == "enough" and n_ev > 0 and not empty_block:
            finish_s = 9.0
        elif finish == "empty" and empty_block and n_ev == 0:
            finish_s = 6.5 if honesty_ok_empty else 4.0
        elif finish in ("max_steps", "done"):
            finish_s = 5.0
        else:
            finish_s = 5.5

    dims = {
        "path": round(path, 1),
        "recall": round(recall, 1),
        "authority": round(authority, 1),
        "multi_hop": round(multi_hop, 1),
        "honesty": round(honesty, 1),
        "evidence": round(evidence, 1),
        "cite": round(cite, 1),
        "finish": round(finish_s, 1),
    }
    avg = round(sum(dims.values()) / len(dims), 2)
    return {
        "dims": dims,
        "avg": avg,
        "flags": {
            "empty_block": empty_block,
            "has_gov": has_gov,
            "has_baidu_link": has_baidu,
            "fetched": fetched,
            "has_pdf": has_pdf,
            "n_ev": n_ev,
            "tools": tools,
        },
    }


def run_one(q: str) -> dict[str, Any]:
    from app.services.assistant.research_agent import apply_research_agent_to_payload

    payload = {
        "mode": "deep_search",
        "useResearchAgent": True,
        "useLlmPlanner": True,
        "researchAgentPrimary": True,
        "messages": [{"role": "user", "content": q}],
        "options": {
            "useResearchAgent": True,
            "useLlmPlanner": True,
            "maxSteps": 8,
            "maxOpen": 3,
            "maxPdf": 2,
            "timeoutSec": 90,
        },
    }
    t0 = time.time()
    out = apply_research_agent_to_payload(payload, max_steps=8, max_open=3)
    sec = round(time.time() - t0, 1)
    steps_raw = out.get("researchAgentSteps") or []
    steps = []
    for s in steps_raw:
        if not isinstance(s, dict):
            continue
        steps.append(
            {
                "tool": s.get("tool") or s.get("stepKey"),
                "sum": str(s.get("summary") or s.get("outputSummary") or "")[:160],
                "args": s.get("args") or s.get("arguments") or {},
            }
        )
    cites = out.get("researchCitations") or []
    clean_cites = []
    for c in cites[:12]:
        if not isinstance(c, dict):
            continue
        clean_cites.append(
            {
                "title": str(c.get("title") or "")[:100],
                "url": str(c.get("url") or "")[:160],
                "fetched": bool(c.get("fetched")),
            }
        )
    block = str(out.get("researchBlock") or "")
    return {
        "ok": True,
        "finish": str(out.get("researchAgentFinishReason") or ""),
        "sec": sec,
        "ev": len(clean_cites),
        "steps": steps,
        "tools": [s.get("tool") for s in steps],
        "cites": clean_cites,
        "block": block[:2500],
        "block_head": block[:500],
    }


def main() -> int:
    cases_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/tmp_compare20_cases.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/compare20_out.json"
    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results: list[dict[str, Any]] = []
    print(f"START n={len(cases)}", flush=True)
    for i, case in enumerate(cases, 1):
        cid = case.get("id")
        q = case.get("q") or ""
        print(f"\n=== [{i}/{len(cases)}] {cid} {case.get('dim')} ===", flush=True)
        print("Q:", q[:100], flush=True)
        row: dict[str, Any] = {
            "id": cid,
            "dim": case.get("dim"),
            "q": q,
        }
        try:
            r = run_one(q)
            row.update(r)
        except Exception as e:
            row.update(
                {
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc()[-800:],
                    "finish": "error",
                    "sec": 0,
                    "ev": 0,
                    "steps": [],
                    "tools": [],
                    "cites": [],
                    "block": "",
                    "block_head": "",
                }
            )
            print("ERR", e, flush=True)
        sc = score_case(case, row)
        row["score"] = sc
        print(
            f"finish={row.get('finish')} ev={row.get('ev')} sec={row.get('sec')} "
            f"avg={sc['avg']} tools={row.get('tools')}",
            flush=True,
        )
        results.append(row)
        # 增量落盘，防中断全丢
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    avgs = [r["score"]["avg"] for r in results if r.get("score")]
    overall = round(sum(avgs) / len(avgs), 2) if avgs else 0.0
    dim_keys = ["path", "recall", "authority", "multi_hop", "honesty", "evidence", "cite", "finish"]
    dim_means = {}
    for k in dim_keys:
        vals = [r["score"]["dims"][k] for r in results if r.get("score")]
        dim_means[k] = round(sum(vals) / len(vals), 2) if vals else 0.0

    summary = {
        "n": len(results),
        "overall_avg": overall,
        "dim_means": dim_means,
        "per_case": [
            {
                "id": r["id"],
                "dim": r.get("dim"),
                "finish": r.get("finish"),
                "ev": r.get("ev"),
                "sec": r.get("sec"),
                "avg": r.get("score", {}).get("avg"),
                "tools": r.get("tools"),
            }
            for r in results
        ],
    }
    summary_path = out_path.replace(".json", "_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("\n=== SUMMARY ===", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    print("WROTE", out_path, summary_path, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
