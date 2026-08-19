from pathlib import Path

from app.services.html_report.bands import band_label
from app.services.html_report.render import render_html
from app.services.html_report.view_model import build_view_model
from app.services.report_service import _humanize_dimension_tokens


CONTRACT = Path(__file__).resolve().parents[1] / "docs" / "scoring-report-contract.md"


def test_contract_document_exists():
    text = CONTRACT.read_text(encoding="utf-8")
    for token in ("一事实一住处", "官方给分", "技能熟练度", "证据台账", "讲述质量", "不同视角会追问什么", "评委分差"):
        assert token in text


def test_humanize_keeps_official_item_name():
    assert _humanize_dimension_tokens("技能熟练度") == "技能熟练度"
    assert "技能熟练度" in _humanize_dimension_tokens("技能熟练度（技能水平）")


def test_band_label_does_not_round_up():
    assert band_label("技能熟练度", 8.2) == "工具用得熟，但临场不稳"
    assert band_label("操作规范性", 6.8) == "还能现场按标准做"


def test_render_uses_seven_chapter_spine_and_drops_profile():
    result = {
        "meeting_id": "c1",
        "project_info": {"project_name": "温室智控", "track": "新一代信息技术赛道"},
        "asr": {"duration": 3300, "transcript": "正文"},
        "character_profile": {"profile_markdown": "好的，作为专业的路演评估分析师，我将生成长文。wpm 300"},
        "ai_score": {
            "overall_score": 68.5,
            "score_overview": {
                "diagnosis": "完成度高，演示稳定性不足。",
                "highlights": ["架构完整"],
                "key_issues": ["演示故障"],
            },
            "evidence_audit": [
                {"level": "强证据", "claim": "架构完整", "source": "第4分钟架构图", "impact": "任务难易度"}
            ],
            "dimensions": {
                "skill_level": {
                    "name": "技能水平",
                    "score": 39,
                    "max_score": 60,
                    "items": [
                        {
                            "name": "技能熟练度",
                            "score": 8.2,
                            "max_score": 15,
                            "reason": "AI问答模块故障，中断约93.96秒。",
                            "gap": "需要备用演示",
                        },
                        {
                            "name": "任务难易度",
                            "score": 10.2,
                            "max_score": 15,
                            "reason": "技术栈完整，但AI问答模块故障，中断约93.96秒。",
                            "gap": "稳定性不足",
                        },
                    ],
                }
            },
            "audio_visual_fusion": {
                "summary": "第40分钟故障，而第26分钟仍是创新点PPT。",
                "contradictions": [
                    {
                        "time": "约第40-42分钟",
                        "description": "AI故障93.96秒；但视频帧第26分钟仍显示创新点PPT",
                    },
                    {
                        "time": "全程",
                        "description": "语速287.8字/分钟，肢体却显得从容",
                    },
                ],
            },
            "action_plan": [
                {"priority": "P0", "title": "加固演示", "method": "准备备用视频", "acceptance": "连续5次零故障"}
            ],
            "final_verdict": {"summary": "演示稳定性不足。", "defensible_strengths": ["架构完整"]},
        },
        "speech_quality": {
            "speech_rate": {"global_chars_per_minute": 287.8},
            "pauses": {"total_pauses": 97},
            "fillers": {"total_fillers": 39, "filler_rate_percent": 3},
        },
    }

    vm = build_view_model(result)
    keys = [s["key"] for s in vm["sections"]]
    assert keys[0] == "overview"
    assert "delivery" in keys
    assert "profile" not in keys
    assert vm["dimensions"][0]["item_rows"][0]["name"] == "技能熟练度"
    assert "93.96" in vm["dimensions"][0]["item_rows"][0]["evidence"]
    assert "详见" not in vm["dimensions"][0]["item_rows"][1]["evidence"]
    assert "技术栈" in vm["dimensions"][0]["item_rows"][1]["evidence"]
    assert all("26分钟" not in (row.get("desc") or "") for row in (vm.get("fusion") or {}).get("rows") or [])

    html = render_html(result)
    assert "成绩单" in html
    assert "证据台账" in html
    assert "官方给分" in html
    assert "选手角色与能力画像" not in html
    assert "作为专业的路演评估分析师" not in html
    assert "wpm" not in html.lower()
    assert "本维有基础，证据仍不足" not in html
    assert html.count("93.96") <= 2


def test_rule_engine_payload_fills_official_items():
    result = {
        "meeting_id": "30",
        "project_info": {"project_name": "温室智控", "track": "新一代信息技术赛道"},
        "asr": {"duration": 3270},
        "ai_score": {
            "overall_score": 52.5,
            "score_overview": {
                "diagnosis": "规则引擎权威分 52.5 分，证据上限 14.5，硬性处罚 0.0。"
            },
            "dimensions": {
                "skill_level": {"name": "skill_level", "score": 37, "max_score": 60, "items": []}
            },
            "critical_issues": ["操作规范性：缺仓库"],
            "action_plan": [{"priority": "P0", "title": "补齐操作规范性", "method": "补仓库"}],
        },
        "rule_engine_shadow": {
            "observations": [
                {
                    "observationCode": "O01",
                    "observationName": "操作规范性",
                    "dimensionCode": "skill_level",
                    "finalScore": 5.0,
                    "maxScore": 10.0,
                    "evidenceLevel": "E2",
                    "evidenceReason": "有架构图和代码讲解，缺代码仓库。",
                    "trainingTaskTemplate": {"action": "补提交记录"},
                },
                {
                    "observationCode": "O02",
                    "observationName": "技能熟练度",
                    "dimensionCode": "skill_level",
                    "finalScore": 10.5,
                    "maxScore": 15.0,
                    "evidenceLevel": "E3",
                    "evidenceReason": "讲解熟练，缺 IDE 画面。",
                },
            ]
        },
    }
    vm = build_view_model(result)
    names = [it["name"] for it in vm["dimensions"][0]["item_rows"]]
    assert names == ["操作规范性", "技能熟练度"]
    assert "规则引擎" not in vm["diagnosis"]
    assert vm["evidence"]
    assert vm["verdict"]
    html = render_html(result)
    assert "技能熟练度" in html
    assert "操作规范性" in html
    assert "证据台账" in html
    assert "判定" in html
