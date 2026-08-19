"""P3 TDD: soft 域名偏好、指标统计、师生同一 agent 入口。"""
from __future__ import annotations

from app.services.assistant.domain_rank import soft_domain_boost, sort_hits_by_soft_rank
from app.services.assistant.research_agent import apply_research_agent_to_payload
from app.services.assistant.research_metrics import summarize_research_metrics


def test_soft_domain_boost_prefers_gov_edu_over_media():
    gov = soft_domain_boost("https://www.moe.gov.cn/a.html")
    edu = soft_domain_boost("https://www.xxx.edu.cn/b.html")
    media = soft_domain_boost("https://www.sohu.com/c.html")
    baike = soft_domain_boost("https://baike.baidu.com/d")
    assert gov > media
    assert edu > media
    assert gov >= edu or edu >= 0
    assert baike < gov


def test_sort_hits_puts_gov_first_when_similar():
    hits = [
        {"title": "名单转载", "url": "https://www.sohu.com/x", "snippet": "职业院校技能大赛获奖"},
        {"title": "教育部名单", "url": "https://www.moe.gov.cn/y", "snippet": "职业院校技能大赛获奖"},
    ]
    ordered = sort_hits_by_soft_rank(hits)
    assert "moe.gov.cn" in (ordered[0].get("url") or "")


def test_metrics_empty_and_attachment():
    m1 = summarize_research_metrics(
        query="河南省技能大赛",
        evidence=[],
        finish_reason="empty",
        steps=[{"tool": "web_search"}],
    )
    assert m1["empty"] is True
    assert m1["evidenceCount"] == 0
    assert m1["hasRequired"] is True  # 河南 extracted

    m2 = summarize_research_metrics(
        query="2025职业院校技能大赛获奖名单",
        evidence=[
            {
                "title": "附件 · 名单",
                "url": "https://www.moe.gov.cn/a.pdf",
                "snippet": "pdf",
            }
        ],
        finish_reason="enough",
        steps=[{"tool": "web_search"}, {"tool": "fetch_pdf"}],
    )
    assert m2["empty"] is False
    assert m2["attachmentCount"] >= 1
    assert m2["hasGovOrEdu"] is True


def test_teacher_and_student_same_agent_entry():
    """师生 payload 都可走 deep_search research agent（不分流两套逻辑）。"""
    base_cites = [
        {
            "title": "教育部职业院校技能大赛通知",
            "url": "https://www.moe.gov.cn/n.html",
            "snippet": "获奖名单",
            "sourceType": "web",
        }
    ]

    def open_fn(url: str):
        return {
            "ok": True,
            "url": url,
            "title": "教育部通知职业院校技能大赛",
            "text": "职业院校技能大赛获奖名单公布",
            "attachments": [{"title": "名单", "url": "https://www.moe.gov.cn/a.pdf"}],
        }

    student = {
        "mode": "deep_search",
        "role": "student",
        "useLlmPlanner": False,
        "messages": [{"role": "user", "content": "搜索2025职业院校技能大赛获奖名单"}],
        "researchCitations": list(base_cites),
    }
    teacher = {
        "mode": "deep_search",
        "role": "teacher",
        "useLlmPlanner": False,
        "options": {"audience": "teacher"},
        "messages": [{"role": "user", "content": "搜索2025职业院校技能大赛获奖名单"}],
        "researchCitations": list(base_cites),
    }
    def search_fn(q: str):
        return list(base_cites)

    s_out = apply_research_agent_to_payload(student, open_fn=open_fn, search_fn=search_fn)
    t_out = apply_research_agent_to_payload(teacher, open_fn=open_fn, search_fn=search_fn)
    assert "researchBlock" in s_out and "researchBlock" in t_out
    assert s_out.get("researchAgentFinishReason")
    assert t_out.get("researchAgentFinishReason")
    # 同一入口：都产生 agent steps
    assert s_out.get("researchAgentSteps")
    assert t_out.get("researchAgentSteps")


def test_no_province_whitelist_in_domain_rank():
    import inspect
    from app.services.assistant import domain_rank as mod

    src = inspect.getsource(mod)
    for banned in ("河南省", "山东省", "jyt.henan"):
        assert banned not in src
