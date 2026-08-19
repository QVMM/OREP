#!/usr/bin/env python3
"""
PPT生成测试脚本
生成5页PPT并验证Token合规
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.expanduser("~/项目/OREP/ai-scoring"))

from app.services.ppt.design_spec import get_theme_by_industry
from app.services.ppt.ruipu_token import get_token_manager
from app.services.ppt.qwen_client import QwenClient
from app.services.ppt.html_generator import HTMLGenerator
from app.config import settings

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# 示例问卷数据（智慧城市项目）
SAMPLE_QUESTIONNAIRE = {
    "project_name": "智慧城市AI数据平台",
    "team_name": "智慧城市创新组",
    "industry": "ai_iot",
    "background": {
        "strategic_alignment": "响应《十四五国家信息化规划》，推动城市数字化转型",
        "industry_trend": "智慧城市市场规模预计2025年达到2.5万亿元",
        "social_need": "城市管理效率低，数据孤岛严重，决策缺乏数据支撑"
    },
    "research": {
        "target_users": "城市管理者、市政部门、市民",
        "market_research": "调研20个城市，80%存在数据孤岛问题",
        "user_pain_points": "数据分散、响应慢、决策难"
    },
    "solution": {
        "solution_overview": "基于AI的城市数据治理平台",
        "data_collection": "IoT传感器网络实时采集",
        "data_analysis": "深度学习智能分析"
    },
    "implementation": {
        "tech_stack": "Python + TensorFlow + Kafka + PostgreSQL",
        "core_functions": "数据采集、清洗、分析、可视化",
        "innovation": "联邦学习保护数据隐私"
    },
    "value": {
        "social_value": "提升城市管理效率30%",
        "economic_value": "降低运营成本20%",
        "promotion_plan": "3年内推广至50个城市"
    }
}


# 5页设计稿
DESIGN_DRAFT_5_PAGES = [
    {
        "page_index": 1,
        "section": "封面",
        "design": {
            "title": {"text": "智慧城市AI数据平台", "font_size": "52px", "color": "#FFFFFF"},
            "subtitle": {"text": "基于人工智能的城市数据治理解决方案", "font_size": "22px"},
            "layout": "cover",
            "elements": [
                {"type": "text", "content": "团队：智慧城市创新组"},
                {"type": "text", "content": "项目类型：AI + IoT数据治理"}
            ]
        }
    },
    {
        "page_index": 2,
        "section": "项目背景",
        "design": {
            "title": {"text": "项目背景与意义", "font_size": "40px", "color": "#FFFFFF"},
            "layout": "two_column",
            "elements": [
                {"type": "text", "content": "国家战略需求：《十四五规划》明确提出数字化转型目标，智慧城市是重点方向"},
                {"type": "text", "content": "行业趋势：智慧城市市场规模预计2025年达到2.5万亿元，年增长率15%"},
                {"type": "text", "content": "社会需求：城市管理效率低，数据孤岛严重，决策缺乏数据支撑"}
            ]
        }
    },
    {
        "page_index": 3,
        "section": "技术方案",
        "design": {
            "title": {"text": "核心技术方案", "font_size": "40px", "color": "#FFFFFF"},
            "layout": "cards",
            "elements": [
                {"type": "card", "title": "数据采集层", "content": "IoT传感器网络，实时采集城市运行数据，支持10万+设备接入"},
                {"type": "card", "title": "数据处理层", "content": "分布式计算框架，支持PB级数据处理，日处理能力1亿条"},
                {"type": "card", "title": "AI分析层", "content": "深度学习模型，智能识别城市问题，准确率95%以上"}
            ]
        }
    },
    {
        "page_index": 4,
        "section": "创新点",
        "design": {
            "title": {"text": "项目创新性", "font_size": "40px", "color": "#FFFFFF"},
            "layout": "content",
            "elements": [
                {"type": "text", "content": "技术创新：首次将联邦学习应用于城市数据治理，保护数据隐私"},
                {"type": "text", "content": "模式创新：构建数据共享与隐私保护的平衡机制"},
                {"type": "text", "content": "应用创新：实现城市治理的智能化决策支持"}
            ]
        }
    },
    {
        "page_index": 5,
        "section": "结尾",
        "design": {
            "title": {"text": "感谢聆听", "font_size": "64px", "color": "#FFFFFF"},
            "layout": "ending",
            "elements": []
        }
    }
]


async def generate_ppt():
    """生成5页PPT"""
    print("\n" + "="*60)
    print("🚀 开始生成5页PPT")
    print("="*60)

    # 1. 获取主题
    theme = get_theme_by_industry("ai_iot")
    theme_name = theme.get('name', 'deep-blue-tech')
    print(f"\n1. 使用主题: {theme_name}")

    # 2. 创建Qwen客户端
    qwen_client = QwenClient(api_key=settings.DASHSCOPE_API_KEY)
    print(f"2. Qwen客户端已创建")

    # 3. 创建HTML生成器
    html_generator = HTMLGenerator(qwen_client=qwen_client)
    print(f"3. HTML生成器已创建")

    # 4. 生成HTML页面
    print(f"\n4. 开始生成5页HTML...")
    html_pages = []

    for i, page_design in enumerate(DESIGN_DRAFT_5_PAGES):
        page_index = i + 1
        section = page_design.get('section', '')
        print(f"   生成第{page_index}页: {section}")

        # 生成HTML（不使用AI，直接使用模板）
        html = html_generator._generate_page_from_design(
            page_design, theme, page_index, len(DESIGN_DRAFT_5_PAGES)
        )

        if html and len(html) > 500:
            html_pages.append(html)
            print(f"   ✅ 第{page_index}页生成成功，长度: {len(html)}")
        else:
            print(f"   ❌ 第{page_index}页生成失败")
            html_pages.append("")

    # 5. 保存HTML文件
    output_dir = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/ppt_test")
    os.makedirs(output_dir, exist_ok=True)

    html_files = []
    for i, html in enumerate(html_pages):
        page_index = i + 1
        html_file = os.path.join(output_dir, f"page_{page_index}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        html_files.append(html_file)
        print(f"5. 第{page_index}页HTML已保存: {html_file}")

    # 6. 验证Token合规
    print(f"\n6. 验证Token合规...")
    token_manager = get_token_manager()
    scores = []

    for i, html in enumerate(html_pages):
        page_index = i + 1
        if html:
            token_result = token_manager.validate_html_compliance(html, theme_name)
            score = token_result.get("percentage", 0)
            scores.append(score)
            print(f"   第{page_index}页: {score}%")

    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\n   平均Token分数: {avg_score:.1f}%")
        print(f"   达标页面: {sum(1 for s in scores if s >= 90)}/{len(scores)}")

    # 7. 生成截图（如果Playwright可用）
    print(f"\n7. 尝试生成截图...")
    try:
        from app.services.ppt.html_renderer import HTMLRenderer
        renderer = HTMLRenderer()

        for i, html_file in enumerate(html_files):
            page_index = i + 1
            page_data = {
                "html_content": html_pages[i],
                "layout": "ai_generated"
            }

            screenshot_path = await renderer.render_page(
                page_data=page_data,
                theme=theme_name,
                page_index=page_index,
                total_pages=len(html_pages)
            )

            if screenshot_path:
                print(f"   ✅ 第{page_index}页截图: {screenshot_path}")
            else:
                print(f"   ⚠️ 第{page_index}页截图失败")
    except Exception as e:
        print(f"   ⚠️ 截图生成失败: {e}")
        print(f"   提示: 可以直接打开HTML文件查看效果")

    # 8. 组装PPTX
    print(f"\n8. 尝试组装PPTX...")
    try:
        from app.services.ppt.pptx_renderer_html import PPTXRendererHTML
        renderer = PPTXRendererHTML()

        outline = {
            "pages": [
                {
                    "page_index": i + 1,
                    "section": DESIGN_DRAFT_5_PAGES[i].get("section", f"第{i+1}页"),
                    "layout": "full_text_page",
                    "html_content": html_pages[i]
                }
                for i in range(len(html_pages))
            ]
        }

        pptx_path = os.path.join(output_dir, "test_5pages.pptx")
        await renderer.render(outline, theme_name, pptx_path)
        print(f"   ✅ PPTX已生成: {pptx_path}")
    except Exception as e:
        print(f"   ⚠️ PPTX生成失败: {e}")
        print(f"   提示: 可以直接打开HTML文件查看效果")

    print(f"\n" + "="*60)
    print(f"✅ 生成完成！")
    print(f"输出目录: {output_dir}")
    print(f"HTML文件: {', '.join(html_files)}")
    print(f"="*60)

    return html_files


async def main():
    """主函数"""
    print("╔" + "═"*58 + "╗")
    print("║   PPT生成测试                                            ║")
    print("║   生成5页PPT并验证Token合规                              ║")
    print("╚" + "═"*58 + "╝")

    await generate_ppt()


if __name__ == '__main__':
    asyncio.run(main())
