"""Session 33 类报告：分数对齐、字段别名、文案和排版。"""
import json

from app.services.html_report.render import render_html
from app.services.html_report.view_model import build_view_model


def _obs(code, name, dim, score, max_score, level="E2", reason="现场有演示，缺第三方证据，故证据等级为E2。"):
    return {
        "observationCode": code,
        "observationName": name,
        "dimensionCode": dim,
        "dimensionName": {
            "skill_level": "技能水平",
            "professionalism": "职业素养",
            "application_value": "应用价值",
            "teamwork": "团队合作",
            "innovation": "创新创意",
        }[dim],
        "finalScore": score,
        "maxScore": max_score,
        "evidenceLevel": level,
        "evidenceReason": reason,
        "trainingTaskTemplate": {"action": f"请补充{name}材料。"},
    }


def _session33_like():
    return {
        "meeting_id": 33,
        "jury_enabled": True,
        "track": "新一代信息技术赛道",
        "project_info": {
            "project_name": "琉璃新区智能大棚环境监测性能项目",
            "track": "新一代信息技术赛道",
        },
        "asr": {"duration": 3270.592},
        "ai_score": {
            "overall_score": 48.2,
            "score_authority": "structured_rule_engine",
            "_skill_visual_rescore": {
                "before": 27.0,
                "after": 34.0,
                "delta": 7.0,
                "overall_before": 41.2,
                "overall_after": 48.2,
            },
            "score_overview": {
                "diagnosis": (
                    "权威总分48.2，主要受技能熟练度维度（34/60）拖累。"
                    "该维度失分集中在任务难易度、技术先进性和技能熟练度三项，"
                    "合计占技能维度失分的主要部分。任务难易度仅展示了中等难度的多模块业务流程。"
                ),
                "highlights": [
                    "团队分工明确，四位成员分别负责环境检测、气象台风、AI问答和项目管理，角色清晰。",
                    "现场演示覆盖多个核心模块，包括蓝牙数据解析、环境监测、智能排风、AI问答和后台管理。",
                    "现场发现并修复参数混淆问题，展示了基本的缺陷处理能力。",
                ],
                "key_issues": [
                    "技术先进性缺乏量化指标和对比数据，无法证明差异化优势。",
                    "技能熟练度证据等级不足，缺少数据库查询、代码仓库和提交记录等第三方证据。",
                    "任务难易度仅覆盖中等难度场景，未深入异常处理、权限模型和边界条件。",
                ],
            },
            "dimensions": {
                "skill_level": {"name": "skill_level", "score": 34.0, "max_score": 60.0},
                "professionalism": {"name": "professionalism", "score": 3.6, "max_score": 10.0},
                "application_value": {"name": "application_value", "score": 3.8, "max_score": 10.0},
                "teamwork": {"name": "teamwork", "score": 3.0, "max_score": 10.0},
                "innovation": {"name": "innovation", "score": 3.8, "max_score": 10.0},
            },
            "evidence_audit": [
                {
                    "observationCode": "O02",
                    "evidenceLevel": "E2",
                    "gap": "有IDE画面，但缺少数据库查询等第三方证据。",
                    "requiredEvidence": "数据库查询截图、仓库链接。",
                }
            ],
            "judge_questioning": [
                {
                    "question": "代码仓库和提交记录在哪里？",
                    "why_it_matters": "操作规范性失分3.0，技能熟练度失分4.5，均因证据等级为E2，缺少第三方佐证。",
                    "prep_evidence": "整理可公开的仓库链接。",
                }
            ],
            "audio_visual_fusion": {
                "summary": "演示衔接顺畅，但视觉证据多停留在IDE画面。",
                "contradictions": ["口头声称团队协作高效，但未展示任何协作工具或记录画面"],
            },
            "pitch_structure_benchmark": [
                {
                    "section": "开场与团队介绍",
                    "score_or_level": "B",
                    "comment": "分工说明清晰，但未展示协作工具。",
                }
            ],
            "team_optimization": [
                {
                    "role": "项目经理",
                    "currentIssue": "协作和合规证据缺失。",
                    "optimization": "整理协作证据和异常场景脚本。",
                }
            ],
            "final_verdict": {
                "summary": "技能维度34/60严重拖累总分。",
                "defensible_strengths": ["路演结构完整"],
                "critical_deductions": [
                    "技术先进性缺乏量化指标和对比数据（-7.5）",
                    "技能熟练度证据等级不足（-4.5）",
                    "操作规范性缺少第三方证据（-3.0）",
                ],
                "next_round_focus": ["补齐量化证据"],
            },
        },
        "rule_engine_shadow": {
            "finalScore": 41.2,
            "dimensionScores": {
                "skill_level": 27.0,
                "professionalism": 3.6,
                "application_value": 3.8,
                "teamwork": 3.0,
                "innovation": 3.8,
            },
            "observations": [
                _obs("O01", "操作规范性", "skill_level", 5.0, 10.0),
                _obs("O02", "技能熟练度", "skill_level", 7.5, 15.0),
                _obs("O03", "任务难易度", "skill_level", 7.5, 15.0),
                _obs("O04", "技术先进性", "skill_level", 4.5, 15.0, "E1"),
                _obs("O05", "现场讲解效果", "skill_level", 2.5, 5.0, reason="讲解逻辑清晰，演示环节完整，达到substantial水平。"),
                _obs("O06", "职业道德与行为规范", "professionalism", 1.2, 4.0, "E1",
                     "缺乏可验证的合规材料。；现场提及申请软件著作权，但未展示授权。"),
                _obs("O07", "工匠精神", "professionalism", 1.5, 3.0),
                _obs("O08", "安全意识", "professionalism", 0.9, 3.0, "E1"),
                _obs("O09", "实用性", "application_value", 2.0, 4.0),
                _obs("O10", "经济性", "application_value", 0.9, 3.0, "E1"),
                _obs("O11", "可持续性", "application_value", 0.9, 3.0, "E1"),
                _obs("O12", "团队精神", "teamwork", 1.5, 5.0, "E1"),
                _obs("O13", "沟通协作", "teamwork", 1.5, 5.0, "E1"),
                _obs("O14", "创新意识", "innovation", 2.0, 4.0),
                _obs("O15", "创新成效", "innovation", 1.8, 6.0, "E1"),
            ],
        },
        "speech_quality": {
            "speech_rate": {"global_chars_per_minute": 290.7, "global_rating": "过快"},
            "pauses": {"total_pauses": 105, "longest_pause": 93.96},
            "fillers": {"total_fillers": 44, "filler_rate_percent": 0.63},
        },
    }


