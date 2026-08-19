import asyncio
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

import app.services.ppt as ppt_package
from app.services.ppt.adapter_code.pipeline_coordinator import PipelineCoordinator
from app.services.ppt.adapter_code.pipeline_coordinator import PipelineContext
from app.services.ppt.layout_rules_gate import (
    build_legacy_layout_rules_gate,
    build_legacy_layout_rules_usage,
)
from app.services.ppt.outline_layout_planner import OutlineLayoutPlanner
from app.services.ppt.outline_generator import OutlineGenerator
from app.services.ppt.ppt_service import PPTService
from app.services.ppt.v4.alignment_bridge import build_v4_quality_alignment_preview
from app.services.ppt.v4.dashboard_bridge import build_v4_shadow_dashboard
from app.services.ppt.v4.deck_consistency_service import build_deck_review_report
from app.services.ppt.v4.diagram_blueprint_builder import build_diagram_blueprint
from app.services.ppt.v4.diagram_isometric_renderer import render_isometric_diagram
from app.services.ppt.v4.diagram_review_rules import review_diagram_render
from app.services.ppt.v4.diagram_svg_renderer import render_diagram_svg
from app.services.ppt.v4.feature_flags import should_enable_diagram_isometric, should_enable_diagrams
from app.services.ppt.v4.layout_grammar_registry import get_layout_family_ids
from app.services.ppt.v4.layout_solver import build_layout_plan
from app.services.ppt.v4.phase4_bridge import build_v4_phase4_readiness_preview
from app.services.ppt.v4.phase4_cutover_bridge import build_v4_phase4_cutover_preview
from app.services.ppt.v4.phase4_dry_run_bridge import build_v4_phase4_dry_run_preview
from app.services.ppt.v4.phase4_gate_bridge import build_v4_phase4_gate_pack
from app.services.ppt.v4.phase5_extension_bridge import build_v4_phase5_extension_pack
from app.services.ppt.v4.phase5_gate_bridge import build_v4_phase5_gate_pack
from app.services.ppt.v4.phase5_preflight_bridge import build_v4_phase5_preflight_pack
from app.services.ppt.v4.phase6_prep_bridge import build_v4_phase6_prep_pack
from app.services.ppt.v4.phase7_cleanup_bridge import (
    build_v3_retirement_cleanup_plan,
    scan_v3_retirement_inventory,
)
from app.services.ppt.v4.phase7_retirement_bridge import (
    build_v4_phase7_retirement_pack,
    build_v4_phase7_task_observation,
)
from app.services.ppt.v4.formal_page_sequence import build_v4_formal_page_sequence
from app.services.ppt.v4.formal_render_engine import render_formal_v4_pages
from app.services.ppt.v4.opening_rhythm_regression import (
    build_front_segment_rhythm_batch_report,
    build_front_segment_rhythm_snapshot,
    build_opening_rhythm_batch_report,
    build_opening_rhythm_snapshot,
)
from app.services.ppt.v4.page_blueprint_builder import build_page_blueprints
from app.services.ppt.v4.deck_blueprint_planner import build_deck_blueprint
from app.services.ppt.v4.preference_resolver import resolve_preference_profile
from app.services.ppt.v4.quality_bridge import build_v4_compat_quality_report
from app.services.ppt.v4.sidecar_coordinator import should_run_shadow_sidecars
from app.services.ppt.v4.render_engine import (
    build_shadow_render_snapshot_payload,
    render_shadow_pages,
)
from app.services.ppt.v4.sidecar_coordinator import build_shadow_review_snapshot_payload
from app.services.ppt.v4.visual_review_v4 import build_page_review_reports
from app.services.ppt.vision_judge_service import PPTVisionJudgeService


