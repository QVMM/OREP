import unittest

from app.services.ppt.v6 import build_v6_pipeline, render_v6_html_pages
from app.services.ppt.v6.blueprint import validate_blueprint
from app.services.ppt.v6.content_ledger import build_content_ledger
from app.services.ppt.v6.layout_solver import BODY, solve_layouts
from app.services.ppt.ppt_service import PPTService

from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock
import asyncio


class V6SchemaPptRendererTests(unittest.TestCase):
    def test_content_ledger_preserves_high_value_atoms(self):
        outline = {
            "pages": [
                {
                    "page_index": 1,
                    "title": "技术架构",
                    "page_series_type": "architecture_system",
                    "core_argument": "边缘网关完成 MQTT、LoRa、HTTP 多协议适配，并对异常数据进行本地预警。",
                    "content_points": ["系统界面截图证明平台可运行", "准确率提升 12%"],
                }
            ]
        }

        atoms = build_content_ledger(outline)

        self.assertGreaterEqual(len(atoms), 3)
        self.assertTrue(any(atom.semantic_type == "technical_fact" and atom.importance == "high" for atom in atoms))
        self.assertTrue(any(atom.semantic_type == "evidence" for atom in atoms))
        self.assertTrue(all(atom.raw_text for atom in atoms))
        self.assertTrue(any(atom.speaker_note for atom in atoms))

    def test_v6_pipeline_builds_professional_blueprint_and_safe_layout(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "端-边-云三层架构",
                    "page_series_type": "architecture_system",
                    "core_argument": "端侧采集、边缘预处理、云端分析构成闭环。",
                    "content_points": ["端侧采集", "边缘协议适配", "云端 AI 分析", "决策看板"],
                }
            ],
        }

        pipeline = build_v6_pipeline(outline, {"project_name": "智慧农业平台"})
        blueprint = pipeline["_objects"]["blueprints"][0]
        layout = pipeline["_objects"]["layouts"][0]

        self.assertEqual(pipeline["version"], "v6_schema_ppt_renderer_p0")
        self.assertTrue(validate_blueprint(blueprint)["pass"])
        self.assertEqual(blueprint.expression_type, "architecture_diagram")
        self.assertTrue(blueprint.main_visual.must_explain)
        self.assertTrue(blueprint.main_visual.required_annotations)
        for region in layout.regions:
            self.assertGreaterEqual(region.x, BODY.x)
            self.assertGreaterEqual(region.y, BODY.y)
            self.assertLessEqual(region.x + region.w, BODY.x + BODY.w)
            self.assertLessEqual(region.y + region.h, BODY.y + BODY.h)

    def test_v6_renderer_outputs_system_svg_not_ai_direct_html(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "端-边-云三层架构",
                    "page_series_type": "architecture_system",
                    "content_points": ["端侧采集", "边缘处理", "云端平台"],
                },
                {
                    "page_index": 2,
                    "title": "实操证据",
                    "page_series_type": "practice_evidence",
                    "content_points": ["实操现场照片", "系统界面截图", "数据样例截图"],
                },
            ],
        }

        pages = render_v6_html_pages(outline, {"project_name": "智慧农业平台"})

        self.assertEqual(len(pages), 2)
        self.assertIn('data-v6-schema-renderer="true"', pages[0])
        self.assertIn('data-v6-svg="true"', pages[0])
        self.assertIn("layered_architecture", build_v6_pipeline(outline) ["diagram_schemas"][0]["diagram_type"])
        self.assertIn("PPT EVIDENCE", pages[1])
        self.assertNotIn("data-body-mode=\"ai_direct\"", pages[0])
        self.assertNotIn("mermaid", pages[0].lower())
        self.assertNotIn("graphviz", pages[0].lower())

    def test_layout_solver_prefers_evidence_mosaic_for_practice_pages(self):
        outline = {
            "pages": [
                {
                    "page_index": 1,
                    "title": "实操验证",
                    "page_series_type": "practice_evidence",
                    "content_points": ["实操现场照片", "系统界面截图", "数据样例截图"],
                }
            ]
        }
        pipeline = build_v6_pipeline(outline)
        layout = pipeline["_objects"]["layouts"][0]

        self.assertEqual(layout.layout_id, "evidence_mosaic")
        self.assertGreaterEqual(layout.score, 80)

    def test_generate_v6_preview_pages_writes_independent_directory(self):
        with TemporaryDirectory() as tmpdir:
            service = PPTService.__new__(PPTService)
            service.output_dir = tmpdir
            service._extract_outline_pages = lambda outline: outline.get("pages") or []
            service._normalize_outline_pages_for_render = lambda task, pages: pages
            service.get_task = AsyncMock(
                return_value={
                    "id": 9010,
                    "project_name": "V6 独立预览",
                    "team_name": "测试团队",
                    "theme": "light_tech_competition",
                    "enhanced_data": {},
                    "outline_json": {
                        "project": {"name": "V6 独立预览"},
                        "pages": [
                            {
                                "page_index": 1,
                                "title": "端-边-云三层架构",
                                "page_series_type": "architecture_system",
                                "content_points": ["端侧采集", "边缘处理", "云端平台"],
                            }
                        ],
                    },
                }
            )

            result = asyncio.run(service.generate_v6_preview_pages(9010, force_rebuild=True))
            pages = asyncio.run(service.get_v6_preview_pages(9010))

            self.assertEqual(result["status"], "completed")
            self.assertTrue(result["preview_dir"].endswith("preview_v6_9010"))
            self.assertEqual(len(pages), 1)
            self.assertIn('data-v6-schema-renderer="true"', pages[0])
            self.assertTrue(service.load_v6_pipeline_snapshot(9010)["version"].startswith("v6_schema"))

    def test_v6_cover_and_agenda_use_dedicated_renderers(self):
        outline = {
            "project": {"name": "智慧农业平台"},
            "pages": [
                {
                    "page_index": 1,
                    "title": "智慧农业平台",
                    "page_series_type": "cover_keynote",
                    "content_points": ["物联网感知", "AI 决策", "实操验证"],
                },
                {
                    "page_index": 2,
                    "title": "路演议程",
                    "page_series_type": "agenda_navigation",
                    "content_points": ["项目背景", "方案设计", "实操验证", "成果价值"],
                },
            ],
        }

        pipeline = build_v6_pipeline(outline, {"project_name": "智慧农业平台"})
        pages = render_v6_html_pages(outline, {"project_name": "智慧农业平台"}, pipeline_payload=pipeline)
        schemas = pipeline["diagram_schemas"]

        self.assertEqual(schemas[0]["diagram_type"], "cover_signal")
        self.assertEqual(schemas[1]["diagram_type"], "route_map")
        self.assertIn("职业院校技能大赛参赛项目", pages[0])
        self.assertIn("data-agenda-node", pages[1])
        self.assertIn("cover_full_hero", pages[0])
        self.assertIn("display:none;", pages[0])
        self.assertNotIn("反馈优化", pages[0])
        self.assertNotIn("反馈优化", pages[1])

    def test_v6_agenda_title_overrides_bad_upstream_series(self):
        outline = {
            "pages": [
                {
                    "page_index": 1,
                    "title": "路演议程",
                    "page_series_type": "closing_board",
                    "content_points": ["项目背景", "方案设计", "实操验证", "成果价值"],
                }
            ]
        }

        pipeline = build_v6_pipeline(outline)
        pages = render_v6_html_pages(outline, pipeline_payload=pipeline)

        self.assertEqual(pipeline["diagram_schemas"][0]["diagram_type"], "route_map")
        self.assertIn("data-agenda-node", pages[0])


if __name__ == "__main__":
    unittest.main()
