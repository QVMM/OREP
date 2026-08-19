from app.services.assistant.brain import plan_turn
from app.services.assistant.tracks.loader import (
    clear_tracks_cache,
    load_anonymity_block,
    resolve_rules_block,
)


def setup_function():
    clear_tracks_cache()


def test_light_confirm_weekly_plan():
    plan = plan_turn(user_text="帮我生成本周训练计划要点")
    assert plan.need_light_confirm is True
    assert plan.light_confirm_kind == "plan"
    assert "草案" in plan.system_addendum or "轻确认" in plan.system_addendum


def test_light_confirm_skipped_on_expand():
    plan = plan_turn(user_text="展开完整计划")
    assert plan.need_light_confirm is False


def test_light_confirm_rewrite_long():
    long_script = "请全文重写下面讲稿，大改口语：" + ("痛点与方案。" * 40)
    plan = plan_turn(user_text=long_script)
    assert plan.goal == "rewrite"
    assert plan.need_light_confirm is True
    assert plan.light_confirm_kind == "rewrite"


def test_force_evidence_on_score_review():
    plan = plan_turn(user_text="根据评分复盘一下扣分")
    assert plan.need_scores is True
    assert plan.force_evidence is True
    assert "强制依据" in plan.system_addendum


def test_rules_anonymity_and_track():
    anon = load_anonymity_block()
    assert "号位" in anon
    assert "姓名" in anon or "禁止" in anon
    block, tags = resolve_rules_block(track="餐饮")
    assert "anonymity" in tags
    assert any("track" in t for t in tags)
    assert "餐饮" in block
    assert "门店" in block or "损耗" in block


def test_daily_agenda_no_light_confirm():
    plan = plan_turn(user_text="今天做什么最优先？")
    # 今日待办不需要大计划草案卡
    assert plan.need_light_confirm is False
