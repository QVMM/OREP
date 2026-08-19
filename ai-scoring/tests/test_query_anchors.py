"""TDD: 通用必选实体锚点（地理/专名）——禁止用错地区/全国结果糊弄用户。

不写死任何省份名表：只靠形态规则从用户问题中抽取。
"""
from __future__ import annotations

from app.services.assistant.query_anchors import (
    extract_query_anchors,
    filter_hits_by_anchors,
    hit_passes_anchors,
)


def test_extract_required_geo_from_henan_query():
    a = extract_query_anchors("河南省2025年职业院校技能大赛的信息帮我搜一搜")
    assert "2025" in a.years
    # 必须抽出行政区划形态实体
    assert any("河南" in r for r in a.required)
    assert a.required  # 非空


def test_national_and_other_province_fail_henan_required():
    a = extract_query_anchors("河南省2025年职业院校技能大赛获奖名单")
    national = {
        "title": "全国职业院校技能大赛官网",
        "snippet": "大赛点亮人生",
        "url": "http://www.nvsc.com.cn/",
    }
    shandong = {
        "title": "第十八届山东省职业院校技能大赛获奖名单",
        "snippet": "山东省教育厅公布",
        "url": "https://example.com/sd",
    }
    world = {
        "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
        "snippet": "世界职业院校技能大赛",
        "url": "https://www.moe.gov.cn/x",
    }
    henan = {
        "title": "河南省教育厅关于2025年职业院校技能大赛的通知",
        "snippet": "河南省职业院校技能大赛获奖名单公示",
        "url": "http://jyt.henan.gov.cn/x",
    }
    assert hit_passes_anchors(national, a, strict=True) is False
    assert hit_passes_anchors(shandong, a, strict=True) is False
    assert hit_passes_anchors(world, a, strict=True) is False
    assert hit_passes_anchors(henan, a, strict=True) is True


def test_filter_drops_all_mismatch_returns_empty():
    a = extract_query_anchors("河南省职业院校技能大赛")
    hits = [
        {"title": "山东省职业院校技能大赛", "snippet": "省赛", "url": "http://a"},
        {"title": "全国职业院校技能大赛", "snippet": "国赛", "url": "http://b"},
    ]
    out = filter_hits_by_anchors(hits, a, strict=True)
    assert out == []


def test_no_geo_query_still_allows_domain_phrase():
    """无行政区划时，不强制 required，可用领域短语过线。"""
    a = extract_query_anchors("2025年职业院校技能大赛获奖名单")
    assert a.required == [] or not any(r.endswith("省") for r in a.required)
    hit = {
        "title": "教育部关于公布2025年世界职业院校技能大赛获奖名单的通知",
        "snippet": "获奖名单",
        "url": "https://www.moe.gov.cn/x",
    }
    assert hit_passes_anchors(hit, a, strict=True) is True


def test_no_hardcoded_province_table_in_module():
    """防回归：实现不得维护省名白名单糊弄。"""
    import inspect
    from app.services.assistant import query_anchors as mod

    src = inspect.getsource(mod)
    # 允许注释里举例，但不得出现业务域名/站内路径硬编码
    for banned in ("jyt.henan", "edu.shandong", "henan.gov.cn/jyt"):
        assert banned not in src, f"hardcoded geo path {banned} not allowed"
    # 不得出现省名列表式白名单赋值
    assert "PROVINCES" not in src and "province_whitelist" not in src