class V4StructurePipelineTests(unittest.TestCase):
    def setUp(self):
        self.service = PPTService.__new__(PPTService)
        self.saved_snapshots = []
        self.service._save_generation_snapshot = self._capture_snapshot

        self.outline_json = {
            "project": {"name": "智慧实训平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智慧实训平台",
                    "slide_role": "cover",
                    "page_series_type": "cover_keynote",
                    "page_visual_role": "keynote_anchor",
                    "contract_id": "cover_opening_keynote_v1",
                    "ppt_text": "面向职业教育 AI 实训的全流程平台",
                    "content_points": ["AI实训", "过程留痕", "结果评估"],
                },
                {
                    "page_index": 2,
                    "title": "项目定义",
                    "slide_role": "project_definition",
                    "page_series_type": "definition_canvas",
                    "page_visual_role": "definition_canvas",
                    "contract_id": "project_definition_canvas_v1",
                    "content": "用一个平台打通教、学、练、评",
                    "content_points": ["服务对象", "核心场景", "价值闭环"],
                },
                {
                    "page_index": 3,
                    "title": "后续扩展页",
                    "slide_role": "content",
                    "page_series_type": "custom_unknown_series",
                    "page_visual_role": "future_extension",
                    "content": "保留给后续页系注册验证使用",
                    "content_points": ["待注册页系", "先走 sidecar", "不得切正式返回"],
                },
            ],
        }
        self.questionnaire_data = {
            "theme": "competition-tech-dark",
            "visual_style_profile": {
                "canvas": {"width": 1920, "height": 1080, "safe_margin": 96},
                "colors": {"primary": "#4A9AFF"},
            },
        }

    def _capture_snapshot(self, **kwargs):
        self.saved_snapshots.append(kwargs)

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase1_artifacts_are_attached_stably(self):
        first = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=101,
            fallback_theme="rapidesign",
        )
        second = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=101,
            fallback_theme="rapidesign",
        )

        self.assertIn("deck_blueprint", first)
        self.assertIn("page_blueprints", first)
        self.assertIn("layout_plan", first)
        self.assertIn("variant_history", first)

        page0 = first["pages"][0]
        for key in (
            "page_goal",
            "core_argument",
            "transition_role",
            "audience_takeaway",
            "emphasis_mode",
            "visual_intent",
        ):
            self.assertIn(key, page0)

        self.assertEqual(first["deck_blueprint"], second["deck_blueprint"])
        self.assertEqual(first["page_blueprints"], second["page_blueprints"])
        self.assertEqual(first["layout_plan"], second["layout_plan"])
        self.assertEqual(first["variant_history"], second["variant_history"])

    def test_layout_solver_selects_before_after_for_contrast_mapping_page(self):
        outline = {
            "project": {"name": "智慧巡检平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "解决方案升级对比",
                    "slide_role": "solution_overview",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "突出改良前后的差异和升级价值。",
                    "core_argument": "传统人工巡检发现晚、损耗高；改良后通过平台协同实现实时预警和闭环处置。",
                    "content_points": ["改良前问题", "改良后做法", "升级价值"],
                }
            ],
        }
        profile = resolve_preference_profile({"theme": "rapidesign"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, variant_history = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].family_id, "mapping_bridge.before_after")
        self.assertIn("contrast", layout_plan[0].selection_trace["semantic_signals"])
        self.assertEqual(layout_plan[0].region_plan["scan_pattern"], "split_compare")
        self.assertIn("phase1_content_aware_family", variant_history[0].reason)

    def test_layout_solver_selects_scenario_map_for_value_expansion_page(self):
        outline = {
            "project": {"name": "乡村服务平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "推广路径与复制场景",
                    "slide_role": "application_value",
                    "page_series_type": "value_matrix",
                    "page_goal": "说明项目如何在不同地区、不同对象中复制推广。",
                    "core_argument": "从种植户、合作社到示范基地，项目具备跨区域复制和行业推广基础。",
                    "content_points": ["服务对象", "应用场景", "推广机制", "复制路径"],
                }
            ],
        }
        profile = resolve_preference_profile({"theme": "roadshow-pro-light"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, _ = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].family_id, "value_matrix.scenario_map")
        self.assertIn("scenario_expansion", layout_plan[0].selection_trace["semantic_signals"])
        self.assertEqual(layout_plan[0].region_plan["focus_strategy"], "hero_first")

    def test_layout_solver_switches_variant_under_repetition_pressure(self):
        outline = {
            "project": {"name": "经济价值回顾"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "阶段成果一",
                    "slide_role": "application_value",
                    "page_series_type": "value_matrix",
                    "core_argument": "病害预警提前3天，农药使用量降低30%，具备直接经济收益。",
                    "content_points": ["降本成效", "增收回报", "量化结果", "验证口径"],
                },
                {
                    "page_index": 2,
                    "title": "阶段成果二",
                    "slide_role": "application_value",
                    "page_series_type": "value_matrix",
                    "core_argument": "识别准确率提升12%，户均年增收约5000元，并形成清晰的量化验证口径。",
                    "content_points": ["量化成效", "收益结果", "指标对照", "验证口径"],
                },
            ],
        }
        profile = resolve_preference_profile({"theme": "competition-tech-dark"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, variant_history = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].family_id, "value_matrix.score_board")
        self.assertEqual(layout_plan[1].family_id, "value_matrix.score_board")
        self.assertNotEqual(layout_plan[0].selected_variant, layout_plan[1].selected_variant)
        self.assertIn("candidate_variant_scores", variant_history[1].selection_trace)
        self.assertEqual(variant_history[1].selection_trace["density_mode"], "dense")

    def test_layout_solver_biases_agenda_to_route_board_for_route_semantics(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 2,
                    "title": "汇报路线与章节推进",
                    "slide_role": "agenda",
                    "page_series_type": "agenda_navigation",
                    "page_goal": "先交代完整的章节推进和阅读路线。",
                    "core_argument": "本次汇报按问题识别、方案设计、平台架构、验证结果、价值收束五个阶段推进。",
                    "content_points": ["问题识别", "方案设计", "平台架构", "验证结果", "价值收束"],
                }
            ],
        }
        profile = resolve_preference_profile({"theme": "formal-tech"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, variant_history = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].family_id, "agenda_navigation.route_board")
        self.assertEqual(layout_plan[0].selected_variant, "route_board_vertical")
        self.assertEqual(layout_plan[0].region_plan["focus_strategy"], "diagram_first")
        self.assertEqual(layout_plan[0].region_plan["scan_pattern"], "staged_progression")
        self.assertIn("flow", layout_plan[0].selection_trace["semantic_signals"])
        self.assertIn("路径", variant_history[0].reason)

    def test_layout_solver_sets_evidence_board_focus_to_evidence_first(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 3,
                    "title": "政策依据与项目价值",
                    "slide_role": "policy_context",
                    "page_series_type": "evidence_board",
                    "page_goal": "用政策、落地抓手和应用价值说明项目可信。",
                    "core_argument": "项目响应国家数字乡村战略，具备明确的政策依据和应用前景。",
                    "content_points": ["政策依据", "落地抓手", "试点成效", "复制价值"],
                }
            ],
        }
        profile = resolve_preference_profile({"theme": "formal-tech"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, _ = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].region_plan["focus_strategy"], "evidence_first")

    def test_layout_solver_emits_narrative_segment_and_role(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 4,
                    "title": "行业痛点与问题边界",
                    "slide_role": "problem_analysis",
                    "page_series_type": "definition_canvas",
                    "page_goal": "界定行业问题和项目切入边界。",
                    "core_argument": "行业痛点集中在识别滞后和处置链路不闭环。",
                    "content_points": ["行业痛点", "问题边界", "切入对象", "实施限制"],
                },
                {
                    "page_index": 5,
                    "title": "平台架构与方案路径",
                    "slide_role": "solution_overview",
                    "page_series_type": "architecture_system",
                    "page_goal": "解释方案结构和模块协同方式。",
                    "core_argument": "平台采用端边云协同架构，实现从采集到分析的闭环。",
                    "content_points": ["采集层", "边缘层", "平台层", "应用层"],
                },
            ],
        }
        profile = resolve_preference_profile({"theme": "formal-tech"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, _ = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].region_plan["narrative_segment"], "definition")
        self.assertEqual(layout_plan[0].region_plan["narrative_role"], "problem_framing")
        self.assertEqual(layout_plan[1].region_plan["narrative_segment"], "solution")
        self.assertEqual(layout_plan[1].region_plan["narrative_role"], "system_explanation")

    def test_layout_solver_splits_bridge_collaboration_timeline_narrative_roles(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 5,
                    "title": "执行反馈与育人成效闭环",
                    "slide_role": "solution_overview",
                    "page_series_type": "bridge_story",
                    "page_goal": "说明执行反馈如何回流到育人成效。",
                    "core_argument": "通过执行、反馈、调整和成效回流形成闭环。",
                    "content_points": ["执行过程", "反馈闭环", "调整动作", "育人成效"],
                },
                {
                    "page_index": 6,
                    "title": "岗位交接与应急补位",
                    "slide_role": "solution_overview",
                    "page_series_type": "collaboration_matrix",
                    "page_goal": "说明岗位分工、交接机制和应急补位。",
                    "core_argument": "多岗位协作需要稳定交接链路和补位机制。",
                    "content_points": ["岗位职责", "交接机制", "应急补位", "协同结果"],
                },
                {
                    "page_index": 7,
                    "title": "问题复盘与质量改进",
                    "slide_role": "solution_overview",
                    "page_series_type": "journey_timeline",
                    "page_goal": "说明阶段推进后的问题复盘与质量改进。",
                    "core_argument": "围绕关键问题复盘后形成持续改进动作。",
                    "content_points": ["需求调研", "测试验证", "问题复盘", "质量改进"],
                },
            ],
        }
        profile = resolve_preference_profile({"theme": "formal-tech"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, _ = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].region_plan["narrative_role"], "feedback_bridge")
        self.assertEqual(layout_plan[1].region_plan["narrative_role"], "handoff_chain")
        self.assertEqual(layout_plan[2].region_plan["narrative_role"], "retrospective_improvement")

    def test_layout_solver_prefers_chain_and_retrospective_variants_for_targeted_roles(self):
        outline = {
            "project": {"name": "真实任务修正验证"},
            "pages": [
                {
                    "page_index": 6,
                    "title": "跨班次交接、异常升级与应急补位",
                    "slide_role": "solution_overview",
                    "page_series_type": "collaboration_matrix",
                    "page_goal": "说明谁接谁、异常如何升级以及断点如何补位。",
                    "core_argument": "多岗位巡检依赖交接链路、异常升级和补位机制，而不是静态职责说明。",
                    "content_points": ["跨班次交接", "异常升级", "临时补位", "接力处置"],
                },
                {
                    "page_index": 7,
                    "title": "问题复盘、修复动作与稳定版本收敛",
                    "slide_role": "solution_overview",
                    "page_series_type": "journey_timeline",
                    "page_goal": "说明哪一轮测试暴露了问题、如何修复并收敛到稳定版本。",
                    "core_argument": "研发过程强调问题复盘、质量改进和稳定版本收敛，不只是里程碑推进。",
                    "content_points": ["测试暴露问题", "修复动作", "质量改进", "稳定版本"],
                },
            ],
        }
        profile = resolve_preference_profile({"theme": "formal-tech"})
        deck_blueprint = build_deck_blueprint(outline, profile)
        page_blueprints = build_page_blueprints(outline, profile)

        layout_plan, _ = build_layout_plan(deck_blueprint, page_blueprints, profile)

        self.assertEqual(layout_plan[0].region_plan["narrative_role"], "handoff_chain")
        self.assertTrue(str(layout_plan[0].selected_variant).endswith("chain"))
        self.assertEqual(layout_plan[1].region_plan["narrative_role"], "retrospective_improvement")
        self.assertTrue(str(layout_plan[1].selected_variant).endswith("cards"))

    @patch("app.services.ppt.v4.visual_review_v4.render_formal_v4_page")
    def test_page_review_reports_use_formal_candidate_html_evidence(self, mock_render_formal):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧巡检平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "解决方案升级对比",
                        "slide_role": "solution_overview",
                        "page_series_type": "mapping_bridge",
                        "page_goal": "突出改良前后的差异和升级价值。",
                        "core_argument": "传统人工巡检发现晚、损耗高；改良后通过平台协同实现实时预警和闭环处置。",
                        "content_points": ["改良前问题", "改良后做法", "升级价值"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=933,
            fallback_theme="rapidesign",
        )
        outline["layout_plan"][0]["selection_trace"] = {}
        shadow_payload = build_shadow_render_snapshot_payload(outline)
        mock_render_formal.return_value = (
            '<!DOCTYPE html><html><body>'
            '<main class="slide" data-v4-formal="true"><section class="bridge-layout"></section></main>'
            '</body></html>'
        )

        reports = build_page_review_reports(outline, shadow_payload)

        self.assertFalse(reports[0]["pass_hard_gate"])
        self.assertTrue(any("layout solver 信号" in issue for issue in reports[0]["issues"]))
        self.assertIn("strengthen_rhythm_structure", reports[0]["suggested_actions"])

    def test_deck_review_report_flags_rhythm_homogeneity(self):
        outline = {
            "deck_blueprint": {
                "project_name": "农业物联网平台",
                "page_count": 5,
                "narrative_rhythm": {"page_roles": ["cover", "content", "content", "content", "closing"]},
            },
            "pages": [
                {
                    "page_index": 1,
                    "title": "方案总览一",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "说明统一链路",
                    "core_argument": "围绕采集、分析、服务形成闭环。",
                    "content_points": ["采集", "分析", "服务"],
                },
                {
                    "page_index": 2,
                    "title": "方案总览二",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "说明统一链路",
                    "core_argument": "围绕采集、分析、服务形成闭环。",
                    "content_points": ["采集", "分析", "服务"],
                },
                {
                    "page_index": 3,
                    "title": "方案总览三",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "说明统一链路",
                    "core_argument": "围绕采集、分析、服务形成闭环。",
                    "content_points": ["采集", "分析", "服务"],
                },
                {
                    "page_index": 4,
                    "title": "方案总览四",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "说明统一链路",
                    "core_argument": "围绕采集、分析、服务形成闭环。",
                    "content_points": ["采集", "分析", "服务"],
                },
                {
                    "page_index": 5,
                    "title": "方案总览五",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "说明统一链路",
                    "core_argument": "围绕采集、分析、服务形成闭环。",
                    "content_points": ["采集", "分析", "服务"],
                },
            ],
            "page_blueprints": [
                {"page_index": 1, "title": "方案总览一", "page_series_type": "mapping_bridge"},
                {"page_index": 2, "title": "方案总览二", "page_series_type": "mapping_bridge"},
                {"page_index": 3, "title": "方案总览三", "page_series_type": "mapping_bridge"},
                {"page_index": 4, "title": "方案总览四", "page_series_type": "mapping_bridge"},
                {"page_index": 5, "title": "方案总览五", "page_series_type": "mapping_bridge"},
            ],
            "layout_plan": [
                {
                    "page_index": 1,
                    "family_id": "mapping_bridge.flow_map",
                    "selected_variant": "flow_map_chain",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
                {
                    "page_index": 2,
                    "family_id": "mapping_bridge.flow_map",
                    "selected_variant": "flow_map_chain",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
                {
                    "page_index": 3,
                    "family_id": "mapping_bridge.flow_map",
                    "selected_variant": "flow_map_chain",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
                {
                    "page_index": 4,
                    "family_id": "mapping_bridge.flow_map",
                    "selected_variant": "flow_map_chain",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
                {
                    "page_index": 5,
                    "family_id": "mapping_bridge.flow_map",
                    "selected_variant": "flow_map_chain",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
            ],
        }
        shadow_payload = {
            "coverage": {
                "unsupported_page_indexes": [],
                "supported_page_count": 5,
                "family_groups": [
                    {
                        "family_id": "mapping_bridge.flow_map",
                        "page_indexes": [1, 2, 3, 4, 5],
                    }
                ],
            }
        }
        page_reports = [
            {"page_index": 1, "score": 92, "pass_hard_gate": True, "issues": [], "suggested_actions": []},
            {"page_index": 2, "score": 92, "pass_hard_gate": True, "issues": [], "suggested_actions": []},
            {"page_index": 3, "score": 92, "pass_hard_gate": True, "issues": [], "suggested_actions": []},
            {"page_index": 4, "score": 92, "pass_hard_gate": True, "issues": [], "suggested_actions": []},
            {"page_index": 5, "score": 92, "pass_hard_gate": True, "issues": [], "suggested_actions": []},
        ]

        report = build_deck_review_report(outline, shadow_payload, page_reports)

        self.assertIn("rebalance_focus_strategy", report["suggested_actions"])
        self.assertIn("spread_density_modes", report["suggested_actions"])
        self.assertIn("reduce_structural_homogeneity", report["suggested_actions"])

    def test_opening_rhythm_snapshot_blocks_single_skeleton_sequence(self):
        outline = {
            "deck_blueprint": {"project_name": "农业物联网平台", "page_count": 3},
            "pages": [
                {"page_index": 1, "title": "封面", "page_series_type": "cover_keynote", "page_goal": "封面锚点", "content_points": ["AI识别", "边缘感知"]},
                {"page_index": 2, "title": "目录", "page_series_type": "agenda_navigation", "page_goal": "目录过渡", "content_points": ["项目背景", "方案设计", "价值结果"]},
                {"page_index": 3, "title": "证据页", "page_series_type": "evidence_board", "page_goal": "说明可信度", "content_points": ["政策依据", "落地抓手", "试点成效", "复制价值", "实施逻辑", "价值结果"]},
            ],
            "page_blueprints": [
                {"page_index": 1, "title": "封面", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "目录", "page_series_type": "agenda_navigation"},
                {"page_index": 3, "title": "证据页", "page_series_type": "evidence_board"},
            ],
            "layout_plan": [
                {
                    "page_index": 1,
                    "family_id": "cover_keynote.hero_split",
                    "selected_variant": "hero_split_left",
                    "region_plan": {
                        "focus_strategy": "hero_first",
                        "density_mode": "balanced",
                        "scan_pattern": "single_anchor",
                    },
                },
                {
                    "page_index": 2,
                    "family_id": "agenda_navigation.route_board",
                    "selected_variant": "route_board_horizontal",
                    "region_plan": {
                        "focus_strategy": "diagram_first",
                        "density_mode": "balanced",
                        "scan_pattern": "staged_progression",
                    },
                },
                {
                    "page_index": 3,
                    "family_id": "evidence_board.caption_grid",
                    "selected_variant": "caption_grid_two_up",
                    "region_plan": {
                        "focus_strategy": "evidence_first",
                        "density_mode": "balanced",
                        "scan_pattern": "single_anchor",
                    },
                },
            ],
        }

        snapshot = build_opening_rhythm_snapshot(outline)

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["unique_skeleton_count"], 3)
        self.assertEqual(snapshot["pages"][1]["layout_skeleton"], "route_board_horizontal")
        self.assertEqual(snapshot["pages"][2]["layout_skeleton"], "caption_grid")

    def test_build_opening_rhythm_batch_report_tracks_agenda_and_third_page_coverage(self):
        report = build_opening_rhythm_batch_report(
            [
                {
                    "task_id": 157,
                    "project_name": "智慧农业平台",
                    "status": "pass",
                    "unique_skeleton_count": 3,
                    "unique_focus_count": 2,
                    "pages": [
                        {"page_index": 1, "page_series_type": "cover_keynote", "layout_skeleton": "hero_split", "focus_strategy": "hero_first", "scan_pattern": "single_anchor", "opening_rhythm_signature": "hero_split|hero_first"},
                        {"page_index": 2, "page_series_type": "agenda_navigation", "layout_skeleton": "route_board_vertical", "focus_strategy": "diagram_first", "scan_pattern": "staged_progression", "opening_rhythm_signature": "route_board_vertical|diagram_first"},
                        {"page_index": 3, "page_series_type": "evidence_board", "layout_skeleton": "caption_grid", "focus_strategy": "evidence_first", "scan_pattern": "single_anchor", "opening_rhythm_signature": "caption_grid|evidence_first"},
                    ],
                },
                {
                    "task_id": 156,
                    "project_name": "乡村服务平台",
                    "status": "warning",
                    "unique_skeleton_count": 2,
                    "unique_focus_count": 2,
                    "pages": [
                        {"page_index": 1, "page_series_type": "cover_keynote", "layout_skeleton": "hero_stack", "focus_strategy": "hero_first", "scan_pattern": "grid_scan", "opening_rhythm_signature": "hero_stack|hero_first"},
                        {"page_index": 2, "page_series_type": "agenda_navigation", "layout_skeleton": "route_board_horizontal", "focus_strategy": "diagram_first", "scan_pattern": "staged_progression", "opening_rhythm_signature": "route_board_horizontal|diagram_first"},
                        {"page_index": 3, "page_series_type": "architecture_system", "layout_skeleton": "layer_stack_center", "focus_strategy": "diagram_first", "scan_pattern": "single_anchor", "opening_rhythm_signature": "layer_stack_center|diagram_first"},
                    ],
                },
            ]
        )

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["agenda_route_adoption_rate"], 1.0)
        self.assertEqual(report["third_page_skeleton_coverage_rate"], 1.0)
        self.assertGreaterEqual(report["unique_opening_signature_count"], 4)

    def test_build_front_segment_rhythm_snapshot_tracks_clusters_and_density(self):
        outline = {
            "deck_blueprint": {"project_name": "农业物联网平台", "page_count": 6},
            "pages": [
                {"page_index": 1, "title": "封面", "slide_role": "cover", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "目录", "slide_role": "agenda", "page_series_type": "agenda_navigation"},
                {"page_index": 3, "title": "问题边界", "slide_role": "problem_analysis", "page_series_type": "definition_canvas"},
                {"page_index": 4, "title": "技术架构", "slide_role": "solution_overview", "page_series_type": "architecture_system"},
                {"page_index": 5, "title": "实操验证", "slide_role": "application_value", "page_series_type": "practice_evidence"},
            ],
            "page_blueprints": [
                {"page_index": 1, "title": "封面", "slide_role": "cover", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "目录", "slide_role": "agenda", "page_series_type": "agenda_navigation"},
                {"page_index": 3, "title": "问题边界", "slide_role": "problem_analysis", "page_series_type": "definition_canvas"},
                {"page_index": 4, "title": "技术架构", "slide_role": "solution_overview", "page_series_type": "architecture_system"},
                {"page_index": 5, "title": "实操验证", "slide_role": "application_value", "page_series_type": "practice_evidence"},
            ],
            "layout_plan": [
                {"page_index": 1, "family_id": "cover_keynote.hero_split", "selected_variant": "hero_split_left", "region_plan": {"focus_strategy": "hero_first", "density_mode": "spacious", "scan_pattern": "single_anchor", "narrative_segment": "opening", "narrative_role": "opening_anchor"}},
                {"page_index": 2, "family_id": "agenda_navigation.route_board", "selected_variant": "route_board_horizontal", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "spacious", "scan_pattern": "staged_progression", "narrative_segment": "opening", "narrative_role": "navigation_routing"}},
                {"page_index": 3, "family_id": "definition_canvas.dual_column", "selected_variant": "dual_column_cardrail", "region_plan": {"focus_strategy": "hero_first", "density_mode": "dense", "scan_pattern": "single_anchor", "narrative_segment": "definition", "narrative_role": "problem_framing"}},
                {"page_index": 4, "family_id": "architecture_system.layer_stack", "selected_variant": "layer_stack_center", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "balanced", "scan_pattern": "single_anchor", "narrative_segment": "solution", "narrative_role": "system_explanation"}},
                {"page_index": 5, "family_id": "practice_evidence.timeline_demo", "selected_variant": "timeline_demo_strip", "region_plan": {"focus_strategy": "evidence_first", "density_mode": "balanced", "scan_pattern": "staged_progression", "narrative_segment": "proof_value", "narrative_role": "execution_proof"}},
            ],
        }

        snapshot = build_front_segment_rhythm_snapshot(outline)

        self.assertEqual(snapshot["status"], "pass")
        self.assertEqual(snapshot["unique_density_count"], 3)
        self.assertEqual(snapshot["unique_focus_count"], 3)
        self.assertEqual(snapshot["clusters"][1]["segment"], "definition")
        self.assertEqual(snapshot["clusters"][-1]["segment"], "proof_value")

    def test_build_front_segment_rhythm_batch_report_tracks_density_diversity(self):
        report = build_front_segment_rhythm_batch_report(
            [
                {
                    "task_id": 157,
                    "project_name": "智慧农业平台",
                    "status": "pass",
                    "unique_skeleton_count": 4,
                    "unique_focus_count": 3,
                    "unique_density_count": 2,
                    "unique_scan_count": 2,
                    "role_transition_count": 3,
                    "clusters": [],
                },
                {
                    "task_id": 156,
                    "project_name": "乡村服务平台",
                    "status": "warning",
                    "unique_skeleton_count": 3,
                    "unique_focus_count": 2,
                    "unique_density_count": 1,
                    "unique_scan_count": 1,
                    "role_transition_count": 2,
                    "clusters": [],
                },
            ]
        )

        self.assertEqual(report["status"], "warning")
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["density_diversity_rate"], 0.5)

    def test_build_front_segment_rhythm_snapshot_tracks_solution_cluster_role_drift(self):
        outline = {
            "deck_blueprint": {"project_name": "农业物联网平台", "page_count": 8},
            "pages": [
                {"page_index": 1, "title": "封面", "slide_role": "cover", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "目录", "slide_role": "agenda", "page_series_type": "agenda_navigation"},
                {"page_index": 3, "title": "方案桥接", "slide_role": "solution_overview", "page_series_type": "bridge_story"},
                {"page_index": 4, "title": "岗位交接", "slide_role": "solution_overview", "page_series_type": "collaboration_matrix"},
                {"page_index": 5, "title": "问题复盘", "slide_role": "solution_overview", "page_series_type": "journey_timeline"},
            ],
            "page_blueprints": [
                {"page_index": 1, "title": "封面", "slide_role": "cover", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "目录", "slide_role": "agenda", "page_series_type": "agenda_navigation"},
                {"page_index": 3, "title": "方案桥接", "slide_role": "solution_overview", "page_series_type": "bridge_story"},
                {"page_index": 4, "title": "岗位交接", "slide_role": "solution_overview", "page_series_type": "collaboration_matrix"},
                {"page_index": 5, "title": "问题复盘", "slide_role": "solution_overview", "page_series_type": "journey_timeline"},
            ],
            "layout_plan": [
                {"page_index": 1, "family_id": "cover_keynote.hero_split", "selected_variant": "hero_split_left", "region_plan": {"focus_strategy": "hero_first", "density_mode": "spacious", "scan_pattern": "single_anchor", "narrative_segment": "opening", "narrative_role": "opening_anchor"}},
                {"page_index": 2, "family_id": "agenda_navigation.route_board", "selected_variant": "route_board_horizontal", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "spacious", "scan_pattern": "staged_progression", "narrative_segment": "opening", "narrative_role": "navigation_routing"}},
                {"page_index": 3, "family_id": "bridge_story.loop_story", "selected_variant": "loop_story_split", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "balanced", "scan_pattern": "single_anchor", "narrative_segment": "solution", "narrative_role": "feedback_bridge"}},
                {"page_index": 4, "family_id": "collaboration_matrix.role_map", "selected_variant": "role_map_chain", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "dense", "scan_pattern": "staged_progression", "narrative_segment": "solution", "narrative_role": "handoff_chain"}},
                {"page_index": 5, "family_id": "journey_timeline.milestone_rail", "selected_variant": "milestone_rail_cards", "region_plan": {"focus_strategy": "diagram_first", "density_mode": "balanced", "scan_pattern": "split_compare", "narrative_segment": "solution", "narrative_role": "retrospective_improvement"}},
            ],
        }

        snapshot = build_front_segment_rhythm_snapshot(outline)

        solution_cluster = next(cluster for cluster in snapshot["clusters"] if cluster["segment"] == "solution")
        solution_skeletons = {page["layout_skeleton"] for page in solution_cluster["pages"]}
        self.assertGreaterEqual(len(solution_skeletons), 2)

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_v4_intermediate_snapshot_payload_is_stable(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=202,
            fallback_theme="rapidesign",
        )

        self.service._maybe_save_v4_intermediate_snapshot(
            task_id=202,
            questionnaire_id=303,
            outline_json=outline,
            stage="phase1_outline_ready",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_intermediate")
        self.assertEqual(snapshot["stage"], "phase1_outline_ready")
        payload = snapshot["payload"]
        self.assertEqual(len(payload["page_semantic_fields"]), 3)
        self.assertIn("deck_blueprint", payload)
        self.assertIn("page_blueprints", payload)
        self.assertIn("layout_plan", payload)
        self.assertIn("variant_history", payload)

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_shadow_render_snapshot_is_sidecar_only(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=404,
            fallback_theme="rapidesign",
        )

        rendered_pages = render_shadow_pages(outline)
        self.assertEqual(len(rendered_pages), 3)
        self.assertIn("V4 Shadow Render", rendered_pages[0]["html"])
        self.assertIn("Shadow only", rendered_pages[0]["html"])
        self.assertEqual(rendered_pages[2]["support_status"], "unsupported")
        self.assertEqual(rendered_pages[2]["render_meta"]["delivery_mode"], "sidecar_only")

        self.service._maybe_save_v4_shadow_render_snapshot(
            task_id=404,
            questionnaire_id=505,
            outline_json=outline,
            stage="phase2_shadow_outline_ready",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_shadow_render")
        self.assertEqual(snapshot["stage"], "phase2_shadow_outline_ready")
        payload = snapshot["payload"]
        self.assertEqual(payload["page_count"], 3)
        self.assertEqual(payload["deck_meta"]["project_name"], "智慧实训平台")
        self.assertEqual(payload["variant_history_summary"]["total_pages"], 3)
        self.assertEqual(payload["variant_history_summary"]["unsupported_count"], 1)
        self.assertEqual(payload["coverage"]["unsupported_page_count"], 1)
        self.assertEqual(payload["coverage"]["unsupported_page_indexes"], [3])
        self.assertEqual(payload["pages"][0]["page_index"], 1)
        self.assertEqual(payload["pages"][2]["support_status"], "unsupported")
        self.assertEqual(
            payload["pages"][2]["render_meta"]["selected_reason"],
            "series_not_registered_phase1",
        )
        self.assertIn("html", payload["pages"][0])

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_shadow_render_payload_contains_organization_meta(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=606,
            fallback_theme="rapidesign",
        )

        payload = build_shadow_render_snapshot_payload(outline)

        self.assertEqual(payload["deck_meta"]["style_preset_id"], "tech_premium")
        self.assertEqual(payload["deck_meta"]["requested_theme"], "competition-tech-dark")
        self.assertEqual(payload["deck_meta"]["page_count"], 3)
        self.assertEqual(payload["coverage"]["supported_page_count"], 2)
        self.assertTrue(payload["coverage"]["family_groups"])
        self.assertTrue(payload["coverage"]["series_groups"])
        self.assertTrue(payload["coverage"]["visual_role_groups"])
        self.assertEqual(
            payload["variant_history_summary"]["decision_reasons"]["series_not_registered_phase1"],
            1,
        )
        self.assertEqual(
            payload["pages"][0]["render_meta"]["deck_style_preset_id"],
            "tech_premium",
        )
        self.assertIn("TitleCluster", payload["pages"][0]["render_meta"]["preferred_primitives"])

    def test_v4_formal_page_sequence_tracks_outline_order(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=607,
            fallback_theme="rapidesign",
        )
        enriched_pages = [
            {"page_index": 3, "title": "错序第三页", "content_points": ["先出现第三页"]},
            {"page_index": 1, "title": "错序第一页", "content_points": ["再出现第一页"]},
            {"page_index": 2, "title": "错序第二页", "content_points": ["最后出现第二页"]},
        ]

        sequence = build_v4_formal_page_sequence(outline, enriched_pages)

        self.assertEqual([item["page_index"] for item in sequence], [1, 2, 3])
        self.assertEqual(sequence[1]["title"], "项目定义")
        self.assertEqual(
            sequence[1]["page_meta"]["layout_family_id"],
            outline["layout_plan"][1]["family_id"],
        )
        self.assertEqual(
            sequence[1]["page_meta"]["preferred_primitives"],
            outline["page_blueprints"][1]["preferred_primitives"],
        )

    def test_v4_formal_renderer_is_not_shadow_markup(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=608,
            fallback_theme="rapidesign",
        )

        sequence = build_v4_formal_page_sequence(outline)
        rendered = render_formal_v4_pages(outline, sequence)

        self.assertEqual(len(rendered), 3)
        self.assertIn('data-v4-formal="true"', rendered[0])
        self.assertNotIn("data-v4-shadow", rendered[0])
        self.assertNotIn("V4 Shadow Render", rendered[0])
        self.assertIn("项目定义", rendered[1])
        self.assertIn("data-family-id=", rendered[1])

    def test_render_v4_formal_html_deck_persists_formal_sources(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=609,
            fallback_theme="rapidesign",
        )
        service = PPTService.__new__(PPTService)
        saved_pages = []
        preview_pages = []
        saved_reports = []

        async def fake_sanitize(
            task,
            html,
            page_meta,
            page_index,
            total_pages,
            quality_context,
            auto_repair=False,
            deck_blueprint=None,
        ):
            if page_index == 2:
                return f"{html}\n<!-- repaired -->"
            return html

        service._sanitize_html_for_delivery_async = fake_sanitize
        service._build_quality_context = lambda task_id, pages: {}
        service._save_single_html_page = lambda **kwargs: saved_pages.append(kwargs)
        service._write_preview_html_page = lambda task_id, page_index, html: preview_pages.append((page_index, html))
        service._analyze_html_page_quality = (
            lambda page_index, html, page_meta, quality_context: {
                "status": "pass",
                "score": 96,
                "regeneration_strategy": "keep",
            }
        )
        service._save_page_quality_reports = lambda task_id, items: saved_reports.extend(items)

        pages, page_meta, html_quality_gate = asyncio.run(
            service._render_v4_formal_html_deck(
                task={"id": 609, "project_name": "智慧实训平台"},
                outline_json=outline,
                enriched_pages=None,
            )
        )

        self.assertEqual(len(pages), 3)
        self.assertEqual(len(page_meta), 3)
        self.assertEqual(len(saved_pages), 3)
        self.assertTrue(all(item["source"].startswith("v4_formal_") for item in saved_pages))
        self.assertIn("v4_formal_repaired", [item["source"] for item in saved_pages])
        self.assertEqual([item["page_index"] for item in saved_pages], [1, 2, 3])
        self.assertEqual(len(preview_pages), 3)
        self.assertEqual(len(saved_reports), 3)
        self.assertEqual(html_quality_gate["mode"], "v4_formal")
        self.assertGreaterEqual(html_quality_gate["passed_after_retry"], 1)
        self.assertEqual(len(html_quality_gate["items"]), 3)

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "610",
            "PPT_HTML_V4_ALLOW_SHADOW_READ": "0",
        },
        clear=False,
    )
    def test_v4_candidate_page_map_is_frozen_without_shadow_read_flag(self):
        service = PPTService.__new__(PPTService)
        service._get_latest_snapshot_payload_by_type = lambda task_id, snapshot_type: {
            "pages": [{"page_index": 1, "html": "<html>shadow</html>"}]
        }

        result = service._get_v4_candidate_page_map(610)

        self.assertEqual(result, {})

    def test_round3_reference_builder_compacts_payload(self):
        coordinator = PipelineCoordinator()
        ctx = PipelineContext(
            task_id=301,
            questionnaire_data={
                "team_name": "星火战队",
                "school_name": "上海某职业技术学院",
                "competition_name": "职业院校技能大赛",
            },
            structured_data={
                "project": {
                    "name": "智慧实训平台",
                    "core_problem": "教师很难在多实训任务并行时稳定追踪全过程证据。",
                    "solution": "  ".join(["平台提供统一任务编排、过程记录、评分归因、复盘沉淀。"] * 30),
                    "raw_text": "x" * 2000,
                },
                "stories": {
                    "practice_demo": [
                        {"scene": "课前", "detail": "自动下发任务", "raw_response": "y" * 1000},
                        {"scene": "课中", "detail": "过程留痕", "analysis": "z" * 1000},
                    ]
                },
                "tech": {"architecture": ["采集层", "分析层", "评分层", "看板层", "运维层", "开放层", "更多层"]},
            },
        )

        compact = coordinator._build_round3_original_data_reference(ctx)

        self.assertEqual(compact["competition"]["team_name"], "星火战队")
        self.assertNotIn("raw_text", compact["project"])
        self.assertLess(len(compact["project"]["solution"]), 285)
        self.assertLessEqual(len(compact["tech"]["architecture"]), 6)

    def test_round3_parser_recovers_first_json_object_before_trailing_text(self):
        coordinator = PipelineCoordinator()
        response = (
            '{"pages":[{"page_index":1,"page_number":1,"title":"Recovered","slide_role":"content",'
            '"ppt_text":"核心表达","content_points":["A","B"],"speech_script":"讲稿","visual_suggestion":"看板"}]}'
            "\n以上是第一页，请继续。"
        )

        parsed = coordinator._parse_round3_response(response)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "Recovered")

    def test_round3_parser_recovers_pages_array_from_single_quote_wrapper(self):
        coordinator = PipelineCoordinator()
        response = (
            "本批结果如下：\n"
            "pages: [{'page_index': 1, 'page_number': 1, 'title': 'Single Quote Recovery', "
            "'slide_role': 'content', 'ppt_text': 'Recovered', 'content_points': ['A', 'B'], "
            "'speech_script': '讲稿', 'visual_suggestion': '流程看板'}]\n"
            "请查收。"
        )

        parsed = coordinator._parse_round3_response(response)

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "Single Quote Recovery")

    def test_round3_format_normalize_helper_recovers_nonempty_unparseable_response(self):
        class DummyQwenClient:
            async def chat(self, *args, **kwargs):
                return (
                    '{"pages":[{"page_index":1,"page_number":1,"title":"Normalized Round3",'
                    '"slide_role":"content","ppt_text":"Recovered","content_points":["A","B"],'
                    '"speech_script":"讲稿","visual_suggestion":"证据看板"}]}'
                )

        coordinator = PipelineCoordinator()
        coordinator._qwen_client = DummyQwenClient()

        parsed = asyncio.run(
            coordinator._normalize_round3_unparseable_response(
                original_response="这是一段有内容但格式损坏的 Round 3 返回。",
                batch_pages=[{"page_index": 1, "title": "测试页", "slide_role": "content"}],
                expected_count=1,
                timeout=120,
            )
        )

        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["title"], "Normalized Round3")

    def test_round3_execute_uses_format_normalize_before_compact_repair(self):
        class DummyQwenClient:
            def __init__(self):
                self.calls = []
                self.responses = [
                    '{"pages":[{"page_index":1,,,"page_number":1,"title":"broken"}]}',
                    (
                        '{"pages":[{"page_index":1,"page_number":1,"title":"Normalized Slide",'
                        '"slide_role":"content","ppt_text":"Recovered","content_points":["A","B"],'
                        '"speech_script":"讲稿","visual_suggestion":"图文证据板"}]}'
                    ),
                ]

            async def chat(self, user_message, **kwargs):
                self.calls.append({"user_message": user_message, **kwargs})
                return self.responses.pop(0)

        coordinator = PipelineCoordinator()
        coordinator._qwen_client = DummyQwenClient()
        coordinator._load_prompt_template = AsyncMock(return_value="system prompt")
        coordinator._apply_enriched_design_defaults = lambda page, *args, **kwargs: page

        ctx = PipelineContext(
            task_id=302,
            questionnaire_data={"theme": "competition-tech-dark"},
            structured_data={"project": {"name": "智慧实训平台", "core_problem": "证据追踪难"}},
            narrative_framework={
                "pages": [
                    {
                        "page_index": 1,
                        "title": "测试页",
                        "slide_role": "content",
                        "content_points": ["A", "B"],
                    }
                ]
            },
        )

        pages = asyncio.run(coordinator._execute_round_3(ctx, timeout=300, progress=None))

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["title"], "Normalized Slide")
        self.assertEqual(len(coordinator._qwen_client.calls), 2)
        self.assertIn("格式正规化", coordinator._qwen_client.calls[1]["user_message"])

    def test_round4_parser_recovers_malformed_html_wrapper(self):
        coordinator = PipelineCoordinator()
        response = (
            '{"page_number":1,"html":"<!DOCTYPE html><html lang="zh-CN"><head>'
            '<meta charset="UTF-8"><title>Test</title></head><body>'
            '<div class="title">Recovered</div><p>Body copy for parser recovery.</p>'
            '</body></html>"}'
        )

        parsed = coordinator._parse_round4_response(response, 0)

        self.assertEqual(len(parsed), 1)
        self.assertIn("<html", parsed[0].lower())
        self.assertIn("Recovered", parsed[0])

    def test_round4_parser_recovers_escaped_html_from_generic_fence(self):
        coordinator = PipelineCoordinator()
        response = (
            "```text\n"
            "page_html: \\u003c!DOCTYPE html\\u003e\\u003chtml lang=\\\"zh-CN\\\"\\u003e"
            "\\u003chead\\u003e\\u003cmeta charset=\\\"UTF-8\\\"\\u003e\\u003ctitle\\u003eEscaped"
            "\\u003c/title\\u003e\\u003c/head\\u003e\\u003cbody\\u003e"
            "\\u003cdiv\\u003eEscaped HTML recovered\\u003c/div\\u003e"
            "\\u003c/body\\u003e\\u003c/html\\u003e\n```"
        )

        parsed = coordinator._parse_round4_response(response, 1)

        self.assertEqual(len(parsed), 1)
        self.assertIn("Escaped HTML recovered", parsed[0])

    def test_round4_parser_preserves_plain_cjk_html_without_mojibake(self):
        coordinator = PipelineCoordinator()
        title = "正常中文标题甲乙丙丁"
        body = "这里是正常中文正文，用来验证 parser 不会把原文错误解码成乱码。"
        response = (
            "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"></head>"
            f"<body><h1>{title}</h1><p>{body}</p></body></html>"
        )

        parsed = coordinator._parse_round4_response(response, 0)

        self.assertEqual(len(parsed), 1)
        self.assertIn(title, parsed[0])
        self.assertIn(body, parsed[0])
        self.assertNotIn("æ", parsed[0])

    def test_round4_format_normalize_helper_recovers_nonempty_unparseable_response(self):
        class DummyHTMLClient:
            default_model = "mimo-v2.5-pro"
            html_model = "mimo-v2.5-pro"

            async def chat(self, *args, **kwargs):
                return (
                    "```html\n<!DOCTYPE html><html><head><meta charset=\"UTF-8\"></head>"
                    "<body><div>Normalized Recovery</div></body></html>\n```"
                )

        coordinator = PipelineCoordinator()
        coordinator._html_client = DummyHTMLClient()

        parsed = asyncio.run(
            coordinator._normalize_round4_unparseable_response(
                original_response="这里有一些解释性文字，但不是合法 HTML 输出。",
                expected_count=1,
                batch_start=0,
                timeout=120,
            )
        )

        self.assertEqual(len(parsed), 1)
        self.assertIn("Normalized Recovery", parsed[0])

    def test_round4_execute_uses_format_normalize_before_single_page_rebuild(self):
        class DummyHTMLClient:
            default_model = "mimo-v2.5-pro"
            html_model = "mimo-v2.5-pro"

            def __init__(self):
                self.responses = [
                    "这是一次非空但不可解析的 Round 4 返回，请整理。",
                    "```html\n<!DOCTYPE html><html><head><meta charset=\"UTF-8\"></head>"
                    "<body><div>Recovered Before Fallback</div></body></html>\n```",
                ]

            async def chat(self, *args, **kwargs):
                return self.responses.pop(0)

        coordinator = PipelineCoordinator()
        coordinator._html_client = DummyHTMLClient()
        coordinator._load_prompt_template = AsyncMock(return_value="system prompt")
        coordinator._ensure_key_page_template_contracts = lambda pages, project_name, project_context: pages

        async def passthrough_quality_gate(**kwargs):
            return kwargs["batch_html"]

        coordinator._quality_gate_round4_batch = passthrough_quality_gate

        ctx = PipelineContext(
            task_id=999,
            questionnaire_data={"theme": "competition-tech-dark"},
            structured_data={"project": {"name": "Recovered Deck"}},
            enriched_pages=[
                {
                    "page_index": 1,
                    "title": "Recovered Deck",
                    "slide_role": "cover",
                    "page_series_type": "cover_keynote",
                    "page_visual_role": "keynote_anchor",
                    "page_template_contract": {"role": "cover", "layout": "center_cover"},
                    "layout_slots": [{"slot_id": "slot_01", "block": "项目名称", "slot_role": "keynote_anchor"}],
                    "score_evidence_blocks": [],
                    "ppt_text": "Recovered Deck",
                }
            ],
        )

        html_pages = asyncio.run(coordinator._execute_round_4_html(ctx, timeout=600, progress=None))

        self.assertEqual(len(html_pages), 1)
        self.assertIn("Recovered Before Fallback", html_pages[0])

    def test_quality_report_flags_mojibake_as_fail(self):
        html = (
            "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"></head>"
            "<body><h1>æºæ§åä¸ç©èç½å¤§æ°æ®å¹³å°</h1>"
            "<p>æ¿ç­èæ¯ä¸è¡ä¸éæ±</p></body></html>"
        )

        report = self.service._analyze_html_page_quality(
            1,
            html,
            {"title": "智慧农业物联网大数据平台", "slide_role": "cover"},
            {},
        )

        self.assertEqual(report["status"], "fail")
        self.assertIn("encoding_clean", report["failed_checks"])
        self.assertEqual(report["regeneration_strategy"], "regenerate_html")

    def test_deliverable_gate_rejects_mojibake_html(self):
        html = (
            "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"></head>"
            "<body><div>" + ("æºæ§åä¸" * 30) + "</div></body></html>"
        )

        self.assertFalse(self.service._is_deliverable_html_page(html))

    def test_round4_quality_gate_skips_targeted_retry_for_hard_shell_failures(self):
        coordinator = PipelineCoordinator()
        coordinator._analyze_round4_html_gate = Mock(
            side_effect=[
                {
                    "needs_retry": True,
                    "failed_checks": ["template_shell", "no_fallback_shell"],
                    "visual_metrics": {},
                },
                {
                    "needs_retry": False,
                    "failed_checks": [],
                    "visual_metrics": {},
                },
            ]
        )
        coordinator._retry_round4_page_html = AsyncMock(return_value="<!DOCTYPE html><html><body>should-not-run</body></html>")
        coordinator._recover_round4_page_with_ai = AsyncMock(
            return_value="<!DOCTYPE html><html><body><div>rebuilt</div></body></html>"
        )

        ctx = PipelineContext(task_id=321, questionnaire_data={})
        pages = asyncio.run(
            coordinator._quality_gate_round4_batch(
                ctx=ctx,
                batch_pages=[{"title": "测试页"}],
                batch_html=["<!DOCTYPE html><html><body>bad</body></html>"],
                batch_start=0,
                total_pages=1,
                prompt_template="prompt",
                style_constraints="constraints",
                timeout=120,
                progress=None,
            )
        )

        coordinator._retry_round4_page_html.assert_not_awaited()
        coordinator._recover_round4_page_with_ai.assert_awaited_once()
        self.assertEqual(len(pages), 1)
        self.assertIn("rebuilt", pages[0])

    def test_round4_finalize_callback_persists_formal_page_incrementally(self):
        service = PPTService.__new__(PPTService)
        service._sanitize_html_for_delivery_async = AsyncMock(return_value="<!DOCTYPE html><html><body><div>final</div></body></html>")
        service._save_single_html_page = Mock()
        service._write_preview_html_page = Mock()
        service._analyze_html_page_quality = Mock(
            return_value={"page_index": 1, "status": "pass", "score": 92, "checks": {}, "can_auto_fix": False}
        )
        service._save_page_quality_reports = Mock()
        service._build_quality_context = Mock(return_value={"project_name": "智慧实训平台"})

        callback = service._build_round4_page_finalize_callback(
            task={"id": 123, "questionnaire_id": 456, "project_name": "智慧实训平台"},
            page_meta=[{"title": "封面"}],
        )

        final_html = asyncio.run(
            callback(
                1,
                "<!DOCTYPE html><html><body><div>raw</div></body></html>",
                {"title": "封面"},
                1,
            )
        )

        self.assertIn("final", final_html)
        service._sanitize_html_for_delivery_async.assert_awaited_once()
        service._save_single_html_page.assert_called_once()
        service._write_preview_html_page.assert_called_once()
        service._save_page_quality_reports.assert_called_once()
        kwargs = service._save_single_html_page.call_args.kwargs
        self.assertEqual(kwargs["task_id"], 123)
        self.assertEqual(kwargs["page_index"], 1)
        self.assertEqual(kwargs["source"], "round4_delivery_repaired")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_shadow_review_payload_is_read_only_and_actionable(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=707,
            fallback_theme="rapidesign",
        )

        payload = build_shadow_review_snapshot_payload(outline)

        self.assertEqual(payload["source"], "v4_shadow_review")
        self.assertEqual(payload["delivery_mode"], "sidecar_only")
        self.assertEqual(payload["render_summary"]["page_count"], 3)
        self.assertEqual(payload["render_summary"]["unsupported_page_count"], 1)
        self.assertEqual(len(payload["page_review_reports_v4"]), 3)
        self.assertFalse(payload["deck_review_report_v4"]["pass_hard_gate"])
        self.assertEqual(payload["quality_report_v4_compat"]["overall_status"], "fail")
        self.assertEqual(payload["quality_report_v4_compat"]["total_pages"], 3)
        self.assertEqual(payload["optimization_queue_v4_preview"]["status"], "has_tasks")
        self.assertGreaterEqual(payload["optimization_queue_v4_preview"]["p0_count"], 1)
        self.assertEqual(payload["deliverability_gate_v4_preview"]["status"], "blocked")
        self.assertEqual(payload["deliverability_gate_v4_preview"]["scope"], "v4_shadow_sidecar_only")
        self.assertEqual(payload["roadshow_health_v4_preview"]["source"], "v4_shadow_review")
        self.assertEqual(payload["roadshow_health_v4_preview"]["delivery_mode"], "sidecar_only")
        self.assertIn(payload["roadshow_health_v4_preview"]["readiness"], {"not_ready", "needs_work"})
        self.assertTrue(payload["roadshow_health_v4_preview"]["blockers"])
        self.assertTrue(payload["roadshow_health_v4_preview"]["top_actions"])
        self.assertEqual(payload["shadow_dashboard_v4_preview"]["delivery_mode"], "sidecar_only")
        self.assertEqual(payload["shadow_dashboard_v4_preview"]["cutover_readiness"]["status"], "blocked")
        self.assertEqual(payload["shadow_dashboard_v4_preview"]["phase_status"]["phase4_formal_cutover"], "blocked")
        self.assertTrue(payload["shadow_dashboard_v4_preview"]["preview_contract"]["sidecar_only"])
        self.assertIn(
            "register_layout_families_for_unsupported_pages",
            payload["deck_review_report_v4"]["suggested_actions"],
        )
        self.assertEqual(payload["repair_plan_preview"]["mode"], "preview_only")
        self.assertEqual(payload["repair_plan_preview"]["delivery_mode"], "sidecar_only")
        self.assertTrue(payload["repair_plan_preview"]["blocked_cutover"])
        self.assertGreaterEqual(payload["repair_plan_preview"]["summary"]["high_priority_count"], 1)
        self.assertTrue(payload["repair_plan_preview"]["deck_action_queue"])
        self.assertTrue(payload["quality_report_v4_compat"]["optimization_tasks_preview"])
        self.assertTrue(payload["optimization_queue_v4_preview"]["tasks"])
        self.assertTrue(payload["deliverability_gate_v4_preview"]["blocker_details"])
        self.assertEqual(payload["repair_plan_preview"]["page_actions"][0]["page_index"], 3)
        self.assertIn(
            "register_series_family",
            payload["repair_plan_preview"]["page_actions"][0]["recommended_actions"],
        )

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_sidecar_pipeline_runs_all_three_shadow_snapshots(self):
        outline = self.service._run_v4_sidecar_pipeline(
            task_id=808,
            questionnaire_id=909,
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            fallback_theme="rapidesign",
            phase1_stage="phase1_outline_ready",
            phase2_stage="phase2_shadow_outline_ready",
            phase3_stage="phase3_shadow_outline_ready",
        )

        self.assertIn("deck_blueprint", outline)
        self.assertEqual(
            [snapshot["snapshot_type"] for snapshot in self.saved_snapshots],
            ["v4_intermediate", "v4_shadow_render", "v4_shadow_review", "v4_phase5_extension_pack", "v4_phase5_preflight_pack", "v4_phase5_gate_pack"],
        )
        self.assertEqual(self.saved_snapshots[2]["stage"], "phase3_shadow_outline_ready")
        self.assertIn("repair_plan_preview", self.saved_snapshots[2]["payload"])
        self.assertEqual(self.saved_snapshots[4]["payload"]["source"], "v4_phase5_preflight_pack")
        self.assertEqual(self.saved_snapshots[5]["payload"]["source"], "v4_phase5_gate_pack")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_shadow_review_flags_lexicon_and_iconography_risks(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=909,
            fallback_theme="rapidesign",
        )

        page_blueprints = outline["page_blueprints"]
        layout_plan = outline["layout_plan"]
        page_blueprints[0]["preferred_primitives"] = ["MetricStrip"]
        page_blueprints[1]["core_argument"] = "致力于全面提升预测维护设备检修效率的创新发展平台"
        layout_plan[0]["region_plan"]["body"] = "hero"

        payload = build_shadow_review_snapshot_payload(outline)
        reports = {
            report["page_index"]: report
            for report in payload["page_review_reports_v4"]
        }
        compat_pages = {
            page["page_index"]: page
            for page in payload["quality_report_v4_compat"]["pages"]
        }

        self.assertFalse(reports[1]["pass_hard_gate"])
        self.assertTrue(
            any("主体 region" in issue for issue in reports[1]["issues"])
        )
        self.assertIn("align_primitive_with_layout_region", reports[1]["suggested_actions"])
        self.assertIn("layout_collision", compat_pages[1]["failed_checks"])
        self.assertEqual(compat_pages[1]["regeneration_strategy"], "fix_layout_hierarchy")

        self.assertFalse(reports[2]["pass_hard_gate"])
        self.assertTrue(
            any("空洞词汇" in issue for issue in reports[2]["issues"])
        )
        self.assertTrue(
            any("跨行业术语" in issue for issue in reports[2]["issues"])
        )
        self.assertIn("align_industry_language", reports[2]["suggested_actions"])
        self.assertIn("industry_consistency", compat_pages[2]["failed_checks"])
        self.assertIn("template_page_risk", compat_pages[2]["failed_checks"])
        self.assertEqual(compat_pages[2]["regeneration_strategy"], "align_industry_language")
        self.assertEqual(payload["quality_report_v4_compat"]["industry_issue_count"], 1)
        self.assertEqual(payload["quality_report_v4_compat"]["template_issue_count"], 1)
        self.assertEqual(payload["optimization_queue_v4_preview"]["tasks"][0]["priority"], "P0")
        self.assertGreaterEqual(payload["roadshow_health_v4_preview"]["signals"]["p0_queue_count"], 1)
        self.assertTrue(
            any(
                blocker["type"] == "industry_consistency"
                for blocker in payload["deliverability_gate_v4_preview"]["blocker_details"]
            )
        )

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_deck_review_flags_repeated_titles_and_orders_repairs(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=910,
            fallback_theme="rapidesign",
        )

        outline["page_blueprints"][1]["title"] = outline["page_blueprints"][0]["title"]
        payload = build_shadow_review_snapshot_payload(outline)
        deck_report = payload["deck_review_report_v4"]
        repair_plan = payload["repair_plan_preview"]

        self.assertTrue(
            any("重复页面标题" in issue for issue in deck_report["issues"])
        )
        self.assertIn("differentiate_repeated_titles", deck_report["suggested_actions"])
        self.assertTrue({1, 2}.issubset(set(deck_report["drift_pages"])))
        self.assertEqual(repair_plan["page_actions"][0]["page_index"], 3)
        self.assertEqual(repair_plan["page_actions"][0]["priority"], "high")
        self.assertTrue(
            any(
                item["action"] == "differentiate_repeated_titles"
                for item in repair_plan["deck_action_queue"]
            )
        )
        self.assertTrue(
            any(
                task["task_type"] == "roadshow"
                for task in payload["optimization_queue_v4_preview"]["tasks"]
            )
        )

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_layout_plan_maps_body_region_by_series_and_registers_content_support(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "pages": [
                    {"page_index": 1, "title": "证据页", "slide_role": "content", "page_series_type": "evidence_board", "content": "证据说明"},
                    {"page_index": 2, "title": "协作页", "slide_role": "content", "page_series_type": "collaboration_matrix", "content": "协作说明"},
                    {"page_index": 3, "title": "价值页", "slide_role": "content", "page_series_type": "value_matrix", "content": "价值说明"},
                    {"page_index": 4, "title": "收尾页", "slide_role": "closing", "page_series_type": "closing_board", "content": "收尾说明"},
                    {"page_index": 5, "title": "补充页", "slide_role": "content", "page_series_type": "content_support", "content": "补充说明"},
                ]
            },
            questionnaire_data=self.questionnaire_data,
            task_id=911,
            fallback_theme="rapidesign",
        )

        layout_by_page = {
            item["page_index"]: item
            for item in outline["layout_plan"]
        }
        blueprint_by_page = {
            item["page_index"]: item
            for item in outline["page_blueprints"]
        }

        self.assertEqual(layout_by_page[1]["region_plan"]["body"], "evidence_wall")
        self.assertEqual(layout_by_page[2]["region_plan"]["body"], "role_matrix")
        self.assertEqual(layout_by_page[3]["region_plan"]["body"], "value_matrix")
        self.assertEqual(layout_by_page[4]["region_plan"]["body"], "summary")
        self.assertEqual(layout_by_page[5]["region_plan"]["body"], "support_cards")
        self.assertEqual(layout_by_page[5]["family_id"], "content_support.support_cards")
        self.assertIn("SupportCardStack", blueprint_by_page[5]["preferred_primitives"])
        self.assertEqual(blueprint_by_page[5]["visual_intent"], "supporting_argument")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_deck_review_allows_serial_continuation_titles_within_same_series(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "pages": [
                    {
                        "page_index": 1,
                        "title": "智慧价值平台",
                        "slide_role": "cover",
                        "page_series_type": "cover_keynote",
                        "page_visual_role": "keynote_anchor",
                        "content": "封面说明",
                        "content_points": ["开场锚点"],
                    },
                    {
                        "page_index": 2,
                        "title": "应用价值：综合效益与推广基础",
                        "slide_role": "content",
                        "page_series_type": "value_matrix",
                        "page_visual_role": "value_score_board",
                        "content": "价值说明一",
                        "content_points": ["效益一", "效益二"],
                    },
                    {
                        "page_index": 3,
                        "title": "经济价值：降本增收，效益显著",
                        "slide_role": "content",
                        "page_series_type": "value_matrix",
                        "page_visual_role": "value_score_board",
                        "content": "价值说明二",
                        "content_points": ["经济一", "经济二"],
                    },
                    {
                        "page_index": 4,
                        "title": "应用价值：综合效益与推广基础",
                        "slide_role": "content",
                        "page_series_type": "value_matrix",
                        "page_visual_role": "value_score_board",
                        "content": "价值说明三",
                        "content_points": ["推广一", "推广二"],
                    },
                ]
            },
            questionnaire_data=self.questionnaire_data,
            task_id=912,
            fallback_theme="rapidesign",
        )

        payload = build_shadow_review_snapshot_payload(outline)
        deck_report = payload["deck_review_report_v4"]

        self.assertFalse(
            any("重复页面标题" in issue for issue in deck_report["issues"])
        )
        self.assertNotIn("differentiate_repeated_titles", deck_report["suggested_actions"])
        self.assertEqual(deck_report["drift_pages"], [])
        self.assertTrue(deck_report["pass_hard_gate"])

    def test_shadow_dashboard_can_mark_candidate_cutover(self):
        dashboard = build_v4_shadow_dashboard(
            render_summary={"page_count": 6, "unsupported_page_count": 0},
            deck_review_report_v4={"pass_hard_gate": True, "drift_pages": []},
            repair_plan_preview={"summary": {"high_priority_count": 0}},
            quality_report_v4_compat={
                "overall_status": "pass",
                "average_score": 91.0,
                "issue_count": 0,
                "density_warning_count": 0,
                "scoring_gap_count": 0,
                "practice_issue_count": 0,
                "material_gap_count": 0,
            },
            optimization_queue_v4_preview={"p0_count": 0, "status": "clear", "total_tasks": 0},
            deliverability_gate_v4_preview={"status": "ready", "blockers": [], "blocker_details": []},
            roadshow_health_v4_preview={"readiness": "ready", "overall_score": 90.0, "top_actions": []},
            deck_meta={"project_name": "智慧实训平台"},
        )

        self.assertEqual(dashboard["cutover_readiness"]["status"], "candidate")
        self.assertTrue(dashboard["cutover_readiness"]["cohort_cutover_allowed"])
        self.assertEqual(dashboard["phase_status"]["phase4_formal_cutover"], "candidate")
        self.assertEqual(dashboard["project_name"], "智慧实训平台")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_quality_alignment_preview_surfaces_legacy_v4_drift(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=911,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)
        legacy_quality = {
            **shadow_payload["quality_report_v4_compat"],
            "overall_status": "warning",
            "average_score": 55.0,
            "issue_count": 4,
            "pages": [
                {
                    **page,
                    "status": "warning" if page["page_index"] == 3 else page["status"],
                    "score": 30 if page["page_index"] == 3 else page["score"],
                    "regeneration_strategy": "rewrite_page_argument" if page["page_index"] == 3 else page["regeneration_strategy"],
                    "failed_checks": (
                        sorted(set((page.get("failed_checks") or []) + ["template_page_risk"]))
                        if page["page_index"] == 3
                        else page.get("failed_checks") or []
                    ),
                }
                for page in shadow_payload["quality_report_v4_compat"]["pages"]
            ],
        }

        alignment = build_v4_quality_alignment_preview(
            legacy_quality,
            shadow_payload["quality_report_v4_compat"],
        )

        self.assertEqual(alignment["source"], "v4_shadow_alignment")
        self.assertEqual(alignment["delivery_mode"], "sidecar_only")
        self.assertFalse(alignment["overall_status_match"])
        self.assertEqual(alignment["alignment_status"], "divergent")
        self.assertIn(3, alignment["summary"]["divergent_pages"])
        self.assertTrue(alignment["recommended_actions"])

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_shadow_alignment_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=912,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_shadow_alignment_snapshot(
            task_id=912,
            questionnaire_id=913,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            stage="phase4_shadow_alignment_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_shadow_alignment")
        self.assertEqual(snapshot["stage"], "phase4_shadow_alignment_test")
        self.assertEqual(snapshot["payload"]["alignment_scope"], "legacy_quality_vs_v4_compat")
        self.assertEqual(snapshot["payload"]["alignment_status"], "aligned")

    def test_phase4_readiness_preview_can_mark_candidate(self):
        payload = build_v4_phase4_readiness_preview(
            shadow_dashboard_v4_preview={
                "cutover_readiness": {
                    "status": "candidate",
                    "recommended_actions": ["开始准备小流量 cohort，对比正式链路与 V4 返回差异。"],
                },
                "scorecard": {"p0_queue_count": 0},
            },
            quality_alignment_preview={
                "alignment_status": "aligned",
                "overall_status_match": True,
                "average_score_delta": 0.0,
                "summary": {
                    "aligned_page_count": 6,
                    "divergent_pages": [],
                    "high_risk_divergent_pages": [],
                },
            },
        )

        self.assertEqual(payload["source"], "v4_phase4_readiness")
        self.assertEqual(payload["delivery_mode"], "sidecar_only")
        self.assertEqual(payload["readiness_status"], "candidate")
        self.assertTrue(payload["cohort_cutover_allowed"])
        self.assertEqual(payload["recommended_next_stage"], "phase4_cohort_enablement")
        self.assertTrue(payload["phase4_contract"]["formal_cutover_not_triggered"])

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase4_readiness_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=914,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_phase4_readiness_snapshot(
            task_id=914,
            questionnaire_id=915,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            stage="phase4_readiness_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase4_readiness")
        self.assertEqual(snapshot["stage"], "phase4_readiness_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase4_readiness")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")
        self.assertEqual(snapshot["payload"]["readiness_status"], "blocked")
        self.assertFalse(snapshot["payload"]["cohort_cutover_allowed"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DUAL_RUN": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "916",
            "PPT_HTML_V4_DEFAULT_ON": "0",
        },
        clear=False,
    )
    def test_phase4_cutover_preview_marks_explicit_cohort_candidate(self):
        payload = build_v4_phase4_cutover_preview(
            task_id=916,
            phase4_readiness_preview={
                "readiness_status": "candidate",
                "cohort_cutover_allowed": True,
                "recommended_actions": ["开始准备小流量 cohort，对比正式链路与 V4 返回差异。"],
                "blocking_reasons": [],
            },
        )

        self.assertEqual(payload["source"], "v4_phase4_cutover_preview")
        self.assertEqual(payload["delivery_mode"], "sidecar_only")
        self.assertTrue(payload["formal_cutover_candidate"])
        self.assertEqual(payload["cohort"]["match_reason"], "explicit_task_id")
        self.assertTrue(payload["signals"]["v4_enabled_for_task"])
        self.assertFalse(payload["signals"]["formal_v4_return_active"])
        self.assertTrue(payload["phase4_contract"]["formal_cutover_not_triggered"])
        get_html_pages_plan = next(
            item for item in payload["entrypoint_plan"] if item["entrypoint"] == "get_html_pages"
        )
        self.assertEqual(
            get_html_pages_plan["proposed_route"],
            "eligible_v4_primary_with_v3_fallback",
        )

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_COHORT_PERCENT": "10",
        },
        clear=False,
    )
    def test_phase4_cutover_preview_keeps_v3_outside_cohort(self):
        payload = build_v4_phase4_cutover_preview(
            task_id=987,
            phase4_readiness_preview={
                "readiness_status": "candidate",
                "cohort_cutover_allowed": True,
                "recommended_actions": [],
                "blocking_reasons": [],
            },
        )

        self.assertFalse(payload["formal_cutover_candidate"])
        self.assertFalse(payload["signals"]["in_cohort"])
        self.assertEqual(payload["cohort"]["match_reason"], "out_of_cohort")
        self.assertTrue(
            any("未命中 Phase 4 cohort" in item for item in payload["blocking_reasons"])
        )
        get_html_pages_plan = next(
            item for item in payload["entrypoint_plan"] if item["entrypoint"] == "get_html_pages"
        )
        self.assertEqual(get_html_pages_plan["proposed_route"], "keep_v3_outside_cohort")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase4_cutover_preview_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=917,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_phase4_cutover_preview_snapshot(
            task_id=917,
            questionnaire_id=918,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            stage="phase4_cutover_preview_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase4_cutover_preview")
        self.assertEqual(snapshot["stage"], "phase4_cutover_preview_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase4_cutover_preview")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")
        self.assertTrue(snapshot["payload"]["current_contract"]["formal_delivery_unchanged"])

    def test_phase4_dry_run_preview_can_mark_candidate(self):
        shadow_render_payload = {
            "page_count": 2,
            "coverage": {"unsupported_page_count": 0},
        }
        cutover_preview = {
            "readiness_status": "candidate",
            "formal_cutover_candidate": True,
            "cohort": {"in_cohort": True},
            "entrypoint_plan": [
                {
                    "entrypoint": "get_html_pages",
                    "current_formal_route": "v3_primary",
                    "proposed_route": "eligible_v4_primary_with_v3_fallback",
                    "rollback_route": "force_v3_primary",
                }
            ],
            "recommended_actions": [],
        }

        payload = build_v4_phase4_dry_run_preview(
            cutover_preview=cutover_preview,
            shadow_render_payload=shadow_render_payload,
            formal_html_pages=["<html>a</html>", "<html>b</html>"],
        )

        self.assertEqual(payload["source"], "v4_phase4_dry_run")
        self.assertEqual(payload["delivery_mode"], "sidecar_only")
        self.assertEqual(payload["dry_run_status"], "candidate")
        self.assertTrue(payload["formal_cutover_candidate"])
        self.assertTrue(payload["preflight"]["page_count_parity"])
        self.assertEqual(payload["preflight"]["failed_guard_count"], 0)
        self.assertEqual(
            payload["entrypoint_dry_run"][0]["dry_run_verdict"],
            "ready_for_cutover_implementation",
        )

    def test_phase4_dry_run_preview_holds_v3_when_page_count_mismatches(self):
        shadow_render_payload = {
            "page_count": 3,
            "coverage": {"unsupported_page_count": 0},
        }
        cutover_preview = {
            "readiness_status": "candidate",
            "formal_cutover_candidate": True,
            "cohort": {"in_cohort": True},
            "entrypoint_plan": [
                {
                    "entrypoint": "get_html_pages",
                    "current_formal_route": "v3_primary",
                    "proposed_route": "eligible_v4_primary_with_v3_fallback",
                    "rollback_route": "force_v3_primary",
                }
            ],
            "recommended_actions": [],
        }

        payload = build_v4_phase4_dry_run_preview(
            cutover_preview=cutover_preview,
            shadow_render_payload=shadow_render_payload,
            formal_html_pages=["<html>a</html>", "<html>b</html>"],
        )

        self.assertEqual(payload["dry_run_status"], "hold_v3")
        self.assertFalse(payload["formal_cutover_candidate"])
        self.assertIn("page_count_parity", payload["failed_guards"])
        self.assertEqual(
            payload["entrypoint_dry_run"][0]["dry_run_verdict"],
            "hold_v3_primary",
        )

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase4_dry_run_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=919,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_phase4_dry_run_snapshot(
            task_id=919,
            questionnaire_id=920,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            html_pages=["<html>1</html>", "<html>2</html>", "<html>3</html>"],
            stage="phase4_dry_run_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase4_dry_run")
        self.assertEqual(snapshot["stage"], "phase4_dry_run_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase4_dry_run")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")
        self.assertTrue(snapshot["payload"]["formal_delivery_unchanged"])
        self.assertIn("unsupported_pages_cleared", snapshot["payload"]["failed_guards"])

    def test_phase4_gate_pack_can_mark_advisory_go(self):
        payload = build_v4_phase4_gate_pack(
            alignment_preview={
                "alignment_status": "aligned",
            },
            readiness_preview={
                "readiness_status": "candidate",
                "blocking_reasons": [],
                "recommended_actions": [],
                "signals": {
                    "dashboard_cutover_status": "candidate",
                    "overall_status_match": True,
                },
            },
            cutover_preview={
                "cohort": {"in_cohort": True, "match_reason": "explicit_task_id"},
                "current_contract": {
                    "formal_delivery_unchanged": True,
                    "formal_html_primary": "v3",
                },
                "blocking_reasons": [],
                "recommended_actions": [],
            },
            dry_run_preview={
                "dry_run_status": "candidate",
                "formal_cutover_candidate": True,
                "failed_guards": [],
                "recommended_actions": [],
                "preflight": {
                    "formal_page_count": 6,
                    "shadow_page_count": 6,
                    "page_count_parity": True,
                    "unsupported_page_count": 0,
                    "failed_guard_count": 0,
                },
            },
        )

        self.assertEqual(payload["source"], "v4_phase4_gate_pack")
        self.assertEqual(payload["delivery_mode"], "sidecar_only")
        self.assertEqual(payload["gate_status"], "candidate")
        self.assertEqual(payload["gate_verdict"], "advisory_go")
        self.assertTrue(payload["formal_cutover_candidate"])
        self.assertTrue(all(item["passed"] for item in payload["checklist"] if item["blocking"]))

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase4_gate_pack_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json=self.outline_json,
            questionnaire_data=self.questionnaire_data,
            task_id=921,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_phase4_gate_pack_snapshot(
            task_id=921,
            questionnaire_id=922,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            html_pages=["<html>1</html>", "<html>2</html>", "<html>3</html>"],
            stage="phase4_gate_pack_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase4_gate_pack")
        self.assertEqual(snapshot["stage"], "phase4_gate_pack_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase4_gate_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")
        self.assertIn(snapshot["payload"]["gate_status"], {"blocked", "hold", "observe"})
        self.assertTrue(snapshot["payload"]["phase4_contract"]["formal_cutover_not_triggered"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "923",
        },
        clear=False,
    )
    def test_shadow_sidecars_stay_on_when_formal_v4_return_is_enabled(self):
        self.assertTrue(should_run_shadow_sidecars(923))

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "924",
        },
        clear=False,
    )
    def test_get_v4_repair_candidate_context_reads_candidate_shadow_review(self):
        service = PPTService.__new__(PPTService)

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "candidate",
                    "formal_cutover_candidate": True,
                    "summary": "ready",
                }
            if snapshot_type == "v4_phase6_prep_pack":
                return {"prep_status": "candidate"}
            if snapshot_type == "v4_shadow_review":
                return {
                    "quality_report_v4_compat": {
                        "pages": [
                            {
                                "page_index": 1,
                                "regeneration_strategy": "fix_layout_hierarchy",
                                "repair_route": "structure",
                                "repair_route_reason": "需要重排结构",
                                "preferred_entry": "quality",
                                "failed_checks": ["ppt_layout_contract"],
                            }
                        ]
                    },
                    "repair_plan_preview": {
                        "page_actions": [
                            {
                                "page_index": 1,
                                "repair_route": "structure_rebuild",
                                "recommended_actions": ["rebalance_regions"],
                                "support_status": "supported",
                            }
                        ]
                    },
                }
            return None

        service._get_latest_snapshot_payload_by_type = fake_snapshot
        context = service._get_v4_repair_candidate_context(924, 1)

        self.assertEqual(context["source"], "v4_shadow_review")
        self.assertEqual(context["regeneration_strategy"], "fix_layout_hierarchy")
        self.assertEqual(context["repair_route"], "structure")
        self.assertEqual(context["preferred_entry"], "quality")
        self.assertEqual(context["recommended_actions"], ["rebalance_regions"])
        self.assertFalse(context["advisory_only"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "924",
        },
        clear=False,
    )
    def test_get_v4_repair_candidate_context_marks_diagram_route_as_advisory_only(self):
        service = PPTService.__new__(PPTService)

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "candidate",
                    "formal_cutover_candidate": True,
                    "summary": "ready",
                }
            if snapshot_type == "v4_phase6_prep_pack":
                return {"prep_status": "candidate"}
            if snapshot_type == "v4_shadow_review":
                return {
                    "quality_report_v4_compat": {
                        "pages": [
                            {
                                "page_index": 1,
                                "regeneration_strategy": "rebuild_diagram_layout",
                                "repair_route": "structure",
                                "repair_route_reason": "diagram 需重建",
                                "preferred_entry": "quality",
                                "failed_checks": ["diagram_integrity"],
                            }
                        ]
                    },
                    "repair_plan_preview": {
                        "page_actions": [
                            {
                                "page_index": 1,
                                "repair_route": "structure_rebuild",
                                "recommended_actions": ["fallback_to_flat_svg"],
                                "support_status": "supported",
                            }
                        ]
                    },
                }
            return None

        service._get_latest_snapshot_payload_by_type = fake_snapshot
        context = service._get_v4_repair_candidate_context(924, 1)

        self.assertTrue(context["advisory_only"])
        self.assertEqual(context["advisory_reason"], "diagram_shadow_review_only")
        self.assertEqual(context["regeneration_strategy"], "rebuild_diagram_layout")

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "924",
        },
        clear=False,
    )
    def test_get_v4_repair_candidate_context_requires_phase6_prep_candidate(self):
        service = PPTService.__new__(PPTService)

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "candidate",
                    "formal_cutover_candidate": True,
                    "summary": "ready",
                }
            if snapshot_type == "v4_phase6_prep_pack":
                return {"prep_status": "observe"}
            if snapshot_type == "v4_shadow_review":
                return {
                    "quality_report_v4_compat": {
                        "pages": [
                            {
                                "page_index": 1,
                                "regeneration_strategy": "fix_layout_hierarchy",
                                "repair_route": "structure",
                                "repair_route_reason": "需要重排结构",
                                "preferred_entry": "quality",
                                "failed_checks": ["ppt_layout_contract"],
                            }
                        ]
                    },
                    "repair_plan_preview": {
                        "page_actions": [
                            {
                                "page_index": 1,
                                "repair_route": "structure_rebuild",
                                "recommended_actions": ["rebalance_regions"],
                                "support_status": "supported",
                            }
                        ]
                    },
                }
            return None

        service._get_latest_snapshot_payload_by_type = fake_snapshot
        context = service._get_v4_repair_candidate_context(924, 1)

        self.assertEqual(context, {})

    def test_phase5_second_batch_series_are_registered(self):
        self.assertTrue(get_layout_family_ids("evidence_board"))
        self.assertTrue(get_layout_family_ids("protocol_board"))
        self.assertTrue(get_layout_family_ids("collaboration_matrix"))
        self.assertTrue(get_layout_family_ids("journey_timeline"))
        self.assertTrue(get_layout_family_ids("bridge_story"))
        self.assertTrue(get_layout_family_ids("innovation_compare"))

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_DIAGRAMS_ENABLED": "1",
            "PPT_HTML_V4_DIAGRAM_ISOMETRIC_ENABLED": "1",
        },
        clear=False,
    )
    def test_phase5_diagram_flags_and_shadow_skeletons(self):
        self.assertTrue(should_enable_diagrams())
        self.assertTrue(should_enable_diagram_isometric())

        blueprint = build_diagram_blueprint(
            {
                "page_index": 1,
                "page_series_type": "architecture_system",
                "page_visual_role": "system_diagram",
                "preferred_primitives": ["LayerStack"],
            },
            {"family_id": "architecture_system.layer_stack"},
        )
        self.assertEqual(blueprint["diagram_mode"], "system_landscape")
        self.assertFalse(blueprint["manual_required"])

        rendered = render_diagram_svg(blueprint, "svg_premium")
        review = review_diagram_render(rendered)
        iso = render_isometric_diagram(blueprint)

        self.assertEqual(rendered["status"], "rendered")
        self.assertTrue(review["pass"])
        self.assertEqual(iso["status"], "not_enabled")

    def test_phase5_diagram_blueprint_can_mark_manual_required_for_non_diagram_page(self):
        blueprint = build_diagram_blueprint(
            {
                "page_index": 2,
                "page_series_type": "definition_canvas",
                "page_visual_role": "definition_canvas",
                "preferred_primitives": ["SupportCardStack"],
            },
            {"family_id": "definition_canvas.center_orbit"},
        )
        rendered = render_diagram_svg(blueprint, "svg_flat")
        review = review_diagram_render(rendered)

        self.assertEqual(blueprint["diagram_mode"], "none")
        self.assertTrue(blueprint["manual_required"])
        self.assertEqual(rendered["status"], "manual_required")
        self.assertFalse(review["pass"])

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_phase5_second_batch_series_render_as_supported_in_shadow(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "证据看板",
                        "slide_role": "content",
                        "page_series_type": "evidence_board",
                        "page_visual_role": "evidence_wall",
                        "content_points": ["截图证据", "结果证据", "评分锚点"],
                    },
                    {
                        "page_index": 2,
                        "title": "协作矩阵",
                        "slide_role": "content",
                        "page_series_type": "collaboration_matrix",
                        "page_visual_role": "role_matrix",
                        "content_points": ["角色分工", "交接链路", "补位机制"],
                    },
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=925,
            fallback_theme="rapidesign",
        )

        pages = render_shadow_pages(outline)
        payload = build_shadow_render_snapshot_payload(outline)

        self.assertEqual([page["support_status"] for page in pages], ["supported", "supported"])
        self.assertEqual(payload["coverage"]["unsupported_page_count"], 0)
        self.assertEqual(payload["diagram_summary"]["diagram_page_count"], 0)

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_SAVE_INTERMEDIATE": "1",
            "PPT_HTML_V4_DIAGRAMS_ENABLED": "1",
        },
        clear=False,
    )
    def test_phase5_shadow_render_can_attach_diagram_payload(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "系统架构",
                        "slide_role": "content",
                        "page_series_type": "architecture_system",
                        "page_visual_role": "system_diagram",
                        "content_points": ["感知层", "平台层", "应用层"],
                    },
                    {
                        "page_index": 2,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    },
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=926,
            fallback_theme="rapidesign",
        )

        pages = render_shadow_pages(outline)
        payload = build_shadow_render_snapshot_payload(outline)

        self.assertEqual(payload["diagram_summary"]["diagram_page_count"], 2)
        self.assertEqual(payload["diagram_summary"]["rendered_diagram_count"], 2)
        self.assertEqual(pages[0]["diagram"]["diagram_render"]["status"], "rendered")
        self.assertEqual(pages[1]["diagram"]["diagram_blueprint"]["diagram_mode"], "protocol_flow")
        self.assertEqual(payload["pages"][0]["render_meta"]["diagram_status"], "rendered")
        self.assertIn("<svg", pages[0]["html"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_SAVE_INTERMEDIATE": "1",
            "PPT_HTML_V4_DIAGRAMS_ENABLED": "1",
        },
        clear=False,
    )
    def test_phase5_shadow_review_accepts_rendered_diagram_pages(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "系统架构",
                        "slide_role": "content",
                        "page_series_type": "architecture_system",
                        "page_visual_role": "system_diagram",
                        "content_points": ["感知层", "平台层", "应用层"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=927,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_render_snapshot_payload(outline)
        reports = build_page_review_reports(outline, shadow_payload)

        self.assertEqual(reports[0]["page_index"], 1)
        self.assertFalse(any("diagram" in issue.lower() for issue in reports[0]["issues"]))

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_SAVE_INTERMEDIATE": "1",
            "PPT_HTML_V4_DIAGRAMS_ENABLED": "1",
        },
        clear=False,
    )
    def test_phase5_shadow_review_flags_broken_diagram_payload(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "系统架构",
                        "slide_role": "content",
                        "page_series_type": "architecture_system",
                        "page_visual_role": "system_diagram",
                        "content_points": ["感知层", "平台层", "应用层"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=928,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_render_snapshot_payload(outline)
        shadow_payload["pages"][0]["diagram"]["diagram_render"]["status"] = "manual_required"
        shadow_payload["pages"][0]["diagram"]["diagram_render"]["svg"] = ""
        shadow_payload["pages"][0]["diagram"]["diagram_review"] = {
            "pass": False,
            "status": "warning",
            "issues": ["diagram 缺少 SVG 输出"],
        }

        reports = build_page_review_reports(outline, shadow_payload)

        self.assertTrue(any("diagram" in issue.lower() for issue in reports[0]["issues"]))
        self.assertIn("fallback_to_flat_svg", reports[0]["suggested_actions"])
        self.assertFalse(reports[0]["pass_hard_gate"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_SAVE_INTERMEDIATE": "1",
            "PPT_HTML_V4_DIAGRAMS_ENABLED": "1",
        },
        clear=False,
    )
    def test_phase5_shadow_render_marks_complex_diagram_manual_required_with_fallback(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "复杂系统架构",
                        "slide_role": "content",
                        "page_series_type": "architecture_system",
                        "page_visual_role": "system_diagram",
                        "content_points": [
                            "感知层", "采集层", "传输层", "数据层", "模型层", "服务层",
                            "应用层", "监控层", "评分层", "反馈层", "治理层",
                        ],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=931,
            fallback_theme="rapidesign",
        )

        payload = build_shadow_render_snapshot_payload(outline)
        page = payload["pages"][0]

        self.assertEqual(page["diagram"]["diagram_render"]["status"], "manual_required")
        self.assertEqual(page["diagram"]["diagram_render"]["reason"], "node_budget_exceeded")
        self.assertTrue(page["render_meta"]["diagram_fallback_ready"])
        self.assertIn('data-diagram-fallback="manual_required"', page["html"])

    def test_phase5_quality_bridge_maps_diagram_risk(self):
        outline = {
            "page_blueprints": [
                {
                    "page_index": 1,
                    "title": "系统架构",
                    "page_role": "content",
                    "page_type": "content_page",
                    "page_series_type": "architecture_system",
                    "page_visual_role": "system_diagram",
                    "contract_id": "arch_v1",
                }
            ]
        }
        shadow_review_payload = {
            "page_review_reports_v4": [
                {
                    "page_index": 1,
                    "score": 68,
                    "pass_hard_gate": False,
                    "issues": ["diagram 缺少 SVG 输出"],
                    "suggested_actions": ["fallback_to_flat_svg"],
                }
            ],
            "repair_plan_preview": {
                "page_actions": [
                    {
                        "page_index": 1,
                        "repair_route": "structure_rebuild",
                        "support_status": "supported",
                    }
                ]
            },
        }

        payload = build_v4_compat_quality_report(outline, shadow_review_payload)
        page = payload["pages"][0]

        self.assertEqual(payload["diagram_risk_count"], 1)
        self.assertIn("diagram_integrity", page["failed_checks"])
        self.assertEqual(page["regeneration_strategy"], "rebuild_diagram_layout")
        self.assertEqual(page["repair_route"], "structure")

    def test_phase5_extension_pack_can_mark_candidate(self):
        payload = build_v4_phase5_extension_pack(
            shadow_render_payload={
                "pages": [
                    {"page_index": 1, "page_series_type": "evidence_board", "support_status": "supported"},
                    {"page_index": 2, "page_series_type": "protocol_board", "support_status": "supported"},
                ],
                "diagram_summary": {
                    "diagram_page_count": 2,
                    "rendered_diagram_count": 2,
                    "warning_diagram_count": 0,
                },
            },
            shadow_review_payload={
                "quality_report_v4_compat": {
                    "diagram_risk_count": 0,
                    "overall_status": "pass",
                },
                "deck_review_report_v4": {
                    "pass_hard_gate": True,
                },
                "repair_plan_preview": {
                    "summary": {
                        "high_priority_count": 0,
                    }
                },
                "shadow_dashboard_v4_preview": {
                    "cutover_readiness": "candidate",
                }
            },
        )

        self.assertEqual(payload["source"], "v4_phase5_extension_pack")
        self.assertEqual(payload["extension_status"], "candidate")
        self.assertEqual(payload["second_batch_summary"]["supported_count"], 2)
        self.assertEqual(payload["diagram_summary"]["rendered_count"], 2)
        self.assertEqual(payload["shadow_quality_guards"]["quality_status"], "pass")

    def test_phase5_extension_pack_blocks_when_shadow_quality_is_not_green(self):
        payload = build_v4_phase5_extension_pack(
            shadow_render_payload={
                "pages": [
                    {"page_index": 1, "page_series_type": "evidence_board", "support_status": "supported"},
                ],
                "diagram_summary": {
                    "diagram_page_count": 1,
                    "rendered_diagram_count": 1,
                    "warning_diagram_count": 0,
                },
            },
            shadow_review_payload={
                "quality_report_v4_compat": {
                    "diagram_risk_count": 0,
                    "overall_status": "fail",
                },
                "deck_review_report_v4": {
                    "pass_hard_gate": False,
                },
                "repair_plan_preview": {
                    "summary": {
                        "high_priority_count": 2,
                    }
                },
                "shadow_dashboard_v4_preview": {
                    "cutover_readiness": "blocked",
                },
            },
        )

        self.assertEqual(payload["extension_status"], "blocked")
        self.assertIn("整体 shadow quality 仍未达到 pass", payload["blocking_reasons"])
        self.assertIn("deck-level consistency 仍未通过 hard gate", payload["blocking_reasons"])

    def test_phase5_preflight_pack_can_mark_candidate(self):
        payload = build_v4_phase5_preflight_pack(
            shadow_render_payload={
                "pages": [
                    {
                        "page_index": 1,
                        "page_series_type": "architecture_system",
                        "diagram": {
                            "diagram_render": {
                                "status": "rendered",
                                "profile_id": "svg_premium",
                                "svg": "<svg viewBox='0 0 640 360'><text>arch</text></svg>",
                            },
                            "diagram_review": {"pass": True, "status": "pass", "issues": []},
                            "diagram_blueprint": {"diagram_mode": "system_landscape"},
                        },
                        "render_meta": {
                            "diagram_fallback_ready": False,
                            "diagram_profile_id": "svg_premium",
                        },
                    }
                ],
            },
            shadow_review_payload={},
            extension_pack={
                "extension_status": "candidate",
                "blocking_reasons": [],
                "recommended_actions": [],
                "second_batch_summary": {"page_count": 1},
            },
        )

        self.assertEqual(payload["preflight_status"], "candidate")
        self.assertEqual(payload["diagram_readability"]["premium_architecture_pass_count"], 1)
        self.assertEqual(payload["manual_fallback"]["status"], "not_applicable")

    def test_phase5_preflight_pack_blocks_when_manual_fallback_is_missing(self):
        payload = build_v4_phase5_preflight_pack(
            shadow_render_payload={
                "pages": [
                    {
                        "page_index": 2,
                        "page_series_type": "protocol_board",
                        "diagram": {
                            "diagram_render": {
                                "status": "manual_required",
                                "profile_id": "svg_flat",
                                "svg": "",
                            },
                            "diagram_review": {"pass": False, "status": "warning", "issues": ["diagram 缺少 SVG 输出"]},
                            "diagram_blueprint": {"diagram_mode": "protocol_flow"},
                        },
                        "render_meta": {
                            "diagram_fallback_ready": False,
                            "diagram_profile_id": "svg_flat",
                        },
                    }
                ],
            },
            shadow_review_payload={},
            extension_pack={
                "extension_status": "observe",
                "blocking_reasons": [],
                "recommended_actions": [],
                "second_batch_summary": {"page_count": 1},
            },
        )

        self.assertEqual(payload["preflight_status"], "blocked")
        self.assertEqual(payload["manual_fallback"]["status"], "at_risk")
        self.assertIn("manual_required 降级路径仍不完整", payload["blocking_reasons"])

    def test_phase5_gate_pack_can_mark_candidate(self):
        payload = build_v4_phase5_gate_pack(
            extension_pack={
                "extension_status": "candidate",
                "second_batch_summary": {"page_count": 2, "unsupported_count": 0},
                "diagram_summary": {"page_count": 1},
                "shadow_quality_guards": {
                    "quality_status": "pass",
                    "deck_pass_hard_gate": True,
                    "high_priority_count": 0,
                    "dashboard_cutover_status": "candidate",
                },
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
            preflight_pack={
                "preflight_status": "candidate",
                "diagram_readability": {
                    "premium_architecture_count": 1,
                    "premium_architecture_pass_count": 1,
                    "unreadable_count": 0,
                },
                "manual_fallback": {
                    "manual_required_count": 0,
                    "at_risk_page_indexes": [],
                },
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
        )

        self.assertEqual(payload["gate_status"], "candidate")
        self.assertEqual(payload["gate_verdict"], "advisory_go")
        self.assertEqual(payload["recommended_next_stage"], "phase6_default_on_prep")
        self.assertTrue(payload["phase5_contract"]["sidecar_only"])

    def test_phase5_gate_pack_blocks_when_preflight_is_blocked(self):
        payload = build_v4_phase5_gate_pack(
            extension_pack={
                "extension_status": "candidate",
                "second_batch_summary": {"page_count": 1, "unsupported_count": 0},
                "diagram_summary": {"page_count": 1},
                "shadow_quality_guards": {
                    "quality_status": "pass",
                    "deck_pass_hard_gate": True,
                    "high_priority_count": 0,
                    "dashboard_cutover_status": "candidate",
                },
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
            preflight_pack={
                "preflight_status": "blocked",
                "diagram_readability": {
                    "premium_architecture_count": 1,
                    "premium_architecture_pass_count": 0,
                    "unreadable_count": 1,
                },
                "manual_fallback": {
                    "manual_required_count": 1,
                    "at_risk_page_indexes": [2],
                },
                "blocking_reasons": ["manual_required 降级路径仍不完整"],
                "recommended_actions": ["先补齐 manual_required 页的可读 fallback，再允许继续 Phase 5 观察。"],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
        )

        self.assertEqual(payload["gate_status"], "blocked")
        self.assertEqual(payload["gate_verdict"], "advisory_block")
        self.assertIn("manual_required 降级路径仍不完整", payload["blocking_reasons"])

    def test_phase6_prep_pack_can_mark_candidate(self):
        payload = build_v4_phase6_prep_pack(
            phase4_gate_pack={
                "gate_status": "candidate",
                "recommended_next_stage": "phase4_cohort_enablement",
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase4_contract": {"formal_cutover_not_triggered": True},
            },
            phase5_gate_pack={
                "gate_status": "candidate",
                "recommended_next_stage": "phase6_default_on_prep",
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
        )

        self.assertEqual(payload["prep_status"], "candidate")
        self.assertEqual(payload["prep_verdict"], "advisory_go")
        self.assertEqual(payload["recommended_next_stage"], "batch_f_default_on_execution")
        self.assertTrue(payload["phase6_contract"]["sidecar_only"])

    def test_phase6_prep_pack_blocks_when_phase5_is_blocked(self):
        payload = build_v4_phase6_prep_pack(
            phase4_gate_pack={
                "gate_status": "candidate",
                "recommended_next_stage": "phase4_cohort_enablement",
                "blocking_reasons": [],
                "recommended_actions": [],
                "phase4_contract": {"formal_cutover_not_triggered": True},
            },
            phase5_gate_pack={
                "gate_status": "blocked",
                "recommended_next_stage": "phase5_shadow_hardening",
                "blocking_reasons": ["manual_required 降级路径仍不完整"],
                "recommended_actions": ["先补齐 manual_required 页的可读 fallback。"],
                "phase5_contract": {"formal_phase5_cutover_not_triggered": True},
            },
        )

        self.assertEqual(payload["prep_status"], "blocked")
        self.assertEqual(payload["prep_verdict"], "advisory_block")
        self.assertIn("manual_required 降级路径仍不完整", payload["blocking_reasons"])

    def test_phase7_task_observation_tracks_retirement_signals(self):
        payload = build_v4_phase7_task_observation(
            task_id=940,
            phase6_prep_pack={"prep_status": "candidate"},
            shadow_review_payload={
                "page_review_reports_v4": [
                    {"page_index": 1, "score": 90, "pass_hard_gate": True},
                    {"page_index": 2, "score": 86, "pass_hard_gate": True},
                    {"page_index": 3, "score": 88, "pass_hard_gate": True},
                ],
                "deck_review_report_v4": {
                    "score": 87,
                    "pass_hard_gate": True,
                },
                "quality_report_v4_compat": {
                    "overall_status": "pass",
                    "total_pages": 3,
                    "template_issue_count": 0,
                },
                "deliverability_gate_v4_preview": {"status": "ready"},
                "roadshow_health_v4_preview": {"readiness": "ready", "overall_score": 90.0},
                "shadow_dashboard_v4_preview": {
                    "cutover_readiness": {"status": "candidate"},
                },
            },
            delivery_auto_repair_count=0,
        )

        self.assertTrue(payload["task_passes_retirement_contract"])
        self.assertEqual(payload["page_critic_median"], 88.0)
        self.assertEqual(payload["deck_critic_score"], 87.0)
        self.assertEqual(payload["delivery_auto_repair_ratio"], 0.0)
        self.assertTrue(payload["signals"]["roadshow_green"])

    def test_phase7_retirement_pack_can_mark_candidate_after_streak_target(self):
        current_task = {
            "task_id": 950,
            "phase6_prep_status": "candidate",
            "task_passes_retirement_contract": True,
            "page_critic_median": 89.0,
            "deck_critic_score": 88.0,
            "delivery_auto_repair_count": 0,
            "delivery_auto_repair_ratio": 0.0,
            "template_shell_leak_count": 0,
            "deliverability_status": "ready",
            "roadshow_readiness": "ready",
            "signals": {
                "phase6_green": True,
                "page_critic_green": True,
                "deck_critic_green": True,
                "auto_repair_green": True,
                "template_shell_green": True,
                "deliverability_green": True,
                "roadshow_green": True,
            },
        }
        recent = [
            {
                **current_task,
                "task_id": 949 - index,
            }
            for index in range(29)
        ]

        payload = build_v4_phase7_retirement_pack(
            current_task_observation=current_task,
            recent_task_observations=recent,
        )

        self.assertEqual(payload["retirement_status"], "candidate")
        self.assertEqual(payload["retirement_verdict"], "advisory_go")
        self.assertEqual(payload["window_signals"]["consecutive_green_tasks"], 30)
        self.assertEqual(payload["recommended_next_stage"], "batch_small_v3_retirement_cleanup")

    def test_phase7_retirement_pack_blocks_when_current_task_is_not_green(self):
        current_task = {
            "task_id": 951,
            "phase6_prep_status": "candidate",
            "task_passes_retirement_contract": False,
            "page_critic_median": 88.0,
            "deck_critic_score": 87.0,
            "delivery_auto_repair_count": 0,
            "delivery_auto_repair_ratio": 0.0,
            "template_shell_leak_count": 1,
            "deliverability_status": "ready",
            "roadshow_readiness": "ready",
            "signals": {
                "phase6_green": True,
                "page_critic_green": True,
                "deck_critic_green": True,
                "auto_repair_green": True,
                "template_shell_green": False,
                "deliverability_green": True,
                "roadshow_green": True,
            },
        }

        payload = build_v4_phase7_retirement_pack(
            current_task_observation=current_task,
            recent_task_observations=[],
        )

        self.assertEqual(payload["retirement_status"], "blocked")
        self.assertEqual(payload["retirement_verdict"], "advisory_block")
        self.assertIn("template shell", "".join(payload["blocking_reasons"]))

    def test_v3_retirement_cleanup_plan_unlocks_batch1_only_when_retirement_is_candidate(self):
        payload = build_v3_retirement_cleanup_plan(
            retirement_pack={
                "retirement_status": "candidate",
                "blocking_reasons": [],
                "recommended_actions": [],
                "current_task": {
                    "template_shell_leak_count": 0,
                    "delivery_auto_repair_ratio": 0.0,
                },
                "window_signals": {
                    "consecutive_green_tasks": 30,
                    "streak_target": 30,
                },
            },
            inventory={
                "batch_count": 2,
                "target_count": 4,
                "match_count": 17,
                "batches": [
                    {
                        "batch_id": "batch1_remove_legacy_fallback_families",
                        "label": "第一批删除对象",
                        "target_count": 2,
                        "match_count": 15,
                        "targets": [{"target_id": "a", "match_count": 14}, {"target_id": "b", "match_count": 1}],
                    },
                    {
                        "batch_id": "batch2_shrink_compat_layers",
                        "label": "第二批收缩对象",
                        "target_count": 2,
                        "match_count": 2,
                        "targets": [{"target_id": "c", "match_count": 1}, {"target_id": "d", "match_count": 1}],
                    },
                ],
            },
        )

        self.assertEqual(payload["cleanup_status"], "candidate")
        self.assertEqual(payload["cleanup_batches"][0]["status"], "candidate")
        self.assertTrue(payload["cleanup_batches"][0]["allowed_now"])
        self.assertEqual(payload["cleanup_batches"][1]["status"], "observe")
        self.assertFalse(payload["cleanup_batches"][1]["allowed_now"])
        self.assertTrue(payload["cleanup_contract"]["no_delete_triggered"])

    def test_v3_retirement_cleanup_plan_stays_blocked_when_retirement_gate_is_not_green(self):
        payload = build_v3_retirement_cleanup_plan(
            retirement_pack={
                "retirement_status": "blocked",
                "blocking_reasons": ["当前任务尚未稳定进入 Phase 6 default-on 绿色区间。"],
                "recommended_actions": [],
                "current_task": {
                    "template_shell_leak_count": 1,
                    "delivery_auto_repair_ratio": 0.12,
                },
                "window_signals": {
                    "consecutive_green_tasks": 4,
                    "streak_target": 30,
                },
            },
            inventory={
                "batch_count": 1,
                "target_count": 1,
                "match_count": 9,
                "batches": [
                    {
                        "batch_id": "batch1_remove_legacy_fallback_families",
                        "label": "第一批删除对象",
                        "target_count": 1,
                        "match_count": 9,
                        "targets": [{"target_id": "a", "match_count": 9}],
                    }
                ],
            },
        )

        self.assertEqual(payload["cleanup_status"], "blocked")
        self.assertEqual(payload["recommended_next_stage"], "keep_v3_compatibility_and_harden_v4")
        self.assertFalse(payload["cleanup_batches"][0]["allowed_now"])
        self.assertIn("Phase 6", "".join(payload["blocking_reasons"]))

    def test_v3_retirement_cleanup_plan_blocks_batch1_when_live_references_remain(self):
        payload = build_v3_retirement_cleanup_plan(
            retirement_pack={
                "retirement_status": "candidate",
                "blocking_reasons": [],
                "recommended_actions": [],
                "current_task": {
                    "template_shell_leak_count": 0,
                    "delivery_auto_repair_ratio": 0.0,
                },
                "window_signals": {
                    "consecutive_green_tasks": 30,
                    "streak_target": 30,
                },
            },
            inventory={
                "batch_count": 1,
                "target_count": 1,
                "match_count": 9,
                "batches": [
                    {
                        "batch_id": "batch1_remove_legacy_fallback_families",
                        "label": "第一批删除对象",
                        "target_count": 1,
                        "match_count": 9,
                        "targets": [
                            {
                                "target_id": "a",
                                "match_count": 9,
                                "cleanup_readiness": "blocked_by_live_refs",
                                "external_reference_count": 3,
                            }
                        ],
                    }
                ],
            },
        )

        self.assertEqual(payload["cleanup_status"], "candidate")
        self.assertEqual(payload["cleanup_batches"][0]["status"], "blocked")
        self.assertFalse(payload["cleanup_batches"][0]["allowed_now"])
        self.assertEqual(payload["recommended_next_stage"], "clear_live_references_before_batch1_cleanup")
        self.assertIn("live 引用", "".join(payload["blocking_reasons"]))

    def test_pipeline_fallback_family_inventory_is_absent_after_cleanup(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "services", "ppt")
        )
        inventory = scan_v3_retirement_inventory(base_dir)

        pipeline_target = None
        series_builder_target = None
        contract_slot_target = None
        for batch in inventory.get("batches") or []:
            if batch.get("batch_id") != "batch1_remove_legacy_fallback_families":
                continue
            for target in batch.get("targets") or []:
                if target.get("target_id") == "pipeline_fallback_family":
                    pipeline_target = target
                if target.get("target_id") == "series_builder_family":
                    series_builder_target = target
                if target.get("target_id") == "render_contract_slots":
                    contract_slot_target = target
            if pipeline_target and series_builder_target and contract_slot_target:
                break

        self.assertIsNotNone(pipeline_target)
        self.assertEqual(pipeline_target["cleanup_readiness"], "already_absent")
        self.assertEqual(pipeline_target["match_count"], 0)
        self.assertEqual(pipeline_target["same_file_reference_count"], 0)
        self.assertEqual(pipeline_target["external_reference_count"], 0)
        self.assertIsNotNone(series_builder_target)
        self.assertEqual(series_builder_target["cleanup_readiness"], "already_absent")
        self.assertEqual(series_builder_target["match_count"], 0)
        self.assertEqual(series_builder_target["same_file_reference_count"], 0)
        self.assertEqual(series_builder_target["external_reference_count"], 0)
        self.assertIsNotNone(contract_slot_target)
        self.assertEqual(contract_slot_target["cleanup_readiness"], "already_absent")
        self.assertEqual(contract_slot_target["match_count"], 0)

    def test_html_generator_compat_inventory_is_absent_after_cleanup(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "services", "ppt")
        )
        inventory = scan_v3_retirement_inventory(base_dir)

        compat_target = None
        for batch in inventory.get("batches") or []:
            if batch.get("batch_id") != "batch2_shrink_compat_layers":
                continue
            for target in batch.get("targets") or []:
                if target.get("target_id") == "html_generator_compat_methods":
                    compat_target = target
                    break
            if compat_target:
                break

        self.assertIsNotNone(compat_target)
        self.assertEqual(compat_target["cleanup_readiness"], "already_absent")
        self.assertEqual(compat_target["match_count"], 0)
        self.assertEqual(compat_target["same_file_reference_count"], 0)
        self.assertEqual(compat_target["external_reference_count"], 0)

    def test_page_contract_template_field_inventory_is_absent_after_cleanup(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "services", "ppt")
        )
        inventory = scan_v3_retirement_inventory(base_dir)

        template_target = None
        for batch in inventory.get("batches") or []:
            if batch.get("batch_id") != "batch2_shrink_compat_layers":
                continue
            for target in batch.get("targets") or []:
                if target.get("target_id") == "page_contract_template_fields":
                    template_target = target
                    break
            if template_target:
                break

        self.assertIsNotNone(template_target)
        self.assertEqual(template_target["cleanup_readiness"], "already_absent")
        self.assertEqual(template_target["match_count"], 0)
        self.assertEqual(template_target["external_reference_count"], 0)

    def test_round4_payload_contract_context_omits_template_id(self):
        coordinator = PipelineCoordinator.__new__(PipelineCoordinator)
        page = {
            "title": "项目定义",
            "page_template_contract": {
                "contract_id": "project_definition_canvas_v1",
                "template_id": "p1_project_definition_canvas",
                "layout": "definition_center_with_four_support_cards",
                "required_blocks": ["一句话定义"],
                "forbidden_blocks": ["只有项目名无定义"],
                "visual_rules": ["禁止空旷"],
                "page_series_type": "definition_canvas",
                "page_visual_role": "definition_canvas",
            },
            "layout_slots": [{"slot_id": "main", "block": "一句话定义", "slot_role": "definition_canvas", "content_hint": "讲清项目定义"}],
        }

        payload = coordinator._prepare_round4_page_payload(page)

        self.assertNotIn("template_id", payload["page_template_contract"])
        self.assertNotIn("template_id", payload["internal_generation_rules"]["forbidden_visible_tokens"])

    def test_page_design_context_omits_template_id(self):
        context = self.service._extract_page_design_context(
            {
                "contract_id": "project_definition_canvas_v1",
                "page_type": "project_definition_page",
                "act_phase": "act_1_opening_alignment",
                "transition_role": "definition_anchor",
                "page_series_type": "definition_canvas",
                "page_visual_role": "definition_canvas",
                "page_template_contract": {
                    "template_id": "p1_project_definition_canvas",
                    "layout": "definition_center_with_four_support_cards",
                    "required_blocks": ["一句话定义"],
                    "forbidden_blocks": ["只有项目名无定义"],
                    "visual_rules": ["禁止空旷"],
                },
            }
        )

        self.assertNotIn("template_id", context["page_template_contract"])

    def test_visual_judge_prompt_omits_template_id(self):
        judge = PPTVisionJudgeService.__new__(PPTVisionJudgeService)
        prompt = judge._build_visual_judge_prompt(
            page_meta={
                "title": "项目定义",
                "contract_id": "project_definition_canvas_v1",
                "page_type": "project_definition_page",
                "act_phase": "act_1_opening_alignment",
                "transition_role": "definition_anchor",
                "page_series_type": "definition_canvas",
                "page_visual_role": "definition_canvas",
                "page_template_contract": {
                    "template_id": "p1_project_definition_canvas",
                    "layout": "definition_center_with_four_support_cards",
                    "required_blocks": ["一句话定义"],
                    "forbidden_blocks": ["只有项目名无定义"],
                    "visual_rules": ["禁止空旷"],
                },
            },
            page_index=2,
            total_pages=12,
            quality_report={},
        )

        self.assertNotIn('"template_id"', prompt)

    def test_package_root_no_longer_exports_legacy_layout_engine(self):
        self.assertFalse(hasattr(ppt_package, "LayoutRuleEngine"))
        self.assertFalse(hasattr(ppt_package, "ContentLengthAdapter"))
        self.assertFalse(hasattr(OutlineGenerator, "_build_legacy_layout_rule_engine"))
        self.assertTrue(hasattr(OutlineGenerator, "_build_outline_layout_planner"))

    def test_formal_outline_layout_planner_preserves_fixed_page_contract(self):
        planner = OutlineLayoutPlanner()
        processed_pages = planner.process(
            [
                {"semantic": "BACKGROUND_DATA", "title": "行业背景", "key_points": ["规模", "增速"]},
                {"semantic": "PAIN_POINTS", "title": "核心痛点", "key_points": ["痛点1", "痛点2", "痛点3"]},
            ]
        )

        self.assertEqual(processed_pages[0]["semantic"], "COVER")
        self.assertEqual(processed_pages[1]["semantic"], "TOC")
        self.assertEqual(processed_pages[-1]["semantic"], "ENDING")
        self.assertGreaterEqual(len(processed_pages), 4)

    def test_legacy_layout_rules_gate_defaults_to_legacy_on(self):
        semantic_pages = [
            {"semantic": "BACKGROUND_DATA", "title": "行业背景"},
            {"semantic": "PAIN_POINTS", "title": "核心痛点"},
        ]

        gate = build_legacy_layout_rules_gate(
            enhanced_data={"task_id": 9301, "domain": "education"},
            semantic_pages=semantic_pages,
            theme="competition-tech-dark",
        )
        usage = build_legacy_layout_rules_usage(gate, semantic_pages, list(semantic_pages))

        self.assertEqual(gate["mode"], "legacy_on")
        self.assertFalse(gate["should_use_legacy_engine"])
        self.assertTrue(gate["should_use_formal_planner"])
        self.assertEqual(gate["deprecation_state"], "legacy_engine_retired")
        self.assertFalse(usage["used_legacy_layout_rules"])
        self.assertTrue(usage["used_formal_outline_layout_planner"])
        self.assertEqual(usage["engine_path"], "outline_layout_planner.OutlineLayoutPlanner")

    @patch.dict(os.environ, {"PPT_HTML_V4_LAYOUT_RULES_LEGACY_MODE": "warn_only"}, clear=False)
    def test_legacy_layout_rules_gate_warn_only_marks_deprecation_state(self):
        gate = build_legacy_layout_rules_gate(
            enhanced_data={"task_id": 9305, "domain": "education"},
            semantic_pages=[{"semantic": "BACKGROUND_DATA", "title": "行业背景"}],
            theme="competition-tech-dark",
        )

        self.assertEqual(gate["mode"], "warn_only")
        self.assertFalse(gate["should_use_legacy_engine"])
        self.assertTrue(gate["should_use_formal_planner"])
        self.assertEqual(gate["gate_reason"], "formal_planner_warn_only")
        self.assertEqual(gate["deprecation_state"], "legacy_engine_retired")

    @patch.dict(os.environ, {"PPT_HTML_V4_LAYOUT_RULES_LEGACY_MODE": "disabled"}, clear=False)
    def test_legacy_layout_rules_gate_can_bypass_to_minimal_outline(self):
        generator = OutlineGenerator.__new__(OutlineGenerator)
        semantic_pages = [
            {"semantic": "BACKGROUND_DATA", "title": "行业背景"},
            {"semantic": "PAIN_POINTS", "title": "核心痛点"},
        ]

        gate = build_legacy_layout_rules_gate(
            enhanced_data={"task_id": 9302, "domain": "education"},
            semantic_pages=semantic_pages,
            theme="competition-tech-dark",
        )
        processed_pages = generator._build_outline_pages_without_layout_planner(semantic_pages)
        usage = build_legacy_layout_rules_usage(gate, semantic_pages, processed_pages)

        self.assertEqual(gate["mode"], "disabled")
        self.assertFalse(gate["should_use_legacy_engine"])
        self.assertFalse(gate["should_use_formal_planner"])
        self.assertEqual(gate["fallback_contract"], "cover_toc_ending_only")
        self.assertEqual(
            [page["semantic"] for page in processed_pages],
            ["COVER", "TOC", "BACKGROUND_DATA", "PAIN_POINTS", "ENDING"],
        )
        self.assertEqual(usage["engine_path"], "outline_generator.minimal_outline_fallback")
        self.assertEqual(usage["auto_page_semantics"], ["COVER", "TOC", "ENDING"])
        self.assertEqual(usage["inserted_auto_pages"], 3)

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1"}, clear=False)
    def test_legacy_layout_rules_usage_snapshot_is_saved_as_sidecar(self):
        gate = build_legacy_layout_rules_gate(
            enhanced_data={"task_id": 9303, "domain": "education"},
            semantic_pages=[{"semantic": "BACKGROUND_DATA", "title": "行业背景"}],
            theme="competition-tech-dark",
        )
        usage = build_legacy_layout_rules_usage(
            gate,
            [{"semantic": "BACKGROUND_DATA", "title": "行业背景"}],
            [{"semantic": "COVER", "auto": True}, {"semantic": "BACKGROUND_DATA", "title": "行业背景"}],
        )
        outline = {
            "pages": [{"page_index": 1, "title": "行业背景"}],
            "generation_diagnostics": {
                "legacy_layout_rules_gate": gate,
                "legacy_layout_rules_usage": usage,
            },
        }

        self.service._maybe_save_legacy_layout_rules_usage_snapshot(
            task_id=9303,
            questionnaire_id=9304,
            outline_json=outline,
            stage="round2_legacy_layout_rules_usage",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "legacy_layout_rules_usage")
        self.assertEqual(snapshot["stage"], "round2_legacy_layout_rules_usage")
        self.assertEqual(snapshot["payload"]["source"], "legacy_layout_rules_usage_snapshot")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")
        self.assertEqual(snapshot["payload"]["cutover_impact"], "none")
        self.assertEqual(snapshot["payload"]["gate"]["mode"], "legacy_on")
        self.assertFalse(snapshot["payload"]["usage"]["used_legacy_layout_rules"])
        self.assertTrue(snapshot["payload"]["usage"]["used_formal_outline_layout_planner"])

    def test_layout_rules_legacy_engine_inventory_is_retired_and_replaced(self):
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "app", "services", "ppt")
        )
        inventory = scan_v3_retirement_inventory(base_dir)

        layout_rules_target = None
        for batch in inventory.get("batches") or []:
            if batch.get("batch_id") != "batch2_shrink_compat_layers":
                continue
            for target in batch.get("targets") or []:
                if target.get("target_id") == "layout_rules_legacy_engine":
                    layout_rules_target = target
                    break
            if layout_rules_target:
                break

        self.assertIsNotNone(layout_rules_target)
        self.assertEqual(layout_rules_target["cleanup_readiness"], "already_absent")
        self.assertEqual(layout_rules_target["match_count"], 0)
        self.assertEqual(layout_rules_target["deprecation_gate"]["status"], "retired_replaced")
        self.assertEqual(
            layout_rules_target["deprecation_gate"]["retirement_hint"],
            "formal_replacement_active",
        )
        self.assertTrue(
            all(check["passed"] for check in layout_rules_target["deprecation_gate"]["checks"])
        )

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_phase5_extension_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=929,
            fallback_theme="rapidesign",
        )

        self.service._maybe_save_v4_phase5_extension_snapshot(
            task_id=929,
            questionnaire_id=930,
            outline_json=outline,
            stage="phase5_extension_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase5_extension_pack")
        self.assertEqual(snapshot["stage"], "phase5_extension_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase5_extension_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_phase5_preflight_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=932,
            fallback_theme="rapidesign",
        )

        self.service._maybe_save_v4_phase5_preflight_snapshot(
            task_id=932,
            questionnaire_id=933,
            outline_json=outline,
            stage="phase5_preflight_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase5_preflight_pack")
        self.assertEqual(snapshot["stage"], "phase5_preflight_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase5_preflight_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_phase5_gate_pack_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=934,
            fallback_theme="rapidesign",
        )

        self.service._maybe_save_v4_phase5_gate_pack_snapshot(
            task_id=934,
            questionnaire_id=935,
            outline_json=outline,
            stage="phase5_gate_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase5_gate_pack")
        self.assertEqual(snapshot["stage"], "phase5_gate_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase5_gate_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_phase6_prep_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=936,
            fallback_theme="rapidesign",
        )
        shadow_payload = build_shadow_review_snapshot_payload(outline)

        self.service._maybe_save_v4_phase6_prep_snapshot(
            task_id=936,
            questionnaire_id=937,
            outline_json=outline,
            legacy_quality_report=shadow_payload["quality_report_v4_compat"],
            html_pages=["<html>1</html>"],
            stage="phase6_prep_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase6_prep_pack")
        self.assertEqual(snapshot["stage"], "phase6_prep_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase6_prep_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_phase7_retirement_snapshot_is_saved_as_sidecar(self):
        outline = self.service._maybe_attach_v4_phase1_artifacts(
            outline_json={
                "project": {"name": "智慧实训平台"},
                "pages": [
                    {
                        "page_index": 1,
                        "title": "协议看板",
                        "slide_role": "content",
                        "page_series_type": "protocol_board",
                        "page_visual_role": "protocol_flow",
                        "content_points": ["协议步骤", "风控动作", "验收规则"],
                    }
                ],
            },
            questionnaire_data=self.questionnaire_data,
            task_id=937,
            fallback_theme="rapidesign",
        )
        self.service._get_latest_snapshot_payload_by_type = (
            lambda task_id, snapshot_type: {"prep_status": "candidate"}
            if snapshot_type == "v4_phase6_prep_pack"
            else None
        )
        self.service._count_snapshot_stage_by_task_ids = lambda task_ids, snapshot_type, stage: {937: 0}
        self.service._get_recent_v4_phase7_observations = lambda limit=30: []

        self.service._maybe_save_v4_phase7_retirement_snapshot(
            task_id=937,
            questionnaire_id=938,
            outline_json=outline,
            stage="phase7_retirement_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v4_phase7_retirement_pack")
        self.assertEqual(snapshot["stage"], "phase7_retirement_test")
        self.assertEqual(snapshot["payload"]["source"], "v4_phase7_retirement_pack")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")

    @patch.dict(os.environ, {"PPT_HTML_V4_SAVE_INTERMEDIATE": "1", "PPT_HTML_V4_DIAGRAMS_ENABLED": "1"}, clear=False)
    def test_v3_retirement_cleanup_plan_snapshot_is_saved_as_sidecar(self):
        self.service._get_latest_snapshot_payload_by_type = (
            lambda task_id, snapshot_type: {
                "retirement_status": "candidate",
                "current_task": {
                    "template_shell_leak_count": 0,
                    "delivery_auto_repair_ratio": 0.0,
                },
                "window_signals": {
                    "consecutive_green_tasks": 30,
                    "streak_target": 30,
                },
                "blocking_reasons": [],
                "recommended_actions": [],
            }
            if snapshot_type == "v4_phase7_retirement_pack"
            else None
        )
        self.service._build_v3_retirement_cleanup_inventory = lambda: {
            "batch_count": 1,
            "target_count": 1,
            "match_count": 3,
            "batches": [
                {
                    "batch_id": "batch1_remove_legacy_fallback_families",
                    "label": "第一批删除对象",
                    "target_count": 1,
                    "match_count": 3,
                    "targets": [{"target_id": "pipeline_fallback_family", "match_count": 3}],
                }
            ],
        }

        self.service._maybe_save_v3_retirement_cleanup_plan_snapshot(
            task_id=938,
            questionnaire_id=939,
            stage="phase7_cleanup_plan_test",
        )

        self.assertEqual(len(self.saved_snapshots), 1)
        snapshot = self.saved_snapshots[0]
        self.assertEqual(snapshot["snapshot_type"], "v3_retirement_cleanup_plan")
        self.assertEqual(snapshot["stage"], "phase7_cleanup_plan_test")
        self.assertEqual(snapshot["payload"]["source"], "v3_retirement_cleanup_plan")
        self.assertEqual(snapshot["payload"]["delivery_mode"], "sidecar_only")


class FormalHtmlReadPathTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_html_pages_defaults_to_non_mutating_read(self):
        service = PPTService.__new__(PPTService)

        async def fake_get_task(task_id):
            return {"id": task_id, "outline_json": {"pages": [{"title": "封面"}]}}

        async def fake_sanitize(**kwargs):
            self.assertFalse(kwargs["auto_repair"])
            return kwargs["html"]

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._get_html_page_map_from_db = lambda task_id: {1: "<html>shadowless</html>"}
        service._build_quality_context = lambda task_id, outline_pages: {"stub": True}
        service._sanitize_html_for_delivery_async = fake_sanitize

        pages = await service.get_html_pages(777)
        self.assertEqual(pages, ["<html>shadowless</html>"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_ALLOW_SHADOW_READ": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "778",
        },
        clear=False,
    )
    async def test_get_html_pages_still_prefers_db_when_shadow_candidate_exists(self):
        service = PPTService.__new__(PPTService)

        async def fake_get_task(task_id):
            return {"id": task_id, "outline_json": {"pages": [{"title": "封面"}]}}

        async def fake_sanitize(**kwargs):
            self.assertFalse(kwargs["auto_repair"])
            return kwargs["html"]

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "candidate",
                    "formal_cutover_candidate": True,
                }
            if snapshot_type == "v4_phase6_prep_pack":
                return {"prep_status": "candidate"}
            if snapshot_type == "v4_shadow_render":
                return {
                    "pages": [
                        {"page_index": 1, "html": "<html>v4-candidate</html>"},
                    ]
                }
            return None

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._get_latest_snapshot_payload_by_type = fake_snapshot
        service._get_html_page_map_from_db = lambda task_id: {1: "<html>legacy-db</html>"}
        service._build_quality_context = lambda task_id, outline_pages: {"stub": True}
        service._sanitize_html_for_delivery_async = fake_sanitize

        pages = await service.get_html_pages(778)
        self.assertEqual(pages, ["<html>legacy-db</html>"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_ALLOW_SHADOW_READ": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "780",
        },
        clear=False,
    )
    async def test_get_html_pages_ignores_shadow_candidate_when_phase6_prep_is_not_candidate(self):
        service = PPTService.__new__(PPTService)

        async def fake_get_task(task_id):
            return {"id": task_id, "outline_json": {"pages": [{"title": "封面"}]}}

        async def fake_sanitize(**kwargs):
            return kwargs["html"]

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "candidate",
                    "formal_cutover_candidate": True,
                }
            if snapshot_type == "v4_phase6_prep_pack":
                return {"prep_status": "blocked"}
            if snapshot_type == "v4_shadow_render":
                return {
                    "pages": [
                        {"page_index": 1, "html": "<html>v4-should-not-serve</html>"},
                    ]
                }
            return None

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._get_latest_snapshot_payload_by_type = fake_snapshot
        service._get_html_page_map_from_db = lambda task_id: {1: "<html>legacy-db</html>"}
        service._build_quality_context = lambda task_id, outline_pages: {"stub": True}
        service._sanitize_html_for_delivery_async = fake_sanitize

        pages = await service.get_html_pages(780)
        self.assertEqual(pages, ["<html>legacy-db</html>"])

    @patch.dict(
        os.environ,
        {
            "PPT_HTML_V4_ENABLED": "1",
            "PPT_HTML_V4_DEFAULT_ON": "1",
            "PPT_HTML_V4_COHORT_TASK_IDS": "779",
        },
        clear=False,
    )
    async def test_get_html_pages_ignores_shadow_candidate_when_gate_pack_is_not_candidate(self):
        service = PPTService.__new__(PPTService)

        async def fake_get_task(task_id):
            return {"id": task_id, "outline_json": {"pages": [{"title": "封面"}]}}

        async def fake_sanitize(**kwargs):
            return kwargs["html"]

        def fake_snapshot(task_id, snapshot_type):
            if snapshot_type == "v4_phase4_gate_pack":
                return {
                    "gate_status": "hold",
                    "formal_cutover_candidate": False,
                }
            if snapshot_type == "v4_shadow_render":
                return {
                    "pages": [
                        {"page_index": 1, "html": "<html>v4-should-not-serve</html>"},
                    ]
                }
            return None

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._get_latest_snapshot_payload_by_type = fake_snapshot
        service._get_html_page_map_from_db = lambda task_id: {1: "<html>legacy-db</html>"}
        service._build_quality_context = lambda task_id, outline_pages: {"stub": True}
        service._sanitize_html_for_delivery_async = fake_sanitize

        pages = await service.get_html_pages(779)
        self.assertEqual(pages, ["<html>legacy-db</html>"])

    async def test_get_html_pages_normalizes_outline_pages_and_passes_deck_blueprint(self):
        service = PPTService.__new__(PPTService)
        captured = {}

        async def fake_get_task(task_id):
            return {
                "id": task_id,
                "project_name": "智慧农业平台",
                "outline_json": {
                    "deck_blueprint": {"style_preset_id": "formal-tech"},
                    "pages": [{"title": "技术架构总览", "page_series_type": "architecture_system"}],
                },
            }

        async def fake_sanitize(**kwargs):
            captured.update(kwargs)
            return kwargs["html"]

        def fake_complete(page, idx, project_name):
            page["page_index"] = idx
            page["project_name"] = project_name
            page["normalized_marker"] = True

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._complete_outline_page_defaults = fake_complete
        service._infer_outline_project_name = lambda outline, pages: "备用项目名"
        service._get_html_page_map_from_db = lambda task_id: {1: "<html>normalized-db</html>"}
        service._build_quality_context = lambda task_id, outline_pages: {
            "titles": [page.get("title") for page in outline_pages],
        }
        service._sanitize_html_for_delivery_async = fake_sanitize

        pages = await service.get_html_pages(781)
        self.assertEqual(pages, ["<html>normalized-db</html>"])
        self.assertEqual(captured["page_meta"]["page_index"], 1)
        self.assertEqual(captured["page_meta"]["project_name"], "智慧农业平台")
        self.assertTrue(captured["page_meta"]["normalized_marker"])
        self.assertEqual(captured["deck_blueprint"]["style_preset_id"], "formal-tech")
        self.assertEqual(captured["deck_blueprint"]["project_name"], "智慧农业平台")
        self.assertEqual(captured["quality_context"], {"titles": ["技术架构总览"]})

    async def test_get_task_opening_rhythm_snapshot_builds_phase1_artifacts_when_missing(self):
        service = PPTService.__new__(PPTService)

        async def fake_get_task(task_id):
            return {
                "id": task_id,
                "project_name": "智慧农业平台",
                "enhanced_data": {"theme": "formal-tech"},
                "outline_json": {
                    "pages": [
                        {"title": "封面", "page_series_type": "cover_keynote", "content_points": ["AI识别", "边缘感知"]},
                        {"title": "目录", "page_series_type": "agenda_navigation", "content_points": ["项目背景", "方案设计", "价值结果"]},
                        {"title": "技术架构", "page_series_type": "architecture_system", "content_points": ["采集层", "平台层", "应用层"]},
                    ]
                },
            }

        def fake_complete(page, idx, project_name):
            page["page_index"] = idx
            page["project_name"] = project_name

        service.get_task = fake_get_task
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._complete_outline_page_defaults = fake_complete
        service._infer_outline_project_name = lambda outline, pages: "备用项目名"

        snapshot = await service.get_task_opening_rhythm_snapshot(157)

        self.assertEqual(snapshot["task_id"], 157)
        self.assertEqual(snapshot["project_name"], "智慧农业平台")
        self.assertIn(snapshot["status"], {"pass", "warning", "block"})
        self.assertGreaterEqual(len(snapshot["pages"]), 2)

    def test_normalize_outline_pages_for_render_merges_layout_plan_signals(self):
        service = PPTService.__new__(PPTService)
        task = {
            "project_name": "智慧农业平台",
            "outline_json": {
                "pages": [
                    {
                        "title": "封面",
                        "page_series_type": "cover_keynote",
                        "content_points": ["AI识别", "边缘感知"],
                    },
                    {
                        "title": "研发历程",
                        "page_series_type": "journey_timeline",
                        "content_points": ["测试验证", "问题复盘", "质量改进"],
                    },
                ],
                "layout_plan": [
                    {
                        "page_index": 1,
                        "family_id": "cover_keynote.hero_split",
                        "selected_variant": "hero_split_center",
                        "region_plan": {
                            "focus_strategy": "hero_first",
                            "density_mode": "spacious",
                            "scan_pattern": "single_anchor",
                            "narrative_role": "opening_anchor",
                            "narrative_segment": "opening",
                        },
                    },
                    {
                        "page_index": 2,
                        "family_id": "journey_timeline.milestone_rail",
                        "selected_variant": "milestone_rail_cards",
                        "region_plan": {
                            "focus_strategy": "diagram_first",
                            "density_mode": "balanced",
                            "scan_pattern": "split_compare",
                            "narrative_role": "retrospective_improvement",
                            "narrative_segment": "solution",
                        },
                    },
                ],
            },
        }

        def fake_complete(page, idx, project_name):
            page["page_index"] = idx
            page["project_name"] = project_name

        service._complete_outline_page_defaults = fake_complete
        service._infer_outline_project_name = lambda outline, pages: "备用项目名"

        normalized = service._normalize_outline_pages_for_render(
            task,
            task["outline_json"]["pages"],
        )

        self.assertEqual(normalized[0]["layout_family_id"], "cover_keynote.hero_split")
        self.assertEqual(normalized[0]["layout_variant"], "hero_split_center")
        self.assertEqual(normalized[0]["region_plan"]["focus_strategy"], "hero_first")
        self.assertEqual(normalized[0]["layout_region_plan"]["narrative_segment"], "opening")
        self.assertEqual(normalized[1]["layout_family_id"], "journey_timeline.milestone_rail")
        self.assertEqual(normalized[1]["layout_variant"], "milestone_rail_cards")
        self.assertEqual(normalized[1]["region_plan"]["narrative_role"], "retrospective_improvement")
        self.assertEqual(normalized[1]["layout_region_plan"]["scan_pattern"], "split_compare")

    async def test_get_task_opening_rhythm_batch_report_aggregates_snapshots(self):
        service = PPTService.__new__(PPTService)

        async def fake_snapshot(task_id):
            return {
                "task_id": task_id,
                "project_name": f"项目{task_id}",
                "status": "pass" if task_id == 157 else "warning",
                "unique_skeleton_count": 3,
                "unique_focus_count": 2,
                "pages": [
                    {"page_index": 1, "page_series_type": "cover_keynote", "layout_skeleton": "hero_split", "focus_strategy": "hero_first", "scan_pattern": "single_anchor", "opening_rhythm_signature": "hero_split|hero_first"},
                    {"page_index": 2, "page_series_type": "agenda_navigation", "layout_skeleton": "route_board_vertical", "focus_strategy": "diagram_first", "scan_pattern": "staged_progression", "opening_rhythm_signature": "route_board_vertical|diagram_first"},
                    {"page_index": 3, "page_series_type": "evidence_board", "layout_skeleton": "caption_grid", "focus_strategy": "evidence_first", "scan_pattern": "single_anchor", "opening_rhythm_signature": "caption_grid|evidence_first"},
                ],
            }

        service.get_task_opening_rhythm_snapshot = fake_snapshot

        report = await service.get_task_opening_rhythm_batch_report([157, 156])

        self.assertEqual(report["task_ids"], [157, 156])
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["agenda_route_adoption_rate"], 1.0)
        self.assertEqual(report["third_page_skeleton_coverage_rate"], 1.0)

    async def test_get_task_front_segment_rhythm_batch_report_aggregates_snapshots(self):
        service = PPTService.__new__(PPTService)

        async def fake_snapshot(task_id):
            return {
                "task_id": task_id,
                "project_name": f"项目{task_id}",
                "status": "pass" if task_id == 157 else "warning",
                "unique_skeleton_count": 4,
                "unique_focus_count": 3,
                "unique_density_count": 2 if task_id == 157 else 1,
                "unique_scan_count": 2,
                "role_transition_count": 3,
                "clusters": [],
            }

        service.get_task_front_segment_rhythm_snapshot = fake_snapshot

        report = await service.get_task_front_segment_rhythm_batch_report([157, 156])

        self.assertEqual(report["task_ids"], [157, 156])
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["density_diversity_rate"], 0.5)

    async def test_sanitize_html_for_delivery_async_prefers_formal_safe_fallback_for_supported_series(self):
        service = PPTService.__new__(PPTService)
        service._attempt_ai_delivery_html_repair = AsyncMock(return_value="")
        service._render_formal_safe_fallback_html = Mock(
            return_value="<!DOCTYPE html><html><body><div>formal-safe</div></body></html>"
        )
        service._generate_roadshow_rebuild_html = Mock(
            return_value="<!DOCTYPE html><html><body><div>roadshow-safe</div></body></html>"
        )

        result = await service._sanitize_html_for_delivery_async(
            task={"id": 1},
            html="",
            page_meta={"title": "技术架构总览", "page_series_type": "architecture_system"},
            page_index=3,
            total_pages=10,
            quality_context={"stub": True},
            auto_repair=True,
            deck_blueprint={"project_name": "智慧农业平台", "style_preset_id": "formal-tech"},
        )

        self.assertIn("formal-safe", result)
        service._render_formal_safe_fallback_html.assert_called_once()
        service._generate_roadshow_rebuild_html.assert_not_called()

    async def test_repair_html_page_prefers_v4_candidate_strategy_and_context(self):
        service = PPTService.__new__(PPTService)
        captured = {}

        async def fake_get_task(task_id):
            return {
                "id": task_id,
                "questionnaire_id": 1,
                "outline_json": {"pages": [{"title": "封面", "page_series_type": "cover_keynote"}]},
                "project_name": "智慧实训平台",
            }

        async def fake_get_html_pages(task_id):
            return ["<html>v4-candidate</html>"]

        async def fake_issue_profiles(task_id, task=None):
            return {"pages": [{"page_index": 1, "repair_route": "html"}]}

        async def fake_run_single_page_repair_pass(**kwargs):
            captured.update(kwargs)
            return {
                "strategy": kwargs["strategy"],
                "repair_mode": "rule_repaired",
                "ai_error": None,
                "html_content": "<html>preview</html>",
                "quality_preview": {},
                "repair_assessment": {
                    "effective": True,
                    "accept_candidate": True,
                    "score_delta": 4,
                    "next_action": "accept_candidate",
                    "summary": "ok",
                },
                "series_validation": {},
            }

        service.get_task = fake_get_task
        service.get_html_pages = fake_get_html_pages
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._infer_outline_project_name = lambda outline, pages: "智慧实训平台"
        service._complete_outline_page_defaults = lambda page, idx, project_name: None
        service._get_latest_page_quality_report = (
            lambda task_id, page_index: {"regeneration_strategy": "regenerate_html", "failed_checks": []}
        )
        service._build_quality_context = lambda task_id, pages: {}
        service.get_task_page_issue_profiles = fake_issue_profiles
        service._get_v4_repair_candidate_context = lambda task_id, page_index: {
            "source": "v4_shadow_review",
            "gate_status": "candidate",
            "gate_summary": "ready",
            "regeneration_strategy": "fix_layout_hierarchy",
            "repair_route": "structure",
            "repair_route_reason": "需要重排结构",
            "preferred_entry": "quality",
            "failed_checks": ["ppt_layout_contract"],
            "recommended_actions": ["rebalance_regions"],
            "support_status": "supported",
        }
        service._run_single_page_repair_pass = fake_run_single_page_repair_pass

        result = await service.repair_html_page(
            task_id=780,
            page_index=1,
            use_ai=False,
            preview_only=True,
            refresh_quality=False,
        )

        self.assertEqual(captured["strategy"], "fix_layout_hierarchy")
        self.assertEqual(captured["page_issue_profile"]["repair_route"], "structure")
        self.assertEqual(captured["repair_context"]["source"], "v4_phase4_candidate")
        self.assertEqual(captured["repair_context"]["repair_route"], "structure")
        self.assertEqual(captured["latest_quality"]["preferred_entry"], "quality")
        self.assertTrue(result["preview_only"])

    async def test_repair_html_page_keeps_diagram_candidate_advisory_only(self):
        service = PPTService.__new__(PPTService)
        captured = {}

        async def fake_get_task(task_id):
            return {
                "id": task_id,
                "questionnaire_id": 1,
                "outline_json": {"pages": [{"title": "系统架构", "page_series_type": "architecture_system"}]},
                "project_name": "智慧实训平台",
            }

        async def fake_get_html_pages(task_id):
            return ["<html>diagram</html>"]

        async def fake_issue_profiles(task_id, task=None):
            return {"pages": [{"page_index": 1, "repair_route": "html"}]}

        async def fake_run_single_page_repair_pass(**kwargs):
            captured.update(kwargs)
            return {
                "strategy": kwargs["strategy"],
                "repair_mode": "rule_repaired",
                "ai_error": None,
                "html_content": "<html>preview</html>",
                "quality_preview": {},
                "repair_assessment": {
                    "effective": True,
                    "accept_candidate": True,
                    "score_delta": 4,
                    "next_action": "accept_candidate",
                    "summary": "ok",
                },
                "series_validation": {},
            }

        service.get_task = fake_get_task
        service.get_html_pages = fake_get_html_pages
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._infer_outline_project_name = lambda outline, pages: "智慧实训平台"
        service._complete_outline_page_defaults = lambda page, idx, project_name: None
        service._get_latest_page_quality_report = (
            lambda task_id, page_index: {"regeneration_strategy": "rewrite_page_argument", "failed_checks": []}
        )
        service._build_quality_context = lambda task_id, pages: {}
        service.get_task_page_issue_profiles = fake_issue_profiles
        service._get_v4_repair_candidate_context = lambda task_id, page_index: {
            "source": "v4_shadow_review",
            "gate_status": "candidate",
            "gate_summary": "ready",
            "regeneration_strategy": "rebuild_diagram_layout",
            "repair_route": "structure",
            "repair_route_reason": "diagram 需重建",
            "preferred_entry": "quality",
            "failed_checks": ["diagram_integrity"],
            "recommended_actions": ["fallback_to_flat_svg"],
            "support_status": "supported",
            "advisory_only": True,
            "advisory_reason": "diagram_shadow_review_only",
        }
        service._run_single_page_repair_pass = fake_run_single_page_repair_pass

        result = await service.repair_html_page(
            task_id=782,
            page_index=1,
            use_ai=False,
            preview_only=True,
            refresh_quality=False,
        )

        self.assertEqual(captured["strategy"], "rewrite_page_argument")
        self.assertEqual(captured["page_issue_profile"]["repair_route"], "html")
        self.assertEqual(captured["repair_context"]["source"], "v4_phase4_candidate_advisory")
        self.assertTrue(captured["repair_context"]["advisory_only"])
        self.assertEqual(captured["repair_context"]["advisory_regeneration_strategy"], "rebuild_diagram_layout")
        self.assertNotIn("repair_route", captured["repair_context"])
        self.assertTrue(result["preview_only"])

    async def test_repair_html_page_falls_back_to_legacy_strategy_without_v4_candidate(self):
        service = PPTService.__new__(PPTService)
        captured = {}

        async def fake_get_task(task_id):
            return {
                "id": task_id,
                "questionnaire_id": 1,
                "outline_json": {"pages": [{"title": "封面", "page_series_type": "cover_keynote"}]},
                "project_name": "智慧实训平台",
            }

        async def fake_get_html_pages(task_id):
            return ["<html>legacy</html>"]

        async def fake_issue_profiles(task_id, task=None):
            return {"pages": [{"page_index": 1, "repair_route": "html"}]}

        async def fake_run_single_page_repair_pass(**kwargs):
            captured.update(kwargs)
            return {
                "strategy": kwargs["strategy"],
                "repair_mode": "rule_repaired",
                "ai_error": None,
                "html_content": "<html>preview</html>",
                "quality_preview": {},
                "repair_assessment": {
                    "effective": True,
                    "accept_candidate": True,
                    "score_delta": 4,
                    "next_action": "accept_candidate",
                    "summary": "ok",
                },
                "series_validation": {},
            }

        service.get_task = fake_get_task
        service.get_html_pages = fake_get_html_pages
        service._extract_outline_pages = lambda outline: outline.get("pages") or []
        service._infer_outline_project_name = lambda outline, pages: "智慧实训平台"
        service._complete_outline_page_defaults = lambda page, idx, project_name: None
        service._get_latest_page_quality_report = (
            lambda task_id, page_index: {"regeneration_strategy": "rewrite_page_argument", "failed_checks": []}
        )
        service._build_quality_context = lambda task_id, pages: {}
        service.get_task_page_issue_profiles = fake_issue_profiles
        service._get_v4_repair_candidate_context = lambda task_id, page_index: {}
        service._run_single_page_repair_pass = fake_run_single_page_repair_pass

        result = await service.repair_html_page(
            task_id=781,
            page_index=1,
            use_ai=False,
            preview_only=True,
            refresh_quality=False,
        )

        self.assertEqual(captured["strategy"], "rewrite_page_argument")
        self.assertNotIn("source", captured["repair_context"])
        self.assertEqual(captured["page_issue_profile"]["repair_route"], "html")
        self.assertTrue(result["preview_only"])


