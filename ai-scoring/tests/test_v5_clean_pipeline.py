import unittest
import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

from app.services.ppt.v5 import (
    build_clean_pipeline,
    build_v5_preview_review_report,
    render_v5_html_pages,
    review_v5_html_page,
)
from app.services.ppt.v5.ai_passes import (
    _agenda_chapter_candidates,
    _ab_candidate_structural_gate,
    _apply_fragment_replacement_json_patch,
    _audit_layout_blueprint,
    _audit_blueprint_html_execution,
    _blueprint_required_marker_present,
    _blueprint_html_rewrite_feedback,
    _body_user_prompt,
    _classify_body_review,
    _controlled_diagram_body_fragment,
    _image_placeholder_brief,
    _infer_zone_class_binding_contract,
    _normalize_evidence_chain_geometry_locally,
    _normalize_blueprint_execution_locally,
    _normalize_proof_nodes_locally,
    _prioritized_fragment_patch_zone_ids,
    _professional_expression_type,
    _repair_instruction_pack,
    _request_direct_body_html,
    apply_ai_design_passes,
    repair_ai_design_passes_from_render_audit,
)
from app.services.ppt.v5.controlled_diagram_renderer import render_controlled_diagram_svg
from app.services.ppt.v5.creative_director import (
    build_creative_director_plan,
    build_creative_director_plans,
    creative_director_plan_map,
)
from app.services.ppt.v5.body_layout_auditor import audit_ai_body_fragment
from app.services.ppt.v5.design_quality_auditor import audit_design_quality_contract
from app.services.ppt.v5.design_contracts import page_contract_map
from app.services.ppt.v5.diagram_prompt_library import (
    classify_diagram_prompt_type,
    diagram_prompt_contract_for_page,
    load_diagram_prompt_library,
)
from app.services.ppt.v5.diagram_spec_builder import build_product_diagram_spec
from app.services.ppt.v5.expression_planner import build_page_expression_plan, classify_page_role
from app.services.ppt.v5.expression_strategy_library import (
    build_page_expression_hypothesis,
    load_expression_strategy_library,
)
from app.services.ppt.v5.page_visual_translation_auditor import audit_page_visual_translation_brief
from app.services.ppt.v5.page_visual_translator import (
    build_page_visual_translation_brief,
    build_page_visual_translation_briefs,
    page_visual_translation_brief_map,
)
from app.services.ppt.v5.slide_playbook_library import load_slide_playbook_library, slide_playbook_for_page
from app.services.ppt.v5.visual_contracts import visual_contract_map
from app.services.ppt.v5.visual_aesthetic_auditor import _score_visual_metrics
from app.services.ppt.v5.visual_quality_gate import evaluate_visual_quality_gate
from app.services.ppt.v5.body_layout_auditor import audit_ai_body_fragment
from app.services.ppt.v5.nested_canvas_auditor import audit_nested_canvas
from app.services.ppt.v5.text_sanitizer import sanitize_v5_text
from app.services.ppt.image_asset_service import PPTImageAssetService
from app.services.ppt.adapter_code.pipeline_coordinator import PipelineCoordinator
from app.services.ppt.ppt_service import PPTService


