from __future__ import annotations

import json
from pathlib import Path

from backend.orchestrator.image2_renderer import (
    _build_image_prompt,
    _load_image2_page_briefs,
    _resolve_image_asset_inputs,
)
from backend.orchestrator.roadshow_agent import (
    _compact_user_requirement_for_image2,
    _image2_asset_token_inventory_block,
    _image2_asset_tokens_from_inventory,
    _image2_outline_segments,
)
from backend.orchestrator.roadshow_cards import (
    PageContentCard,
    build_image2_page_briefs_payload,
)
from backend.parser.paper_model import ParsedPaper


def test_image2_page_briefs_include_layout_and_evidence_fields():
    payload = build_image2_page_briefs_payload(
        [
            PageContentCard(
                page=1,
                page_type="cover",
                formal_title="智农云控",
                core_sentence="温室环境智能监测与调控系统",
                visible_content="实时感知；智能预警；联动控制",
            ),
            PageContentCard(
                page=2,
                page_type="content",
                section="项目背景",
                formal_title="政策引领与产业需求",
                core_sentence="项目符合农业现代化与数字化转型方向",
                visible_content="政策导向；传统温室痛点；市场需求",
                judge_focus="证明立项真实、方向正确、问题值得解决",
                primary_visual={
                    "type": "policy_market_map",
                    "purpose": "把政策、痛点和需求放在一起",
                    "required_elements": "政策截图、痛点地图、趋势图",
                    "visual_weight": "65%",
                    "forbidden_layouts": "不要做成空泛三张卡片",
                },
                required_assets=["[[ASSET:asset_001]]"],
                asset_status="provided",
            ),
        ]
    )

    brief = payload["briefs"][1]

    assert brief["title"] == "政策引领与产业需求"
    assert "65%" in brief["layout_intent"]
    assert "立项真实" in brief["evidence_focus"]
    assert brief["asset_refs"] == ["[[ASSET:asset_001]]"]
    assert "asset_id" in brief["image_prompt_notes"]


def test_image2_renderer_prefers_page_briefs_and_resolves_asset_images(tmp_path: Path):
    project_dir = tmp_path / "project"
    asset_dir = project_dir / "sources" / "images" / "assets"
    asset_dir.mkdir(parents=True)
    image_path = asset_dir / "asset_001.png"
    image_path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (project_dir / "sources" / "asset_registry.json").write_text(
        json.dumps(
            {
                "version": 1,
                "assets": [
                    {
                        "asset_id": "asset_001",
                        "asset_type": "policy_source",
                        "filename": "asset_001.png",
                        "path": "images/assets/asset_001.png",
                        "href": "../sources/images/assets/asset_001.png",
                        "caption": "政策截图",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (project_dir / "image2_page_briefs.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "briefs": [
                    {
                        "page": 2,
                        "title": "政策背景",
                        "core_message": "政策支持农业数字化",
                        "visible_points": "政策导向；产业升级",
                        "visual_scene": "政策截图和趋势图组合",
                        "layout_intent": "政策/痛点/需求三栏",
                        "evidence_focus": "证明方向正确",
                        "asset_refs": ["[[ASSET:asset_001]]"],
                        "image_prompt_notes": "使用真实政策截图，不要显示 asset_id",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    briefs = _load_image2_page_briefs(project_dir)
    asset_context = _resolve_image_asset_inputs(
        project_dir,
        "[[ASSET:asset_001]]",
        {
            "asset_001": {
                "asset_id": "asset_001",
                "filename": "asset_001.png",
                "path": "images/assets/asset_001.png",
                "caption": "政策截图",
            }
        },
        page_num=2,
    )
    prompt = _build_image_prompt(
        "# 政策背景",
        design_spec="科技农业风格",
        language="zh",
        canvas_format="ppt169",
        card=briefs[2],
        asset_context=asset_context,
    )

    assert asset_context["image_paths"] == [image_path.resolve()]
    assert "Layout intent: 政策/痛点/需求三栏" in prompt
    assert "Evidence focus: 证明方向正确" in prompt
    assert "Attached material images are available" in prompt
    assert "[[ASSET:asset_001]]" not in prompt


def test_image2_outline_inputs_dedupe_user_requirement_and_use_asset_tokens(tmp_path: Path):
    project_dir = tmp_path / "project"
    asset_dir = project_dir / "sources" / "images" / "assets"
    asset_dir.mkdir(parents=True)
    (asset_dir / "asset_001.png").write_bytes(b"png")
    (project_dir / "sources" / "asset_registry.json").write_text(
        json.dumps(
            {
                "version": 1,
                "assets": [
                    {
                        "asset_id": "asset_001",
                        "asset_type": "policy_source",
                        "filename": "asset_001.png",
                        "path": "images/assets/asset_001.png",
                        "caption": "政策截图",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    repeated = (
        "用户补充说明：\n面向职业院校技能大赛作品汇报，突出项目背景。\n"
        "用户问卷信息：\n- extra_requirements: 面向职业院校技能大赛作品汇报，突出项目背景。\n"
    ) * 6

    compact = _compact_user_requirement_for_image2(repeated)
    inventory = _image2_asset_token_inventory_block(
        project_dir,
        ParsedPaper(title="智农云控温室环境智能监测与调控系统"),
    )

    assert "用户补充说明" not in compact
    assert "用户问卷信息" not in compact
    assert compact.count("面向职业院校技能大赛作品汇报") <= 2
    assert "[[ASSET:asset_001]]" in inventory
    assert "[[FIG:" not in inventory
    assert _image2_asset_tokens_from_inventory(inventory) == {"asset_001"}


def test_image2_outline_segments_cover_requested_page_range():
    segments = _image2_outline_segments(45)

    assert segments[0]["start"] == 1
    assert segments[-1]["end"] == 45
    assert all(int(left["end"]) + 1 == int(right["start"]) for left, right in zip(segments, segments[1:]))
