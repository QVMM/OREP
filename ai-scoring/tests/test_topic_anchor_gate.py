"""双硬锚点：地理 + 主题同时命中；禁止「河南旅游局」冒充「河南技能大赛」。"""
from __future__ import annotations

from app.services.assistant.query_anchors import (
    extract_query_anchors,
    filter_hits_by_anchors,
    hit_passes_anchors,
)


Q = "河南省2025年职业院校技能大赛信息帮我搜索一下"


def test_extracts_geo_and_topic_phrases():
    a = extract_query_anchors(Q)
    assert any("河南" in r for r in a.required)
    # 主题短语应覆盖技能大赛类
    blob = " ".join(a.content_phrases + a.content_tokens)
    assert "技能" in blob or "大赛" in blob or any("技能大赛" in p for p in a.content_phrases)


def test_tourism_baike_portal_fail_topic_gate():
    a = extract_query_anchors(Q)
    bad = [
        {"title": "河南旅游景点大全-河南省旅游局官方网站", "snippet": "景点介绍", "url": "https://www.hnta.cn/"},
        {"title": "河南省（中国华中地区省级行政区）_百度百科", "snippet": "简称豫", "url": "https://baike.baidu.com/x"},
        {"title": "河南省人民政府门户网站", "snippet": "政务公开", "url": "https://www.henan.gov.cn/"},
        {"title": "河南频道_凤凰网", "snippet": "河南新闻", "url": "https://hn.ifeng.com/"},
        {"title": "河南省教育考试院", "snippet": "高考报名", "url": "https://www.haeea.cn/"},
    ]
    for h in bad:
        assert hit_passes_anchors(h, a, strict=True) is False, h["title"]


def test_real_competition_page_passes():
    a = extract_query_anchors(Q)
    good = {
        "title": "河南省教育厅关于举办2025年职业院校技能大赛的通知",
        "snippet": "职业院校技能大赛赛项与报名",
        "url": "http://jyt.henan.gov.cn/2025/skill.html",
    }
    assert hit_passes_anchors(good, a, strict=True) is True


def test_filter_all_portal_noise_empty():
    a = extract_query_anchors(Q)
    hits = [
        {"title": "河南省人民政府门户网站", "snippet": "首页", "url": "https://www.henan.gov.cn/"},
        {"title": "河南旅游", "snippet": "景点", "url": "https://travel.example.com/"},
    ]
    assert filter_hits_by_anchors(hits, a, strict=True) == []