def _num(value) -> float:
    return float(str(value).replace("—", "0") or 0)


def test_official_items_sum_to_dimension_and_overall():
    vm = build_view_model(_session33_like())
    dims = {d["key"]: d for d in vm["dimensions"]}
    skill = dims["skill_level"]
    item_sum = sum(_num(it["score"]) for it in skill["item_rows"])
    assert len(skill["item_rows"]) == 5
    assert abs(item_sum - _num(skill["score"])) < 0.05
    assert abs(item_sum - 34.0) < 0.05
    dim_sum = sum(_num(d["score"]) for d in vm["dimensions"])
    assert abs(dim_sum - _num(vm["overall"])) < 0.05
    assert vm["overall"] == "48.2"
    assert vm.get("score_note")


def test_verdict_deductions_use_max_minus_score():
    vm = build_view_model(_session33_like())
    skill = next(d for d in vm["dimensions"] if d["key"] == "skill_level")
    by_name = {it["name"]: it for it in skill["item_rows"]}
    adv_gap = _num(by_name["技术先进性"]["max_score"]) - _num(by_name["技术先进性"]["score"])
    text = "\n".join(row["text"] for row in vm["verdict"]["rows"])
    assert f"（-{adv_gap:.1f}）".replace(".0）", "）") in text.replace(".0）", "）")
    assert "（-7.5）" not in text


def test_alias_fields_fill_empty_chapters_and_cover():
    vm = build_view_model(_session33_like())
    assert vm["cover"]["session"] == "第 33 场"
    assert "进行中" not in vm["cover"]["report_type"]
    assert vm["pitch"]
    assert vm["pitch"][0]["stage"] == "开场与团队介绍"
    assert vm["pitch"][0]["score"] == "B"
    assert "协作工具" in vm["pitch"][0]["actual"]
    assert vm["team"][0]["issue"] == "协作和合规证据缺失。"
    assert "异常场景" in vm["team"][0]["action"]
    assert vm["evidence"]
    assert vm["evidence"][0]["claim"] == "技能熟练度"
    assert "第三方" in vm["evidence"][0]["source"]
    assert vm["fusion"]
    assert vm["fusion"]["rows"]
    assert "协作工具" in vm["fusion"]["rows"][0]["desc"]


