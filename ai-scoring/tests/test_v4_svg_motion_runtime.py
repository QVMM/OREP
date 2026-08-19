import unittest

from app.services.ppt.ppt_service import PPTService
from app.services.ppt.page_contracts import normalize_page_contract_for_context
from app.services.ppt.presentation_sanitizer import sanitize_final_presentation_html
from app.services.ppt.v4.page_acceptance import evaluate_formal_page_acceptance
from app.services.ppt.v4.formal_render_engine import render_formal_v4_page


class V4SvgMotionRuntimeTests(unittest.TestCase):
    def test_formal_svg_page_includes_motion_runtime(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 10,
                "title": "技术架构总览",
                "page_series_type": "architecture_system",
                "content_points": [
                    "采集层",
                    "边缘层",
                    "平台层",
                    "应用层",
                    "设备接入",
                    "边缘计算",
                    "平台分析",
                    "业务应用",
                ],
            },
        )

        self.assertIn('data-orep-svg-family="architecture_system"', html)
        self.assertIn('data-orep-motion-scope="svg-family"', html)
        self.assertIn("window.__OREP_MOTION_MODE__", html)
        self.assertIn("__OREP_CAPTURE_READY__", html)
        self.assertIn("anime.createTimeline", html)

    def test_cover_renderer_switches_to_split_layout(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 1,
                "title": "智慧农业病虫害监测与预警平台",
                "page_series_type": "cover_keynote",
                "layout_family_id": "cover_keynote.hero_split",
                "layout_variant": "hero_split_left",
                "layout_region_plan": {
                    "focus_strategy": "hero_first",
                    "density_mode": "spacious",
                    "scan_pattern": "single_anchor",
                },
                "content_points": ["AI识别", "边缘感知", "降本增效", "产业落地"],
                "page_goal": "用一页封面明确项目锚点与价值方向。",
                "core_argument": "围绕识别、预警和处置形成完整项目表达。",
            },
        )

        self.assertIn('data-layout-skeleton="hero_split"', html)
        self.assertIn("cover-layout--split", html)
        self.assertIn("cover-summary-card", html)

    def test_agenda_renderer_switches_to_route_board_layout(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 2,
                "title": "汇报目录",
                "page_series_type": "agenda_navigation",
                "layout_family_id": "agenda_navigation.route_board",
                "layout_variant": "route_board_vertical",
                "layout_region_plan": {
                    "focus_strategy": "diagram_first",
                    "density_mode": "dense",
                    "scan_pattern": "staged_progression",
                },
                "content_points": ["项目背景", "方案设计", "架构实现", "应用价值", "答辩总结"],
                "page_goal": "先说明阅读路线，再进入正文。",
                "core_argument": "整套汇报沿着问题、方案、验证、价值展开。",
            },
        )

        self.assertIn('data-layout-skeleton="route_board_vertical"', html)
        self.assertIn("agenda-layout--route", html)
        self.assertIn("agenda-route-card", html)

    def test_evidence_board_emits_caption_grid_skeleton(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 3,
                "title": "项目证据与价值闭环",
                "page_series_type": "evidence_board",
                "layout_family_id": "evidence_board.caption_grid",
                "layout_variant": "caption_grid_two_up",
                "layout_region_plan": {
                    "focus_strategy": "evidence_first",
                    "density_mode": "balanced",
                    "scan_pattern": "single_anchor",
                },
                "content_points": [
                    "政策依据",
                    "行业痛点",
                    "试点成效",
                    "实施抓手",
                    "复制价值",
                    "落地回报",
                ],
                "page_goal": "用证据、逻辑和价值三段式说明项目为何可信。",
            },
        )

        self.assertIn('data-layout-skeleton="caption_grid"', html)
        self.assertIn("evidence-layout--evidence_first", html)
        self.assertIn("logic-column", html)

    def test_definition_canvas_emits_dual_column_skeleton(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 4,
                "title": "行业痛点与问题边界",
                "page_series_type": "definition_canvas",
                "layout_family_id": "definition_canvas.dual_column",
                "layout_variant": "dual_column_cardrail",
                "layout_region_plan": {
                    "narrative_segment": "definition",
                    "narrative_role": "problem_framing",
                    "focus_strategy": "hero_first",
                    "density_mode": "dense",
                    "scan_pattern": "single_anchor",
                },
                "content_points": ["行业痛点", "用户现状", "边界约束", "技术抓手"],
                "core_argument": "当前痛点集中在识别滞后、反馈断层和处置链路不闭环。",
            },
        )

        self.assertIn('data-layout-skeleton="definition_dual_column"', html)
        self.assertIn("definition-hero-card", html)

    def test_content_support_focus_variant_emits_support_focus_stack(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 5,
                "title": "关键支撑论据",
                "page_series_type": "content_support",
                "layout_family_id": "content_support.support_cards",
                "layout_variant": "support_cards_focus",
                "layout_region_plan": {
                    "narrative_segment": "definition",
                    "narrative_role": "scope_definition",
                    "focus_strategy": "hero_first",
                    "density_mode": "balanced",
                    "scan_pattern": "single_anchor",
                },
                "content_points": ["核心论点", "支撑论据一", "支撑论据二", "支撑论据三"],
                "core_argument": "先把中心论点打稳，再补三条关键支撑。",
            },
        )

        self.assertIn('data-layout-skeleton="support_focus_stack"', html)
        self.assertIn("support-hero-card", html)

    def test_practice_evidence_timeline_variant_emits_timeline_strip(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 6,
                "title": "实操验证链路",
                "page_series_type": "practice_evidence",
                "layout_family_id": "practice_evidence.timeline_demo",
                "layout_variant": "timeline_demo_strip",
                "layout_region_plan": {
                    "narrative_segment": "proof_value",
                    "narrative_role": "execution_proof",
                    "focus_strategy": "evidence_first",
                    "density_mode": "balanced",
                    "scan_pattern": "staged_progression",
                },
                "content_points": ["数据接入", "模型推理", "结果验证", "证据回看", "评分对齐"],
                "core_argument": "把输入、操作、结果与证据形成可验证的实操闭环。",
            },
        )

        self.assertIn('data-layout-skeleton="practice_timeline_strip"', html)
        self.assertIn("practice-timeline-strip", html)

    def test_bridge_story_feedback_mode_emits_feedback_loop_board(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 7,
                "title": "执行反馈与育人成效闭环",
                "page_series_type": "bridge_story",
                "layout_family_id": "bridge_story.loop_story",
                "layout_variant": "loop_story_split",
                "layout_region_plan": {
                    "narrative_segment": "solution",
                    "narrative_role": "feedback_bridge",
                    "focus_strategy": "diagram_first",
                    "density_mode": "balanced",
                    "scan_pattern": "single_anchor",
                },
                "content_points": ["执行过程", "反馈闭环", "调整动作", "育人成效"],
                "core_argument": "把执行、反馈、调整和成效形成闭环表达。",
            },
        )

        self.assertIn('data-layout-skeleton="feedback_loop_board"', html)
        self.assertIn("edu-loop-grid", html)

    def test_collaboration_matrix_chain_mode_emits_handoff_chain_board(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 8,
                "title": "岗位交接与应急补位",
                "page_series_type": "collaboration_matrix",
                "layout_family_id": "collaboration_matrix.role_map",
                "layout_variant": "role_map_chain",
                "layout_region_plan": {
                    "narrative_segment": "solution",
                    "narrative_role": "handoff_chain",
                    "focus_strategy": "diagram_first",
                    "density_mode": "balanced",
                    "scan_pattern": "staged_progression",
                },
                "content_points": ["岗位职责", "交接机制", "应急补位", "协同结果"],
            },
        )

        self.assertIn('data-layout-skeleton="handoff_chain_board"', html)
        self.assertIn("team-chain-grid", html)

    def test_journey_timeline_retrospective_mode_emits_retrospective_split(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 9,
                "title": "问题复盘与质量改进",
                "page_series_type": "journey_timeline",
                "layout_family_id": "journey_timeline.milestone_rail",
                "layout_variant": "milestone_rail_cards",
                "layout_region_plan": {
                    "narrative_segment": "solution",
                    "narrative_role": "retrospective_improvement",
                    "focus_strategy": "diagram_first",
                    "density_mode": "balanced",
                    "scan_pattern": "split_compare",
                },
                "content_points": ["需求调研", "测试验证", "问题复盘", "质量改进"],
            },
        )

        self.assertIn('data-layout-skeleton="retrospective_split"', html)
        self.assertIn("timeline-retro-side", html)

    def test_acceptance_flags_collaboration_role_skeleton_mismatch(self):
        result = evaluate_formal_page_acceptance(
            '<!DOCTYPE html><html><body><main class="slide" data-v4-formal="true" data-layout-skeleton="role_grid_board"></main></body></html>',
            {
                "title": "岗位交接与应急补位",
                "page_series_type": "collaboration_matrix",
                "layout_region_plan": {"narrative_role": "handoff_chain"},
            },
        )

        self.assertIn("role_skeleton_binding_mismatch", result["failed_checks"])

    def test_acceptance_flags_timeline_role_skeleton_mismatch(self):
        result = evaluate_formal_page_acceptance(
            '<!DOCTYPE html><html><body><main class="slide" data-v4-formal="true" data-layout-skeleton="retrospective_split"></main></body></html>',
            {
                "title": "研发历程与里程碑",
                "page_series_type": "journey_timeline",
                "layout_region_plan": {"narrative_role": "milestone_progress"},
            },
        )

        self.assertIn("role_skeleton_binding_mismatch", result["failed_checks"])

    def test_structure_rebuild_prefers_formal_renderer_for_svg_series(self):
        service = PPTService.__new__(PPTService)
        html = service._repair_html_page_content(
            html="",
            page_meta={
                "page_index": 8,
                "title": "方案桥接页",
                "page_series_type": "mapping_bridge",
                "content_points": [
                    "人工巡检延迟",
                    "病虫害响应慢",
                    "数据来源分散",
                    "平台统一接入",
                    "实时预警分析",
                    "闭环处置反馈",
                ],
            },
            page_index=8,
            total_pages=40,
            strategy="structure_rebuild",
            quality_context={},
            deck_blueprint={"project_name": "测试项目", "page_count": 40},
        )

        self.assertIn('data-v4-formal="true"', html)
        self.assertIn('data-orep-svg-family="mapping_bridge"', html)
        self.assertIn("window.__OREP_MOTION_MODE__", html)
        self.assertNotIn("ROADSHOW SLIDE", html)

    def test_sanitizer_keeps_hidden_slot_role_contracts(self):
        html = sanitize_final_presentation_html(
            '<section class="panel" data-slot-role="flow_mapping"><div data-orep-svg-family="mapping_bridge"></div></section>'
        )
        self.assertIn('data-slot-role="flow_mapping"', html)

    def test_mapping_bridge_prefers_slot_blocks_over_fixed_mode_labels(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 7,
                "title": "痛点深挖页",
                "page_series_type": "mapping_bridge",
                "layout_slots": [
                    {"slot_role": "flow_mapping", "block": "痛点映射"},
                    {"slot_role": "flow_mapping", "block": "解决动作"},
                    {"slot_role": "flow_mapping", "block": "数据闭环"},
                    {"slot_role": "flow_mapping", "block": "价值输出"},
                ],
                "content_points": [
                    "围绕核心痛点做监测",
                    "形成自动预警与处置建议",
                    "沉淀数据反馈与决策支撑",
                ],
            },
        )

        self.assertIn("痛点映射", html)
        self.assertIn("解决动作", html)
        self.assertIn("数据闭环", html)
        self.assertIn("价值输出", html)
        self.assertNotIn("传统模式", html)
        self.assertNotIn("平台模式", html)

    def test_solution_overview_contract_normalization_relabels_generic_bridge_blocks(self):
        page = {
            "page_index": 8,
            "title": "我们的解决方案：智慧农业物联网大数据平台",
            "page_goal": "用一张架构图总览平台的端-边-云三层技术架构和核心功能。",
            "core_argument": "平台采用端-边-云协同架构，实现从数据采集、边缘处理到云端智能分析的全链路覆盖。",
        }
        contract = normalize_page_contract_for_context(
            page,
            {
                "role": "solution_overview",
                "page_series_type": "mapping_bridge",
                "required_blocks": ["痛点映射", "解决动作", "数据闭环", "价值输出"],
            },
        )

        self.assertEqual(
            contract["required_blocks"][:4],
            ["终端采集", "边缘处理", "云端分析", "业务服务"],
        )

    def test_solution_overview_slot_refresh_uses_normalized_bridge_blocks(self):
        service = PPTService.__new__(PPTService)
        page = {
            "page_index": 8,
            "title": "我们的解决方案：智慧农业物联网大数据平台",
            "page_goal": "用一张架构图总览平台的端-边-云三层技术架构和核心功能。",
            "core_argument": "平台采用端-边-云协同架构，实现从数据采集、边缘处理到云端智能分析的全链路覆盖。",
        }
        contract = normalize_page_contract_for_context(
            page,
            {
                "role": "solution_overview",
                "page_series_type": "mapping_bridge",
                "required_blocks": ["痛点映射", "解决动作", "数据闭环", "价值输出"],
            },
        )
        old_slots = [
            {"slot_role": "flow_mapping", "block": "痛点映射"},
            {"slot_role": "flow_mapping", "block": "解决动作"},
            {"slot_role": "flow_mapping", "block": "数据闭环"},
            {"slot_role": "flow_mapping", "block": "价值输出"},
        ]

        self.assertTrue(service._layout_slots_need_refresh(old_slots, contract))
        new_slots = service._build_page_layout_slots(page, contract)
        self.assertEqual(
            [slot["block"] for slot in new_slots[:4]],
            ["终端采集", "边缘处理", "云端分析", "业务服务"],
        )

    def test_title_semantics_override_section_noise_when_guessing_role(self):
        service = PPTService.__new__(PPTService)
        role = service._guess_outline_role(
            {
                "title": "产教融合实践",
                "section": "产教融合与团队协作",
                "slide_role": "team_collaboration",
                "page_series_type": "collaboration_matrix",
            }
        )
        self.assertEqual(role, "industry_education")

    def test_architecture_system_uses_short_stage_labels(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 10,
                "title": "技术架构总览：端-边-云三层协同",
                "page_series_type": "architecture_system",
                "layout_slots": [
                    {"slot_role": "supporting_argument", "block": "架构分层"},
                    {"slot_role": "supporting_argument", "block": "关键技术难点"},
                    {"slot_role": "supporting_argument", "block": "选型理由"},
                    {"slot_role": "supporting_argument", "block": "实操证明"},
                ],
                "content_points": [
                    "采用端-边-云三层架构，实现数据采集、预处理到智能分析的全链路覆盖",
                    "说明协议与标准适配方式",
                ],
            },
        )

        self.assertIn("端侧采集", html)
        self.assertIn("边缘处理", html)
        self.assertIn("云端平台", html)
        self.assertIn("架构分层", html)

    def test_architecture_renderer_consumes_focus_and_density_signals(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 10,
                "title": "技术架构总览",
                "page_series_type": "architecture_system",
                "layout_family_id": "architecture_system.layer_stack",
                "layout_variant": "layer_stack_center",
                "layout_region_plan": {
                    "focus_strategy": "diagram_first",
                    "density_mode": "spacious",
                    "scan_pattern": "single_anchor",
                },
                "layout_slots": [
                    {"slot_role": "supporting_argument", "block": "架构分层"},
                    {"slot_role": "supporting_argument", "block": "关键能力"},
                    {"slot_role": "supporting_argument", "block": "落地验证"},
                ],
                "content_points": ["端边云三层协同", "数据链路清晰", "验证过程完整"],
            },
        )

        self.assertIn('data-focus-strategy="diagram_first"', html)
        self.assertIn('data-density-mode="spacious"', html)
        self.assertIn('data-layout-skeleton="layer_stack_center"', html)
        self.assertIn("arch-layout--diagram_first", html)
        self.assertIn("grid-template-columns: 1.34fr .66fr", html)

    def test_value_matrix_renderer_uses_contextual_blocks_and_metrics(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 30,
                "title": "经济价值：降本增效增收",
                "page_series_type": "value_matrix",
                "layout_slots": [
                    {"slot_role": "value_matrix", "block": "降本成效"},
                    {"slot_role": "value_matrix", "block": "增产表现"},
                    {"slot_role": "value_matrix", "block": "增收回报"},
                    {"slot_role": "value_matrix", "block": "预警价值"},
                ],
                "ppt_text": "可量化的经济效益：\n• 降低农药使用量 30%\n• 提高作物产量 15%\n• 户均年增收约 5000元\n• 提前3-5天预警病虫害",
                "core_argument": "平台能为用户带来可量化的降本、增产、增收效益。",
            },
        )

        self.assertIn('data-v4-formal="true"', html)
        self.assertIn("降本成效", html)
        self.assertIn("30%", html)
        self.assertIn("5000元", html)

    def test_value_matrix_renderer_switches_to_scenario_layout(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 30,
                "title": "推广路径与应用场景",
                "page_series_type": "value_matrix",
                "layout_family_id": "value_matrix.scenario_map",
                "layout_variant": "scenario_map_split",
                "layout_region_plan": {
                    "focus_strategy": "hero_first",
                    "density_mode": "balanced",
                    "scan_pattern": "grid_scan",
                },
                "layout_slots": [
                    {"slot_role": "value_matrix", "block": "服务对象"},
                    {"slot_role": "value_matrix", "block": "应用场景"},
                    {"slot_role": "value_matrix", "block": "推广机制"},
                    {"slot_role": "value_matrix", "block": "复制路径"},
                ],
                "ppt_text": "面向种植户、合作社和示范基地，项目具备跨区域复制和行业推广基础。",
            },
        )

        self.assertIn("value-layout--scenario", html)
        self.assertIn("scenario-board", html)
        self.assertIn('data-scan-pattern="grid_scan"', html)

    def test_mapping_bridge_renderer_switches_to_compare_layout(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 8,
                "title": "解决方案升级对比",
                "page_series_type": "mapping_bridge",
                "layout_family_id": "mapping_bridge.before_after",
                "layout_variant": "before_after_with_lane",
                "layout_region_plan": {
                    "focus_strategy": "diagram_first",
                    "density_mode": "balanced",
                    "scan_pattern": "split_compare",
                },
                "layout_slots": [
                    {"slot_role": "flow_mapping", "block": "改良前问题"},
                    {"slot_role": "flow_mapping", "block": "改良后做法"},
                    {"slot_role": "flow_mapping", "block": "数据闭环"},
                    {"slot_role": "flow_mapping", "block": "价值输出"},
                ],
                "content_points": ["传统人工巡检发现晚", "平台协同实现实时预警", "形成数据闭环与价值回收"],
            },
        )

        self.assertIn("bridge-layout--compare", html)
        self.assertIn("bridge-compare-grid", html)
        self.assertIn("改良前", html)
        self.assertIn("改良后", html)

    def test_bridge_story_renderer_outputs_formal_bridge_cards(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 35,
                "title": "产教融合实践",
                "page_series_type": "bridge_story",
                "layout_slots": [
                    {"slot_role": "bridge_flow", "block": "课程能力来源"},
                    {"slot_role": "bridge_flow", "block": "行业场景任务"},
                    {"slot_role": "bridge_flow", "block": "合作探究过程"},
                    {"slot_role": "feedback_loop", "block": "反馈闭环"},
                    {"slot_role": "feedback_loop", "block": "育人成效"},
                ],
                "core_argument": "项目响应国家数字乡村战略，解决真实产业痛点，具备明确的政策支持和应用基础。",
            },
        )

        self.assertIn('data-v4-formal="true"', html)
        self.assertIn('data-slot-role="bridge_flow"', html)
        self.assertIn('data-slot-role="feedback_loop"', html)
        self.assertIn("课程能力来源", html)
        self.assertIn("育人成效", html)

    def test_application_value_contract_can_promote_to_innovation_compare(self):
        service = PPTService.__new__(PPTService)
        page = {
            "page_index": 32,
            "title": "应用价值：综合效益与推广基础",
            "slide_role": "application_value",
            "served_scoring_dimension": "创新创意10",
            "page_goal": "清晰列出项目的核心技术创新点，并与同类方案对比，突出差异化优势。",
            "ppt_text": "核心技术创新点：\n1. 多源传感器融合建模\n2. 轻量化病害识别模型（仅2.3MB）\n3. 边缘-云端协同（告警<3秒）",
        }

        service._complete_outline_page_defaults(page, 32, "测试项目")

        self.assertEqual(page["slide_role"], "innovation")
        self.assertEqual(page["contract_id"], "innovation_effect_board_v1")
        self.assertEqual(page["page_series_type"], "innovation_compare")
        self.assertEqual(page["title"], "创新对照：机制升级与量化结果")
        self.assertIn("改良前问题", [slot["block"] for slot in page["layout_slots"]])

    def test_innovation_renderer_uses_problem_fallback_when_source_has_no_before_state(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 32,
                "title": "创新对照：机制升级与量化结果",
                "page_series_type": "innovation_compare",
                "layout_slots": [
                    {"slot_role": "before_after_compare", "block": "创新机制"},
                    {"slot_role": "before_after_compare", "block": "改良前问题"},
                    {"slot_role": "before_after_compare", "block": "改良后做法"},
                    {"slot_role": "innovation_metric", "block": "创新成效"},
                    {"slot_role": "innovation_metric", "block": "量化结果"},
                ],
                "ppt_text": "核心技术创新点：\n1. 多源传感器融合建模\n2. 轻量化病害识别模型（仅2.3MB）\n3. 边缘-云端协同（告警<3秒）",
            },
        )

        self.assertIn("改良前问题", html)
        self.assertIn("旧做法的效率瓶颈", html)

    def test_journey_timeline_merges_track_and_iteration_slots_into_milestones(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 34,
                "title": "研发历程与里程碑",
                "page_series_type": "journey_timeline",
                "layout_slots": [
                    {"slot_role": "timeline_track", "block": "需求调研", "semantic_group": "journey_stage", "sequence_index": 1},
                    {"slot_role": "timeline_track", "block": "原型开发", "semantic_group": "journey_stage", "sequence_index": 2},
                    {"slot_role": "timeline_track", "block": "测试验证", "semantic_group": "journey_stage", "sequence_index": 3},
                    {"slot_role": "iteration_evidence", "block": "问题复盘", "semantic_group": "journey_stage", "sequence_index": 4},
                    {"slot_role": "iteration_evidence", "block": "质量改进", "semantic_group": "journey_stage", "sequence_index": 5},
                ],
                "content_points": [
                    "项目遵循调研、设计、开发、验证的工程化路径",
                    "每个阶段都有明确产出和验证方式",
                ],
            },
        )

        self.assertIn("需求调研", html)
        self.assertIn("原型开发", html)
        self.assertIn("测试验证", html)
        self.assertIn("问题复盘", html)
        self.assertIn("质量改进", html)

    def test_placeholder_analysis_ignores_hidden_slot_attrs_and_inline_runtime(self):
        service = PPTService.__new__(PPTService)
        analysis = service._analyze_placeholder_markers(
            "这是一个正式页面",
            '<section data-slot-role="flow_mapping">正式内容</section><script>const pending = false;</script>',
        )
        self.assertTrue(analysis["pass"])

    def test_practice_evidence_renderer_outputs_formal_operation_and_evidence_slots(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 18,
                "title": "实操演示：病害识别推理流程",
                "page_series_type": "practice_evidence",
                "layout_slots": [
                    {"slot_role": "operation_stage_board", "block": "当前操作：病害识别推理流程"},
                    {"slot_role": "operation_stage_board", "block": "输入数据"},
                    {"slot_role": "operation_stage_board", "block": "关键操作"},
                    {"slot_role": "operation_stage_board", "block": "输出结果"},
                    {"slot_role": "evidence_wall", "block": "验证证据"},
                    {"slot_role": "supporting_argument", "block": "评分对齐"},
                ],
                "ppt_text": "输入叶片图像后完成推理，输出病害类别和置信度，并展示识别结果截图。",
            },
        )

        self.assertIn('data-v4-formal="true"', html)
        self.assertIn('data-slot-role="operation_stage_board"', html)
        self.assertIn('data-slot-role="evidence_wall"', html)
        self.assertNotIn("generic-layout", html)

    def test_protocol_board_renderer_outputs_protocol_and_risk_slots(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 28,
                "title": "开发规范与安全保障",
                "page_series_type": "protocol_board",
                "layout_slots": [
                    {"slot_role": "protocol_flow", "block": "开发规范"},
                    {"slot_role": "protocol_flow", "block": "数据合规"},
                    {"slot_role": "protocol_flow", "block": "操作安全"},
                    {"slot_role": "risk_action_board", "block": "知识产权"},
                    {"slot_role": "risk_action_board", "block": "异常处置"},
                ],
                "content_points": ["代码留痕、访问控制、异常告警和应急响应均有明确规则。"],
            },
        )

        self.assertIn('data-slot-role="protocol_flow"', html)
        self.assertIn('data-slot-role="risk_action_board"', html)
        self.assertNotIn("generic-layout", html)

    def test_closing_board_renderer_outputs_closing_signal(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 40},
            {
                "page_index": 40,
                "title": "总结与答辩收束",
                "page_series_type": "closing_board",
                "layout_slots": [
                    {"slot_role": "closing_signal", "block": "一句话总结"},
                    {"slot_role": "closing_signal", "block": "核心成果回扣"},
                    {"slot_role": "closing_signal", "block": "价值落点"},
                    {"slot_role": "closing_signal", "block": "答辩收束"},
                ],
                "core_argument": "项目已经完成从识别、预警到处置建议的闭环验证，具备明确落地价值。",
                "ppt_text": "病害预警提前3-5天，农药使用量降低30%，户均年增收约5000元。",
            },
        )

        self.assertIn('data-slot-role="closing_signal"', html)
        self.assertIn("5000元", html)
        self.assertIn("closing-layout--hero_first", html)

    def test_formal_acceptance_rejects_registered_series_generic_layout(self):
        report = evaluate_formal_page_acceptance(
            '<!DOCTYPE html><html><body><main class="slide" data-v4-formal="true"><section class="generic-layout"><h1>开发规范与安全保障</h1></section></main></body></html>',
            page_meta={"title": "开发规范与安全保障", "page_series_type": "protocol_board"},
            strict_formal=True,
        )

        self.assertFalse(report["pass"])
        self.assertIn("generic_registered_series_fallback", report["failed_checks"])

    def test_formal_acceptance_rejects_missing_rhythm_signals(self):
        report = evaluate_formal_page_acceptance(
            (
                '<!DOCTYPE html><html><body><main class="slide" data-v4-formal="true">'
                '<h1>推广路径与应用场景</h1>'
                '<section class="value-layout value-layout--score"></section>'
                '</main></body></html>'
            ),
            page_meta={
                "title": "推广路径与应用场景",
                "page_series_type": "value_matrix",
                "layout_family_id": "value_matrix.scenario_map",
                "layout_variant": "scenario_map_split",
                "layout_region_plan": {
                    "focus_strategy": "hero_first",
                    "density_mode": "balanced",
                    "scan_pattern": "grid_scan",
                },
            },
            strict_formal=True,
        )

        self.assertFalse(report["pass"])
        self.assertIn("missing_focus_strategy_signal", report["failed_checks"])
        self.assertIn("missing_layout_skeleton", report["failed_checks"])

    def test_formal_acceptance_accepts_cover_with_rhythm_structure(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 1,
                "title": "智慧农业病虫害监测与预警平台",
                "page_series_type": "cover_keynote",
                "layout_family_id": "cover_keynote.hero_stack",
                "layout_variant": "hero_stack_right",
                "layout_region_plan": {
                    "focus_strategy": "hero_first",
                    "density_mode": "balanced",
                    "scan_pattern": "grid_scan",
                },
                "content_points": ["AI识别", "边缘感知", "降本增效", "产业落地"],
                "page_goal": "形成有锚点、有标签、有呼吸感的封面表达。",
            },
        )
        report = evaluate_formal_page_acceptance(
            html,
            page_meta={
                "title": "智慧农业病虫害监测与预警平台",
                "page_series_type": "cover_keynote",
                "layout_family_id": "cover_keynote.hero_stack",
                "layout_variant": "hero_stack_right",
                "layout_region_plan": {
                    "focus_strategy": "hero_first",
                    "density_mode": "balanced",
                    "scan_pattern": "grid_scan",
                },
            },
            strict_formal=True,
        )

        self.assertTrue(report["pass"])

    def test_formal_acceptance_accepts_evidence_board_with_rhythm_structure(self):
        html = render_formal_v4_page(
            {"project_name": "测试项目", "page_count": 20},
            {
                "page_index": 3,
                "title": "项目证据与价值闭环",
                "page_series_type": "evidence_board",
                "layout_family_id": "evidence_board.caption_grid",
                "layout_variant": "caption_grid_two_up",
                "layout_region_plan": {
                    "focus_strategy": "evidence_first",
                    "density_mode": "balanced",
                    "scan_pattern": "single_anchor",
                },
                "content_points": [
                    "政策依据",
                    "行业痛点",
                    "试点成效",
                    "实施抓手",
                    "复制价值",
                    "落地回报",
                ],
            },
        )
        report = evaluate_formal_page_acceptance(
            html,
            page_meta={
                "title": "项目证据与价值闭环",
                "page_series_type": "evidence_board",
                "layout_family_id": "evidence_board.caption_grid",
                "layout_variant": "caption_grid_two_up",
                "layout_region_plan": {
                    "focus_strategy": "evidence_first",
                    "density_mode": "balanced",
                    "scan_pattern": "single_anchor",
                },
            },
            strict_formal=True,
        )

        self.assertTrue(report["pass"])


if __name__ == "__main__":
    unittest.main()
