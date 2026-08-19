from app.services import llm_scoring_service, report_service


def _story_text(flowables):
    chunks = []
    for flowable in flowables:
        if hasattr(flowable, "getPlainText"):
            chunks.append(flowable.getPlainText())
            continue
        for row in getattr(flowable, "_cellvalues", []) or []:
            for cell in row:
                if isinstance(cell, list):
                    chunks.extend(item.getPlainText() for item in cell if hasattr(item, "getPlainText"))
                elif hasattr(cell, "getPlainText"):
                    chunks.append(cell.getPlainText())
    return "\n".join(chunks)


def test_llm_output_contract_requires_deep_report_sections():
    contract_text = llm_scoring_service.SYSTEM_PROMPT + llm_scoring_service.OUTPUT_FORMAT

    for field in [
        "score_overview",
        "evidence_audit",
        "pitch_structure_benchmark",
        "audio_visual_fusion",
        "action_plan",
        "team_optimization",
        "final_verdict",
    ]:
        assert field in contract_text
    assert "jury_review" not in llm_scoring_service.OUTPUT_FORMAT
    assert "字段互斥" in contract_text


def test_report_renderer_exposes_reference_pdf_sections():
    assert hasattr(report_service, "_add_deep_analysis_sections")
    assert hasattr(report_service, "_add_jury_independent_review")
    assert hasattr(report_service, "_add_pitch_structure_benchmark")
    assert hasattr(report_service, "_add_action_plan")
    assert hasattr(report_service, "_add_team_optimization")
    assert hasattr(report_service, "_add_final_verdict")


def test_reference_pdf_sections_render_from_ai_score_payload():
    story = []
    styles = report_service._styles()
    result = {
        "ai_score": {
            "jury_review": [
                {
                    "judge_code": "ENTP",
                    "judge_type": "创新挑战型评委",
                    "score": 71.2,
                    "focus": "创新点是否经得起质询",
                    "comment": "组合式创新需要说明原创贡献。",
                    "recognition": "技术选型有眼光",
                    "concern": "创新来源说明不足",
                }
            ],
            "pitch_structure_benchmark": [
                {
                    "stage": "商业闭环",
                    "time_range": "35-45min",
                    "score": 2,
                    "actual": "未说明商业模式、定价和市场规模。",
                    "fix": "增加盈利方式、目标客户和市场容量。",
                }
            ],
            "action_plan": [
                {
                    "priority": "P0",
                    "title": "控制语速",
                    "problem": "语速偏快，评委消化不足。",
                    "method": "目标语速220-260wpm，每个技术点后停顿2秒。",
                    "owner": "全体选手",
                    "timebox": "路演前1周",
                    "acceptance": "语速稳定在240wpm左右",
                }
            ],
            "team_optimization": [
                {
                    "priority": "P0",
                    "role": "主讲人A",
                    "issue": "控场强但语速过快。",
                    "training": "每30秒停顿2秒并用手势标记重点。",
                    "target": "语速稳定，眼神交流提升。",
                }
            ],
            "final_verdict": {
                "jury_summary": "项目技术扎实，但商业闭环和证据来源不足。",
                "defensible_strengths": ["真实落地", "技术栈丰富"],
                "critical_deductions": ["商业闭环缺失"],
                "priority_actions": [
                    {"priority": "P0", "item": "补商业模式", "owner": "主讲人A", "expected_gain": "商业闭环2→6"}
                ],
            },
        }
    }

    sections = report_service._SectionCounter()
    report_service._add_jury_independent_review(story, result, styles, sections)
    report_service._add_pitch_structure_benchmark(story, result, styles, sections)
    report_service._add_action_plan(story, result, styles, sections)
    report_service._add_team_optimization(story, result, styles, sections)
    report_service._add_final_verdict(story, result, styles, sections)
    text = _story_text(story)

    assert "创新挑战型评委" not in text
    assert "路演结构对标分析" in text
    assert "商业闭环" in text
    assert "综合改进行动计划" in text
    assert "团队分工优化路线图" in text
    assert "主讲人A" in text
    assert "综合结论" in text
    assert "补商业模式" in text


def test_llm_parse_backfills_reference_report_sections_when_model_omits_them():
    result = llm_scoring_service._parse_and_validate(
        """{
          "overall_score": 0,
          "dimensions": {
            "skill_level": {"name": "技能水平", "max_score": 60, "score": 0, "items": [
              {"name": "技能熟练度", "max_score": 15, "score": 8.5, "reason": "现场演示出现故障。", "improvement": "准备备用演示。"}
            ]}
          },
          "highlights": ["真实落地"],
          "critical_issues": ["商业闭环缺失"],
          "improvement_priorities": [
            {"priority": 1, "dimension": "应用价值", "issue": "商业模式未说明", "suggestion": "补商业模式页"}
          ]
        }"""
    )

    assert result.get("score_overview")
    assert result.get("action_plan")
    assert result.get("final_verdict")
    assert result.get("jury_review") is None
    assert not result.get("audio_visual_fusion")
    assert not result.get("pitch_structure_benchmark")


def test_character_profile_renders_general_markdown_sections():
    story = []
    styles = report_service._styles()
    result = {
        "asr": {"duration": 2400},
        "character_profile": {
            "profile_markdown": """
## 1. 路演整体节奏分析
前半段市场铺垫较长，后半段技能展示证据不足，需要压缩背景并前置关键结论。

## 2. 团队分工推断
- **一号选手**：负责视觉营销与产品上架，表达稳定但标准依据不足。
- **二号选手**：负责内容营销，讲解节奏偏快，需要减少填充词。
"""
        },
    }

    report_service._add_character_profile(story, result, styles, report_service._SectionCounter())
    text = _story_text(story)

    assert "选手角色与能力画像" in text
    assert "路演整体节奏分析" in text
    assert "一号选手" in text


def test_character_profile_removes_llm_preface_and_metadata():
    cleaned = report_service._clean_profile_markdown(
        """好的，作为一名专业的路演评估分析师，我将根据您提供的音视频融合分析数据，为您生成一份独立的、定性的《选手团队能力画像报告》。

---

### **选手团队能力画像报告**

**项目名称：** Session SC-20260704112908577
**赛道：** 商贸赛道
**评估分析师：** AI路演评估系统

### 1. 路演整体节奏分析
本次路演呈现双峰结构。
"""
    )

    assert "作为一名专业" not in cleaned
    assert "评估分析师" not in cleaned
    assert "路演整体节奏分析" in cleaned


def test_report_does_not_include_transcript_appendix_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("OREP_REPORT_ENGINE", "reportlab")
    calls = []
    monkeypatch.setattr(report_service, "_add_transcript_appendix", lambda *args: calls.append(True))

    pdf_path = report_service.generate_report(
        {
            "meeting_id": "contract",
            "asr": {"duration": 60, "transcript": "这段原始转写不应默认进入正式报告"},
            "ai_score": {},
        },
        str(tmp_path),
    )

    assert pdf_path.endswith("report_contract.pdf")
    assert calls == []