def test_copy_is_complete_and_uses_official_names():
    vm = build_view_model(_session33_like())
    assert "…" not in vm["diagnosis"]
    assert "多模块" in vm["diagnosis"]
    assert "技能熟练度维度" not in vm["diagnosis"]
    assert "技能水平" in vm["diagnosis"]
    names = [d["name"] for d in vm["dimensions"]]
    assert "团队合作" in names
    assert "创新创意" in names
    assert "团队协作" not in names
    assert "创新能力" not in names
    assert not any(t.endswith(("环", "蓝", "展示", "未")) for t in vm["highlight_tags"] + vm["issue_tags"])
    assert any("四位成员" in t or "团队分工" in t for t in vm["highlight_tags"])
    assert "E2" not in vm["questions"][0]["why"]
    item_text = " ".join(
        f"{it['evidence']} {it['gap']}"
        for d in vm["dimensions"]
        for it in d["item_rows"]
    )
    assert "。；" not in item_text
    assert "故证据等级" not in item_text
    explain = next(
        it for d in vm["dimensions"] if d["key"] == "skill_level" for it in d["item_rows"] if it["name"] == "现场讲解效果"
    )
    assert "substantial" not in explain["evidence"]
    assert "达到水平" not in explain["evidence"]
    assert not any(it["evidence"].rstrip().endswith("，") for d in vm["dimensions"] for it in d["item_rows"] if it["evidence"])
    html = render_html(_session33_like())
    assert "团队合作" in html
    assert "创新创意" in html


def test_jury_chapter_uses_praise_concern_and_consensus():
    result = _session33_like()
    result["jury_enabled"] = True
    result["jury"] = {
        "judge_count": 3,
        "official_score": 48.2,
        "trimmed_average_score": 60.6,
        "highest_score": 61.5,
        "lowest_score": 59.3,
        "score_diff_from_official": 12.4,
        "consensus_issues": [
            {"issue": "创新成效数据没有来源", "count": 2},
            {"issue": "创新成效数据无来源，开发周期缩短60%经不起追问", "count": 2},
        ],
        "dimension_stats": [
            {
                "key": "application_value",
                "name": "应用价值",
                "average_score": 6.7,
                "max_score": 10,
                "highest_score": 6.8,
                "lowest_score": 6.5,
                "range": 0.3,
            },
        ],
        "score_cards": [
            {
                "role_label": "价值初心型评委",
                "overall_score": 61.5,
                "short_label": "初心和用户是否真诚",
                "highlights": ["语音00:27四位成员分工清楚。"],
                "critical_issues": [
                    "40:22-42:44 AI问答演示出现约2分钟故障冷场，参数混淆导致未应答。",
                    "创新成效没有对比数据。",
                ],
                "improvement_priorities": [{"suggestion": "补一张小农户真实使用案例。"}],
                "top_concerns": ["项目动机是否落到真实农户"],
                "persona_view": {
                    "top_concerns": ["项目动机是否落到真实农户"],
                    "score_reasoning_style": "先看愿景和用户是否被证据托住。",
                    "optimization_angle": "补小农户案例，把愿景落到人。",
                },
            },
            {
                "role_label": "实操验证型评委",
                "overall_score": 59.3,
                "short_label": "能不能当场跑通",
                "highlights": ["现场修了参数混淆。"],
                "critical_issues": ["AI问答冷场约两分钟，暴露联调不足。"],
                "improvement_priorities": [{"suggestion": "赛前做一次端到端联调。"}],
                "top_concerns": ["AI问答演示故障冷场暴露联调不足"],
                "persona_view": {
                    "top_concerns": ["技术栈口头描述与视觉代码画面不一致"],
                    "score_reasoning_style": "看现场能不能跑通，以及口头和画面是否对得上。",
                    "optimization_angle": "赛前联调，并准备离线应答脚本。",
                },
            },
            {
                "role_label": "规范审查型评委",
                "overall_score": 60.3,
                "short_label": "标准、流程、记录",
                "highlights": ["约26.5min安全防护方案页有HTTPS和JWT。"],
                "critical_issues": [
                    "语音40:36-42:44明确说参数混搅在一起，AI应答无效，现场改代码导致冷场。",
                    "声称遵循国家标准，但未给出标准编号或条款对照。",
                ],
                "improvement_priorities": [{"suggestion": "在PPT里补GB/T编号和条款对照表。"}],
                "top_concerns": ["标准编号和条款对照缺失"],
                "persona_view": {
                    "top_concerns": ["标准编号和条款对照缺失"],
                    "score_reasoning_style": "缺编号、缺记录、缺验收材料就往下压。",
                    "optimization_angle": "补标准编号、合规检查记录和测试报告。",
                },
            },
        ],
        "members": [],
    }
    vm = build_view_model(result)
    assert vm["jury"]
    assert vm["jury"]["count"] == 3
    assert vm["jury"]["summary"]["official"]
    assert vm["jury"]["summary"]["jury_avg"]
    consensus_text = " ".join(c["text"] for c in vm["jury"]["consensus"])
    assert consensus_text.count("冷场") <= 1
    assert consensus_text.count("创新成效") <= 1
    assert any((c.get("n") or 0) >= 2 for c in vm["jury"]["consensus"])
    assert vm["jury"]["lenses"]
    assert {row["role"] for row in vm["jury"]["lenses"]} == {c["role"] for c in vm["jury"]["cards"]}
    assert any("标准编号" in (row.get("ask") or "") for row in vm["jury"]["lenses"])
    assert any("真实农户" in (row.get("ask") or "") or "小农户" in (row.get("ask") or "") for row in vm["jury"]["lenses"])
    card0 = vm["jury"]["cards"][0]
    assert card0["praise"]
    assert card0["concern"]
    assert card0["advice"]
    assert card0["why"]
    assert "INFP" not in card0["role"]
    assert "农户" in card0["concern"] or "农户" in card0["advice"]
    review_card = next(c for c in vm["jury"]["cards"] if "规范" in c["role"])
    assert "标准" in review_card["concern"] or "条款" in review_card["advice"]
    assert len({c["advice"] for c in vm["jury"]["cards"]}) >= 2
    assert vm["jury"]["dim_compare"][0]["spread"]
    html = render_html(result)
    assert "合议" in html
    assert "认可" in html
    assert "质疑" in html
    assert "下一刀" in html
    assert "打分时看重" in html
    assert "不同视角会追问" in html
    assert "多数评委卡住" in html
    assert "评委分差" in html
    assert "INFP" not in html
    assert "J01" not in html
    assert any(s["key"] == "jury" for s in vm["sections"])


