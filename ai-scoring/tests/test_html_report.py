import os

from app.services.html_report.render import render_html
from app.services.html_report.view_model import build_view_model


def _sample():
    return {
        "meeting_id": "html-sample",
        "project_info": {"project_name": "温室智控", "track": "新一代信息技术赛道"},
        "asr": {"duration": 3300, "segment_count": 12, "transcript": "项目名称是温室智控项目。"},
        "ai_score": {
            "overall_score": 68.5,
            "score_overview": {"diagnosis": "技术方案完整，但演示故障拉低技能水平。"},
            "highlights": ["技术架构完整：覆盖物联网与后台。"],
            "critical_issues": ["AI问答模块演示严重故障。"],
            "evidence_audit": [
                {
                    "level": "强证据",
                    "claim": "演示中途出现故障",
                    "source": "约第40分钟转写",
                    "impact": "技能水平-技能熟练度",
                }
            ],
            "dimensions": {
                "skill_level": {
                    "name": "技能水平",
                    "score": 39,
                    "max_score": 60,
                    "items": [
                        {"name": "技能熟练度", "score": 6, "max_score": 15, "reason": "中途故障。", "gap": "准备备用演示"}
                    ],
                }
            },
            "action_plan": [
                {
                    "priority": "P0",
                    "title": "加固演示",
                    "problem": "故障中断",
                    "method": "准备备用视频",
                    "owner": "三号选手",
                    "timebox": "2周",
                    "acceptance": "连续5次零故障",
                }
            ],
            "team_optimization": [
                {
                    "role": "AI工程师",
                    "issue": "缺少应急预案",
                    "training": "补离线降级",
                }
            ],
            "pitch_structure_benchmark": [
                {
                    "stage": "破冰钩子",
                    "time_range": "00:00-00:30",
                    "score": 6,
                    "actual": "自我介绍为主",
                    "fix": "用痛点数据开场",
                }
            ],
            "final_verdict": {
                "summary": "完成度高，演示稳定性不足。",
                "defensible_strengths": ["架构完整"],
                "critical_deductions": ["演示故障"],
                "next_round_focus": ["备用方案"],
            },
            "jury_review": [
                {"judge_type": "创新挑战型评委", "score": 99, "comment": "不应出现"}
            ],
        },
        "speech_quality": {
            "speech_rate": {"global_chars_per_minute": 240},
            "pauses": {"total_pauses": 8, "rating": "正常"},
            "fillers": {"total_fillers": 4, "filler_rate_percent": 3},
            "duration": 3300,
        },
    }


def test_view_model_keeps_real_scores_and_hides_fake_jury():
    vm = build_view_model(_sample())
    assert vm["overall"] == "68.5"
    assert vm["cover"]["project"]
    assert vm["cover"]["track"] == "新一代信息技术赛道"
    assert "技术架构完整" in vm["highlight_tags"]
    assert vm["team"][0]["action"] == "补离线降级"
    assert vm["jury"] is None
    assert vm.get("profile") is None
    assert any(s["key"] == "overview" for s in vm["sections"])
    assert any(s["key"] == "actions" for s in vm["sections"])
    assert any(s["key"] == "delivery" for s in vm["sections"])
    assert all(s["key"] != "profile" for s in vm["sections"])
    assert vm["dimensions"][0]["item_rows"][0]["name"] == "技能熟练度"


def test_html_template_uses_brochure_tokens():
    html = render_html(_sample())
    assert "#e84a1c" in html
    assert "PingFang SC" in html
    assert "竞赛大脑" in html
    assert "路演评分报告" in html
    assert "qifa-jixue-logo" in html or "cover-publisher" in html
    assert "68.5" in html
    assert "温室智控" in html
    assert "技能熟练度" in html
    assert "成绩单" in html
    assert "创新挑战型评委" not in html
    assert "不应出现" not in html
    assert "这段原始转写" not in html


def test_generate_report_html_writes_pdf_and_html(tmp_path):
    from app.services.html_report import generate_html_report

    pdf_path = generate_html_report(_sample(), str(tmp_path))
    html_path = os.path.join(str(tmp_path), "report_html-sample.html")
    assert pdf_path.endswith("report_html-sample.pdf")
    assert os.path.isfile(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    assert os.path.isfile(html_path)
    assert "多维度" in open(html_path, encoding="utf-8").read()
    import subprocess
    text = subprocess.check_output(["pdftotext", "-layout", pdf_path, "-"], text=True)
    assert "竞赛大脑" in text
    assert "jingsaidanao.com" in text or "启发教育" in text
