from pathlib import Path

from app.services.assistant.skills.loader import (
    apply_skill_tool_gates,
    clear_skills_cache,
    discover_skills,
    format_skills_block,
    match_skills,
    resolve_skills_for_turn,
)


def setup_function():
    clear_skills_cache()


def test_discover_builtin_skills():
    skills = discover_skills()
    names = {s.name for s in skills}
    assert "opening" in names
    assert "score-review" in names
    assert "daily-agenda" in names
    assert "rewrite-script" in names


def test_slash_match_opening():
    matches = match_skills("/开场 帮我写一版", audience="student")
    assert matches
    assert matches[0].skill.name == "opening"
    assert matches[0].reason == "slash"


def test_trigger_match_daily_agenda():
    matches = match_skills("今天做什么最优先？", audience="student")
    assert matches
    assert matches[0].skill.name == "daily-agenda"
    assert matches[0].skill.need_learning is True


def test_score_review_forces_scores_gate():
    class Plan:
        need_scores = False
        need_learning = False
        need_tasks = False
        need_collab = False

    plan = Plan()
    matches = match_skills("根据评分复盘一下扣分", audience="student")
    tags = apply_skill_tool_gates(plan, matches)
    assert plan.need_scores is True
    assert any("scores" in t for t in tags)


def test_teacher_skill_not_for_student_slash_only_when_audience():
    student = match_skills("/工作台 待批多少", audience="student")
    # teacher-desk is teacher-only; slash alone still filtered by audience
    assert all(m.skill.name != "teacher-desk" for m in student)
    teacher = match_skills("/工作台 待批多少", audience="teacher")
    assert teacher and teacher[0].skill.name == "teacher-desk"


def test_format_skills_block_injects_body():
    matches, block = resolve_skills_for_turn("写一段30秒开场", audience="student")
    assert matches
    assert "本轮启用技能" in block
    assert "开场全文" in block or "30 秒" in block


def test_limit_two_skills():
    # text that could hit rewrite + opening — still cap
    matches = match_skills("润色开场 改一版讲稿", audience="student", limit=2)
    assert len(matches) <= 2


def test_list_skills_public_student():
    from app.services.assistant.skills.loader import list_skills_public

    rows = list_skills_public(audience="student")
    names = {r["name"] for r in rows}
    assert "opening" in names
    assert "teacher-desk" not in names
    assert all(r.get("slash") for r in rows)