def test_jury_package_keeps_persona_lens_fields():
    from app.services.report_service import _normalize_jury_session_to_package

    pkg = _normalize_jury_session_to_package({
        "status": "completed",
        "judge_count": 1,
        "official_score": 44.6,
        "members": [{"code": "ISTJ", "role_label": "规范审查型评委", "short_label": "标准、流程、记录"}],
        "judge_reports": [
            {
                "status": "completed",
                "persona_code": "ISTJ",
                "role_label": "规范审查型评委",
                "overall_score": 60.3,
                "highlights": ["三端架构有仪表盘佐证。"],
                "critical_issues": ["标准编号缺失。"],
                "improvement_priorities": [{"suggestion": "补条款对照表。"}],
                "persona_view": {
                    "top_concerns": ["标准编号和条款对照缺失"],
                    "score_reasoning_style": "缺记录就压分。",
                    "optimization_angle": "先补标准编号。",
                },
            }
        ],
        "aggregate": {"trimmed_average_score": 60.3, "consensus_issues": []},
    })
    assert pkg
    card = pkg["score_cards"][0]
    assert card["persona_view"]["top_concerns"][0].startswith("标准编号")
    assert "缺记录" in card["score_reasoning_style"]
    assert "标准编号" in card["optimization_angle"]
    assert "ISTJ" not in json.dumps(card["role_label"], ensure_ascii=False)


def test_refresh_report_after_jury_flips_flag(tmp_path, monkeypatch):
    from app.services import report_service

    result_dir = tmp_path / "results"
    result_dir.mkdir()
    payload = {"meeting_id": "35", "jury_enabled": False, "ai_score": {"overall_score": 48.8}}
    (result_dir / "result_35.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(report_service, "generate_report", lambda result, output_dir: str(tmp_path / "report_35.pdf"))

    class _Settings:
        UPLOAD_DIR = str(tmp_path)

    import app.config as config
    monkeypatch.setattr(config, "settings", _Settings())
    path = report_service.refresh_report_after_jury("35")
    saved = json.loads((result_dir / "result_35.json").read_text(encoding="utf-8"))
    assert saved["jury_enabled"] is True
    assert path.endswith("report_35.pdf")


def test_print_chrome_templates_carry_brand_and_page():
    html = render_html(_session33_like())
    assert "page-break-before: always" in html
    from app.services.html_report.render import _footer_template, _header_template
    header = _header_template("data:image/png;base64,QQ==", "竞赛大脑")
    footer = _footer_template("https://www.jingsaidanao.com", "启发教育科技有限公司")
    assert "路演评分报告" in header
    assert "竞赛大脑" in header
    assert "data:image/png" in header
    assert "letter-spacing:0.06em" in header
    assert "pageNumber" in footer
    assert "jingsaidanao.com" in footer
    assert "启发教育科技有限公司" in footer
    assert "data:image/svg+xml" not in header
    assert "qifa-jixue" not in render_html(_session33_like())
