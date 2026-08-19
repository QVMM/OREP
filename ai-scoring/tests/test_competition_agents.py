import pytest

from app.services.ppt.competition_agents import CompetitionPPTAgentPipeline


@pytest.mark.asyncio
async def test_competition_pipeline_redacts_identity_and_builds_38_page_draft():
    pipeline = CompetitionPPTAgentPipeline()
    result = await pipeline.run(
        {
            "core_problem": "现场设备巡检依赖人工记录，问题发现滞后，数据无法复盘，班组协同效率低。",
            "solution_overview": "通过传感器采集、边缘网关预处理、AI异常识别、可视化看板和工单反馈形成闭环。",
            "demo_workflow": "设备接入、网关配置、数据采集、模型推理、告警处置、结果复盘。",
            "tech_stack": "物联网网关、时序数据库、异常检测模型、Web可视化看板。",
            "team_members": "队长：张三，来自测试职业技术学院，电话13812345678。算法岗、前端岗、硬件岗协同。",
        },
        project_name="智能巡检系统",
        team_name="测试职业技术学院代表队",
        enable_web_research=False,
    )

    assert result["safety_report"]["removed_count"] >= 2
    assert "13812345678" not in str(result["sanitized_payload"])
    assert "职业技术学院" not in str(result["sanitized_payload"])
    assert result["generation_mode"] == "draft"
    assert len(result["outline_json"]["pages"]) == 38
    assert result["outline_json"]["target_page_range"] == "35-45"


@pytest.mark.asyncio
async def test_competition_pipeline_blocks_idea_only_materials():
    pipeline = CompetitionPPTAgentPipeline()
    result = await pipeline.run(
        {"idea": "想做一个AI项目"},
        project_name="AI项目",
        enable_web_research=False,
    )

    assert result["generation_mode"] == "materials_only"
    assert result["can_generate_draft"] is False
    assert result["formal_export_blocked"] is True
    assert result["clarification_report"]["need_clarification"] is True