class TaskStatusGuardTests(unittest.TestCase):
    class _FakeCursor:
        def __init__(self, state):
            self.state = state
            self._result = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params):
            if sql.startswith("SELECT status, progress, current_step FROM ppt_task"):
                self._result = {
                    "status": self.state.get("status"),
                    "progress": self.state.get("progress"),
                    "current_step": self.state.get("current_step"),
                }
                return
            if sql.startswith("UPDATE ppt_task SET"):
                index = 0
                self.state["status"] = params[index]
                index += 1
                if "progress = %s" in sql:
                    self.state["progress"] = params[index]
                    index += 1
                if "current_step = %s" in sql:
                    self.state["current_step"] = params[index]
                    index += 1
                if "repair_substep = %s" in sql:
                    self.state["repair_substep"] = params[index]
                    index += 1
                if "error_msg = %s" in sql:
                    self.state["error_msg"] = params[index]
                elif "error_msg = NULL" in sql:
                    self.state["error_msg"] = None
                if "repair_substep = NULL" in sql:
                    self.state["repair_substep"] = None
                return
            raise AssertionError(f"Unexpected SQL: {sql}")

        def fetchone(self):
            return self._result

    class _FakeConnection:
        def __init__(self, state):
            self.state = state

        def cursor(self):
            return TaskStatusGuardTests._FakeCursor(self.state)

        def commit(self):
            return None

        def close(self):
            return None

    def test_update_task_status_keeps_generating_progress_monotonic(self):
        service = PPTService.__new__(PPTService)
        service._ensure_task_runtime_columns = lambda: None
        state = {
            "status": "generating",
            "progress": 60,
            "current_step": "Round 3: 内容充实（第 3/4 批）",
            "repair_substep": None,
            "error_msg": None,
        }
        service._get_connection = lambda: self._FakeConnection(state)

        asyncio.run(
            service._update_task_status(
                task_id=999,
                status="generating",
                progress=45,
                step="Round 3: 内容充实（第 2/4 批）",
            )
        )

        self.assertEqual(state["progress"], 60)
        self.assertEqual(state["current_step"], "Round 3: 内容充实（第 3/4 批）")

    def test_update_task_status_accepts_forward_generating_progress(self):
        service = PPTService.__new__(PPTService)
        service._ensure_task_runtime_columns = lambda: None
        state = {
            "status": "generating",
            "progress": 60,
            "current_step": "Round 3: 内容充实（第 3/4 批）",
            "repair_substep": None,
            "error_msg": None,
        }
        service._get_connection = lambda: self._FakeConnection(state)

        asyncio.run(
            service._update_task_status(
                task_id=1000,
                status="generating",
                progress=70,
                step="Round 3: 内容充实（第 4/4 批）",
            )
        )

        self.assertEqual(state["progress"], 70)
        self.assertEqual(state["current_step"], "Round 3: 内容充实（第 4/4 批）")


if __name__ == "__main__":
    unittest.main()
