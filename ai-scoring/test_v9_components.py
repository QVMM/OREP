"""
V9 组件化设计系统 - 测试脚本
验证组件渲染和组装引擎
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ppt.components import get_component, get_all_component_ids, ThemeContext
from app.services.ppt.layouts import get_layout, get_all_layout_ids
from app.services.ppt.assembly_engine import AssemblyEngine, assemble_html
from app.services.ppt.content_compiler_v2 import ContentCompilerV2


def test_theme_context():
    """测试主题上下文"""
    print("=== 测试主题上下文 ===")
    theme = ThemeContext("deep-blue-tech")
    print(f"主题: {theme.theme_name}")
    print(f"背景色: {theme.bg_primary}")
    print(f"强调色: {theme.accent}")
    print(f"发光色: {theme.glow_color}")
    print("✓ 主题上下文测试通过\n")


def test_components():
    """测试组件渲染"""
    print("=== 测试组件渲染 ===")
    theme = ThemeContext("deep-blue-tech")
    component_ids = get_all_component_ids()
    print(f"可用组件: {len(component_ids)}个")
    print(f"组件列表: {', '.join(component_ids)}")

    # 测试封面组件
    cover = get_component("cover")
    html = cover.render({
        "title": "测试项目",
        "subtitle": "这是测试副标题",
        "team": "测试团队"
    }, theme, 1, 10)
    assert "<!DOCTYPE html>" in html
    assert "测试项目" in html
    print("✓ 封面组件测试通过")

    # 测试目录组件
    toc = get_component("toc")
    html = toc.render({
        "sections": ["章节1", "章节2", "章节3"]
    }, theme, 2, 10)
    assert "目录" in html
    assert "章节1" in html
    print("✓ 目录组件测试通过")

    # 测试三列卡片组件
    cards = get_component("three_column_cards")
    html = cards.render({
        "title": "特性展示",
        "cards": [
            {"title": "特性1", "content": "描述1"},
            {"title": "特性2", "content": "描述2"},
            {"title": "特性3", "content": "描述3"}
        ]
    }, theme, 3, 10)
    assert "特性展示" in html
    assert "特性1" in html
    print("✓ 三列卡片组件测试通过")

    # 测试结束组件
    ending = get_component("ending")
    html = ending.render({
        "title": "感谢聆听"
    }, theme, 10, 10)
    assert "感谢聆听" in html
    print("✓ 结束组件测试通过")

    print()


def test_layouts():
    """测试布局"""
    print("=== 测试布局 ===")
    theme = ThemeContext("deep-blue-tech")
    layout_ids = get_all_layout_ids()
    print(f"可用布局: {len(layout_ids)}个")
    print(f"布局列表: {', '.join(layout_ids)}")
    print("✓ 布局注册测试通过\n")


def test_assembly_engine():
    """测试组装引擎"""
    print("=== 测试组装引擎 ===")

    # 测试内容JSON
    content_json = [
        {
            "layout": "cover_layout",
            "title": "智能PPT生成系统",
            "subtitle": "AI驱动的演示文稿自动化方案",
            "team": "OREP团队"
        },
        {
            "layout": "toc_layout",
            "sections": ["项目背景", "问题分析", "解决方案", "技术实现", "团队介绍"]
        },
        {
            "layout": "section_layout",
            "title": "项目背景"
        },
        {
            "layout": "content_layout",
            "title": "市场痛点",
            "sections": [
                {"name": "痛点1", "items": ["制作耗时", "设计质量不稳定"]},
                {"name": "痛点2", "items": ["内容组织困难", "缺乏专业模板"]}
            ]
        },
        {
            "layout": "two_column_layout",
            "title": "痛点 vs 方案",
            "left": {"title": "痛点", "content": "传统PPT制作效率低下"},
            "right": {"title": "方案", "content": "AI自动化生成"}
        },
        {
            "layout": "data_layout",
            "title": "关键指标",
            "metrics": [
                {"name": "效率提升", "value": "10x"},
                {"name": "成本降低", "value": "80%"},
                {"name": "质量评分", "value": "95分"},
                {"name": "用户满意度", "value": "98%"}
            ]
        },
        {
            "layout": "team_layout",
            "title": "核心团队",
            "members": [
                {"name": "张三", "role": "CEO", "description": "10年行业经验"},
                {"name": "李四", "role": "CTO", "description": "AI专家"}
            ]
        },
        {
            "layout": "ending_layout",
            "title": "感谢聆听"
        }
    ]

    # 组装HTML
    engine = AssemblyEngine("deep-blue-tech")
    html_pages = engine.assemble_pages(content_json)

    assert len(html_pages) == len(content_json)
    print(f"生成页面数: {len(html_pages)}")

    # 验证每个页面
    for i, html in enumerate(html_pages):
        assert "<!DOCTYPE html>" in html, f"Page {i+1} missing DOCTYPE"
        assert "1280" in html, f"Page {i+1} missing viewport width"
        print(f"  ✓ 第{i+1}页渲染成功")

    print("✓ 组装引擎测试通过\n")


def test_theme_variants():
    """测试不同主题"""
    print("=== 测试主题变体 ===")
    themes = ["deep-blue-tech", "black-gold", "fresh-green", "sky-blue-tech"]

    for theme_name in themes:
        theme = ThemeContext(theme_name)
        cover = get_component("cover")
        html = cover.render({
            "title": f"主题测试 - {theme_name}",
            "team": "测试团队"
        }, theme, 1, 1)
        assert theme.bg_primary in html or "background" in html
        print(f"  ✓ {theme_name} 主题渲染成功")

    print()


def test_content_compiler():
    """测试内容编译器"""
    print("=== 测试内容编译器 ===")

    # 测试数据
    questionnaire_data = {
        "project_name": "智能PPT生成系统",
        "industry": "AI/科技",
        "description": "基于AI的PPT自动生成方案",
        "team": [
            {"name": "张三", "role": "CEO"},
            {"name": "李四", "role": "CTO"}
        ],
        "solution": "使用AI自动生成高质量PPT"
    }

    compiler = ContentCompilerV2()
    content_json, missing = compiler.compile(questionnaire_data, "科技", 10)

    assert len(content_json) > 0
    assert content_json[0].get("layout") == "cover_layout"
    assert content_json[-1].get("layout") == "ending_layout"
    print(f"生成页面数: {len(content_json)}")
    print(f"缺失内容: {missing}")
    print("✓ 内容编译器测试通过\n")


if __name__ == "__main__":
    print("V9 组件化设计系统测试\n")
    print("=" * 50)

    try:
        test_theme_context()
        test_components()
        test_layouts()
        test_assembly_engine()
        test_theme_variants()
        test_content_compiler()

        print("=" * 50)
        print("所有测试通过! ✓")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