class V5CleanPipelineTests(unittest.TestCase):
    def test_expression_strategy_library_builds_page_hypothesis_before_html(self):
        library = load_expression_strategy_library()
        self.assertGreaterEqual(library["strategy_count"], 20)

        page = {
            "page_index": 12,
            "title": "数据流：从采集到分析",
            "page_series_type": "architecture_system",
            "page_goal": "说明传感器数据如何通过边缘处理进入云端分析。",
            "content_points": ["传感器采集", "边缘网关清洗", "云端模型分析", "应用反馈"],
        }
        hypothesis = build_page_expression_hypothesis(page)

        self.assertEqual(hypothesis["strategy_id"], "data_handoff_pipeline")
        self.assertIn("audience_memory", hypothesis)
        self.assertGreaterEqual(hypothesis["main_visual_ratio_target"], 0.6)
        self.assertIn("layout_blueprint", hypothesis)
        self.assertTrue(hypothesis["speaker_notes_content"]["use_for_details"])

    def test_page_visual_translator_builds_evidence_chain_brief_before_html(self):
        page = {
            "page_index": 24,
            "title": "技术证据链：从数据到价值",
            "page_series_type": "practice_evidence",
            "core_argument": "数据采集、边缘清洗、云端分析和终端反馈形成可验证闭环。",
            "content_points": [
                "传感器采集日志证明数据来源真实",
                "边缘网关过滤异常值保证实时性",
                "云端模型输出预警看板",
                "农事建议回传形成生产动作",
                "详细接口和参数进入讲稿说明",
            ],
        }
        brief = build_page_visual_translation_brief(page=page)

        self.assertTrue(brief["enabled"])
        self.assertEqual(brief["version"], "v5_page_visual_translation_brief_v1")
        self.assertEqual(brief["visual_strategy"]["diagram_type"], "evidence_chain_stage")
        self.assertGreaterEqual(brief["layout_blueprint"]["main_visual_ratio"], 0.7)
        self.assertIn("proof_rail", [region["id"] for region in brief["layout_blueprint"]["regions"]])
        self.assertIn("equal_cards", brief["diagram_contract"]["forbidden_shapes"])
        self.assertIn("free_random_paths", brief["diagram_contract"]["forbidden_shapes"])
        self.assertLessEqual(brief["diagram_contract"]["max_free_path_count"], 1)
        self.assertIn("must_keep", brief["content_extraction"])
        self.assertTrue(any("page_memory" in item for item in brief["mimo_instruction"]["must_do"]))

    def test_page_visual_translation_auditor_rejects_empty_high_risk_brief(self):
        page = {"page_index": 12, "page_series_type": "architecture_system"}
        bad = {
            "version": "v5_page_visual_translation_brief_v1",
            "page_index": 12,
            "enabled": True,
            "page_series_type": "architecture_system",
            "page_memory": {},
            "visual_strategy": {},
            "layout_blueprint": {"main_visual_ratio": 0.3, "regions": []},
            "diagram_contract": {"nodes": [], "forbidden_shapes": []},
            "content_extraction": {"must_keep": []},
        }
        audit = audit_page_visual_translation_brief(bad, page)

        self.assertFalse(audit["pass"])
        self.assertIn("missing_one_second_takeaway", audit["issues"])
        self.assertIn("missing_diagram_type", audit["issues"])
        self.assertIn("main_visual_ratio_too_low", audit["issues"])

    def test_page_visual_translation_briefs_map_by_page_index(self):
        pages = [
            {"page_index": 8, "page_series_type": "evidence_board", "core_argument": "证据可追溯", "content_points": ["日志", "截图"]},
            {"page_index": 12, "page_series_type": "architecture_system", "core_argument": "系统闭环", "content_points": ["采集", "分析"]},
        ]
        briefs = build_page_visual_translation_briefs(pages)
        mapped = page_visual_translation_brief_map(briefs)

        self.assertEqual(set(mapped), {8, 12})
        self.assertTrue(mapped[8]["enabled"])
        self.assertEqual(mapped[12]["visual_strategy"]["diagram_type"], "layered_architecture_stage")

    def test_visual_aesthetic_metric_scoring_reports_weak_main_visual_and_card_risk(self):
        scored = _score_visual_metrics(
            page_meta={"page_index": 12, "title": "数据管道", "page_series_type": "architecture_system"},
            dom_metrics={
                "largestVisual": {"areaRatio": 0.12},
                "utilization": 0.42,
                "cardLikeCount": 8,
                "visibleTextLength": 260,
                "overflowCount": 0,
                "smallText": [],
                "rootAttrs": {"creativeMode": "large_system_map", "focusText": "数据闭环"},
            },
            screenshot_metrics={"content_bbox_ratio": 0.36, "edge_density": 0.06, "contrast": 18},
            expression_hypothesis={"strategy_id": "data_handoff_pipeline", "main_visual_ratio_target": 0.68},
        )

        self.assertFalse(scored["pass"])
        self.assertIn("main_visual_below_expression_hypothesis", scored["failure_reasons"])
        self.assertIn("card_or_system_ui_heavy", scored["failure_reasons"])
        self.assertGreaterEqual(scored["scores"]["card_ui_risk"], 4)
        self.assertIn("competition_ppt_fit", scored["scores"])

    def test_visual_quality_gate_blocks_structure_valid_empty_diagram_page(self):
        gate = evaluate_visual_quality_gate(
            page_meta={"page_index": 24, "title": "证据链", "page_series_type": "practice_evidence"},
            visual_item={
                "pass": True,
                "failure_reasons": ["main_visual_below_expression_hypothesis"],
                "scores": {
                    "competition_ppt_fit": 4,
                    "visual_anchor_strength": 3,
                    "one_second_readability": 4,
                    "diagram_clarity": 4,
                    "card_ui_risk": 1,
                },
                "key_metrics": {
                    "largest_visual_ratio": 0.49,
                    "target_visual_ratio": 0.7,
                    "utilization": 0.36,
                    "visible_text_length": 94,
                    "card_like_count": 0,
                },
            },
            body_audit={"pass": True, "issues": []},
            blueprint={"primitive": "evidence_stage"},
            structural_gate={"pass": True},
        )

        self.assertFalse(gate["pass"])
        self.assertEqual(gate["recommended_action"], "same_blueprint_visual_redraw")
        self.assertIn("主视觉", " ".join(gate["issues"]))

    def test_visual_quality_gate_blocks_compliant_but_sparse_diagram_page(self):
        gate = evaluate_visual_quality_gate(
            page_meta={"page_index": 24, "title": "证据链", "page_series_type": "practice_evidence"},
            visual_item={
                "pass": True,
                "failure_reasons": [],
                "scores": {
                    "competition_ppt_fit": 4,
                    "visual_anchor_strength": 5,
                    "one_second_readability": 4,
                    "diagram_clarity": 4,
                    "card_ui_risk": 1,
                },
                "key_metrics": {
                    "largest_visual_ratio": 0.6992,
                    "target_visual_ratio": 0.7,
                    "utilization": 0.3623,
                    "visible_text_length": 81,
                    "visual_candidate_count": 7,
                    "edge_density": 0.2949,
                    "focus_font_size": 20,
                    "focus_area_ratio": 0.012,
                    "card_like_count": 0,
                },
            },
            body_audit={"pass": True, "issues": []},
            blueprint={"primitive": "evidence_stage"},
            structural_gate={"pass": True},
        )

        self.assertFalse(gate["pass"])
        joined = " ".join(gate["issues"])
        self.assertIn("利用率", joined)
        self.assertIn("焦点文字", joined)

    def test_visual_quality_gate_allows_strong_structure_valid_diagram_page(self):
        gate = evaluate_visual_quality_gate(
            page_meta={"page_index": 24, "title": "证据链", "page_series_type": "practice_evidence"},
            visual_item={
                "pass": True,
                "failure_reasons": [],
                "scores": {
                    "competition_ppt_fit": 4,
                    "visual_anchor_strength": 4,
                    "one_second_readability": 4,
                    "diagram_clarity": 4,
                    "card_ui_risk": 1,
                },
                "key_metrics": {
                    "largest_visual_ratio": 0.64,
                    "target_visual_ratio": 0.7,
                    "utilization": 0.52,
                    "visible_text_length": 120,
                    "card_like_count": 0,
                },
            },
            body_audit={"pass": True, "issues": []},
            blueprint={"primitive": "evidence_stage"},
            structural_gate={"pass": True},
        )

        self.assertTrue(gate["pass"])

    def test_v5_layout_blueprint_normalizes_zone_class_binding_contract(self):
        blueprint = {
            "blueprint_id": "strategy_system_layer_stack",
            "primitive": "system_layer_stack",
            "focus_statement": "高效数据流水线是AI基础",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "layer_stack_stage", "role": "系统架构总舞台", "x": 4, "y": 10, "w": 92, "h": 70},
                {"id": "data_layer", "role": "数据接入层", "x": 8, "y": 18, "w": 22, "h": 18},
                {"id": "data_bus", "role": "数据总线", "x": 35, "y": 18, "w": 55, "h": 58},
                {"id": "application_output", "role": "业务应用与输出", "x": 35, "y": 20, "w": 18, "h": 15},
            ],
            "zone_class_binding_contract": [
                {"zone_id": "layer_stack_stage", "required_classes": ["system-stage", "data-zone-layer_stack_stage"]},
                {"zone_id": "data_layer", "required_classes": ["system-layer", "data-zone-data_layer"]},
                {"zone_id": "data_bus", "required_classes": ["system-bus", "data-zone-data_bus"]},
                {"zone_id": "application_output", "required_classes": ["system-node", "data-zone-application_output"]},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_system_layer_stack"',
                'data-zone-id="layer_stack_stage"',
                'data-zone-id="data_layer"',
                'data-zone-id="data_bus"',
                'data-zone-id="application_output"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "数据流水线", "page_series_type": "architecture_system"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["system_layer_stack"],
                        "default_primitive_id": "system_layer_stack",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])
        contract = {
            item["zone_id"]: item["required_classes"]
            for item in report["normalized_blueprint"]["zone_class_binding_contract"]
        }
        self.assertIn("layer-stack-stage", contract["layer_stack_stage"])
        self.assertNotIn("system-stage", contract["layer_stack_stage"])
        self.assertNotIn("data-zone-layer_stack_stage", contract["layer_stack_stage"])
        self.assertEqual(contract["data_bus"], ["layer-bus"])
        self.assertEqual(contract["application_output"], ["application-node"])

    def test_v5_layout_blueprint_coerces_system_like_layered_track_for_architecture(self):
        blueprint = {
            "blueprint_id": "strategy_layered_track",
            "primitive": "layered_track",
            "focus_statement": "数据从采集到价值流转",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "layer_stack_stage", "role": "系统架构舞台边界", "x": 4, "y": 10, "w": 92, "h": 70},
                {"id": "data_ingestion_layer", "role": "数据接入层", "x": 8, "y": 18, "w": 22, "h": 18},
                {"id": "central_data_bus", "role": "数据总线", "x": 35, "y": 18, "w": 55, "h": 58},
                {"id": "value_output_node", "role": "业务价值输出", "x": 75, "y": 70, "w": 20, "h": 8},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_layered_track"',
                'data-zone-id="layer_stack_stage"',
                'data-zone-id="data_ingestion_layer"',
                'data-zone-id="central_data_bus"',
                'data-zone-id="value_output_node"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "数据流水线", "page_series_type": "architecture_system"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["system_layer_stack", "layered_track"],
                        "default_primitive_id": "system_layer_stack",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])
        self.assertEqual(report["normalized_blueprint"]["primitive"], "system_layer_stack")
        contract = {
            item["zone_id"]: item["required_classes"]
            for item in report["normalized_blueprint"]["zone_class_binding_contract"]
        }
        self.assertEqual(contract["central_data_bus"], ["layer-bus"])

    def test_v5_layout_blueprint_normalizes_common_stage_zone_ids(self):
        blueprint = {
            "blueprint_id": "strategy_system_layer_stack",
            "primitive": "system_layer_stack",
            "focus_statement": "高效流水线是业务基石",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "system_stage", "role": "系统舞台边界", "x": 4, "y": 10, "w": 92, "h": 70},
                {"id": "data_ingest_layer", "role": "数据接入层", "x": 10, "y": 15, "w": 28, "h": 25},
                {"id": "data_bus", "role": "中央数据总线", "x": 40, "y": 15, "w": 20, "h": 79},
                {"id": "business_app_layer", "role": "业务应用层/输出", "x": 62, "y": 15, "w": 30, "h": 79},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_system_layer_stack"',
                'data-zone-id="system_stage"',
                'data-zone-id="data_ingest_layer"',
                'data-zone-id="data_bus"',
                'data-zone-id="business_app_layer"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "数据流水线", "page_series_type": "architecture_system"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["system_layer_stack"],
                        "default_primitive_id": "system_layer_stack",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])
        ids = [zone["id"] for zone in report["normalized_blueprint"]["zones"]]
        self.assertIn("layer_stack_stage", ids)
        self.assertNotIn("system_stage", ids)
        self.assertTrue(any('data-zone-id="layer_stack_stage"' in item for item in report["normalized_blueprint"]["required_html_markers"]))

    def test_v5_layout_blueprint_keeps_evidence_stage_binding_single_purpose(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "primitive": "evidence_stage",
            "focus_statement": "数据证据转化生产动作",
            "primary_stage": {"x": 4, "y": 6, "w": 92, "h": 76, "role": "包裹主张、证据和结论的证据舞台"},
            "zones": [
                {"id": "primary_stage", "role": "包裹主张、证据和结论的证据舞台", "x": 4, "y": 6, "w": 92, "h": 76},
                {"id": "claim_zone", "role": "大主张区", "x": 8, "y": 8, "w": 58, "h": 30},
                {"id": "evidence_flow", "role": "证据轨道", "x": 8, "y": 44, "w": 84, "h": 32},
                {"id": "result_seal", "role": "结果章印，价值落地强调", "x": 72, "y": 12, "w": 20, "h": 22},
                {"id": "proof_node_collect", "role": "证据节点", "x": 10, "y": 48, "w": 22, "h": 20},
            ],
            "zone_class_binding_contract": [
                {"zone_id": "primary_stage", "required_classes": ["evidence-stage", "claim-zone", "conclusion-rail"]},
                {"zone_id": "result_seal", "required_classes": ["result-seal", "value-stamp"]},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_evidence_stage"',
                'data-zone-id="primary_stage"',
                'data-zone-id="claim_zone"',
                'data-zone-id="evidence_flow"',
                'data-zone-id="result_seal"',
                'data-zone-id="proof_node_collect"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "证据链", "page_series_type": "practice_evidence"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["evidence_stage"],
                        "default_primitive_id": "evidence_stage",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])
        contract = {
            item["zone_id"]: item["required_classes"]
            for item in report["normalized_blueprint"]["zone_class_binding_contract"]
        }
        self.assertEqual(contract["primary_stage"], ["evidence-stage"])
        self.assertEqual(contract["result_seal"], ["result-seal"])

    def test_v5_layout_blueprint_infers_handoff_ladder_output_classes(self):
        blueprint = {
            "blueprint_id": "strategy_handoff_ladder",
            "primitive": "handoff_ladder",
            "focus_statement": "产教协同需求变方案",
            "primary_stage": {"x": 5, "y": 8, "w": 90, "h": 65, "role": "阶梯主舞台"},
            "zones": [
                {"id": "ladder_stage", "role": "阶梯主舞台", "x": 5, "y": 8, "w": 90, "h": 65},
                {"id": "lane_collaboration", "role": "校企协作阶梯", "x": 32, "y": 10, "w": 36, "h": 55},
                {"id": "handoff_feedback", "role": "持续反馈与优化箭头", "x": 35, "y": 60, "w": 30, "h": 10},
                {"id": "conclusion_seal", "role": "结论章印", "x": 75, "y": 75, "w": 18, "h": 12},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_handoff_ladder"',
                'data-zone-id="ladder_stage"',
                'data-zone-id="lane_collaboration"',
                'data-zone-id="handoff_feedback"',
                'data-zone-id="conclusion_seal"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "产教协同开发历程", "page_series_type": "bridge_story"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["proof_wall", "handoff_ladder"],
                        "default_primitive_id": "proof_wall",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])
        contract = {
            item["zone_id"]: item["required_classes"]
            for item in report["normalized_blueprint"]["zone_class_binding_contract"]
        }
        self.assertIn("handoff-ladder", contract["ladder_stage"])
        self.assertIn("ladder-step", contract["lane_collaboration"])
        self.assertIn("handoff-arrow", contract["handoff_feedback"])
        self.assertEqual(contract["conclusion_seal"], ["output-node"])

    def test_v5_layout_blueprint_allows_bridge_proof_wall_near_threshold(self):
        blueprint = {
            "blueprint_id": "strategy_proof_wall",
            "primitive": "proof_wall",
            "focus_statement": "校企协同真实驱动",
            "primary_stage": {"x": 8, "y": 12, "w": 84, "h": 62, "role": "证据舞台整体边界"},
            "zones": [
                {"id": "primary_stage", "role": "证据舞台整体边界", "x": 8, "y": 12, "w": 84, "h": 62},
                {"id": "claim_zone", "role": "核心结论陈述", "x": 12, "y": 14, "w": 40, "h": 28},
                {"id": "proof_rail", "role": "证据链路与节点容器", "x": 12, "y": 42, "w": 76, "h": 28},
                {"id": "proof_node_1", "role": "证据节点", "x": 14, "y": 44, "w": 18, "h": 24},
                {"id": "result_seal", "role": "最终成果或收益证明", "x": 78, "y": 44, "w": 14, "h": 24},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_proof_wall"',
                'data-zone-id="primary_stage"',
                'data-zone-id="claim_zone"',
                'data-zone-id="proof_rail"',
                'data-zone-id="proof_node_1"',
                'data-zone-id="result_seal"',
            ],
        }
        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "产教协同开发历程", "page_series_type": "bridge_story"},
            page_contract={
                "creative_director_plan": {
                    "expression_primitive_contract": {
                        "allowed_primitive_ids": ["proof_wall", "handoff_ladder"],
                        "default_primitive_id": "proof_wall",
                    }
                }
            },
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertTrue(report["pass"])

    def test_clean_pipeline_builds_isolated_contract_chain(self):
        outline = {
            "project": {"name": "智慧巡检平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智慧巡检平台",
                    "page_series_type": "cover_keynote",
                    "content_points": ["巡检闭环", "应急处置"],
                },
                {
                    "page_index": 2,
                    "title": "团队协作与分工",
                    "page_series_type": "collaboration_matrix",
                    "page_goal": "突出交接机制与异常升级链路。",
                    "core_argument": "通过岗位交接、异常升级和应急补位构成闭环协作。",
                },
                {
                    "page_index": 3,
                    "title": "研发历程：里程碑与问题复盘",
                    "page_series_type": "journey_timeline",
                    "page_goal": "突出测试暴露的问题和后续质量改进动作。",
                    "core_argument": "围绕问题复盘、改进动作和版本收敛形成工程叙事。",
                },
            ],
        }

        result = build_clean_pipeline(outline, {"theme": "clean-formal"})

        self.assertTrue(result["cutover_readiness"]["isolated_from_v4_repair_chain"])
        self.assertEqual(result["cutover_readiness"]["legacy_fallback_dependencies"], [])
        self.assertEqual(result["cutover_readiness"]["html_delivery_mode"], "shell_composition_svg_contracts")
        self.assertEqual(result["cutover_readiness"]["migration_stage"], "composition_cutover")
        self.assertEqual(result["shell_spec"]["theme_id"], "clean-formal")
        self.assertEqual(result["composition_plans"][1]["composition_id"], "center_chain_side_roles")
        self.assertEqual(result["composition_plans"][1]["visual_intent"], "chain_flow")
        self.assertIn("clarify_handoffs", result["composition_plans"][1]["body_goals"])
        self.assertEqual(result["svg_schemas"][1]["svg_kind"], "handoff_chain")
        self.assertEqual(result["layout_decisions"][1]["family_id"], "collaboration_matrix.role_map")
        self.assertEqual(result["cutover_readiness"]["design_contract_layer"]["page_expression_hypothesis_count"], 3)
        self.assertGreaterEqual(result["cutover_readiness"]["design_contract_layer"]["expression_strategy_count"], 20)
        self.assertEqual(len(result["v5_page_expression_hypotheses"]), 3)
        self.assertEqual(result["v5_page_contracts"][0]["page_expression_hypothesis"]["strategy_id"], "cover_poster_scene")
        self.assertTrue(result["v5_page_contracts"][0]["expression_hypothesis_gate"]["must_exist_before_html"])
        self.assertEqual(result["layout_decisions"][1]["variant_id"], "role_map_chain")
        self.assertEqual(result["layout_decisions"][1]["layout_skeleton"], "handoff_chain_board")
        self.assertEqual(result["layout_decisions"][2]["layout_skeleton"], "retrospective_split")
        self.assertEqual(result["deck_design_spec"]["version"], "v5_deck_design_spec_v1")
        self.assertIn("v5_page_expression_plans", result)
        self.assertIn("v5_slide_playbooks", result)
        self.assertIn("v5_creative_director_plans", result)
        self.assertEqual(result["v5_page_expression_plans"][0]["version"], "v5_page_expression_plan_v1")
        self.assertEqual(result["v5_slide_playbooks"][0]["version"], "v5_slide_playbook_binding_v1")
        self.assertEqual(result["v5_creative_director_plans"][0]["version"], "v5_creative_director_plan_v1")
        self.assertEqual(len(result["v5_page_contracts"]), 3)
        first_contract = result["v5_page_contracts"][0]
        self.assertEqual(first_contract["version"], "v5_page_contract_v1")
        self.assertEqual(first_contract["page_series_type"], "cover_keynote")
        self.assertEqual(first_contract["page_expression_plan"]["page_role"], "opening_hook")
        self.assertEqual(first_contract["slide_playbook"]["playbook_id"], "cover_key_visual")
        self.assertEqual(first_contract["creative_director_plan"]["creative_mode"], "poster_key_visual")
        self.assertTrue(first_contract["creative_director_plan"]["material_strategy"]["asset_usage_is_gate"])
        self.assertEqual(
            first_contract["creative_director_plan"]["visual_anchor"]["hard_layout_contract"]["asset_policy"],
            "image_first",
        )
        self.assertIn("main_visual", first_contract)
        self.assertIn("text_budget", first_contract)
        self.assertIn("diagram_contract", first_contract)
        self.assertIn("v5_diagram_specs", result)
        self.assertEqual(result["v5_diagram_specs"][0]["version"], "v5_diagram_spec_v1")
        self.assertIn("v5_visual_contracts", result)
        self.assertEqual(len(result["v5_visual_contracts"]), 2)
        self.assertEqual(result["v5_visual_contracts"][0]["version"], "v5_visual_contract_v1")
        self.assertEqual(result["cutover_readiness"]["design_contract_layer"]["visual_contract_count"], 2)
        self.assertEqual(result["cutover_readiness"]["design_contract_layer"]["creative_director_plan_count"], 3)

    def test_v5_page_contract_is_injected_into_body_prompt(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构总览：端-边-云协同",
                    "page_series_type": "architecture_system",
                    "page_goal": "说明数据如何进入系统并形成分析结果。",
                    "core_argument": "平台通过采集、网关、云端分析和应用反馈形成闭环。",
                    "content_points": ["传感器采集田间数据", "边缘网关完成初筛", "云端模型输出预警"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = page_contract_map(pipeline["v5_page_contracts"])
        visual_contracts = visual_contract_map(pipeline["v5_visual_contracts"])
        visual_brief = build_page_visual_translation_brief(
            page=outline["pages"][0],
            page_contract=contracts[1],
            diagram_spec=pipeline["v5_diagram_specs"][0],
            visual_contract=visual_contracts[1],
        )
        contracts[1]["page_visual_translation_brief"] = visual_brief
        controlled_diagram = render_controlled_diagram_svg(pipeline["v5_diagram_specs"][0])
        prompt = _body_user_prompt(
            deck={"project_name": "智慧农业物联网大数据平台"},
            shell_spec=pipeline["shell_spec"],
            page=outline["pages"][0],
            decision=pipeline["layout_decisions"][0],
            strategy_brief={"subgoal": "technical_proof"},
            recent_family_context=[],
            all_pages=outline["pages"],
            deck_design_spec=pipeline["deck_design_spec"],
            page_contract=contracts[1],
            diagram_spec=pipeline["v5_diagram_specs"][0],
            visual_contract=visual_contracts[1],
            controlled_diagram_svg=controlled_diagram,
        )
        payload = json.loads(prompt)
        self.assertEqual(payload["deck_design_spec"]["version"], "v5_deck_design_spec_v1")
        self.assertEqual(payload["page_expression_plan"]["page_role"], "technical_architecture")
        self.assertEqual(payload["slide_playbook"]["playbook_id"], "architecture_system_map")
        self.assertEqual(payload["creative_director_plan"]["creative_mode"], "large_system_map")
        self.assertEqual(payload["creative_execution_contract"]["visual_anchor"]["type"], "layered_system_diagram")
        self.assertIn("primary_bounds", payload["creative_execution_contract"]["visual_anchor_geometry"])
        self.assertEqual(payload["creative_execution_contract"]["visual_anchor_hard_layout"]["layout_lock"], "layered_system_map")
        self.assertFalse(payload["creative_execution_contract"]["card_policy"]["allow_equal_card_grid"])
        self.assertEqual(payload["page_contract"]["strategy_key"], "architecture_system")
        self.assertEqual(payload["page_contract"]["diagram_contract"]["diagram_type"], "architecture_system")
        self.assertTrue(payload["page_visual_translation_brief"]["enabled"])
        self.assertEqual(payload["page_visual_translation_brief"]["visual_strategy"]["diagram_type"], "layered_architecture_stage")
        self.assertGreaterEqual(payload["page_visual_translation_brief"]["layout_blueprint"]["main_visual_ratio"], 0.65)
        self.assertEqual(payload["page_visual_translation_gate"]["trace"]["diagram_type"], "layered_architecture_stage")
        self.assertGreaterEqual(payload["page_contract"]["main_visual"]["min_area_ratio"], 0.45)
        self.assertEqual(payload["diagram_spec"]["diagram_type"], "architecture_system")
        self.assertEqual(payload["diagram_spec"]["diagram_prompt_type"], "architecture")
        self.assertEqual(payload["product_grade_diagram_spec"]["diagram_prompt_type"], "architecture")
        self.assertEqual(payload["product_grade_diagram_spec"]["layout"], "layered_architecture_with_system_boundary")
        self.assertTrue(payload["product_grade_diagram_spec"]["visual_rules"]["no_crossing_lines"])
        self.assertEqual(payload["diagram_prompt_contract"]["diagram_prompt_type"], "architecture")
        self.assertIn("extract_schema", payload["diagram_prompt_contract"])
        self.assertIn("render_contract", payload["diagram_prompt_contract"])
        self.assertTrue(any("Show layers and boundaries" in item for item in payload["diagram_prompt_contract"]["render_contract"]))
        self.assertEqual(payload["diagram_construction_contract"]["version"], "v5_diagram_render_contract_v2")
        self.assertIn("node_geometry", payload["diagram_construction_contract"]["global"])
        self.assertIn("composition_strength", payload["diagram_construction_contract"]["global"])
        self.assertIn("anti_table", payload["diagram_construction_contract"]["type_specific"])
        self.assertIn("system boundary", payload["diagram_construction_contract"]["type_specific"]["layout"])
        self.assertIn("65%-80%", payload["diagram_construction_contract"]["type_specific"]["composition"])
        self.assertEqual(payload["visual_contract"]["visual_role"], "technical_architecture_map")
        self.assertEqual(payload["visual_contract"]["relationship_model"], "layered_architecture")
        self.assertGreaterEqual(payload["visual_contract"]["main_visual_ratio"], 0.6)
        self.assertIn("layers", payload["diagram_spec"]["payload"])
        self.assertEqual(payload["page_specific_diagram_json"]["renderer_status"], "page_specific_diagram_json")
        self.assertIn("传感器采集田间数据", payload["page_specific_diagram_json"]["payload"]["modules"])
        self.assertEqual(payload["controlled_diagram_safety_reference"]["status"], "ok")
        self.assertIn("几何安全参考", payload["controlled_diagram_safety_reference"]["usage_rule"])
        self.assertTrue(any("优先执行 visual_contract" in item for item in payload["design_direction"]))
        self.assertTrue(any("diagram_prompt_contract.render_contract" in item for item in payload["design_direction"]))
        self.assertTrue(any("page_expression_plan" in item for item in payload["design_direction"]))
        self.assertTrue(any("product_grade_diagram_spec" in item for item in payload["design_direction"]))
        self.assertTrue(any("creative_director_plan" in item for item in payload["design_direction"]))
        self.assertTrue(any("page_visual_translation_brief" in item for item in payload["design_direction"]))
        self.assertIn("data-creative-mode", payload["rapidesign_v2_execution_contract"]["root_trace_required"]["required_attrs"])

    def test_ab_candidate_body_prompt_uses_short_contract_payload(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 12,
                    "title": "数据处理流程",
                    "page_series_type": "architecture_system",
                    "core_argument": "多源数据经过清洗、建模和反馈形成生产闭环。",
                    "content_points": ["采集", "清洗", "建模", "反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = page_contract_map(pipeline["v5_page_contracts"])
        visual_contracts = visual_contract_map(pipeline["v5_visual_contracts"])
        visual_brief = build_page_visual_translation_brief(
            page=outline["pages"][0],
            page_contract=contracts[12],
            diagram_spec=pipeline["v5_diagram_specs"][0],
            visual_contract=visual_contracts[12],
        )
        contracts[12]["page_visual_translation_brief"] = visual_brief
        common_kwargs = {
            "deck": {"project_name": "智慧农业物联网大数据平台"},
            "shell_spec": pipeline["shell_spec"],
            "page": outline["pages"][0],
            "decision": pipeline["layout_decisions"][0],
            "strategy_brief": {"subgoal": "technical_proof"},
            "recent_family_context": [],
            "all_pages": outline["pages"],
            "deck_design_spec": pipeline["deck_design_spec"],
            "page_contract": contracts[12],
            "diagram_spec": pipeline["v5_diagram_specs"][0],
            "visual_contract": visual_contracts[12],
        }

        long_prompt = _body_user_prompt(**common_kwargs)
        short_prompt = _body_user_prompt(
            **common_kwargs,
            candidate_variant={
                "variant_id": "diagram",
                "strategy_instruction": "主图占主体区65%以上，按diagram contract画稳定对称图示。",
                "selection_goal": "diagram_precision_and_visual_weight",
            },
        )
        payload = json.loads(short_prompt)

        self.assertEqual(payload["prompt_mode"], "ab_short_prompt_v1")
        self.assertEqual(payload["candidate_variant"]["variant_id"], "diagram")
        self.assertIn("diagram_contract_summary", payload)
        self.assertIn("render_contract_summary", payload["diagram_contract_summary"])
        self.assertIn("page_expression_hypothesis", payload)
        self.assertIn("page_visual_translation_brief", payload)
        self.assertEqual(payload["page_visual_translation_gate"]["trace"]["composition"], "中心数据总线 + 3-4层能力舞台 + 结果节点")
        self.assertLess(len(short_prompt), len(long_prompt) * 0.45)
        self.assertLess(len(short_prompt), 30000)
        self.assertNotIn("ruipu_image_ppt_style", short_prompt)
        self.assertNotIn("rapidesign_dynamic_case_knowledge_v2", short_prompt)
        self.assertNotIn("controlled_diagram_safety_reference", short_prompt)

    def test_ab_candidate_body_generation_uses_process_isolation(self):
        outline = {
            "project": {"name": "隔离生成验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构总览",
                    "page_series_type": "architecture_system",
                    "core_argument": "端边云协同形成数据闭环。",
                    "content_points": ["采集", "清洗", "分析", "反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "隔离生成验证"})
        contracts = page_contract_map(pipeline["v5_page_contracts"])
        visual_contracts = visual_contract_map(pipeline["v5_visual_contracts"])
        isolated_calls = []

        async def fake_isolated(**kwargs):
            isolated_calls.append(kwargs)
            return (
                "<div class='mimo-body-root' data-page-archetype='architecture' "
                "data-visual-motif='system_layer_stack' data-dominant-visual='layered_system_diagram' "
                "data-creative-mode='large_system_map' data-focus-text='端边云闭环' "
                "data-expression-primitive='system_layer_stack'>"
                "<svg class='layer-stack-stage system-boundary system-layer layer-bus data-flow application-node' "
                "viewBox='0 0 800 420'></svg>"
                "</div>"
            )

        with patch.dict(os.environ, {"PPT_V5_AB_PROCESS_ISOLATION": "1"}, clear=False), \
             patch("app.services.ppt.v5.ai_passes._generate_html_in_isolated_process", side_effect=fake_isolated), \
             patch("app.services.ppt.v5.ai_passes.create_ppt_html_client", side_effect=AssertionError("main client should not be used")):
            fragment, audit = asyncio.run(
                _request_direct_body_html(
                    deck={"project_name": "隔离生成验证"},
                    shell_spec=pipeline["shell_spec"],
                    page=outline["pages"][0],
                    decision=pipeline["layout_decisions"][0],
                    strategy_brief={"subgoal": "technical_proof"},
                    recent_family_context=[],
                    all_pages=outline["pages"],
                    page_timeout_seconds=30,
                    deck_design_spec=pipeline["deck_design_spec"],
                    page_contract=contracts[1],
                    diagram_spec=pipeline["v5_diagram_specs"][0],
                    visual_contract=visual_contracts[1],
                    max_attempts_override=1,
                    candidate_variant={"variant_id": "strategy", "strategy_instruction": "强表达"},
                )
            )

        self.assertEqual(len(isolated_calls), 1)
        self.assertIn("ab_short_prompt_v1", isolated_calls[0]["prompt"])
        self.assertIn("mimo-body-root", fragment)
        self.assertIn("review_classification", audit)

    def test_product_grade_expression_playbook_and_diagram_spec_are_bound(self):
        page = {
            "page_index": 24,
            "title": "技术证据链：从数据到决策",
            "page_series_type": "practice_evidence",
            "core_argument": "从传感器采集到生产反馈形成可追溯技术闭环。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板", "农事建议反馈"],
        }

        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        diagram_spec = build_product_diagram_spec(
            page=page,
            expression_plan=expression_plan,
            slide_playbook=playbook,
            legacy_diagram_type="process_flow",
        )

        self.assertEqual(classify_page_role(page), "technical_evidence")
        self.assertEqual(expression_plan["primary_visual_type"], "evidence_chain_proof")
        self.assertEqual(playbook["playbook_id"], "evidence_chain_proof")
        self.assertEqual(creative_plan["creative_mode"], "answer_first_proof_chain")
        self.assertGreaterEqual(creative_plan["visual_anchor"]["min_area_ratio"], 0.6)
        self.assertEqual(creative_plan["visual_anchor"]["geometry_contract"]["max_primary_nodes"], 4)
        self.assertIn("proof_zone", creative_plan["visual_anchor"]["geometry_contract"])
        self.assertEqual(creative_plan["visual_anchor"]["hard_layout_contract"]["layout_lock"], "answer_first_proof_chain")
        self.assertEqual(creative_plan["visual_anchor"]["hard_layout_contract"]["max_freeform_paths"], 1)
        self.assertEqual(creative_plan["expression_primitive_contract"]["default_primitive_id"], "evidence_stage")
        self.assertIn("proof_wall", creative_plan["expression_primitive_contract"]["allowed_primitive_ids"])
        self.assertIn("wave_path_chain", creative_plan["forbidden_layouts"])
        self.assertEqual(diagram_spec["version"], "v5_product_diagram_spec_v1")
        self.assertEqual(diagram_spec["diagram_prompt_type"], "evidence_chain")
        self.assertEqual(diagram_spec["layout"], "answer_first_claim_three_proofs")
        self.assertEqual(len(diagram_spec["nodes"]), 4)
        self.assertTrue(diagram_spec["visual_rules"]["must_be_symmetric"])
        self.assertTrue(diagram_spec["visual_rules"]["no_crossing_lines"])

    def test_slide_playbook_library_loads_core_playbooks(self):
        library = load_slide_playbook_library()

        self.assertEqual(library["version"], "v5_slide_playbook_library_20260509_v1")
        self.assertIn("agenda_story_map", library["playbooks"])
        self.assertIn("architecture_system_map", library["playbooks"])
        self.assertIn("evidence_chain_proof", library["playbooks"])

    def test_creative_director_plans_drive_quality_audit(self):
        pages = [
            {
                "page_index": 1,
                "title": "技术证据链：从数据到决策",
                "page_series_type": "practice_evidence",
                "core_argument": "从传感器采集到生产反馈形成可追溯技术闭环。",
                "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板", "农事建议反馈"],
            }
        ]
        expression_plan = build_page_expression_plan(pages[0])
        playbook = slide_playbook_for_page(pages[0], expression_plan)
        plans = build_creative_director_plans(pages, [expression_plan], [playbook])
        by_index = creative_director_plan_map(plans)

        self.assertEqual(by_index[1]["creative_mode"], "answer_first_proof_chain")
        bad_html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='cards' data-dominant-visual='主视觉' data-focus-text='价值可量化'>"
            "<div class='card'>A</div><div class='card'>B</div><div class='card'>C</div>"
            "<div class='card'>D</div><div class='card'>E</div>"
            "</div>"
        )
        audit = audit_design_quality_contract(
            html_fragment=bad_html,
            page=pages[0],
            creative_director_plan=by_index[1],
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("创意模式" in issue for issue in audit["issues"]))
        self.assertTrue(any("卡片" in issue for issue in audit["issues"]))

    def test_cover_and_agenda_image_prompt_uses_creative_contract(self):
        page = {
            "page_index": 1,
            "title": "智慧农业物联网大数据平台",
            "page_series_type": "cover_keynote",
            "content_points": ["实时监测", "智能决策"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        prompt = PPTImageAssetService(api_key="test").build_prompt(
            deck={"project_name": "智慧农业物联网大数据平台"},
            page=page,
            visual_style={},
            creative_director_plan=creative_plan,
        )

        self.assertIn("qwen", PPTImageAssetService(api_key="test").model)
        self.assertIn("创意模式：poster_key_visual", prompt)
        self.assertIn("主视觉类型：industry_scene_poster", prompt)
        self.assertIn("geometry_contract", prompt)
        self.assertIn("硬布局合同", prompt)
        self.assertIn("不要生成任何可读文字", prompt)

    def test_generated_cover_asset_is_a_quality_gate_when_available(self):
        page = {
            "page_index": 1,
            "title": "智慧农业物联网大数据平台",
            "page_series_type": "cover_keynote",
            "content_points": ["实时监测", "智能决策"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='cover' "
            "data-visual-motif='poster' data-dominant-visual='industry_scene_poster' "
            "data-creative-mode='poster_key_visual'><svg class='poster-scene'></svg>智慧农业物联网大数据平台</div>"
        )

        audit = audit_design_quality_contract(
            html_fragment=html,
            page=page,
            creative_director_plan=creative_plan,
            generated_visual_asset={"status": "ok", "file_url": "file:///tmp/generated-cover.png"},
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("没有使用生成素材" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_rejects_plain_white_cards(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='dashboard_wall' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-focus-text='价值可量化'>"
            "<div style='background:rgba(255,255,255,.82);border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.04)'>证据一</div>"
            "<div style='background:rgba(255,255,255,.82);border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.04)'>证据二</div>"
            "<div style='background:rgba(255,255,255,.82);border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.04)'>证据三</div>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("普通白卡片" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_rejects_card_like_proof_node_css(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-focus-text='价值可量化'>"
            "<style>.proof-node{background:rgba(255,255,255,.65);border:2px solid rgba(37,99,235,.2);"
            "border-radius:12px;box-shadow:0 4px 12px rgba(15,23,42,.08);}</style>"
            "<section class='claim-zone'>数据证据 → 生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node'>采集日志</div>"
            "<div class='proof-node'>异常过滤</div><div class='proof-node'>指标看板</div></section>"
            "<aside class='result-seal'>价值落地</aside>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("卡片化 CSS" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_rejects_inline_card_like_proof_node_css(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-focus-text='价值可量化'>"
            "<section class='claim-zone'>数据证据 → 生产动作</section>"
            "<section class='evidence-flow'>"
            "<div class='proof-node' style='background:rgba(37,99,235,.08);border:1px solid rgba(37,99,235,.25);border-radius:10px;'>采集日志</div>"
            "<div class='proof-node' style='background:rgba(37,99,235,.08);border:1px solid rgba(37,99,235,.25);border-radius:10px;'>异常过滤</div>"
            "<div class='proof-node' style='background:rgba(37,99,235,.08);border:1px solid rgba(37,99,235,.25);border-radius:10px;'>指标看板</div>"
            "</section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("卡片化 CSS" in issue for issue in audit["issues"]))

    def test_repair_pack_targets_card_like_proof_node_css(self):
        instructions = _repair_instruction_pack(
            item={
                "issues": ["proof-node 仍使用白底/阴影/完整边框等卡片化 CSS，缺少轨道锚点质感。"],
                "metrics": {},
            },
            page={"page_index": 24, "page_series_type": "practice_evidence"},
        )

        joined = "\n".join(instructions)
        self.assertIn("证据链专项重画", joined)
        self.assertIn("proof-anchor-spine", joined)
        self.assertIn("spine_label", joined)
        self.assertNotIn("proof-node--cut-corner-tag", joined)
        self.assertIn("不得自创第三种结构", joined)
        self.assertIn("data-proof-id", joined)
        self.assertIn("proof_node_bboxes", joined)
        self.assertIn("proof-title", joined)
        self.assertIn("source-tag >=12px", joined)
        self.assertIn(">=72px", joined)
        self.assertIn(">=对应 bbox 高度 62%", joined)
        self.assertIn("left:0", joined)
        self.assertIn("不得 left:-4px", joined)
        self.assertIn("result-seal", joined)
        self.assertIn("跨 bbox 长竖线", joined)
        self.assertIn("box-shadow", joined)

    def test_answer_first_proof_chain_rejects_compressed_proof_node_and_small_source_tag(self):
        page = {
            "page_index": 24,
            "title": "技术证据链",
            "page_series_type": "practice_evidence",
            "core_argument": "数据证据转化为生产动作。",
            "content_points": ["传感器日志", "边缘过滤", "云端分析"],
        }
        html = """
        <div class="mimo-body-root" data-page-archetype="evidence" data-visual-motif="stage"
             data-dominant-visual="proof chain" data-creative-mode="answer_first_proof_chain"
             data-focus-text="数据证据转化生产动作">
          <style>
            .proof-node { height:17%; background:rgba(30,64,175,.64); }
            .source-tag { font-size:11px; }
            .evidence-snippet { font-size:12px; }
          </style>
          <div class="claim-zone">数据证据</div>
          <div class="evidence-flow">
            <div class="proof-node proof-node--spine-label" data-proof-id="proof_1">
              <span class="proof-index">01</span>
              <span class="source-tag">ev_sensor_log</span>
              <span class="evidence-snippet">采集日志</span>
              <i class="proof-connector"></i>
            </div>
          </div>
          <div class="result-seal">生产动作</div>
        </div>
        """
        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan={"page_archetype": "evidence"},
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("字号或尺寸低于枚举结构下限" in issue for issue in audit["issues"]))

    def test_expression_primitive_rejects_negative_positioned_seal(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='价值可量化'>"
            "<style>.result-seal{position:absolute;right:-4%;top:-8%;}</style>"
            "<section class='claim-zone'>价值可量化：数据证据 → 生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node'>采集日志</div></section>"
            "<aside class='result-seal'>价值落地</aside>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("负向定位" in issue for issue in audit["issues"]))

    def test_expression_primitive_rejects_negative_decorative_offsets(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='价值可量化'>"
            "<style>.proof-anchor-spine{position:absolute;left:-4px;top:8px;}"
            ".proof-connector{position:absolute;bottom:-15px;left:0;}"
            ".value-seal-ring::after{content:'';right:-12px;bottom:-12px;}</style>"
            "<section class='claim-zone'>价值可量化：数据证据 → 生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--spine-label' data-proof-id='proof_1'>"
            "<span class='proof-title'>采集日志</span><span class='source-tag'>源头可信</span>"
            "<span class='evidence-snippet'>传感器记录</span><i class='proof-anchor-spine'></i></div></section>"
            "<aside class='result-seal value-seal-ring'>价值落地</aside>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("装饰件使用负向偏移" in issue for issue in audit["issues"]))

    def test_expression_primitive_rejects_card_like_proof_material_chip(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='价值可量化'>"
            "<style>.proof-node{height:72px;}.proof-material-chip{background:#fff;border:1px solid #dbeafe;"
            "border-radius:14px;box-shadow:0 8px 24px rgba(15,23,42,.12);}</style>"
            "<section class='claim-zone'>价值可量化</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--cut-corner-tag' data-proof-id='proof_1'>"
            "<div class='proof-material-chip'><span class='proof-index'>01</span><span class='proof-title'>采集记录</span>"
            "<span class='source-tag'>ev_log</span><span class='evidence-snippet'>源头可信</span><i class='proof-connector'></i></div>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("卡片化 CSS" in issue for issue in audit["issues"]))
        self.assertTrue(any("cut_corner_tag" in issue or "proof-material-chip" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_requires_proof_node_modifier(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node' data-proof-id='proof_1'>"
            "<span class='proof-index'>01</span><span class='proof-title'>采集记录</span>"
            "<span class='source-tag'>ev_log</span><span class='evidence-snippet'>源头可信</span><i class='proof-connector'></i>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("强制枚举结构 modifier" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_rejects_inner_anonymous_white_panel(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--spine-label' data-proof-id='proof_1'>"
            "<span class='proof-anchor-spine'></span>"
            "<div style='background: rgba(255,255,255,.85); border: 1px solid rgba(37,99,235,.15); "
            "border-radius: 8px; padding: 14px 18px;'>"
            "<span class='proof-index'>01</span><span class='proof-title'>采集记录</span>"
            "<span class='source-tag'>ev_log</span><span class='evidence-snippet'>源头可信</span>"
            "<i class='proof-connector'></i></div>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("内部匿名容器" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_requires_positive_proof_node_skeleton(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--spine-label' data-proof-id='proof_1'>"
            "<span class='proof-anchor-spine'></span>"
            "<span class='proof-index'>01</span><span class='proof-title'>采集记录</span>"
            "<span class='source-tag'>ev_log</span><span class='evidence-snippet'>源头可信</span><i class='proof-connector'></i>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("正向组件骨架" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_accepts_canonical_proof_text_group(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--bracket-anchor' data-proof-id='proof_1' style='height:72px;'>"
            "<span class='rail-attached-bracket'></span><span class='proof-index'>01</span>"
            "<div class='proof-text-group' style='background:transparent;border:0;box-shadow:none;border-radius:0;'>"
            "<span class='proof-title'>采集记录</span><span class='source-tag'>ev_log</span>"
            "<span class='evidence-snippet'>源头可信</span></div><i class='proof-connector'></i>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(any("正向组件骨架" in issue for issue in audit["issues"]), audit["issues"])
        self.assertFalse(any("内部匿名容器" in issue for issue in audit["issues"]), audit["issues"])

    def test_answer_first_proof_chain_rejects_card_like_proof_text_group(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<style>.proof-text-group{background:rgba(241,245,249,.7);border:1px solid #dbeafe;border-radius:12px;}</style>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--bracket-anchor' data-proof-id='proof_1' style='height:72px;'>"
            "<span class='rail-attached-bracket'></span><span class='proof-index'>01</span>"
            "<div class='proof-text-group'><span class='proof-title'>采集记录</span><span class='source-tag'>ev_log</span>"
            "<span class='evidence-snippet'>源头可信</span></div><i class='proof-connector'></i>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("proof-text-group 使用背景" in issue for issue in audit["issues"]))

    def test_answer_first_proof_chain_rejects_thin_proof_rail_stage(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["采集记录", "过程追踪", "结果验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<style>.evidence-flow{width:82%;height:16%;}.proof-node{height:72px;}</style>"
            "<section class='claim-zone'>数据证据转化为生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node proof-node--bracket-anchor' data-proof-id='proof_1'>"
            "<span class='rail-attached-bracket'></span><span class='proof-index'>01</span>"
            "<div class='proof-text-group' style='background:transparent;border:0;box-shadow:none;border-radius:0;'>"
            "<span class='proof-title'>采集记录</span><span class='source-tag'>ev_log</span>"
            "<span class='evidence-snippet'>源头可信</span></div><i class='proof-connector'></i>"
            "</div></section><aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="evidence_board",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("证据轨道高度或宽度不足" in issue for issue in audit["issues"]))

    def test_expression_primitive_requires_trace_and_structure_classes(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
            "core_argument": "技术指标转化为生产动作。",
            "content_points": ["传感器采集日志", "边缘异常过滤", "云端模型看板"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        good_html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='stage' data-dominant-visual='claim_three_proofs' "
            "data-creative-mode='answer_first_proof_chain' data-expression-primitive='evidence_stage' "
            "data-focus-text='价值可量化'>"
            "<section class='claim-zone'>价值可量化：数据证据 → 生产动作</section>"
            "<section class='evidence-flow'><div class='proof-node'>采集日志</div>"
            "<div class='proof-node'>过滤结果</div><div class='proof-node'>模型看板</div></section>"
            "<aside class='result-seal'>价值落地</aside>"
            "<p>源头可信、过程可追溯、结果可验证。</p>"
            "</div>"
        )
        bad_html = good_html.replace("data-expression-primitive='evidence_stage' ", "").replace("evidence-flow", "support-row")

        bad_audit = audit_design_quality_contract(
            html_fragment=bad_html,
            page=page,
            creative_director_plan=creative_plan,
        )
        good_audit = audit_design_quality_contract(
            html_fragment=good_html,
            page=page,
            creative_director_plan=creative_plan,
        )

        self.assertFalse(bad_audit["pass"])
        self.assertTrue(any("表达原语" in issue for issue in bad_audit["issues"]))
        self.assertTrue(good_audit["pass"], good_audit["issues"])

    def test_design_quality_accepts_split_visible_focus_text(self):
        page = {
            "page_index": 24,
            "title": "证据链：从技术实操到实际效益",
            "page_series_type": "practice_evidence",
        }
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain' "
            "data-expression-primitive='evidence_stage' data-focus-text='数据证据转化为生产动作'>"
            "<section class='claim-zone'><span>数据证据</span><span>转化为生产动作</span></section>"
            "<section class='evidence-flow'><div class='proof-node'>采集日志</div></section>"
            "<aside class='result-seal'>价值落地</aside></div>"
        )

        audit = audit_design_quality_contract(
            html_fragment=html,
            page=page,
            creative_director_plan={
                "creative_mode": "answer_first_proof_chain",
                "first_glance_focus": "数据证据转化为生产动作",
                "card_policy": {"max_cards": 3},
            },
        )

        self.assertTrue(audit["pass"], audit["issues"])

    def test_system_layer_stack_rejects_card_grid_and_requires_stage(self):
        page = {
            "page_index": 12,
            "title": "技术架构总览：端边云三层协同",
            "page_series_type": "architecture_system",
            "core_argument": "系统通过端边云三层协同形成稳定闭环。",
            "content_points": ["传感器采集", "边缘清洗", "云端建模", "应用反馈"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        bad_html = (
            "<div class='mimo-body-root' data-page-archetype='architecture' "
            "data-visual-motif='layered' data-dominant-visual='layered_system_diagram' "
            "data-creative-mode='large_system_map' data-expression-primitive='system_layer_stack' "
            "data-focus-text='系统通过端边云三层协同形成稳定闭环'>"
            "<div class='card'>采集</div><div class='card'>清洗</div><div class='card'>建模</div><div class='card'>反馈</div>"
            "</div>"
        )
        good_html = (
            "<div class='mimo-body-root' data-page-archetype='architecture' "
            "data-visual-motif='layered' data-dominant-visual='layered_system_diagram' "
            "data-creative-mode='large_system_map' data-expression-primitive='system_layer_stack' "
            "data-focus-text='系统通过端边云三层协同形成稳定闭环'>"
            "<p>系统通过端边云三层协同形成稳定闭环。</p>"
            "<section class='layer-stack-stage'><div class='system-boundary'>"
            "<div class='system-layer'>感知层</div><div class='system-layer'>边缘层</div><div class='system-layer'>云端层</div>"
            "<div class='layer-bus'><span class='data-flow'>数据上行</span></div><div class='application-node'>应用反馈</div>"
            "</div></section></div>"
        )

        bad_audit = audit_ai_body_fragment(
            html_fragment=bad_html,
            page=page,
            expression_type="architecture_diagram",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )
        good_audit = audit_design_quality_contract(
            html_fragment=good_html,
            page=page,
            creative_director_plan=creative_plan,
        )

        self.assertFalse(bad_audit["pass"])
        self.assertTrue(any("system_layer_stack" in issue or "系统层叠" in issue for issue in bad_audit["issues"]))
        self.assertTrue(good_audit["pass"], good_audit["issues"])

    def test_system_layer_stack_rejects_web_component_class_names(self):
        page = {
            "page_index": 12,
            "title": "技术架构总览",
            "page_series_type": "architecture_system",
            "core_argument": "系统通过分层总线形成稳定闭环。",
            "content_points": ["数据源", "总线", "模型", "应用"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)
        html = (
            "<div class='mimo-body-root' data-page-archetype='architecture' "
            "data-visual-motif='layered' data-dominant-visual='layered_system_diagram' "
            "data-creative-mode='large_system_map' data-expression-primitive='system_layer_stack' "
            "data-focus-text='分层总线形成闭环'>"
            "<p>分层总线形成闭环</p>"
            "<section class='layer-stack-stage'><div class='system-boundary'>"
            "<div class='system-layer module-card'>数据源</div>"
            "<div class='layer-bus'><span class='data-flow'>数据流</span></div>"
            "<div class='application-node output-panel'>应用输出</div>"
            "</div></section></div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="architecture_diagram",
            image_placeholders=[],
            creative_director_plan=creative_plan,
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("网页组件类名" in issue for issue in audit["issues"]))

    def test_before_after_breakthrough_gets_expression_primitives(self):
        page = {
            "page_index": 35,
            "title": "创新突破：产教协同开发历程",
            "page_series_type": "bridge_story",
            "core_argument": "校企融合让项目从课堂方案升级为可落地成果。",
            "content_points": ["需求调研", "校企共创", "成果迭代", "落地验证"],
        }
        expression_plan = build_page_expression_plan(page)
        playbook = slide_playbook_for_page(page, expression_plan)
        creative_plan = build_creative_director_plan(page, expression_plan, playbook)

        self.assertEqual(creative_plan["creative_mode"], "before_after_breakthrough")
        self.assertEqual(creative_plan["expression_primitive_contract"]["default_primitive_id"], "proof_wall")
        self.assertIn("handoff_ladder", creative_plan["expression_primitive_contract"]["allowed_primitive_ids"])

    def test_round3_page_index_coerces_summary_range_ids(self):
        coordinator = PipelineCoordinator()

        self.assertEqual(coordinator._coerce_round3_page_index("31-32_summary", 31), 31)
        self.assertEqual(coordinator._coerce_round3_page_index("page_24", 24), 24)
        self.assertEqual(coordinator._coerce_round3_page_index("summary", 37), 37)

    def test_v5_diagram_spec_uses_page_specific_process_steps(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "数据处理流程：从采集到应用",
                    "page_series_type": "architecture_system",
                    "page_goal": "说明高效可靠的数据处理流程。",
                    "core_argument": "高效、可靠的数据处理流程是AI分析准确性的前提。",
                    "ppt_text": "传感器采集田间数据→边缘网关清洗异常值→云端模型分析→农户端反馈预警",
                    "chart": {"type": "flowchart", "specification": "展示从采集到应用的流程"},
                }
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        spec = pipeline["v5_diagram_specs"][0]

        self.assertEqual(spec["diagram_type"], "process_flow")
        self.assertEqual(spec["diagram_prompt_type"], "data_flow")
        self.assertIn("processing_steps", spec["extraction_schema"])
        self.assertEqual(spec["diagram_prompt_contract"]["diagram_prompt_type"], "data_flow")
        self.assertIn("render_contract_v2", spec["diagram_prompt_contract"])
        self.assertEqual(spec["diagram_prompt_contract"]["render_contract_v2"]["connectors"]["line_width"], "2.2-3.2px normal, 4-6px for one main flow/bus/path.")
        self.assertIn("pipeline", spec["diagram_prompt_contract"]["type_specific_render_contract_v2"]["layout"])
        self.assertEqual(spec["renderer_status"], "page_specific_diagram_json")
        self.assertIn("传感器采集", spec["payload"]["steps"])
        self.assertIn("边缘清洗", spec["payload"]["steps"])
        self.assertNotEqual(spec["payload"]["steps"], ["输入", "处理", "输出", "验证"])
        self.assertIn("visual_variation_directive", spec["payload"])
        self.assertEqual(spec["payload"]["visual_variation_directive"]["composition_family"], "swimlane_operation_flow")

    def test_v5_diagram_prompt_library_classifies_core_types(self):
        library = load_diagram_prompt_library()
        self.assertEqual(library["version"], "v5_diagram_prompt_library_20260510_v3")
        self.assertIn("architecture", library["diagram_types"])
        self.assertIn("evidence_chain", library["diagram_types"])
        self.assertIn("render_contract_v2", library["global_contract"])
        self.assertIn("type_specific_render_contract_v2", library["global_contract"])

        architecture_page = {
            "title": "端-边-云三层架构",
            "page_series_type": "architecture_system",
            "core_argument": "系统通过端边云协同形成完整闭环。",
        }
        evidence_page = {
            "title": "技术证据链",
            "page_series_type": "practice_evidence",
            "core_argument": "日志、测试和截图证明系统结果可追溯。",
        }
        metrics_page = {
            "title": "实操成效指标看板",
            "page_series_type": "value_matrix",
            "core_argument": "准确率达到92%，查询耗时下降40%。",
        }

        self.assertEqual(classify_diagram_prompt_type(architecture_page, "architecture_system")[0], "architecture")
        self.assertEqual(classify_diagram_prompt_type(evidence_page, "process_flow")[0], "evidence_chain")
        self.assertEqual(classify_diagram_prompt_type(metrics_page, "value_matrix")[0], "metric_dashboard")

        contract = diagram_prompt_contract_for_page(evidence_page, "process_flow")
        self.assertEqual(contract["diagram_prompt_type"], "evidence_chain")
        self.assertIn("claim", contract["extract_schema"])
        self.assertIn("render_contract_v2", contract)
        self.assertIn("node_geometry", contract["render_contract_v2"])
        self.assertIn("Claim/value stage", contract["type_specific_render_contract_v2"]["sizes"])
        self.assertTrue(any("Start with the claim" in item for item in contract["render_contract"]))

    def test_solution_overview_visual_contract_forces_full_business_loop(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 8,
                    "title": "我们的解决方案：智慧农业物联网大数据平台",
                    "page_series_type": "mapping_bridge",
                    "page_goal": "让评委看懂平台如何从田间数据形成生产决策。",
                    "core_argument": "传感器、边缘网关、云端 AI 和农户端反馈共同形成生产闭环。",
                    "content_points": [
                        "田间传感器采集土壤、温湿度和图像数据",
                        "边缘网关完成异常过滤和断网缓存",
                        "云端 AI 识别病害并预测产量",
                        "农户 APP 和监管大屏反馈预警与农事建议",
                        "目标实现降药30%、增产15%、亩均增收5000元",
                    ],
                }
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        visual_contract = pipeline["v5_visual_contracts"][0]

        self.assertEqual(visual_contract["visual_role"], "solution_overview_hero")
        self.assertEqual(visual_contract["page_importance"], "hero_diagram_page")
        self.assertEqual(visual_contract["relationship_model"], "closed_loop")
        self.assertGreaterEqual(visual_contract["main_visual_ratio"], 0.65)
        self.assertTrue(any("田间传感器" in item for item in visual_contract["must_include"]))
        self.assertTrue(any("边缘网关" in item for item in visual_contract["must_include"]))
        self.assertTrue(any("云端 AI" in item for item in visual_contract["must_include"]))
        self.assertTrue(any("农户端" in item for item in visual_contract["must_include"]))
        self.assertIn("和技术架构页重复", visual_contract["failure_conditions"])

    def test_agenda_visual_contract_forces_directory_not_timeline(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {"page_index": 1, "title": "封面", "page_series_type": "cover_keynote"},
                {
                    "page_index": 2,
                    "title": "路演议程",
                    "page_series_type": "agenda_navigation",
                    "core_argument": "目录页要呈现章节结构和汇报节奏。",
                },
                {"page_index": 3, "title": "政策背景", "page_series_type": "evidence_board"},
                {"page_index": 4, "title": "方案总览", "page_series_type": "mapping_bridge"},
                {"page_index": 5, "title": "技术架构", "page_series_type": "architecture_system"},
                {"page_index": 6, "title": "实操验证", "page_series_type": "practice_evidence"},
                {"page_index": 7, "title": "成果价值", "page_series_type": "value_matrix"},
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = visual_contract_map(pipeline["v5_visual_contracts"])

        self.assertEqual(contracts[2]["visual_role"], "competition_agenda_directory")
        self.assertEqual(contracts[2]["relationship_model"], "chapter_directory")
        self.assertIn("image_header_band", contracts[2]["visual_pattern"])
        self.assertIn("细路线时间轴", contracts[2]["failure_conditions"])
        self.assertEqual(contracts[2]["layout_bounds"]["chapter_node_count"], "4-6")

    def test_visual_contract_distinguishes_architecture_and_process_pages(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 10,
                    "title": "技术架构总览：端-边-云三层协同",
                    "page_series_type": "architecture_system",
                    "core_argument": "传感器、边缘网关、云端平台共同形成架构闭环。",
                    "content_points": ["传感器采集", "边缘网关预处理", "云端AI分析", "应用端反馈"],
                },
                {
                    "page_index": 11,
                    "title": "数据处理流程：从采集到应用",
                    "page_series_type": "architecture_system",
                    "core_argument": "数据经过采集、清洗、分析和反馈形成可靠应用流程。",
                    "ppt_text": "传感器采集田间数据→边缘网关清洗异常值→云端模型分析→农户端反馈预警",
                    "chart": {"type": "flowchart", "specification": "展示从采集到应用的流程"},
                },
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = visual_contract_map(pipeline["v5_visual_contracts"])

        self.assertEqual(contracts[10]["relationship_model"], "layered_architecture")
        self.assertEqual(contracts[10]["visual_pattern"], "layered_system_map_with_boundary_and_data_flow")
        self.assertGreaterEqual(contracts[10]["main_visual_ratio"], 0.6)
        self.assertEqual(contracts[11]["relationship_model"], "swimlane_flow")
        self.assertIn("swimlane", contracts[11]["visual_pattern"])
        self.assertIn("相邻流程页不得使用同一种横向节点链", contracts[11]["anti_repetition"])
        self.assertIn("svg_viewbox_inner_margin_ratio", contracts[10]["layout_bounds"])

    def test_evidence_contract_and_prompt_include_slot_bounds_and_svg_safety(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 19,
                    "title": "实操一：多源传感器数据采集与传输",
                    "page_series_type": "practice_evidence",
                    "core_argument": "通过现场部署和数据样例证明采集链路可运行。",
                    "content_points": ["传感器部署现场", "LoRa网关传输", "输入数据样例"],
                }
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = page_contract_map(pipeline["v5_page_contracts"])
        visual_contracts = visual_contract_map(pipeline["v5_visual_contracts"])
        placeholders = _image_placeholder_brief(outline["pages"][0])
        prompt = _body_user_prompt(
            deck={"project_name": "智慧农业物联网大数据平台"},
            shell_spec=pipeline["shell_spec"],
            page=outline["pages"][0],
            decision=pipeline["layout_decisions"][0],
            strategy_brief={"subgoal": "proof"},
            recent_family_context=[],
            all_pages=outline["pages"],
            deck_design_spec=pipeline["deck_design_spec"],
            page_contract=contracts[19],
            diagram_spec=pipeline["v5_diagram_specs"][0],
            visual_contract=visual_contracts[19],
        )
        payload = json.loads(prompt)

        self.assertTrue(placeholders)
        self.assertIn("单个占位禁止超过 50%", placeholders[0]["area_bounds"])
        self.assertEqual(payload["visual_contract"]["visual_role"], "evidence_proof_board")
        self.assertEqual(payload["visual_contract"]["evidence_slot_bounds"]["max_total_placeholder_area_ratio"], 0.52)
        self.assertTrue(payload["hard_rules"]["body_root_overflow_hidden"])
        self.assertEqual(payload["hard_rules"]["svg_safe_area_inset_ratio"], 0.06)
        self.assertIn("主证据位占主体区 28%-48%", payload["image_placeholder_requirements"]["size_rule"])
        self.assertIn("safe_bounds", payload["canvas_contract"])

    def test_evidence_chain_page_gets_parameterized_diagram_contract(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 24,
                    "title": "技术证据链：从数据到价值",
                    "page_series_type": "practice_evidence",
                    "core_argument": "演示完整呈现了数据采集、边缘处理、云端智能和应用赋能的技术闭环。",
                    "content_points": ["传感器采集", "边缘清洗", "云端分析", "终端反馈"],
                }
            ],
        }

        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        contracts = page_contract_map(pipeline["v5_page_contracts"])
        visual_contracts = visual_contract_map(pipeline["v5_visual_contracts"])
        diagram_spec = pipeline["v5_diagram_specs"][0]
        prompt = _body_user_prompt(
            deck={"project_name": "智慧农业物联网大数据平台"},
            shell_spec=pipeline["shell_spec"],
            page=outline["pages"][0],
            decision=pipeline["layout_decisions"][0],
            strategy_brief={"subgoal": "proof_chain"},
            recent_family_context=[],
            all_pages=outline["pages"],
            deck_design_spec=pipeline["deck_design_spec"],
            page_contract=contracts[24],
            diagram_spec=diagram_spec,
            visual_contract=visual_contracts[24],
        )
        payload = json.loads(prompt)

        self.assertEqual(_image_placeholder_brief(outline["pages"][0]), [])
        self.assertEqual(diagram_spec["diagram_type"], "process_flow")
        self.assertEqual(diagram_spec["payload"]["diagram_subtype"], "evidence_chain")
        self.assertEqual(diagram_spec["payload"]["layout_pattern"], "answer_first_value_proof")
        self.assertEqual([zone["id"] for zone in diagram_spec["payload"]["zones"]], ["hero_claim", "proof_strip", "result_badge"])
        self.assertEqual(diagram_spec["payload"]["bbox_layout_blueprint"]["version"], "evidence_chain_bbox_layout_v1")
        self.assertEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["regions"][0]["id"],
            "claim_stage",
        )
        self.assertEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_bboxes"][1]["bbox"]["x"],
            0.385,
        )
        self.assertGreaterEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["regions"][2]["bbox"]["h"],
            0.30,
        )
        self.assertGreaterEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_bboxes"][1]["bbox"]["h"],
            0.22,
        )
        self.assertIn(
            "source-tag",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["required_internal_classes"],
        )
        self.assertIn(
            "claim-stage-plate",
            diagram_spec["payload"]["bbox_layout_blueprint"]["visual_finish_contract"]["claim_stage"]["required_classes"],
        )
        self.assertIn(
            "value-seal-ring",
            diagram_spec["payload"]["bbox_layout_blueprint"]["visual_finish_contract"]["result_seal"]["required_classes"],
        )
        self.assertIn(
            "proof-rail-axis",
            diagram_spec["payload"]["bbox_layout_blueprint"]["visual_finish_contract"]["proof_rail"]["required_classes"],
        )
        self.assertIn(
            "card",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["forbidden_class_tokens"],
        )
        self.assertIn(
            "proof-anchor-spine",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["required_surface_cues"],
        )
        self.assertEqual(
            sorted(diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["allowed_structures"].keys()),
            ["bracket_anchor", "spine_label"],
        )
        self.assertIn(
            "proof-node--spine-label",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["allowed_structures"][
                "spine_label"
            ]["required_classes"],
        )
        self.assertIn(
            "proof-title",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"][
                "required_internal_classes"
            ],
        )
        self.assertIn(
            "data-proof-id",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "required_data_attrs"
            ],
        )
        self.assertIn(
            "long vertical connector crossing more than one bbox",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "forbid"
            ],
        )
        self.assertIn(
            "proof-node compressed into a thin strip",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "forbid"
            ],
        )
        self.assertIn(
            "source-tag font-size below 12px",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "forbid"
            ],
        )
        self.assertIn(
            "placing result-seal with right/bottom instead of bbox left/top/width/height",
            diagram_spec["payload"]["bbox_layout_blueprint"]["placement_contract"]["forbid"],
        )
        self.assertIn(
            "left:0",
            diagram_spec["payload"]["bbox_layout_blueprint"]["placement_contract"]["decorative_css"],
        )
        self.assertIn(
            ">=72px",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "size_rule"
            ],
        )
        self.assertIn(
            "source-tag font-size >=12px",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["bbox_binding_contract"][
                "typography_rule"
            ],
        )
        self.assertIn(
            "background: rgba(255,255,255,*) on .proof-node",
            diagram_spec["payload"]["bbox_layout_blueprint"]["proof_node_visual_contract"]["forbidden_css"],
        )
        self.assertEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["legibility_contract"]["contrast"]["min_text_contrast_ratio"],
            4.5,
        )
        self.assertEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["legibility_contract"]["opacity"]["forbid_text_opacity_below"],
            0.82,
        )
        self.assertEqual(
            diagram_spec["payload"]["bbox_layout_blueprint"]["legibility_contract"]["opacity"][
                "result_seal_background_alpha_min"
            ],
            0.88,
        )
        self.assertIn(
            "position:absolute",
            diagram_spec["payload"]["bbox_layout_blueprint"]["placement_contract"]["region_css"],
        )
        self.assertTrue(
            any(
                "display:flex on .mimo-body-root" in item
                for item in diagram_spec["payload"]["bbox_layout_blueprint"]["placement_contract"]["forbid"]
            )
        )
        self.assertEqual(len(diagram_spec["payload"]["nodes"]), 4)
        self.assertEqual(len(diagram_spec["payload"]["edges"]), 3)
        self.assertEqual(diagram_spec["payload"]["edges"][0]["action"], "清洗去噪")
        self.assertNotIn("label", diagram_spec["payload"]["edges"][0])
        self.assertEqual(diagram_spec["payload"]["composition_bounds"]["min_occupied_height_ratio"], 0.68)
        self.assertEqual(diagram_spec["payload"]["hero_focus"]["target_node"], "hero_claim")
        value_pos = diagram_spec["payload"]["nodes"][3]["position"]
        proof_pos = diagram_spec["payload"]["nodes"][0]["position"]
        self.assertGreater(value_pos["w"] * value_pos["h"], proof_pos["w"] * proof_pos["h"])
        self.assertIn("一个大箭头", diagram_spec["payload"]["visual_rules"]["path_rule"])
        self.assertIn("连接线本身不要放文字", diagram_spec["payload"]["visual_rules"]["edge_label_rule"])
        self.assertEqual(visual_contracts[24]["relationship_model"], "proof_chain_to_value")
        self.assertEqual(visual_contracts[24]["diagram_clarity_rules"]["line_crossing"], "forbidden")
        self.assertEqual(visual_contracts[24]["diagram_clarity_rules"]["value_node"], "largest_and_brightest")
        self.assertEqual(visual_contracts[24]["diagram_clarity_rules"]["layout_family"], "answer_first_claim_three_proofs")
        self.assertEqual(visual_contracts[24]["diagram_clarity_rules"]["max_primary_message_count"], 1)
        self.assertGreaterEqual(visual_contracts[24]["main_visual_ratio"], 0.78)
        self.assertEqual(payload["diagram_execution_requirements"]["type"], "evidence_chain")
        self.assertEqual(payload["diagram_execution_requirements"]["zones"][0]["id"], "hero_claim")
        self.assertEqual(
            payload["diagram_execution_requirements"]["bbox_layout_blueprint"]["regions"][0]["class_name"],
            "claim-zone",
        )
        self.assertIn("bbox", payload["diagram_execution_requirements"]["bbox_rule"])
        self.assertIn("data-proof-id", payload["diagram_execution_requirements"]["bbox_rule"])
        self.assertIn("proof-index", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("proof-title", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn(">=72px", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("source-tag >=12px", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("box-shadow", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("rgba(255,255,255,*)", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("proof-anchor-spine", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("spine_label", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("proof-node--bracket-anchor", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("禁止自创第三种结构", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("proof_node_bboxes.id", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("长度 <=24px", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("禁止跨 bbox 长竖线", payload["diagram_execution_requirements"]["proof_node_visual_rule"])
        self.assertIn("claim-stage-plate", payload["diagram_execution_requirements"]["visual_finish_rule"])
        self.assertIn("value-seal-ring", payload["diagram_execution_requirements"]["visual_finish_rule"])
        self.assertIn("proof-rail-axis", payload["diagram_execution_requirements"]["visual_finish_rule"])
        self.assertIn("position:absolute", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("禁止使用负", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("任何可见元素", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("伪元素也禁止负偏移", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("result-seal 必须放在 result_seal bbox", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("不得 left:-4px", payload["diagram_execution_requirements"]["placement_rule"])
        self.assertIn("对比度", payload["diagram_execution_requirements"]["legibility_rule"])
        self.assertIn("0.82", payload["diagram_execution_requirements"]["legibility_rule"])
        self.assertIn("20-28px/800", payload["diagram_execution_requirements"]["legibility_rule"])
        self.assertIn("答案优先版式", payload["diagram_execution_requirements"]["layout"])
        self.assertIn("不要把文字压在线条上", payload["diagram_execution_requirements"]["edge_labels"])
        self.assertEqual(payload["diagram_execution_requirements"]["composition_bounds"]["top_empty_limit_ratio"], 0.10)
        self.assertEqual(payload["diagram_execution_requirements"]["hero_focus"]["target_node"], "hero_claim")
        self.assertIn("第一眼看不到核心主张", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("波浪链路版式", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("价值节点不突出", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("rgba(255,255,255,*) proof-node background", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("full bordered proof-node rectangle", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("proof-node outside proof_node_bboxes", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("proof-node compressed into thin strip", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("source-tag font-size below 12px", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("proof-title font-size below 16px", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("long vertical connector crossing proof-node bboxes", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("negative top/right/bottom/left values on any element", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("negative offsets on ::before/::after pseudo elements", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("text opacity below 82%", payload["diagram_execution_requirements"]["forbidden"])
        self.assertIn("16:9/4:3/1:1/9:16 建议比例", payload["diagram_execution_requirements"]["forbidden"])
        self.assertTrue(any("diagram_execution_requirements.type=evidence_chain" in item for item in payload["design_direction"]))
        self.assertTrue(any("legibility_rule" in item for item in payload["design_direction"]))
        self.assertEqual(payload["expression_primitive_contract"]["default_primitive_id"], "evidence_stage")
        self.assertEqual(payload["diagram_construction_contract"]["version"], "v5_diagram_render_contract_v2")
        self.assertEqual(payload["diagram_construction_contract"]["priority"], "hard_before_html")
        self.assertIn("node_geometry", payload["diagram_construction_contract"]["global"])
        self.assertIn("composition_strength", payload["diagram_construction_contract"]["global"])
        self.assertIn("proof nodes", payload["diagram_construction_contract"]["type_specific"]["sizes"])
        self.assertIn("anti_card", payload["diagram_construction_contract"]["type_specific"])
        self.assertIn("30%-45%", payload["diagram_construction_contract"]["type_specific"]["composition"])
        self.assertTrue(any("diagram_construction_contract" in item for item in payload["design_direction"]))
        self.assertIn("data-expression-primitive", payload["output_contract"]["root_required_data_attrs"])
        self.assertTrue(any("expression_primitive_contract" in item for item in payload["design_direction"]))
        self.assertEqual(
            payload["competition_design_director"]["ruipu_image_ppt_style"]["instant_comprehension_model"]["one_second"],
            "第一眼只能让观众读到一个主张、一个产品/对象、一个强数字或一个画面焦点。",
        )
        self.assertTrue(payload["competition_design_director"]["ruipu_image_ppt_style"]["observed_patterns"])
        self.assertIn(
            "answer_first_proof",
            payload["competition_design_director"]["ruipu_image_ppt_style"]["page_archetypes"],
        )
        self.assertIn("rapidesign_dynamic_case_knowledge_v2", payload["competition_design_director"])
        self.assertEqual(
            payload["competition_design_director"]["rapidesign_dynamic_case_knowledge_v2"]["required_design_decision_before_html"]["must_choose"],
            ["page_archetype", "visual_motif", "dominant_visual", "evidence_structure"],
        )
        self.assertTrue(payload["hard_rules"]["must_choose_visual_motif_before_html"])
        self.assertIn("data-visual-motif", payload["output_contract"]["root_required_data_attrs"])
        self.assertIn("architecture", payload["rapidesign_v2_execution_contract"]["allowed_page_archetypes"])

    def test_v5_architecture_pages_do_not_require_device_evidence_slots(self):
        page = {
            "page_index": 10,
            "title": "技术架构总览：端-边-云三层协同",
            "page_series_type": "architecture_system",
            "core_argument": "传感器、边缘网关、云端平台共同形成架构闭环。",
            "content_points": ["传感器采集", "边缘网关预处理", "云端AI分析"],
        }

        placeholders = _image_placeholder_brief(page)
        audit = audit_ai_body_fragment(
            html_fragment="<div class='mimo-body-root'><svg></svg><p>田间感知层 边缘网关层 云端平台层 应用决策层</p></div>",
            page=page,
            expression_type=_professional_expression_type(page),
            image_placeholders=placeholders,
        )

        device_slots = [item for item in placeholders if item["image_type"] == "设备图片"]
        self.assertTrue(device_slots)
        self.assertFalse(device_slots[0]["required"])
        self.assertFalse(any("缺少必要图片/证据占位" in issue for issue in audit["issues"]))

    def test_v5_needs_review_classification_splits_assets_and_layout(self):
        page = {
            "page_index": 20,
            "title": "实操环节二：边缘网关实时预处理",
            "page_series_type": "practice_evidence",
            "core_argument": "边缘网关完成实时预处理。",
        }
        placeholders = [
            {"image_type": "实操现场图片", "required": True},
            {"image_type": "设备图片", "required": True},
        ]
        asset_classification = _classify_body_review(
            {
                "pass": False,
                "issues": ["缺少必要图片/证据占位：实操现场图片。", "缺少必要图片/证据占位：设备图片。"],
            },
            page=page,
            image_placeholders=placeholders,
        )
        layout_classification = _classify_body_review(
            {"pass": False, "issues": ["卡片/面板数量过多，呈现方式单调。"]},
            page={**page, "page_series_type": "architecture_system"},
            image_placeholders=[],
        )

        self.assertEqual(asset_classification["primary_category"], "asset_missing")
        self.assertEqual(asset_classification["priority_repair_strategy"], "asset_generation_or_evidence_slot")
        self.assertTrue(any("实操现场图片" in action for action in asset_classification["actions"]))
        self.assertEqual(layout_classification["primary_category"], "layout_monotony")
        self.assertEqual(layout_classification["priority_repair_strategy"], "visual_variation_redesign")

    def test_v5_ab_structural_gate_does_not_treat_asset_missing_as_structural_failure(self):
        gate = _ab_candidate_structural_gate(
            {
                "pass": False,
                "issues": ["缺少必要图片/证据占位：实操现场图片。"],
                "review_classification": {"primary_category": "asset_missing"},
            }
        )

        self.assertTrue(gate["pass"])
        self.assertEqual(gate["critical_reasons"], [])

    def test_v5_needs_review_classification_detects_expression_primitive_failure(self):
        classification = _classify_body_review(
            {
                "pass": False,
                "issues": [
                    "system_layer_stack 被实现成卡片/表格，缺少系统层叠主图。",
                    "所选表达原语缺少必要结构类名。",
                ],
            },
            page={"page_index": 12, "title": "数据流水线", "page_series_type": "architecture_system"},
            image_placeholders=[],
        )

        self.assertIn("expression_primitive_missing", classification["categories"])
        self.assertEqual(classification["primary_category"], "expression_primitive_missing")
        self.assertEqual(classification["priority_repair_strategy"], "visual_variation_redesign")

    def test_render_repair_timeout_preserves_existing_body_and_continues(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "核心证据链展示",
                    "page_series_type": "practice_evidence",
                    "core_argument": "从传感器采集到生产反馈形成可追溯技术闭环。",
                    "content_points": ["采集日志", "边缘过滤", "模型看板"],
                },
                {
                    "page_index": 2,
                    "title": "经济价值：可量化的增产降本",
                    "page_series_type": "value_matrix",
                    "core_argument": "亩均增收5000元，降本15%。",
                    "content_points": ["亩均增收5000元", "农药降低30%"],
                },
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        for composition in pipeline["composition_plans"]:
            composition["body_mode"] = "ai_direct"
            composition["body_html_fragment"] = "<div class='mimo-body-root' data-focus-text='旧页面'>旧页面</div>"
        render_audit = {
            "failed_count": 2,
            "items": [
                {"page_index": 1, "pass": False, "issues": ["主视觉过小"]},
                {"page_index": 2, "pass": False, "issues": ["文字过多"]},
            ],
        }

        async def slow_repair(**kwargs):
            await asyncio.sleep(3)
            return "<div class='mimo-body-root'>新页面</div>", {"pass": True}

        async def run_repair():
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_RENDER_REPAIR_PAGE_TIMEOUT_SECONDS": "1",
                    "PPT_V5_RENDER_REPAIR_TOTAL_TIMEOUT_SECONDS": "3",
                    "PPT_V5_RENDER_REPAIR_MAX_ATTEMPTS": "1",
                    "PPT_V5_RENDER_REPAIR_MAX_PAGES": "2",
                },
                clear=False,
            ), patch("app.services.ppt.v5.ai_passes._request_direct_body_html", side_effect=slow_repair):
                return await repair_ai_design_passes_from_render_audit(
                    outline,
                    {"project_name": "智慧农业物联网大数据平台"},
                    pipeline,
                    render_audit,
                )

        result = asyncio.run(run_repair())
        repair_pass = result["cutover_readiness"]["render_layout_repair_pass"]

        self.assertEqual(repair_pass["processed_count"], 2)
        self.assertEqual(repair_pass["timeout_count"], 2)
        self.assertEqual(repair_pass["repaired_count"], 0)
        self.assertTrue(all(item["preserved_existing_body"] for item in repair_pass["pages"]))
        self.assertEqual(result["composition_plans"][0]["body_html_fragment"], "<div class='mimo-body-root' data-focus-text='旧页面'>旧页面</div>")

    def test_render_repair_pass_carries_expression_primitive_contract(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构总览：端边云三层协同",
                    "page_series_type": "architecture_system",
                    "core_argument": "系统通过端边云三层协同形成稳定闭环。",
                    "content_points": ["传感器采集", "边缘清洗", "云端建模", "应用反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        pipeline["composition_plans"][0]["body_mode"] = "ai_direct"
        pipeline["composition_plans"][0]["body_html_fragment"] = "<div class='mimo-body-root'>旧页面</div>"
        pipeline["composition_plans"][0]["ai_body_audit"] = {
            "pass": False,
            "issues": ["system_layer_stack 被实现成卡片/表格，缺少系统层叠主图。"],
        }
        render_audit = {
            "failed_count": 1,
            "items": [
                {
                    "page_index": 1,
                    "pass": False,
                    "issues": ["主体区重复外层标题。"],
                    "metrics": {
                        "rootAttrs": {
                            "creativeMode": "large_system_map",
                            "expressionPrimitive": "system_layer_stack",
                        }
                    },
                }
            ],
        }
        captured = {}

        async def capture_repair(**kwargs):
            captured["repair_feedback"] = kwargs.get("initial_repair_feedback")
            return (
                "<div class='mimo-body-root' data-page-archetype='architecture' data-visual-motif='layered' "
                "data-dominant-visual='layered_system_diagram' data-creative-mode='large_system_map' "
                "data-expression-primitive='system_layer_stack' data-focus-text='端边云稳定闭环'>"
                "<section class='layer-stack-stage'><div class='system-boundary'>"
                "<div class='system-layer'>感知层</div><div class='layer-bus'><span class='data-flow'>数据流</span></div>"
                "<div class='application-node'>反馈</div></div></section></div>",
                {"pass": True},
            )

        async def run_repair():
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_RENDER_REPAIR_PAGE_TIMEOUT_SECONDS": "5",
                    "PPT_V5_RENDER_REPAIR_TOTAL_TIMEOUT_SECONDS": "10",
                    "PPT_V5_RENDER_REPAIR_MAX_ATTEMPTS": "1",
                    "PPT_V5_RENDER_REPAIR_MAX_PAGES": "1",
                },
                clear=False,
            ), patch("app.services.ppt.v5.ai_passes._request_direct_body_html", side_effect=capture_repair):
                return await repair_ai_design_passes_from_render_audit(
                    outline,
                    {"project_name": "智慧农业物联网大数据平台"},
                    pipeline,
                    render_audit,
                )

        result = asyncio.run(run_repair())
        feedback = captured["repair_feedback"]

        self.assertEqual(feedback["expression_primitive_repair_contract"]["selected_primitive"], "system_layer_stack")
        self.assertIn("layer-stack-stage", feedback["expression_primitive_repair_contract"]["required_classes"])
        self.assertIn("previous_body_audit_issues", feedback)
        self.assertIn("expression_primitive_missing", feedback["review_classification"]["categories"])
        self.assertEqual(result["cutover_readiness"]["render_layout_repair_pass"]["repaired_count"], 1)

    def test_render_repair_maps_subset_render_index_to_original_page_index(self):
        outline = {
            "project": {"name": "智慧农业物联网大数据平台"},
            "pages": [
                {"page_index": 1, "title": "封面", "page_series_type": "cover_keynote"},
                {"page_index": 2, "title": "汇报大纲", "page_series_type": "agenda_navigation"},
                {
                    "page_index": 12,
                    "title": "数据流水线",
                    "page_series_type": "architecture_system",
                    "core_argument": "从采集到价值形成闭环。",
                    "content_points": ["采集", "边缘清洗", "云端建模", "应用反馈"],
                },
            ],
        }
        pipeline = build_clean_pipeline(outline, {"project_name": "智慧农业物联网大数据平台"})
        for composition in pipeline["composition_plans"]:
            if composition.get("page_index") == 12:
                composition["body_mode"] = "ai_direct"
                composition["body_html_fragment"] = "<div class='mimo-body-root'>旧 P12</div>"
                composition["ai_body_audit"] = {
                    "pass": False,
                    "issues": ["system_layer_stack 缺少 layer-stack-stage 主舞台。"],
                }
        render_audit = {
            "failed_count": 1,
            "items": [
                {
                    "page_index": 1,
                    "title": "数据流水线",
                    "page_series_type": "architecture_system",
                    "pass": False,
                    "issues": ["主体区重复外层标题。"],
                    "metrics": {
                        "rootAttrs": {
                            "creativeMode": "large_system_map",
                            "expressionPrimitive": "system_layer_stack",
                        }
                    },
                }
            ],
        }
        captured = {}

        async def capture_repair(**kwargs):
            captured["page"] = kwargs.get("page")
            captured["repair_feedback"] = kwargs.get("initial_repair_feedback")
            return (
                "<div class='mimo-body-root' data-page-archetype='architecture' data-visual-motif='layered' "
                "data-dominant-visual='layered_system_diagram' data-creative-mode='large_system_map' "
                "data-expression-primitive='system_layer_stack' data-focus-text='从采集到价值形成闭环'>"
                "<section class='layer-stack-stage'><div class='system-boundary'>"
                "<div class='system-layer'>采集层</div><div class='layer-bus'><span class='data-flow'>数据流</span></div>"
                "<div class='application-node'>应用反馈</div></div></section></div>",
                {"pass": True},
            )

        async def run_repair():
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_RENDER_REPAIR_PAGE_TIMEOUT_SECONDS": "5",
                    "PPT_V5_RENDER_REPAIR_TOTAL_TIMEOUT_SECONDS": "10",
                    "PPT_V5_RENDER_REPAIR_MAX_ATTEMPTS": "1",
                    "PPT_V5_RENDER_REPAIR_MAX_PAGES": "1",
                },
                clear=False,
            ), patch("app.services.ppt.v5.ai_passes._request_direct_body_html", side_effect=capture_repair):
                return await repair_ai_design_passes_from_render_audit(
                    outline,
                    {"project_name": "智慧农业物联网大数据平台"},
                    pipeline,
                    render_audit,
                )

        result = asyncio.run(run_repair())
        repair_page = result["cutover_readiness"]["render_layout_repair_pass"]["pages"][0]

        self.assertEqual(captured["page"]["page_index"], 12)
        self.assertEqual(captured["repair_feedback"]["source_render_page_index"], 1)
        self.assertEqual(repair_page["page_index"], 12)
        self.assertEqual(repair_page["source_render_page_index"], 1)

    def test_v5_deterministic_cleanup_handles_duplicate_title_small_text_and_overflow(self):
        service = PPTService()
        html = """
        <html><head></head><body>
          <section class="shell-body">
            <div class="mimo-body-root">
              <div style="font-size:18px">政策背景与行业机遇</div>
              <span style="font-size:10px">国家战略方向</span>
              <div class="application-node" style="transform: translate(100%, -50%);">闭环输出</div>
            </div>
          </section>
          <footer class="shell-footer">03 / 38</footer>
        </body></html>
        """
        cleaned, report = service._apply_v5_deterministic_render_cleanup(
            html_pages=[html],
            page_meta_list=[{"page_index": 1, "title": "政策背景与行业机遇"}],
            render_layout_audit={
                "failed_count": 1,
                "items": [
                    {
                        "page_index": 1,
                        "title": "政策背景与行业机遇",
                        "pass": False,
                        "issues": ["主体区重复外层标题。", "主体区存在过小文字，截图/投屏阅读风险高。", "主体区存在元素越界。"],
                    }
                ],
            },
        )

        _, body_part, _ = service._split_v5_shell_body(cleaned[0])
        self.assertEqual(report["changed_count"], 1)
        self.assertNotIn("政策背景与行业机遇", body_part)
        self.assertIn("font-size:12px", body_part)
        self.assertIn("data-v5-deterministic-cleanup", cleaned[0])
        self.assertIn("application-node", cleaned[0])

    def test_v5_render_audit_blocks_hard_failures_but_not_soft_visual_warnings(self):
        service = PPTService()
        hard = {
            "items": [
                {"page_index": 1, "pass": False, "issues": ["主体区存在过小文字，截图/投屏阅读风险高。"]},
                {"page_index": 2, "pass": False, "issues": ["主视觉面积不足，页面像文字/卡片堆叠。"]},
            ]
        }
        soft = {
            "items": [
                {"page_index": 2, "pass": False, "issues": ["主视觉面积不足，页面像文字/卡片堆叠。", "卡片/面板数量过多，结构同质化风险高。"]},
            ]
        }

        self.assertEqual([item["page_index"] for item in service._v5_blocking_render_audit_failures(hard)], [1])
        self.assertEqual(service._v5_blocking_render_audit_failures(soft), [])

    def test_controlled_diagram_renderer_outputs_auditable_svg_fragment(self):
        diagram_spec = {
            "diagram_type": "process_flow",
            "payload": {
                "steps": ["数据采集", "边缘清洗", "云端分析", "预警反馈"],
                "outcome": "形成闭环验证",
            },
        }

        rendered = render_controlled_diagram_svg(diagram_spec, width=900, height=360)
        fragment = _controlled_diagram_body_fragment(
            rendered,
            {"required_content": ["采集到反馈形成可追溯闭环。"]},
            [{"image_type": "设备图片", "required": True}],
        )

        self.assertEqual(rendered["status"], "ok")
        self.assertIn("<svg", rendered["svg"])
        self.assertIn("data-v5-controlled-diagram", rendered["svg"])
        self.assertIn("mimo-body-root", fragment)
        self.assertIn("mimo-image-placeholder", fragment)
        self.assertIn("采集到反馈形成可追溯闭环", fragment)

    def test_clean_pipeline_keeps_role_and_contract_aligned(self):
        outline = {
            "project": {"name": "农业监测终端"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "研发历程：里程碑与问题复盘",
                    "page_series_type": "journey_timeline",
                    "core_argument": "从测试问题复盘到质量改进形成稳定版本收敛。",
                }
            ],
        }

        result = build_clean_pipeline(outline, {"theme": "clean-formal"})
        narrative = result["narrative_graph"][0]
        layout = result["layout_decisions"][0]
        contract = result["render_contracts"][0]
        composition = result["composition_plans"][0]
        svg_schema = result["svg_schemas"][0]

        self.assertEqual(narrative["narrative_role"], "retrospective_improvement")
        self.assertEqual(layout["layout_skeleton"], "retrospective_split")
        self.assertEqual(contract["layout_skeleton"], "retrospective_split")
        self.assertEqual(contract["motion_scope"], "svg-family")
        self.assertEqual(composition["composition_id"], "left_timeline_right_retro")
        self.assertEqual(composition["visual_intent"], "timeline_retro")
        self.assertIn("contrast_issues_and_fixes", composition["body_goals"])
        self.assertEqual(svg_schema["svg_kind"], "timeline_path")

    def test_composition_plans_do_not_only_follow_legacy_layout_skeleton(self):
        outline = {
            "project": {"name": "价值表达验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "应用价值：综合效益与推广基础",
                    "page_series_type": "value_matrix",
                    "content_points": ["推广基础", "综合效益", "复用价值", "推广路径"],
                    "core_argument": "强调场景可复制和推广基础。",
                },
                {
                    "page_index": 2,
                    "title": "量化结果：指标改善与成效证明",
                    "page_series_type": "value_matrix",
                    "content_points": ["量化结果", "指标改善", "收益提升", "成效证明"],
                    "core_argument": "强调量化结果、指标变化和成效证明。",
                },
            ],
        }

        result = build_clean_pipeline(outline, {"theme": "clean-formal"})
        first_layout = result["layout_decisions"][0]
        second_layout = result["layout_decisions"][1]
        first_composition = result["composition_plans"][0]
        second_composition = result["composition_plans"][1]

        self.assertEqual(first_layout["layout_skeleton"], "scenario_grid")
        self.assertEqual(second_layout["layout_skeleton"], "scenario_grid")
        self.assertEqual(first_composition["visual_intent"], "scenario_value")
        self.assertEqual(second_composition["visual_intent"], "value_evidence")
        self.assertEqual(first_composition["composition_id"], "scenario_board_metric_side")
        self.assertEqual(second_composition["composition_id"], "top_value_statement_bottom_evidence")

    def test_definition_support_and_evidence_roles_reduce_blank_with_content_goals(self):
        outline = {
            "project": {"name": "前半段语义增强"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "政策与产业背景",
                    "page_series_type": "evidence_board",
                    "content_points": ["政策依据", "行业需求", "痛点证据"],
                    "core_argument": "结合政策背景、产业需求和现实痛点给出可信证据。",
                },
                {
                    "page_index": 2,
                    "title": "项目定义与范围边界",
                    "page_series_type": "definition_canvas",
                    "content_points": ["研究对象", "业务边界", "约束条件"],
                    "core_argument": "明确项目定义、边界范围和约束条件。",
                },
                {
                    "page_index": 3,
                    "title": "方案支撑逻辑",
                    "page_series_type": "content_support",
                    "content_points": ["处理流程", "支撑理由", "关键步骤"],
                    "core_argument": "按步骤组织支撑论证，说明方案成立的原因。",
                },
            ],
        }

        result = build_clean_pipeline(outline, {"theme": "clean-formal"})
        evidence_comp = result["composition_plans"][0]
        definition_comp = result["composition_plans"][1]
        support_comp = result["composition_plans"][2]

        self.assertEqual(evidence_comp["composition_id"], "evidence_mosaic_insight")
        self.assertEqual(evidence_comp["visual_intent"], "evidence_mosaic")
        self.assertIn("anchor_proof", evidence_comp["body_goals"])
        self.assertEqual(definition_comp["composition_id"], "definition_split_focus")
        self.assertEqual(definition_comp["visual_intent"], "definition_scope")
        self.assertIn("state_constraints", definition_comp["body_goals"])
        self.assertEqual(support_comp["composition_id"], "support_stack_focus")
        self.assertEqual(support_comp["visual_intent"], "support_stack")
        self.assertIn("sequence_supporting_steps", support_comp["body_goals"])

    def test_unclear_pages_do_not_fallback_to_legacy_skeleton_templates(self):
        outline = {
            "project": {"name": "不明确页面验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "项目封面",
                    "page_series_type": "cover_keynote",
                    "content_points": ["项目概览"],
                },
                {
                    "page_index": 2,
                    "title": "说明页",
                    "page_series_type": "misc_page",
                    "content_points": [],
                    "core_argument": "",
                    "page_goal": "",
                }
            ],
        }

        result = build_clean_pipeline(outline, {"theme": "clean-formal"})
        composition = result["composition_plans"][1]
        html = render_v5_html_pages(outline, {"theme": "clean-formal"})[1]

        self.assertEqual(composition["composition_id"], "blank_body")
        self.assertEqual(composition["visual_intent"], "unclear")
        self.assertEqual(composition["body_goals"], [])
        self.assertIn('data-composition-id="blank_body"', html)

    def test_blank_body_is_treated_as_pending_not_pass(self):
        outline = {
            "project": {"name": "空主体态审核"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "项目封面",
                    "page_series_type": "cover_keynote",
                    "content_points": ["项目概览"],
                },
                {
                    "page_index": 2,
                    "title": "说明页",
                    "page_series_type": "misc_page",
                    "content_points": [],
                    "core_argument": "",
                }
            ],
        }

        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        html = render_v5_html_pages(outline, {"theme": "clean-formal"})[1]
        report = review_v5_html_page(
            html,
            outline["pages"][1],
            pipeline["layout_decisions"][1],
            pipeline["render_contracts"][1],
            pipeline["composition_plans"][1],
        )

        self.assertFalse(report["pass"])
        self.assertTrue(any("blank composition" in issue for issue in report["issues"]))

    def test_render_v5_html_pages_outputs_independent_html_for_first_batch(self):
        outline = {
            "project": {"name": "V5 首批迁移验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "V5 路演封面",
                    "page_series_type": "cover_keynote",
                    "content_points": ["智能巡检", "闭环处置", "工程化表达"],
                    "core_argument": "用 V5 clean renderer 直接输出 PPT 式 HTML。",
                },
                {
                    "page_index": 2,
                    "title": "汇报路径",
                    "page_series_type": "agenda_navigation",
                    "content_points": ["项目背景", "方案链路", "协作机制", "价值结果"],
                    "core_argument": "目录页要像路演导航，不是网页列表。",
                },
                {
                    "page_index": 3,
                    "title": "研发历程：里程碑与问题复盘",
                    "page_series_type": "journey_timeline",
                    "content_points": ["需求调研", "原型开发", "测试验证", "问题复盘", "质量改进"],
                    "core_argument": "从问题复盘到质量改进形成稳定版本收敛。",
                },
                {
                    "page_index": 4,
                    "title": "团队协作与分工",
                    "page_series_type": "collaboration_matrix",
                    "content_points": ["岗位职责", "任务交接", "异常升级", "应急补位"],
                    "core_argument": "通过交接链路和应急补位构成协作闭环。",
                },
                {
                    "page_index": 5,
                    "title": "应用价值：综合效益与推广基础",
                    "page_series_type": "value_matrix",
                    "content_points": ["推广基础", "综合效益", "复用价值", "推广路径", "落地场景"],
                    "core_argument": "平台化表达要突出综合效益和复制价值。",
                },
            ],
        }

        pages = render_v5_html_pages(outline, {"theme": "clean-formal"})

        self.assertEqual(len(pages), 5)
        self.assertTrue(all('data-v5-clean="true"' in page for page in pages))
        self.assertTrue(all('data-theme-id="clean-formal"' in page for page in pages))
        self.assertIn('data-layout-skeleton="hero_split"', pages[0])
        self.assertIn('data-composition-id="hero_statement_support"', pages[0])
        self.assertIn('data-visual-intent="hero_signal"', pages[0])
        self.assertIn('data-structure-marker="cover_split"', pages[0])
        self.assertIn('data-layout-skeleton="route_board_horizontal"', pages[1])
        self.assertIn('data-composition-id="route_board_metric_tail"', pages[1])
        self.assertIn('data-body-goals="show_route | summarize_sections', pages[1])
        self.assertIn('data-slot-role="navigation_board"', pages[1])
        self.assertIn('data-layout-skeleton="retrospective_split"', pages[2])
        self.assertIn('data-composition-id="left_timeline_right_retro"', pages[2])
        self.assertIn('data-structure-marker="timeline_retro_side"', pages[2])
        self.assertIn('data-layout-skeleton="handoff_chain_board"', pages[3])
        self.assertIn('data-composition-id="center_chain_side_roles"', pages[3])
        self.assertIn('data-structure-marker="team_chain_grid"', pages[3])
        self.assertIn('data-layout-skeleton="scenario_grid"', pages[4])
        self.assertIn('data-composition-id="scenario_board_metric_side"', pages[4])
        self.assertIn('data-structure-marker="scenario_grid"', pages[4])

    def test_v5_shell_reduces_title_and_gives_cover_director_larger_body(self):
        outline = {
            "project": {"name": "封面导演验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智慧农业物联网平台",
                    "page_series_type": "cover_keynote",
                    "content_points": ["物联网感知", "AI决策"],
                },
                {
                    "page_index": 2,
                    "title": "技术架构",
                    "page_series_type": "architecture_system",
                    "core_argument": "端边云协同处理。",
                },
            ],
        }

        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        pipeline["composition_plans"][0]["body_mode"] = "ai_direct"
        pipeline["composition_plans"][0]["body_html_fragment"] = "<div class='mimo-body-root'>封面主体</div>"
        pages = render_v5_html_pages(outline, {"theme": "clean-formal"}, pipeline_payload=pipeline)

        self.assertIn("font-size: 51px", pages[1])
        self.assertIn("font-size: 19px", pages[1])
        self.assertIn("top:224px;width:1752px;height:764px", pages[1])
        self.assertIn('data-shell-mode="cover_director"', pages[0])
        self.assertIn("top:76px;width:1752px;height:912px", pages[0])
        self.assertIn(".shell-footer {\n      left", pages[0])
        self.assertIn("display:none;", pages[0])
        self.assertIn("padding: 0 !important", pages[1])
        self.assertIn("background: transparent !important", pages[1])

    def test_v5_evidence_placeholder_is_ppt_evidence_not_upload_box(self):
        outline = {
            "project": {"name": "证据位视觉验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "实操现场与系统界面验证",
                    "page_series_type": "practice_evidence",
                    "core_argument": "通过实操现场图片和系统界面截图证明方案可运行。",
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        pipeline["composition_plans"][0]["body_mode"] = "ai_direct"
        pipeline["composition_plans"][0]["body_html_fragment"] = (
            "<div class='mimo-body-root'><div class='mimo-image-placeholder' "
            "data-image-type='实操现场图片'>现场操作证据位</div></div>"
        )

        html = render_v5_html_pages(outline, {"theme": "clean-formal"}, pipeline_payload=pipeline)[0]

        self.assertIn("PPT EVIDENCE", html)
        self.assertNotIn("border: 2px dashed", html)

    def test_nested_canvas_auditor_rejects_inner_whiteboard(self):
        page = {
            "page_index": 11,
            "title": "技术栈选型：前后端与数据库",
            "page_series_type": "architecture_system",
        }
        html_fragment = """
        <style>
        .mimo-body-root { width:100%; height:100%; background: linear-gradient(#f8fafc, #e2e8f0); padding: 40px; }
        .tech-container { width:100%; height:100%; display:grid; background: rgba(255,255,255,.92); border-radius: 28px; padding: 36px; }
        </style>
        <div class="mimo-body-root"><section class="tech-container">架构图</section></div>
        """

        report = audit_nested_canvas(html_fragment=html_fragment, page=page)

        self.assertFalse(report["pass"])
        self.assertTrue(any("二次背景" in issue for issue in report["issues"]))
        self.assertTrue(any("内层白板" in issue for issue in report["issues"]))

    def test_nested_canvas_auditor_rejects_inline_root_canvas_styles(self):
        page = {"page_index": 6, "title": "方案", "page_series_type": "mapping_bridge"}
        html_fragment = (
            "<div class='mimo-body-root' "
            "style='padding:40px;background:#fff;border-radius:28px;box-shadow:0 20px 60px rgba(0,0,0,.1)'>"
            "主体</div>"
        )

        report = audit_nested_canvas(html_fragment=html_fragment, page=page)

        self.assertFalse(report["pass"])
        self.assertTrue(any("内联设置了内边距" in issue for issue in report["issues"]))
        self.assertTrue(any("内联设置了圆角" in issue for issue in report["issues"]))

    def test_ai_body_prompt_contains_director_and_canvas_constraints(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智慧农业平台",
                    "page_series_type": "cover_keynote",
                    "content_points": ["AI识别", "边缘感知"],
                },
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        captured = {}

        class PromptCaptureHtmlClient:
            async def generate_html(self, prompt, system_prompt):
                captured["prompt"] = prompt
                captured["system_prompt"] = system_prompt
                return (
                    "<div class='mimo-body-root' data-page-archetype='cover' data-visual-motif='real_scene' data-dominant-visual='智慧农业平台主视觉'>"
                    "<svg viewBox='0 0 100 100'></svg>"
                    "<h2>智慧农业平台</h2><p>基于 AI 与边缘感知的一句话价值，团队：创新组，职业院校技能大赛。</p>"
                    "<span>AI识别</span><span>边缘感知</span>"
                    "</div>"
                )

        with patch("app.services.ppt.v5.ai_passes.create_ppt_html_client", return_value=PromptCaptureHtmlClient()):
            result = asyncio.run(apply_ai_design_passes(outline, {"theme": "clean-formal"}, pipeline))

        self.assertEqual(result["composition_plans"][0]["body_mode"], "ai_direct")
        self.assertIn("cover_director", captured["prompt"])
        self.assertIn("no_body_root_background", captured["prompt"])
        self.assertIn("max_single_panel_area_ratio", captured["prompt"])
        self.assertIn("competition_design_director", captured["prompt"])
        self.assertIn("speaker_notes_future_json", captured["prompt"])
        self.assertIn("no_scoring_point_language", captured["prompt"])
        self.assertIn("ruipu_image_ppt_style", captured["prompt"])
        self.assertIn("rapidesign_dynamic_case_knowledge_v2", captured["prompt"])
        self.assertIn("rapidesign_v2_execution_contract", captured["prompt"])
        self.assertIn("data-page-archetype", captured["prompt"])
        self.assertIn("information_density_policy", captured["prompt"])
        self.assertIn("html_friendly_diagram_policy", captured["prompt"])
        self.assertIn("beauty_first", captured["prompt"])
        self.assertIn("left_right_relaxed", captured["prompt"])
        self.assertIn("图片化主题海报", captured["prompt"])
        self.assertIn("根据项目行业选择", captured["prompt"])
        self.assertIn("不要固定成农业风", captured["prompt"])
        self.assertIn("网页 hero banner", captured["prompt"])
        self.assertIn("mimo-body-root 必须透明", captured["system_prompt"])
        self.assertIn("参赛级成品 PPT", captured["system_prompt"])

    def test_v5_detects_image_evidence_placeholders_for_competition_pages(self):
        page = {
            "page_index": 8,
            "title": "政策依据与实操现场验证",
            "page_series_type": "practice_evidence",
            "core_argument": "结合政策网页截图、设备图片和线下实操现场图片形成证据链。",
            "content_points": ["政策文件", "传感器设备", "现场部署实操"],
        }

        placeholders = _image_placeholder_brief(page)
        expression_type = _professional_expression_type(page)
        audit = audit_ai_body_fragment(
            html_fragment="<div class='mimo-body-root'><svg></svg><p>现场部署实操</p></div>",
            page=page,
            expression_type=expression_type,
            image_placeholders=placeholders,
        )

        self.assertEqual(expression_type, "evidence_board")
        self.assertIn("政策网页截图", [item["image_type"] for item in placeholders])
        self.assertIn("设备图片", [item["image_type"] for item in placeholders])
        self.assertIn("实操现场图片", [item["image_type"] for item in placeholders])
        self.assertFalse(audit["pass"])
        self.assertTrue(any("缺少必要图片/证据占位" in issue for issue in audit["issues"]))

    def test_v5_agenda_chapter_ranges_are_sequential_not_overlapping(self):
        pages = [
            {"page_index": 1, "title": "封面", "page_series_type": "cover_keynote"},
            {"page_index": 2, "title": "目录", "page_series_type": "agenda_navigation"},
            {"page_index": 3, "title": "政策背景", "page_series_type": "evidence_board"},
            {"page_index": 4, "title": "行业痛点", "page_series_type": "evidence_board"},
            {"page_index": 5, "title": "总体方案", "page_series_type": "mapping_bridge"},
            {"page_index": 6, "title": "技术架构", "page_series_type": "architecture_system"},
            {"page_index": 7, "title": "实操验证", "page_series_type": "practice_evidence"},
            {"page_index": 8, "title": "成果价值", "page_series_type": "value_matrix"},
            {"page_index": 9, "title": "总结展望", "page_series_type": "closing_board"},
        ]

        chapters = _agenda_chapter_candidates(pages)
        ranges = []
        for chapter in chapters:
            start, end = [int(part) for part in chapter["page_range"].split("-")]
            ranges.append((start, end))

        self.assertGreaterEqual(len(chapters), 4)
        self.assertEqual(ranges, sorted(ranges))
        for left, right in zip(ranges, ranges[1:]):
            self.assertLess(left[1], right[0])

    def test_v5_closing_and_agenda_do_not_request_evidence_placeholders(self):
        closing = {
            "page_index": 38,
            "title": "总结展望与答辩感谢",
            "page_series_type": "closing_board",
            "core_argument": "通过证据链证明价值，并进入答辩收束。",
        }
        agenda = {
            "page_index": 2,
            "title": "路演议程",
            "page_series_type": "agenda_navigation",
            "core_argument": "包含系统界面截图和实操现场。",
        }

        self.assertEqual(_image_placeholder_brief(closing), [])
        self.assertEqual(_image_placeholder_brief(agenda), [])

    def test_v5_sanitizes_prompt_leaks_from_subtitle(self):
        polluted = "把「技术架构」讲清楚，并给出支撑这一页结论的事实、动作或结果。"
        outline = {
            "project": {"name": "提示词清理"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构",
                    "page_series_type": "architecture_system",
                    "core_argument": polluted,
                    "content_points": ["端侧采集", "边缘处理", "云端平台"],
                }
            ],
        }

        html = render_v5_html_pages(outline, {"theme": "clean-formal"})[0]

        self.assertEqual(sanitize_v5_text(polluted), "")
        self.assertNotIn("把「技术架构」讲清楚", html)
        self.assertNotIn("支撑这一页结论", html)

    def test_v5_body_auditor_rejects_closing_placeholder_and_prompt_leak(self):
        page = {
            "page_index": 38,
            "title": "总结展望与答辩感谢",
            "page_series_type": "closing_board",
        }
        audit = audit_ai_body_fragment(
            html_fragment=(
                "<div class='mimo-body-root'>"
                "<div class='mimo-image-placeholder' data-image-type='证据图片'>证据</div>"
                "<p>把「总结」讲清楚，并给出支撑这一页结论的事实、动作或结果。</p>"
                "</div>"
            ),
            page=page,
            expression_type="closing_signal",
            image_placeholders=[],
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("结束页出现图片" in issue for issue in audit["issues"]))
        self.assertTrue(any("系统提示句" in issue for issue in audit["issues"]))

    def test_v5_body_auditor_rejects_scoring_meta_copy_and_card_dump(self):
        page = {
            "page_index": 6,
            "title": "技术架构",
            "page_series_type": "architecture_system",
        }
        html = (
            "<div class='mimo-body-root'>"
            "<section class='card'>评分点覆盖：系统架构、数据链路、平台价值。</section>"
            + "".join(f"<div class='info-card'>模块{i}</div>" for i in range(8))
            + "</div>"
        )
        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="architecture_diagram",
            image_placeholders=[],
        )

        self.assertFalse(audit["pass"])
        self.assertTrue(any("评审清单" in issue or "元话术" in issue for issue in audit["issues"]))
        self.assertTrue(any("卡片/面板数量过多" in issue for issue in audit["issues"]))
        self.assertTrue(any("缺少专业图解主视觉" in issue for issue in audit["issues"]))

    def test_v5_body_auditor_requires_rapidesign_v2_trace_and_rejects_card_grid(self):
        page = {
            "page_index": 12,
            "title": "能力体系",
            "page_series_type": "value_matrix",
        }
        html = (
            "<div class='mimo-body-root'>"
            + "".join(f"<div class='metric-card'>能力{i}</div>" for i in range(4))
            + "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="comparison_matrix",
            image_placeholders=[],
        )
        classification = _classify_body_review(audit, page=page, image_placeholders=[])

        self.assertFalse(audit["pass"])
        self.assertTrue(any("构图打法声明" in issue for issue in audit["issues"]))
        self.assertTrue(any("卡片网格" in issue for issue in audit["issues"]))
        self.assertIn("missing_design_decision", classification["categories"])
        self.assertIn("card_grid_template", classification["categories"])
        self.assertEqual(classification["priority_repair_strategy"], "visual_variation_redesign")

    def test_v5_body_auditor_accepts_v2_trace_for_scene_diagram(self):
        page = {
            "page_index": 10,
            "title": "技术架构总览",
            "page_series_type": "architecture_system",
        }
        html = (
            "<div class='mimo-body-root' data-page-archetype='architecture' "
            "data-visual-motif='ring' data-dominant-visual='端边云数据闭环' "
            "data-focus-text='数据闭环驱动决策'>"
            "<svg class='architecture-diagram ring-map' viewBox='0 0 100 60'></svg>"
            "<p class='focus-statement'>数据闭环驱动决策</p>"
            "<p>传感器采集、边缘清洗、云端分析和终端反馈形成闭环。</p>"
            "<span>采集日志</span><span>异常过滤</span><span>模型看板</span><span>生产建议</span>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="architecture_diagram",
            image_placeholders=[],
        )

        self.assertTrue(audit["pass"], audit["issues"])

    def test_v5_body_auditor_rejects_thin_content_without_focus(self):
        page = {
            "page_index": 24,
            "title": "技术证据链",
            "page_series_type": "practice_evidence",
        }
        html = (
            "<div class='mimo-body-root' data-page-archetype='evidence_chain' "
            "data-visual-motif='light_path' data-dominant-visual='数据到价值链路'>"
            "<svg class='evidence-chain' viewBox='0 0 100 60'></svg>"
            "<p>形成技术闭环。</p>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="process_flow",
            image_placeholders=[],
        )
        classification = _classify_body_review(audit, page=page, image_placeholders=[])

        self.assertFalse(audit["pass"])
        self.assertTrue(any("信息量过薄" in issue for issue in audit["issues"]))
        self.assertTrue(any("视觉焦点文字" in issue for issue in audit["issues"]))
        self.assertIn("content_density_or_focus", classification["categories"])
        self.assertEqual(classification["priority_repair_strategy"], "visual_variation_redesign")

    def test_v5_body_auditor_rejects_freeform_path_geometry(self):
        page = {
            "page_index": 25,
            "title": "闭环路径",
            "page_series_type": "practice_evidence",
        }
        paths = "".join("<path d='M0 0 C10 40 30 10 50 30' />" for _ in range(5))
        html = (
            "<div class='mimo-body-root' data-page-archetype='process' "
            "data-visual-motif='light_path' data-dominant-visual='多段数据链路' "
            "data-focus-text='证据链路清晰闭环'>"
            f"<svg class='freeform-flow' viewBox='0 0 100 60'>{paths}</svg>"
            "<p class='focus-statement'>证据链路清晰闭环</p>"
            "<p>采集日志、过滤结果、模型判断和终端反馈构成可追溯链路。</p>"
            "<span>源头可信</span><span>过程可追溯</span><span>结果可验证</span>"
            "</div>"
        )

        audit = audit_ai_body_fragment(
            html_fragment=html,
            page=page,
            expression_type="process_flow",
            image_placeholders=[],
        )
        classification = _classify_body_review(audit, page=page, image_placeholders=[])

        self.assertFalse(audit["pass"])
        self.assertTrue(any("自由路径" in issue for issue in audit["issues"]))
        self.assertIn("diagram_geometry", classification["categories"])

    def test_v5_body_auditor_rejects_webby_cover_and_timeline_agenda(self):
        cover_audit = audit_ai_body_fragment(
            html_fragment=(
                "<div class='mimo-body-root'>"
                "<section class='hero-banner'><button>了解更多</button><span class='chip'>AI农业</span></section>"
                "<h1>智慧农业物联网大数据平台</h1><p>职业院校技能大赛项目</p>"
                "</div>"
            ),
            page={"page_index": 1, "title": "智慧农业物联网大数据平台", "page_series_type": "cover_keynote"},
            expression_type="cover_hero",
            image_placeholders=[],
        )
        agenda_audit = audit_ai_body_fragment(
            html_fragment=(
                "<div class='mimo-body-root'>"
                "<svg class='route-timeline'></svg>"
                "<div>01 项目背景 P3-P8</div><div>02 方案设计 P9-P17</div><div>03 实操验证 P18-P28</div>"
                "</div>"
            ),
            page={"page_index": 2, "title": "路演议程", "page_series_type": "agenda_navigation"},
            expression_type="chapter_navigation",
            image_placeholders=[],
        )

        self.assertFalse(cover_audit["pass"])
        self.assertTrue(any("网页感" in issue for issue in cover_audit["issues"]))
        self.assertTrue(any("不要固定成农业风" in suggestion for suggestion in cover_audit["repair_instructions"]))
        self.assertFalse(agenda_audit["pass"])
        self.assertTrue(any("目录页风格不足" in issue for issue in agenda_audit["issues"]))

    def test_v5_ai_body_prompt_includes_generated_image_asset_when_enabled(self):
        outline = {
            "project": {"name": "智能制造质检平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智能制造质检平台",
                    "page_series_type": "cover_keynote",
                    "content_points": ["产线质检", "缺陷识别", "设备协同"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        captured = {}

        class PromptCaptureHtmlClient:
            async def generate_html(self, prompt, system_prompt):
                captured["prompt"] = prompt
                return (
                    "<div class='mimo-body-root'>"
                    "<img src='file:///tmp/generated_cover.png' class='cover-photo'>"
                    "<h1>智能制造质检平台</h1><p>面向产线缺陷识别的视觉检测方案。</p>"
                    "</div>"
                )

        class FakeImageAssetService:
            def should_generate_for_page(self, page, generated_count):
                return True

            async def generate_page_asset(self, **kwargs):
                return {
                    "status": "ok",
                    "local_path": "/tmp/generated_cover.png",
                    "file_url": "file:///tmp/generated_cover.png",
                }

        with patch("app.services.ppt.v5.ai_passes.create_ppt_html_client", return_value=PromptCaptureHtmlClient()), \
             patch("app.services.ppt.v5.ai_passes.PPTImageAssetService", return_value=FakeImageAssetService()):
            result = asyncio.run(
                apply_ai_design_passes(
                    outline,
                    {
                        "theme": "clean-formal",
                        "_ppt_image_assets_enabled": True,
                        "_ppt_task_id": 1234,
                    },
                    pipeline,
                )
            )

        self.assertIn("generated_visual_asset", captured["prompt"])
        self.assertIn("file:///tmp/generated_cover.png", captured["prompt"])
        self.assertEqual(result["cutover_readiness"]["ai_design_passes"]["generated_image_asset_count"], 1)

    def test_v5_failed_debug_pages_are_kept_outside_official_preview(self):
        with TemporaryDirectory() as tmpdir:
            service = PPTService.__new__(PPTService)
            service.output_dir = tmpdir
            debug_dir = service._write_v5_failed_debug_pages(
                77,
                ["<html>bad page</html>"],
                {"failed_count": 1, "items": [{"page_index": 1, "pass": False}]},
            )

            self.assertTrue(debug_dir.endswith("preview_v5_77_failed_debug"))
            with open(f"{debug_dir}/page_1.html", encoding="utf-8") as f:
                self.assertIn("bad page", f.read())
            with open(f"{debug_dir}/_render_audit_failed.json", encoding="utf-8") as f:
                self.assertEqual(__import__("json").load(f)["failed_count"], 1)

    def test_v5_ai_body_timeout_marks_page_and_continues(self):
        outline = {
            "project": {"name": "超时监控验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "超时封面",
                    "page_series_type": "cover_keynote",
                    "content_points": ["监控", "跳过"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        events = []

        class SlowHtmlClient:
            async def generate_html(self, prompt, system_prompt):
                await asyncio.sleep(0.05)
                return "<div class='mimo-body-root'>too late</div>"

        async def on_event(event):
            events.append(event)

        with patch("app.services.ppt.v5.ai_passes.create_ppt_html_client", return_value=SlowHtmlClient()):
            result = asyncio.run(
                apply_ai_design_passes(
                    outline,
                    {"theme": "clean-formal"},
                    pipeline,
                    page_event_callback=on_event,
                    page_timeout_seconds=0,
                )
            )

        composition = result["composition_plans"][0]
        self.assertEqual(composition["body_mode"], "ai_direct")
        self.assertEqual(composition["ai_status"], "needs_review")
        self.assertTrue(composition["ai_body_audit"]["timeout"])
        self.assertEqual([event["event"] for event in events], ["start", "done"])

    def test_v5_ab_candidate_prototype_selects_best_visual_candidate(self):
        outline = {
            "project": {"name": "A/B/C 候选验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构：系统闭环",
                    "page_series_type": "architecture_system",
                    "core_argument": "数据采集、平台服务、模型分析和生产反馈构成闭环。",
                    "content_points": ["数据采集", "平台服务", "模型分析", "生产反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        seen_variants = []

        async def fake_request(**kwargs):
            variant = (kwargs.get("candidate_variant") or {}).get("variant_id") or "none"
            self.assertIn("approved_layout_blueprint", kwargs.get("candidate_variant") or {})
            seen_variants.append(variant)
            return (
                "<div class='mimo-body-root' data-page-archetype='architecture' "
                "data-visual-motif='system-stage' data-dominant-visual='系统闭环主图' "
                "data-creative-mode='ab_candidate' data-focus-text='数据闭环进入生产动作' "
                f"data-layout-blueprint-id='{variant}_blueprint'>"
                "<div class='focus-statement'>数据闭环进入生产动作</div>"
                f"<svg class='hero-diagram-{variant} system_stage layer-stack-stage' data-zone-id='primary_stage' viewBox='0 0 800 360'>"
                "<g class='layer-bus' data-zone-id='layer_bus'></g><g class='data-flow' data-zone-id='data_flow'></g></svg>"
                f"<strong>{variant}</strong></div>"
            ), {"pass": True, "issues": [], "variant": variant}

        async def fake_blueprint(**kwargs):
            variant = (kwargs.get("candidate_variant") or {}).get("variant_id") or "none"
            blueprint = {
                "blueprint_id": f"{variant}_blueprint",
                "primitive": "system_layer_stack",
                "focus_statement": "数据闭环进入生产动作",
                "primary_stage": {"x": 8, "y": 12, "w": 78, "h": 72, "role": "主舞台"},
                "zones": [
                    {"id": "primary_stage", "role": "系统舞台", "x": 8, "y": 12, "w": 78, "h": 72},
                    {"id": "layer_bus", "role": "数据总线", "x": 16, "y": 45, "w": 60, "h": 12},
                    {"id": "data_flow", "role": "流向", "x": 20, "y": 30, "w": 56, "h": 20},
                ],
                "required_html_markers": [f"{variant}_blueprint", "primary_stage", "layer_bus", "data_flow"],
            }
            return blueprint, {"pass": True, "issues": [], "normalized_blueprint": blueprint}, "{}"

        async def fake_visual_audit(html_pages, outline_pages, **kwargs):
            items = []
            for html_page in html_pages:
                if "hero-diagram-strategy" in html_page:
                    fit, anchor, card = 5, 5, 1
                elif "hero-diagram-diagram" in html_page:
                    fit, anchor, card = 4, 5, 2
                else:
                    fit, anchor, card = 3, 3, 3
                items.append(
                    {
                        "pass": True,
                        "scores": {
                            "competition_ppt_fit": fit,
                            "visual_anchor_strength": anchor,
                            "one_second_readability": fit,
                            "diagram_clarity": anchor,
                            "card_ui_risk": card,
                        },
                        "failure_reasons": [],
                        "key_metrics": {"overflow_count": 0},
                    }
                )
            return {"status": "completed", "summary": {}, "items": items}

        with TemporaryDirectory() as tmp_dir:
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_AB_ENABLE": "1",
                    "PPT_V5_AB_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AI_PASS_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AB_ARTIFACT_DIR": tmp_dir,
                },
                clear=False,
            ), patch(
                "app.services.ppt.v5.ai_passes._request_direct_body_html",
                side_effect=fake_request,
            ), patch(
                "app.services.ppt.v5.ai_passes._generate_layout_blueprint_for_candidate",
                side_effect=fake_blueprint,
            ), patch(
                "app.services.ppt.v5.visual_aesthetic_auditor.audit_v5_visual_aesthetics",
                side_effect=fake_visual_audit,
            ):
                result = asyncio.run(apply_ai_design_passes(outline, {"theme": "clean-formal"}, pipeline))
            artifact_dir = Path(tmp_dir) / "page_01"
            self.assertTrue((artifact_dir / "strategy.blueprint.json").exists())
            self.assertTrue((artifact_dir / "strategy.html").exists())
            self.assertTrue((artifact_dir / "strategy.body.html").exists())
            self.assertTrue((artifact_dir / "ab_selection_report.json").exists())

        composition = result["composition_plans"][0]
        report = result["v5_ab_candidate_report"]
        self.assertEqual(seen_variants, ["safe", "strategy", "diagram"])
        self.assertEqual(composition["ab_candidate_selected_variant"], "strategy")
        self.assertIn("strategy", composition["body_html_fragment"])
        self.assertEqual(report["page_count"], 1)
        self.assertEqual(report["items"][0]["selected_variant"], "strategy")
        self.assertTrue(report["items"][0]["selected_structural_gate"]["pass"])

    def test_v5_ab_candidate_selection_respects_structural_gate_before_visual_score(self):
        outline = {
            "project": {"name": "结构门禁验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构：系统闭环",
                    "page_series_type": "architecture_system",
                    "core_argument": "数据采集、平台服务、模型分析和生产反馈构成闭环。",
                    "content_points": ["数据采集", "平台服务", "模型分析", "生产反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})

        async def fake_request(**kwargs):
            variant = (kwargs.get("candidate_variant") or {}).get("variant_id") or "none"
            audit = {"pass": True, "issues": [], "variant": variant, "review_classification": {}}
            if variant == "strategy":
                audit = {
                    "pass": False,
                    "issues": ["system_layer_stack 缺少必要结构类名，实际仍像表格卡片。"],
                    "variant": variant,
                    "review_classification": {"primary_category": "expression_primitive_missing"},
                }
            return (
                "<div class='mimo-body-root' data-page-archetype='architecture' "
                "data-visual-motif='system-stage' data-dominant-visual='系统闭环主图' "
                "data-creative-mode='ab_candidate' data-focus-text='数据闭环进入生产动作' "
                f"data-layout-blueprint-id='{variant}_blueprint'>"
                "<div class='focus-statement'>数据闭环进入生产动作</div>"
                f"<svg class='hero-diagram-{variant} system_stage layer-stack-stage' data-zone-id='primary_stage' viewBox='0 0 800 360'>"
                "<g class='layer-bus' data-zone-id='layer_bus'></g><g class='data-flow' data-zone-id='data_flow'></g></svg>"
                f"<strong>{variant}</strong></div>"
            ), audit

        async def fake_blueprint(**kwargs):
            variant = (kwargs.get("candidate_variant") or {}).get("variant_id") or "none"
            blueprint = {
                "blueprint_id": f"{variant}_blueprint",
                "primitive": "system_layer_stack",
                "focus_statement": "数据闭环进入生产动作",
                "primary_stage": {"x": 8, "y": 12, "w": 78, "h": 72, "role": "主舞台"},
                "zones": [
                    {"id": "primary_stage", "role": "系统舞台", "x": 8, "y": 12, "w": 78, "h": 72},
                    {"id": "layer_bus", "role": "数据总线", "x": 16, "y": 45, "w": 60, "h": 12},
                    {"id": "data_flow", "role": "流向", "x": 20, "y": 30, "w": 56, "h": 20},
                ],
                "required_html_markers": [f"{variant}_blueprint", "primary_stage", "layer_bus", "data_flow"],
            }
            return blueprint, {"pass": True, "issues": [], "normalized_blueprint": blueprint}, "{}"

        async def fake_visual_audit(html_pages, outline_pages, **kwargs):
            items = []
            for html_page in html_pages:
                if "hero-diagram-strategy" in html_page:
                    fit, anchor, card = 5, 5, 1
                elif "hero-diagram-diagram" in html_page:
                    fit, anchor, card = 4, 4, 2
                else:
                    fit, anchor, card = 3, 3, 3
                items.append(
                    {
                        "pass": True,
                        "scores": {
                            "competition_ppt_fit": fit,
                            "visual_anchor_strength": anchor,
                            "one_second_readability": fit,
                            "diagram_clarity": anchor,
                            "card_ui_risk": card,
                        },
                        "failure_reasons": [],
                        "key_metrics": {"overflow_count": 0},
                    }
                )
            return {"status": "completed", "summary": {}, "items": items}

        with TemporaryDirectory() as tmp_dir:
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_AB_ENABLE": "1",
                    "PPT_V5_AB_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AI_PASS_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AB_ARTIFACT_DIR": tmp_dir,
                },
                clear=False,
            ), patch(
                "app.services.ppt.v5.ai_passes._request_direct_body_html",
                side_effect=fake_request,
            ), patch(
                "app.services.ppt.v5.ai_passes._generate_layout_blueprint_for_candidate",
                side_effect=fake_blueprint,
            ), patch(
                "app.services.ppt.v5.visual_aesthetic_auditor.audit_v5_visual_aesthetics",
                side_effect=fake_visual_audit,
            ):
                result = asyncio.run(apply_ai_design_passes(outline, {"theme": "clean-formal"}, pipeline))

        composition = result["composition_plans"][0]
        report = result["v5_ab_candidate_report"]["items"][0]
        self.assertEqual(composition["ab_candidate_selected_variant"], "diagram")
        strategy = next(item for item in report["candidates"] if item["variant_id"] == "strategy")
        self.assertFalse(strategy["structural_gate"]["pass"])
        self.assertEqual(report["selected_variant"], "diagram")

    def test_v5_layout_blueprint_rejects_overlong_focus_statement(self):
        base_blueprint = {
            "blueprint_id": "strategy_layer_stack",
            "primitive": "system_layer_stack",
            "focus_statement": "数据闭环进入生产动作",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "primary_stage", "role": "stage", "x": 4, "y": 10, "w": 92, "h": 70},
                {"id": "system_boundary", "role": "boundary", "x": 6, "y": 12, "w": 88, "h": 66},
                {"id": "data_layer", "role": "layer", "x": 8, "y": 20, "w": 84, "h": 16},
                {"id": "data_bus", "role": "bus", "x": 46, "y": 20, "w": 4, "h": 48},
                {"id": "output_node", "role": "application output", "x": 72, "y": 68, "w": 16, "h": 10},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_layer_stack"',
                'data-zone-id="primary_stage"',
                'data-zone-id="system_boundary"',
                'data-zone-id="data_layer"',
                'data-zone-id="data_bus"',
                'data-zone-id="output_node"',
            ],
        }
        page = {"title": "技术架构", "page_series_type": "architecture_system"}
        page_contract = {
            "creative_director_plan": {
                "expression_primitive_contract": {
                    "allowed_primitive_ids": ["system_layer_stack"],
                    "default_primitive_id": "system_layer_stack",
                }
            }
        }

        ok_report = _audit_layout_blueprint(
            base_blueprint,
            page=page,
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )
        self.assertTrue(ok_report["pass"])

        long_blueprint = dict(base_blueprint)
        long_blueprint["focus_statement"] = "数据从边缘采集云端处理到应用价值分层驱动落地"
        long_report = _audit_layout_blueprint(
            long_blueprint,
            page=page,
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )
        self.assertFalse(long_report["pass"])
        self.assertIn("focus_statement 超过18个字", " ".join(long_report["issues"]))

    def test_v5_layout_blueprint_requires_declared_system_stage_zone(self):
        blueprint = {
            "blueprint_id": "strategy_layer_stack",
            "primitive": "system_layer_stack",
            "focus_statement": "分层总线支撑应用",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "system_boundary", "role": "boundary stage", "x": 6, "y": 12, "w": 88, "h": 66},
                {"id": "data_layer", "role": "layer", "x": 8, "y": 20, "w": 70, "h": 16},
                {"id": "data_bus", "role": "bus", "x": 44, "y": 22, "w": 8, "h": 42},
                {"id": "output_node", "role": "application output", "x": 72, "y": 66, "w": 18, "h": 10},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_layer_stack"',
                'data-zone-id="system_boundary"',
                'data-zone-id="data_layer"',
                'data-zone-id="data_bus"',
                'data-zone-id="output_node"',
            ],
        }
        page_contract = {
            "creative_director_plan": {
                "expression_primitive_contract": {
                    "allowed_primitive_ids": ["system_layer_stack"],
                    "default_primitive_id": "system_layer_stack",
                }
            }
        }

        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "技术架构", "page_series_type": "architecture_system"},
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertFalse(report["pass"])
        self.assertIn("缺少舞台zone", " ".join(report["issues"]))

    def test_v5_layout_blueprint_rejects_full_width_layer_rows(self):
        blueprint = {
            "blueprint_id": "strategy_layer_stack",
            "primitive": "system_layer_stack",
            "focus_statement": "分层总线支撑应用",
            "primary_stage": {"x": 4, "y": 10, "w": 92, "h": 70, "role": "系统舞台"},
            "zones": [
                {"id": "primary_stage", "role": "stage", "x": 4, "y": 10, "w": 92, "h": 70},
                {"id": "system_boundary", "role": "boundary", "x": 6, "y": 12, "w": 88, "h": 66},
                {"id": "layer_access", "role": "接入层", "x": 8, "y": 18, "w": 84, "h": 12},
                {"id": "layer_service", "role": "服务层", "x": 8, "y": 34, "w": 84, "h": 12},
                {"id": "layer_model", "role": "模型层", "x": 8, "y": 50, "w": 84, "h": 12},
                {"id": "data_bus", "role": "bus", "x": 46, "y": 18, "w": 4, "h": 44},
                {"id": "output_node", "role": "application output", "x": 72, "y": 68, "w": 16, "h": 10},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_layer_stack"',
                'data-zone-id="primary_stage"',
                'data-zone-id="system_boundary"',
                'data-zone-id="layer_access"',
                'data-zone-id="layer_service"',
                'data-zone-id="layer_model"',
                'data-zone-id="data_bus"',
                'data-zone-id="output_node"',
            ],
        }
        page_contract = {
            "creative_director_plan": {
                "expression_primitive_contract": {
                    "allowed_primitive_ids": ["system_layer_stack"],
                    "default_primitive_id": "system_layer_stack",
                }
            }
        }

        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "技术架构", "page_series_type": "architecture_system"},
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertFalse(report["pass"])
        self.assertIn("同宽横向层表格", " ".join(report["issues"]))

    def test_v5_layout_blueprint_rejects_thin_evidence_rail_and_small_proof_nodes(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "primitive": "evidence_stage",
            "focus_statement": "数据证据转化生产",
            "primary_stage": {"x": 4, "y": 8, "w": 90, "h": 70, "role": "整张证据舞台"},
            "zones": [
                {"id": "primary_stage", "role": "整张证据舞台", "x": 4, "y": 8, "w": 90, "h": 70},
                {"id": "claim_stage", "role": "claim 主张", "x": 8, "y": 8, "w": 58, "h": 30},
                {"id": "proof_rail", "role": "proof 证据轨道", "x": 9, "y": 50, "w": 70, "h": 16},
                {"id": "result_seal", "role": "result 结果章印", "x": 72, "y": 12, "w": 20, "h": 22},
                {"id": "proof_node_1", "role": "proof-node 证据节点", "x": 10, "y": 52, "w": 12, "h": 14},
            ],
            "required_html_markers": [
                "strategy_evidence_stage",
                "primary_stage",
                "claim_stage",
                "proof_rail",
                "result_seal",
                "proof_node_1",
            ],
        }
        page_contract = {
            "creative_director_plan": {
                "expression_primitive_contract": {
                    "allowed_primitive_ids": ["evidence_stage"],
                    "default_primitive_id": "evidence_stage",
                }
            }
        }

        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "证据链", "page_series_type": "practice_evidence"},
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertFalse(report["pass"])
        joined = " ".join(report["issues"])
        self.assertIn("proof rail 太薄", joined)
        self.assertIn("proof-node bbox 太小", joined)

    def test_v5_layout_blueprint_requires_primary_stage_for_evidence_chain(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "primitive": "evidence_stage",
            "focus_statement": "数据证据转化生产",
            "primary_stage": {"x": 4, "y": 8, "w": 90, "h": 70, "role": "整张证据舞台"},
            "zones": [
                {"id": "claim_stage", "role": "claim 主张", "x": 8, "y": 8, "w": 58, "h": 30},
                {"id": "proof_rail", "role": "proof 证据轨道", "x": 8, "y": 44, "w": 84, "h": 32},
                {"id": "result_seal", "role": "result 结果章印", "x": 72, "y": 12, "w": 20, "h": 22},
            ],
            "required_html_markers": ["strategy_evidence_stage", "claim_stage", "proof_rail", "result_seal"],
        }
        page_contract = {
            "creative_director_plan": {
                "expression_primitive_contract": {
                    "allowed_primitive_ids": ["evidence_stage"],
                    "default_primitive_id": "evidence_stage",
                }
            }
        }

        report = _audit_layout_blueprint(
            blueprint,
            page={"title": "证据链", "page_series_type": "practice_evidence"},
            page_contract=page_contract,
            candidate_variant={"variant_id": "strategy"},
        )

        self.assertFalse(report["pass"])
        self.assertIn("缺少 primary_stage 舞台zone", " ".join(report["issues"]))

    def test_v5_blueprint_html_focus_allows_arrow_equivalent_visible_text(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "focus_statement": "数据证据转化为生产动作",
            "zones": [
                {"id": "hero_claim"},
                {"id": "proof_rail"},
                {"id": "result_seal"},
            ],
            "required_html_markers": [
                "strategy_evidence_stage",
                "hero_claim",
                "proof_rail",
                "result_seal",
            ],
        }
        html = (
            "<div class='mimo-body-root' data-layout-blueprint-id='strategy_evidence_stage' "
            "data-focus-text='数据证据转化为生产动作'>"
            "<section data-zone-id='hero_claim'><div class='focus-statement'>数据证据 → 生产动作</div></section>"
            "<section data-zone-id='proof_rail'></section><aside data-zone-id='result_seal'></aside></div>"
        )

        report = _audit_blueprint_html_execution(blueprint, html)

        self.assertTrue(report["pass"])

    def test_v5_blueprint_html_rejects_duplicate_zone_ids(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "focus_statement": "数据证据转化为生产动作",
            "zones": [
                {"id": "primary_stage"},
                {"id": "claim_stage"},
                {"id": "evidence_flow"},
                {"id": "result_seal"},
            ],
            "required_html_markers": [
                'data-layout-blueprint-id="strategy_evidence_stage"',
                'data-zone-id="primary_stage"',
                'data-zone-id="claim_stage"',
                'data-zone-id="evidence_flow"',
                'data-zone-id="result_seal"',
            ],
        }
        html = (
            '<div class="mimo-body-root" data-layout-blueprint-id="strategy_evidence_stage" '
            'data-focus-text="数据证据转化为生产动作">'
            '<div data-zone-id="primary_stage">'
            '<section data-zone-id="claim_stage"><div class="focus-statement">数据证据转化为生产动作</div></section>'
            '<section class="evidence-flow" data-zone-id="evidence_flow"></section>'
            '<div class="proof-rail" data-zone-id="evidence_flow"></div>'
            '<aside data-zone-id="result_seal"></aside>'
            '</div></div>'
        )

        report = _audit_blueprint_html_execution(blueprint, html)

        self.assertFalse(report["pass"])
        self.assertIn("重复使用blueprint data-zone-id", " ".join(report["issues"]))

    def test_v5_blueprint_html_rewrite_feedback_is_local_patch_contract(self):
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "primitive": "evidence_stage",
            "focus_statement": "数据证据转化为生产动作",
            "zones": [
                {"id": "primary_stage", "x": 4, "y": 6, "w": 92, "h": 76},
                {"id": "claim_stage", "x": 8, "y": 8, "w": 58, "h": 30},
                {"id": "proof_rail", "x": 8, "y": 44, "w": 84, "h": 32},
                {"id": "proof_node_1", "x": 12, "y": 52, "w": 18, "h": 22},
                {"id": "result_seal", "x": 72, "y": 12, "w": 20, "h": 22},
            ],
            "required_html_markers": ["strategy_evidence_stage", "primary_stage", "claim_stage", "proof_rail"],
        }
        body_audit = {
            "pass": False,
            "issues": [
                "HTML的zone-class绑定未执行：data-zone-id=proof_rail 缺少class evidence-flow, proof-rail。",
                "proof-node 缺少合法 modifier class，不能确认 spine_label 或 bracket_anchor。",
                "主体区使用负向定位，容易把章印、图形或文字推出主体区。",
            ],
            "layout_blueprint_execution_audit": {"checked": True, "pass": False, "issues": []},
        }

        feedback = _blueprint_html_rewrite_feedback(body_audit=body_audit, blueprint=blueprint, attempt=2)
        contract = feedback["html_rewrite_contract"]

        self.assertEqual(contract["rewrite_scope"], "same_blueprint_local_patch")
        self.assertEqual(contract["patch_intent"], "local_patch_same_blueprint_no_recomposition")
        self.assertEqual(contract["locked_fields"]["data_zone_ids"], ["primary_stage", "claim_stage", "proof_rail", "proof_node_1", "result_seal"])
        self.assertTrue(contract["locked_fields"]["zone_bboxes_locked"])
        self.assertIn("add_missing_classes_to_existing_data_zone_element", contract["allowed_local_operations"])
        self.assertIn("do_not_move_or_resize_zones_except_to_restore_blueprint_bbox", contract["forbidden_recomposition_operations"])
        self.assertEqual(contract["missing_zone_class_patches"][0]["zone_id"], "proof_rail")
        self.assertIn("proof-rail", contract["missing_zone_class_patches"][0]["add_classes_to_existing_data_zone_element"])
        self.assertEqual(contract["proof_node_local_patch_targets"][0]["zone_id"], "proof_node_1")
        joined = " ".join(feedback["repair_instructions"])
        self.assertIn("本次不是重新设计页面", joined)
        self.assertIn('给 data-zone-id="proof_rail" 的同一个元素补 class', joined)

    def test_v5_blueprint_html_rewrite_feedback_scopes_negative_only_to_geometry_patch(self):
        blueprint = {
            "blueprint_id": "strategy_path",
            "primitive": "handoff_ladder",
            "focus_statement": "协同链路闭环",
            "zones": [
                {"id": "ladder_stage", "x": 8, "y": 12, "w": 84, "h": 64},
                {"id": "output_node", "x": 70, "y": 42, "w": 18, "h": 20},
            ],
            "required_html_markers": ["strategy_path", "ladder_stage", "output_node"],
        }
        body_audit = {
            "pass": False,
            "issues": ["主体区使用负向定位，容易把章印、图形或文字推出主体区。"],
        }

        feedback = _blueprint_html_rewrite_feedback(body_audit=body_audit, blueprint=blueprint, attempt=1)
        contract = feedback["html_rewrite_contract"]

        self.assertEqual(contract["rewrite_scope"], "local_geometry_patch")
        self.assertIn("replace_negative_positioned_decoration_with_inline_svg_inside_owner_bbox", contract["allowed_local_operations"])
        self.assertTrue(contract["locked_fields"]["overall_composition_locked"])
        self.assertIn("Do not recompose the page", contract["same_blueprint_patch_rule"])

    def test_v5_ab_short_prompt_patches_existing_html_instead_of_blank_regeneration(self):
        repair_feedback = {
            "rewrite_mode": "same_blueprint_html_rewrite",
            "issues": ["主体区使用负向定位，容易把章印、图形或文字推出主体区。"],
            "html_rewrite_contract": {
                "rewrite_scope": "local_geometry_patch",
                "patch_intent": "local_patch_same_blueprint_no_recomposition",
                "locked_fields": {
                    "blueprint_id": "strategy_path",
                    "data_zone_ids": ["claim_stage"],
                    "overall_composition_locked": True,
                },
                "allowed_local_operations": ["replace_negative_positioned_decoration_with_inline_svg_inside_owner_bbox"],
                "forbidden_recomposition_operations": ["do_not_choose_new_layout_blueprint"],
                "same_blueprint_patch_rule": "Patch only the failing local construction items. Do not recompose the page.",
            },
        }
        existing_html = (
            "<div class='mimo-body-root' data-layout-blueprint-id='strategy_path'>"
            "<section data-zone-id='claim_stage' style='right:-12px'>旧版主张</section>"
            "<section data-zone-id='unrelated_zone'>不应进入局部补丁输入</section></div>"
        )

        prompt = _body_user_prompt(
            deck={"project_name": "补丁验证"},
            shell_spec={"theme_id": "clean-formal", "palette": {}, "typography": {}},
            page={"page_index": 1, "title": "证据链", "page_series_type": "practice_evidence"},
            decision={"narrative_role": "execution_proof"},
            strategy_brief={},
            recent_family_context=[],
            all_pages=[],
            repair_feedback=repair_feedback,
            page_contract={},
            diagram_spec={},
            visual_contract={},
            candidate_variant={"variant_id": "strategy", "approved_layout_blueprint": {"blueprint_id": "strategy_path"}},
            existing_body_html=existing_html,
        )
        payload = json.loads(prompt)

        self.assertEqual(payload["task"], "patch_existing_html_fragment")
        patch_source = payload["existing_body_html_patch_source"]
        self.assertTrue(patch_source["do_not_start_from_blank"])
        self.assertTrue(patch_source["do_not_recompose"])
        self.assertEqual(patch_source["patch_source"]["scope_mode"], "targeted_fragments")
        self.assertEqual(patch_source["patch_source"]["target_zone_ids"], ["claim_stage"])
        self.assertIn("data-zone-id='claim_stage'", patch_source["patch_source"]["html_fragment"])
        self.assertNotIn("unrelated_zone", patch_source["patch_source"]["html_fragment"])
        self.assertEqual(payload["html_rewrite_local_patch_directive"]["rewrite_scope"], "local_geometry_patch")

    def test_v5_fragment_replacement_json_patch_only_replaces_target_zone(self):
        html = (
            "<div class='mimo-body-root'>"
            "<section data-zone-id='proof_node_1' class='proof-node'>旧节点</section>"
            "<section data-zone-id='unrelated_zone'>保留内容</section>"
            "</div>"
        )
        patch_payload = {
            "replacements": [
                {
                    "zone_id": "proof_node_1",
                    "html": (
                        "<section data-zone-id='proof_node_1' class='proof-node proof-node--spine-label'>"
                        "<span class='proof-anchor-spine'></span>"
                        "<div class='proof-text-group'><b class='proof-title'>图像采集</b>"
                        "<span class='source-tag'>传感器日志</span>"
                        "<span class='evidence-snippet'>来源真实</span></div></section>"
                    ),
                },
                {
                    "zone_id": "unrelated_zone",
                    "html": "<section data-zone-id='unrelated_zone'>不该替换</section>",
                },
            ]
        }

        patched, report = _apply_fragment_replacement_json_patch(
            html,
            patch_payload,
            target_zone_ids=["proof_node_1"],
        )

        self.assertTrue(report["pass"])
        self.assertEqual(report["applied_replacements"], ["proof_node_1"])
        self.assertIn("proof-node--spine-label", patched)
        self.assertIn("保留内容", patched)
        self.assertNotIn("不该替换", patched)

    def test_v5_fragment_patch_prioritizes_proof_nodes(self):
        zones = ["primary_stage", "proof_node_1", "proof_rail", "proof_node_2", "result_seal"]

        self.assertEqual(
            _prioritized_fragment_patch_zone_ids(zones),
            ["proof_node_1", "proof_node_2"],
        )

    def test_v5_local_proof_node_normalizer_rewrites_only_proof_nodes(self):
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain'>"
            "<section data-zone-id='proof_node_1' class='proof-node proof-node--cut-corner-tag' "
            "data-proof-id='proof_node_1' style='position:absolute;left:12%;top:50%;width:18%;height:17%;"
            "background:#fff;border:1px solid #ddd;border-radius:12px;box-shadow:0 10px 24px rgba(0,0,0,.14)'>"
            "<div style='background:#fff;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,.1)'>"
            "<b>图像采集</b><span>传感器日志</span><p>解决数据来源真实性</p>"
            "</div></section>"
            "<style>.proof-node{background:#fff;border:1px solid #ddd;border-radius:12px;box-shadow:0 10px 24px rgba(0,0,0,.14)}"
            ".proof-index{background:#fff;border-radius:50%}</style>"
            "<section data-zone-id='unrelated_zone'>保留内容</section>"
            "</div>"
        )
        repair_feedback = {
            "issues": ["proof-node 正向组件骨架不完整，未按 spine_label/bracket_anchor 范式施工。"],
            "html_rewrite_contract": {
                "proof_node_local_patch_targets": [{"zone_id": "proof_node_1"}],
                "locked_fields": {"data_zone_ids": ["proof_node_1", "unrelated_zone"]},
            },
        }

        patched, report = _normalize_proof_nodes_locally(html, repair_feedback)

        self.assertTrue(report["pass"])
        self.assertEqual(report["applied_normalizations"], ["proof_node_1"])
        self.assertGreaterEqual(report["scrubbed_global_css_blocks"], 1)
        self.assertIn("data-zone-id=\"proof_node_1\"", patched)
        self.assertIn("proof-node--spine-label", patched)
        self.assertIn("proof-anchor-spine", patched)
        self.assertIn("proof-text-group", patched)
        self.assertIn("proof-title", patched)
        self.assertIn("source-tag", patched)
        self.assertIn("evidence-snippet", patched)
        self.assertIn("保留内容", patched)
        self.assertNotIn("proof-node--cut-corner-tag", patched)
        self.assertNotIn("box-shadow:0 10px", patched)
        self.assertNotIn("background:#fff", patched)
        self.assertNotIn(".proof-node{", patched)

    def test_v5_local_proof_node_normalizer_discovers_nodes_without_contract_targets(self):
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain'>"
            "<section data-zone-id='proof_node_auto' class='proof-node' style='background:#fff;box-shadow:0 10px 24px rgba(0,0,0,.14)'>"
            "<b>日志采集</b><span>设备记录</span><p>证明来源可信</p>"
            "</section><style>.proof-node{background:#fff;box-shadow:0 10px 24px rgba(0,0,0,.14)}</style></div>"
        )

        patched, report = _normalize_proof_nodes_locally(
            html,
            {"issues": ["proof-node 仍使用白底/阴影/完整边框等卡片化 CSS，缺少轨道锚点质感。"]},
        )

        self.assertTrue(report["pass"])
        self.assertEqual(report["applied_normalizations"], ["proof_node_auto"])
        self.assertIn("proof-node--spine-label", patched)
        self.assertNotIn(".proof-node{", patched)

    def test_v5_local_proof_node_normalizer_assigns_missing_zone_ids(self):
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain'>"
            "<div class='proof-node proof-node--spine-label' style='background:#fff;box-shadow:0 4px 12px rgba(0,0,0,.1)'>"
            "<div class='proof-anchor-spine'></div><div><b>图像采集</b><span>传感器日志</span><p>来源可信</p></div>"
            "</div>"
            "<div class='proof-node proof-node--spine-label'><div><b>样本标注</b><span>过滤结果</span><p>过程可追溯</p></div></div>"
            "</div>"
        )

        patched, report = _normalize_proof_nodes_locally(
            html,
            {"issues": ["proof-node 内部存在非 proof-text-group 的匿名视觉容器，容易再次变成卡片。"]},
        )

        self.assertTrue(report["pass"])
        self.assertEqual(report["applied_normalizations"], ["proof_node_1", "proof_node_2"])
        self.assertIn('data-zone-id="proof_node_1"', patched)
        self.assertIn('data-zone-id="proof_node_2"', patched)
        self.assertIn("proof-text-group", patched)
        self.assertNotIn("background:#fff", patched)

    def test_v5_blueprint_marker_accepts_class_token_inside_multi_class_attr(self):
        markup = "<div class='evidence-flow proof-rail stable-geometry' data-zone-id='proof_rail'></div>"

        self.assertTrue(_blueprint_required_marker_present(markup, 'class="evidence-flow"'))
        self.assertTrue(_blueprint_required_marker_present(markup, 'class="proof-rail"'))
        self.assertTrue(_blueprint_required_marker_present(markup, 'data-zone-id="proof_rail"'))
        self.assertFalse(_blueprint_required_marker_present(markup, 'class="result-seal"'))

    def test_v5_evidence_rail_binding_does_not_require_proof_node_class(self):
        blueprint = {
            "primitive": "evidence_stage",
            "zones": [
                {"id": "proof_rail", "role": "证据轨道承载三枚证据节点"},
                {"id": "proof_node_1", "role": "证据节点"},
            ],
        }

        contract = {
            item["zone_id"]: item["required_classes"]
            for item in _infer_zone_class_binding_contract(blueprint)
        }

        self.assertEqual(contract["proof_rail"], ["evidence-flow", "proof-rail"])
        self.assertEqual(contract["proof_node_1"], ["proof-node"])

    def test_v5_local_blueprint_normalizer_fixes_markers_focus_and_negative_offsets(self):
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain'>"
            "<style>.result-seal{right:-24px;bottom:-10px}.proof-connector{left:-12px;top:-4px}</style>"
            "<section data-zone-id='primary_stage' class='evidence-stage' style='position:absolute;left:8%;top:16%;width:80%;height:64%'>"
            "<div class='result-seal' style='position:absolute;right:-24px;bottom:-10px'>价值落地</div>"
            "</section></div>"
        )
        blueprint = {
            "blueprint_id": "strategy_evidence_stage",
            "focus_statement": "证据驱动价值落地",
            "required_html_markers": ['data-layout-blueprint-id="strategy_evidence_stage"', 'data-zone-id="primary_stage"'],
            "zones": [{"id": "primary_stage", "role": "证据舞台", "x": 8, "y": 16, "w": 80, "h": 64}],
        }

        patched, report = _normalize_blueprint_execution_locally(html, blueprint, {})

        self.assertTrue(report["pass"])
        self.assertIn("negative_positioning_neutralized", report["applied"])
        self.assertIn("data_layout_blueprint_id", report["applied"])
        self.assertIn("visible_focus_statement", report["applied"])
        self.assertIn('data-layout-blueprint-id="strategy_evidence_stage"', patched)
        self.assertIn('data-focus-text="证据驱动价值落地"', patched)
        self.assertIn(">证据驱动价值落地</div>", patched)
        self.assertNotRegex(patched, r"(?:left|right|top|bottom)\s*:\s*-")

    def test_v5_local_geometry_normalizer_reduces_evidence_chain_free_paths(self):
        html = (
            "<div class='mimo-body-root' data-creative-mode='answer_first_proof_chain' data-focus-text='证据驱动价值落地'>"
            "<div class='evidence-flow proof-rail' data-zone-id='proof_rail'>"
            "<section class='proof-node proof-node--spine-label' data-zone-id='proof_node_1'>"
            "<svg class='proof-connector' viewBox='0 0 24 8'><path d='M1 4H20'/><path d='M17 1.5L21 4L17 6.5'/></svg>"
            "</section>"
            "<section class='proof-node proof-node--spine-label' data-zone-id='proof_node_2'>"
            "<svg class='proof-connector' viewBox='0 0 24 8'><path d='M1 4H20'/><path d='M17 1.5L21 4L17 6.5'/></svg>"
            "</section>"
            "<section class='proof-node proof-node--spine-label' data-zone-id='proof_node_3'>"
            "<svg class='proof-connector' viewBox='0 0 24 8'><path d='M1 4H20'/><path d='M17 1.5L21 4L17 6.5'/></svg>"
            "</section>"
            "</div><div class='result-seal' data-zone-id='result_seal'>价值落地"
            "<svg><path d='M 100,5 L 10,5' stroke='#2563eb' stroke-width='2.5' fill='none'/></svg>"
            "</div></div>"
        )

        patched, report = _normalize_evidence_chain_geometry_locally(html)

        self.assertTrue(report["pass"])
        self.assertEqual(report["path_count_before"], 7)
        self.assertEqual(report["path_count_after"], 0)
        self.assertIn("proof_connector_line_polyline", report["applied"])
        self.assertIn("simple_arrow_path_to_line_polygon", report["applied"])
        self.assertIn("stable-geometry", patched)
        self.assertIn("<line", patched)
        self.assertIn("<polyline", patched)
        self.assertIn("<polygon", patched)
        self.assertNotIn("<path", patched)

    def test_v5_ab_candidate_rewrites_html_against_same_blueprint(self):
        outline = {
            "project": {"name": "施工图返工验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术证据链",
                    "page_series_type": "practice_evidence",
                    "core_argument": "证据链证明数据能转化为生产动作。",
                    "content_points": ["采集", "分析", "反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        calls = []

        async def fake_blueprint(**kwargs):
            blueprint = {
                "blueprint_id": "strategy_evidence_stage",
                "primitive": "evidence_stage",
                "focus_statement": "数据证据转化为生产动作",
                "primary_stage": {"x": 4, "y": 6, "w": 92, "h": 76, "role": "整张证据舞台"},
                "zones": [
                    {"id": "primary_stage", "role": "整张证据舞台", "x": 4, "y": 6, "w": 92, "h": 76},
                    {"id": "claim_stage", "role": "主张", "x": 8, "y": 8, "w": 58, "h": 30},
                    {"id": "proof_rail", "role": "证据轨道", "x": 8, "y": 44, "w": 84, "h": 32},
                    {"id": "result_seal", "role": "结果章印", "x": 72, "y": 12, "w": 20, "h": 22},
                ],
                "required_html_markers": [
                    "strategy_evidence_stage",
                    "primary_stage",
                    "claim_stage",
                    "proof_rail",
                    "result_seal",
                ],
            }
            return blueprint, {"pass": True, "issues": [], "normalized_blueprint": blueprint}, "{}"

        async def fake_request(**kwargs):
            calls.append(
                {
                    "repair_feedback": kwargs.get("initial_repair_feedback") or {},
                    "existing_body_html": kwargs.get("existing_body_html") or "",
                }
            )
            if len(calls) == 1:
                self.assertEqual(calls[-1]["existing_body_html"], "")
                return (
                    "<div class='mimo-body-root' data-layout-blueprint-id='strategy_evidence_stage'>"
                    "<div data-zone-id='claim_stage'>主张</div></div>"
                ), {
                    "pass": False,
                    "issues": [
                        "proof-node 仍使用白底/阴影/完整边框等卡片化 CSS，缺少轨道锚点质感。",
                        "proof-node 字号或尺寸低于枚举结构下限，节点被压成细条或投屏不可读。",
                        "主体区使用负向定位，容易把章印、图形或文字推出主体区。",
                        "所选表达原语缺少必要结构类名。",
                    ],
                    "review_classification": {},
                }
            self.assertIn("data-zone-id='claim_stage'", calls[-1]["existing_body_html"])
            self.assertEqual(calls[-1]["repair_feedback"].get("rewrite_mode"), "same_blueprint_html_rewrite")
            contract = calls[-1]["repair_feedback"].get("html_rewrite_contract") or {}
            self.assertEqual(contract.get("mode"), "same_blueprint_html_rewrite")
            self.assertEqual(contract.get("patch_intent"), "local_patch_same_blueprint_no_recomposition")
            self.assertIn(contract.get("rewrite_scope"), {"same_blueprint_local_patch", "same_blueprint_execution_patch"})
            self.assertTrue(contract["locked_fields"]["overall_composition_locked"])
            self.assertIn("do_not_change_primitive", contract["forbidden_recomposition_operations"])
            self.assertIn("replace_negative_positioned_decoration_with_inline_svg_inside_owner_bbox", contract["allowed_local_operations"])
            self.assertIn("proof_node_contract", contract)
            self.assertIn("negative_position_rule", contract)
            self.assertIn("zone_id_rule", contract)
            self.assertIn("focus_text_rule", contract)
            self.assertEqual(contract.get("required_visible_focus_text"), "数据证据转化为生产动作")
            self.assertIn("surface_rule", contract["proof_node_contract"])
            self.assertIn("system_layer_stack_contract", contract)
            self.assertIn("SVG wrappers", contract["negative_position_rule"])
            joined_instructions = " ".join(calls[-1]["repair_feedback"].get("repair_instructions") or [])
            self.assertIn("本次不是重新设计页面", joined_instructions)
            self.assertIn("proof-node--spine-label", joined_instructions)
            self.assertIn('data-expression-primitive="evidence_stage"', joined_instructions)
            self.assertIn("proof-node wrapper 只负责 bbox 定位", joined_instructions)
            self.assertIn("right:-40px", joined_instructions)
            self.assertIn("逐个复制 approved_layout_blueprint.zones[].id", joined_instructions)
            self.assertIn("data-focus-text 必须等于 approved_layout_blueprint.focus_statement", joined_instructions)
            self.assertIn('<div class="focus-statement">数据证据转化为生产动作</div>', joined_instructions)
            return (
                "<div class='mimo-body-root' data-layout-blueprint-id='strategy_evidence_stage' "
                "data-focus-text='数据证据转化为生产动作'>"
                "<div class='focus-statement'>数据证据转化为生产动作</div>"
                "<div class='evidence-stage' data-zone-id='primary_stage'>证据舞台</div>"
                "<div class='claim-zone' data-zone-id='claim_stage'>主张</div>"
                "<div class='evidence-flow proof-rail' data-zone-id='proof_rail'>轨道</div>"
                "<div class='result-seal' data-zone-id='result_seal'>章印</div></div>"
            ), {"pass": True, "issues": [], "review_classification": {}}

        async def fake_visual_audit(html_pages, outline_pages, **kwargs):
            return {
                "status": "completed",
                "summary": {},
                "items": [
                    {
                        "pass": True,
                        "scores": {
                            "competition_ppt_fit": 4,
                            "visual_anchor_strength": 4,
                            "one_second_readability": 4,
                            "diagram_clarity": 4,
                            "card_ui_risk": 1,
                        },
                        "failure_reasons": [],
                        "key_metrics": {"overflow_count": 0},
                    }
                ],
            }

        with TemporaryDirectory() as tmp_dir:
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_AB_ENABLE": "1",
                    "PPT_V5_AB_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AI_PASS_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AB_VARIANTS": "strategy",
                    "PPT_V5_AB_BLUEPRINT_HTML_REWRITE_ATTEMPTS": "2",
                    "PPT_V5_AB_FRAGMENT_JSON_PATCH_ENABLE": "0",
                    "PPT_V5_AB_BLUEPRINT_LOCAL_NORMALIZE_ENABLE": "0",
                    "PPT_V5_AB_PROOF_NODE_LOCAL_NORMALIZE_ENABLE": "0",
                    "PPT_V5_AB_ARTIFACT_DIR": tmp_dir,
                },
                clear=False,
            ), patch(
                "app.services.ppt.v5.ai_passes._generate_layout_blueprint_for_candidate",
                side_effect=fake_blueprint,
            ), patch(
                "app.services.ppt.v5.ai_passes._request_direct_body_html",
                side_effect=fake_request,
            ), patch(
                "app.services.ppt.v5.visual_aesthetic_auditor.audit_v5_visual_aesthetics",
                side_effect=fake_visual_audit,
            ):
                result = asyncio.run(apply_ai_design_passes(outline, {"theme": "clean-formal"}, pipeline))

        report = result["v5_ab_candidate_report"]["items"][0]
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["selected_variant"], "strategy")
        self.assertEqual(report["candidates"][0]["html_attempts"][0]["body_audit_pass"], False)
        self.assertEqual(report["candidates"][0]["html_attempts"][1]["input_existing_body_html_present"], True)
        self.assertEqual(report["candidates"][0]["html_attempts"][1]["body_audit_pass"], True)

    def test_v5_ab_candidate_visual_gate_triggers_same_blueprint_redraw(self):
        outline = {
            "project": {"name": "视觉门禁验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "证据链",
                    "page_series_type": "practice_evidence",
                    "core_argument": "证据链证明数据能转化为生产动作。",
                    "content_points": ["采集", "分析", "反馈"],
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        calls = []

        async def fake_blueprint(**kwargs):
            blueprint = {
                "blueprint_id": "strategy_evidence_stage",
                "primitive": "evidence_stage",
                "focus_statement": "数据证据转化为生产动作",
                "primary_stage": {"x": 4, "y": 6, "w": 92, "h": 76, "role": "整张证据舞台"},
                "zones": [
                    {"id": "primary_stage", "role": "整张证据舞台", "x": 4, "y": 6, "w": 92, "h": 76},
                    {"id": "claim_stage", "role": "主张", "x": 8, "y": 8, "w": 58, "h": 30},
                    {"id": "proof_rail", "role": "证据轨道", "x": 8, "y": 44, "w": 84, "h": 32},
                    {"id": "result_seal", "role": "结果章印", "x": 72, "y": 12, "w": 20, "h": 22},
                ],
                "required_html_markers": [
                    'data-layout-blueprint-id="strategy_evidence_stage"',
                    'data-zone-id="primary_stage"',
                    'data-zone-id="claim_stage"',
                    'data-zone-id="proof_rail"',
                    'data-zone-id="result_seal"',
                ],
            }
            return blueprint, {"pass": True, "issues": [], "normalized_blueprint": blueprint}, "{}"

        async def fake_request(**kwargs):
            feedback = kwargs.get("initial_repair_feedback") or {}
            calls.append(feedback.get("rewrite_mode") or "initial")
            marker = "visual-redraw" if feedback.get("rewrite_mode") == "same_blueprint_visual_redraw" else "sparse-initial"
            return (
                f'<div class="mimo-body-root {marker}" data-layout-blueprint-id="strategy_evidence_stage" '
                'data-page-archetype="practice_evidence" data-visual-motif="evidence_chain" '
                'data-dominant-visual="claim_stage" data-creative-mode="answer_first_proof_chain" '
                'data-expression-primitive="evidence_stage" data-focus-text="数据证据转化为生产动作">'
                '<div class="focus-statement">数据证据转化为生产动作</div>'
                '<div class="evidence-stage" data-zone-id="primary_stage">'
                '<div class="claim-zone" data-zone-id="claim_stage"></div>'
                '<div class="evidence-flow proof-rail" data-zone-id="proof_rail"></div>'
                '<div class="result-seal" data-zone-id="result_seal"></div>'
                '</div></div>'
            ), {"pass": True, "issues": [], "review_classification": {}}

        async def fake_visual_audit(html_pages, outline_pages, **kwargs):
            items = []
            for html_page in html_pages:
                is_redraw = "visual-redraw" in html_page
                items.append(
                    {
                        "pass": True,
                        "scores": {
                            "competition_ppt_fit": 4,
                            "visual_anchor_strength": 4 if is_redraw else 3,
                            "one_second_readability": 4,
                            "diagram_clarity": 4,
                            "card_ui_risk": 1,
                        },
                        "failure_reasons": [] if is_redraw else ["main_visual_below_expression_hypothesis"],
                        "key_metrics": {
                            "largest_visual_ratio": 0.64 if is_redraw else 0.32,
                            "target_visual_ratio": 0.7,
                            "utilization": 0.52 if is_redraw else 0.38,
                            "visible_text_length": 110,
                            "card_like_count": 0,
                            "overflow_count": 0,
                        },
                    }
                )
            return {"status": "completed", "summary": {}, "items": items}

        with TemporaryDirectory() as tmp_dir:
            with patch.dict(
                os.environ,
                {
                    "PPT_V5_AB_ENABLE": "1",
                    "PPT_V5_AB_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AI_PASS_TARGET_PAGE_INDEXES": "1",
                    "PPT_V5_AB_VARIANTS": "strategy",
                    "PPT_V5_AB_BLUEPRINT_HTML_REWRITE_ATTEMPTS": "1",
                    "PPT_V5_AB_VISUAL_REDRAW_ENABLE": "1",
                    "PPT_V5_AB_VISUAL_REDRAW_ATTEMPTS": "1",
                    "PPT_V5_AB_ARTIFACT_DIR": tmp_dir,
                },
                clear=False,
            ), patch(
                "app.services.ppt.v5.ai_passes._generate_layout_blueprint_for_candidate",
                side_effect=fake_blueprint,
            ), patch(
                "app.services.ppt.v5.ai_passes._request_direct_body_html",
                side_effect=fake_request,
            ), patch(
                "app.services.ppt.v5.visual_aesthetic_auditor.audit_v5_visual_aesthetics",
                side_effect=fake_visual_audit,
            ):
                result = asyncio.run(apply_ai_design_passes(outline, {"theme": "clean-formal"}, pipeline))

        composition = result["composition_plans"][0]
        report = result["v5_ab_candidate_report"]["items"][0]
        candidate = report["candidates"][0]
        self.assertIn("same_blueprint_visual_redraw", calls)
        self.assertIn("visual-redraw", composition["body_html_fragment"])
        self.assertTrue(candidate["selected_from_visual_redraw"])
        self.assertTrue(candidate["visual_quality_gate"]["pass"])

    def test_render_v5_html_pages_does_not_need_v4_renderer(self):
        outline = {
            "project": {"name": "独立渲染验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "团队协作与分工",
                    "page_series_type": "collaboration_matrix",
                    "core_argument": "通过交接、衔接和应急补位构成闭环。",
                }
            ],
        }

        page = render_v5_html_pages(outline, {"theme": "clean-formal"})[0]

        self.assertIn('data-family-id="collaboration_matrix.role_map"', page)
        self.assertIn('data-selected-variant="role_map_chain"', page)
        self.assertIn('data-composition-id="center_chain_side_roles"', page)
        self.assertNotIn('data-v4-formal="true"', page)

    def test_generate_v5_preview_pages_writes_preview_v5_directory(self):
        with TemporaryDirectory() as tmpdir:
            service = PPTService.__new__(PPTService)
            service.output_dir = tmpdir
            service._extract_outline_pages = lambda outline: outline.get("pages") or []
            service.get_task = AsyncMock(
                return_value={
                    "id": 9001,
                    "project_name": "V5 预览写盘验证",
                    "enhanced_data": {"theme": "clean-formal", "v5_ai_passes": False},
                    "outline_json": {
                        "project": {"name": "V5 预览写盘验证"},
                        "pages": [
                            {
                                "page_index": 1,
                                "title": "V5 路演封面",
                                "page_series_type": "cover_keynote",
                                "content_points": ["巡检闭环", "工程化表达"],
                            },
                            {
                                "page_index": 2,
                                "title": "汇报路径",
                                "page_series_type": "agenda_navigation",
                                "content_points": ["项目背景", "方案链路", "价值结果"],
                            },
                        ],
                    },
                }
            )

            import asyncio

            result = asyncio.run(service.generate_v5_preview_pages(9001, force_rebuild=True))
            pages = asyncio.run(service.get_v5_preview_pages(9001))

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["preview_dir"].endswith("preview_v5_9001"))
            self.assertEqual(len(pages), 2)
            self.assertTrue(all('data-v5-clean="true"' in page for page in pages))

    def test_get_v5_preview_pages_does_not_depend_on_v4_get_html_pages(self):
        with TemporaryDirectory() as tmpdir:
            service = PPTService.__new__(PPTService)
            service.output_dir = tmpdir
            service._extract_outline_pages = lambda outline: outline.get("pages") or []
            service.get_task = AsyncMock(
                return_value={
                    "id": 9002,
                    "project_name": "V5 独立读路径验证",
                    "enhanced_data": {"theme": "clean-formal", "v5_ai_passes": False},
                    "outline_json": {
                        "project": {"name": "V5 独立读路径验证"},
                        "pages": [
                            {
                                "page_index": 1,
                                "title": "团队协作与分工",
                                "page_series_type": "collaboration_matrix",
                                "core_argument": "通过交接、应急补位和升级链路构成闭环。",
                            }
                        ],
                    },
                }
            )
            service.get_html_pages = AsyncMock(side_effect=AssertionError("V4 get_html_pages should not be called"))

            import asyncio

            pages = asyncio.run(service.get_v5_preview_pages(9002, force_rebuild=True))

            self.assertEqual(len(pages), 1)
            self.assertIn('data-v5-clean="true"', pages[0])
            self.assertIn('preview_v5_9002', service._write_v5_preview_html_page(9002, 1, pages[0]))

    def test_review_v5_html_page_validates_v5_contract_without_v4_acceptance(self):
        outline = {
            "project": {"name": "V5 Reviewer 验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "团队协作与分工",
                    "page_series_type": "collaboration_matrix",
                    "content_points": ["岗位职责", "任务交接", "异常升级", "应急补位"],
                    "core_argument": "通过交接、升级与补位构成闭环。",
                }
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        html = render_v5_html_pages(outline, {"theme": "clean-formal"})[0]
        report = review_v5_html_page(
            html,
            outline["pages"][0],
            pipeline["layout_decisions"][0],
            pipeline["render_contracts"][0],
            pipeline["composition_plans"][0],
        )

        self.assertTrue(report["pass"])
        self.assertGreaterEqual(report["score"], 78)
        self.assertEqual(report["evidence"]["data_attrs"]["v5-clean"], "true")

    def test_build_v5_preview_review_report_summarizes_pages(self):
        outline = {
            "project": {"name": "V5 Summary 验证"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "V5 路演封面",
                    "page_series_type": "cover_keynote",
                    "content_points": ["巡检闭环", "工程化表达"],
                    "core_argument": "V5 clean renderer 直接输出 PPT 式 HTML。",
                },
                {
                    "page_index": 2,
                    "title": "汇报路径",
                    "page_series_type": "agenda_navigation",
                    "content_points": ["项目背景", "方案链路", "价值结果"],
                    "core_argument": "目录页要像答辩型导航。",
                },
            ],
        }
        pipeline = build_clean_pipeline(outline, {"theme": "clean-formal"})
        html_pages = render_v5_html_pages(outline, {"theme": "clean-formal"})
        report = build_v5_preview_review_report(pipeline, html_pages, outline["pages"])

        self.assertEqual(report["page_count"], 2)
        self.assertEqual(report["pass_count"], 2)
        self.assertGreater(report["avg_score"], 80)


if __name__ == "__main__":
    unittest.main()
