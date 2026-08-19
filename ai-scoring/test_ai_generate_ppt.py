#!/usr/bin/env python3
"""
AI驱动PPT生成测试脚本
使用AI生成丰富内容的5页PPT
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.expanduser("~/项目/OREP/ai-scoring"))

from app.services.ppt.content_compiler import ContentCompiler
from app.services.ppt.html_generator import HTMLGenerator
from app.services.ppt.design_spec import get_theme_by_industry
from app.services.ppt.ruipu_token import get_token_manager
from app.services.ppt.qwen_client import QwenClient
from app.config import settings

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def load_questionnaire():
    """加载问卷数据"""
    questionnaire_file = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/questionnaire_sample.json")
    if os.path.exists(questionnaire_file):
        with open(questionnaire_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logger.error(f"问卷文件不存在: {questionnaire_file}")
        return None


async def generate_with_ai():
    """使用AI生成5页PPT"""
    print("\n" + "="*60)
    print("🚀 AI驱动PPT生成测试")
    print("="*60)

    # 1. 加载问卷数据
    print("\n1. 加载问卷数据...")
    questionnaire = await load_questionnaire()
    if not questionnaire:
        print("❌ 无法加载问卷数据")
        return

    print(f"   问卷字段: {len(questionnaire)} 个")
    print(f"   项目名称: {questionnaire.get('project_name', '未知')}")
    print(f"   行业: {questionnaire.get('industry', '未知')}")

    # 2. 创建Qwen客户端
    print("\n2. 创建Qwen客户端...")
    qwen_client = QwenClient(api_key=settings.DASHSCOPE_API_KEY)
    print("   ✅ Qwen客户端已创建")

    # 3. 创建内容编排器
    print("\n3. 创建内容编排器...")
    compiler = ContentCompiler(qwen_client)
    print("   ✅ 内容编排器已创建")

    # 4. 生成设计稿（使用AI）
    print("\n4. 使用AI生成设计稿...")
    print("   ⏳ 这可能需要几分钟时间，请耐心等待...")

    industry = questionnaire.get('industry', 'ai_iot')
    design_draft, missing_content = await compiler.compile(questionnaire, industry)

    print(f"   ✅ 设计稿生成完成")
    print(f"   总页数: {len(design_draft)} 页")
    print(f"   缺失内容: {len(missing_content)} 项")

    # 5. 取前5页
    print("\n5. 取前5页进行测试...")
    first_5_pages = design_draft[:5]
    for i, page in enumerate(first_5_pages):
        section = page.get('section', '未知')
        print(f"   第{i+1}页: {section}")

    # 6. 保存设计稿
    output_dir = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/ppt_ai_test")
    os.makedirs(output_dir, exist_ok=True)

    draft_file = os.path.join(output_dir, "design_draft_5pages.json")
    with open(draft_file, 'w', encoding='utf-8') as f:
        json.dump(first_5_pages, f, ensure_ascii=False, indent=2)
    print(f"\n6. 设计稿已保存: {draft_file}")

    # 7. 获取主题
    print("\n7. 获取主题配置...")
    theme = get_theme_by_industry(industry)
    theme_name = theme.get('name', 'deep-blue-tech')
    print(f"   主题: {theme_name}")

    # 8. 创建HTML生成器
    print("\n8. 创建HTML生成器...")
    html_generator = HTMLGenerator(qwen_client=qwen_client)
    print("   ✅ HTML生成器已创建")

    # 9. 生成HTML页面（使用AI）
    print("\n9. 使用AI生成HTML页面...")
    print("   ⏳ 这可能需要几分钟时间，请耐心等待...")

    html_pages = await html_generator.generate_html_pages(
        first_5_pages, theme, enable_review=True
    )

    print(f"   ✅ HTML生成完成")
    print(f"   生成页面数: {len(html_pages)}")

    # 10. 保存HTML文件
    print("\n10. 保存HTML文件...")
    html_files = []
    for i, html in enumerate(html_pages):
        page_index = i + 1
        html_file = os.path.join(output_dir, f"page_{page_index}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        html_files.append(html_file)
        print(f"    第{page_index}页: {html_file}")

    # 11. 验证Token合规
    print("\n11. 验证Token合规...")
    token_manager = get_token_manager()
    scores = []

    for i, html in enumerate(html_pages):
        page_index = i + 1
        if html and len(html) > 500:
            token_result = token_manager.validate_html_compliance(html, theme_name)
            score = token_result.get("percentage", 0)
            scores.append(score)
            status = "✅" if score >= 90 else "⚠️"
            print(f"    第{page_index}页: {score}% {status}")

    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\n    平均Token分数: {avg_score:.1f}%")
        print(f"    达标页面: {sum(1 for s in scores if s >= 90)}/{len(scores)}")

    # 12. 生成截图
    print("\n12. 生成截图...")
    try:
        from app.services.ppt.html_renderer import HTMLRenderer
        renderer = HTMLRenderer()

        for i, html in enumerate(html_pages):
            page_index = i + 1
            page_data = {
                "html_content": html,
                "layout": "ai_generated"
            }

            screenshot_path = await renderer.render_page(
                page_data=page_data,
                theme=theme_name,
                page_index=page_index,
                total_pages=len(html_pages)
            )

            if screenshot_path:
                print(f"    ✅ 第{page_index}页截图: {screenshot_path}")
    except Exception as e:
        print(f"    ⚠️ 截图生成失败: {e}")

    # 13. 组装PPTX
    print("\n13. 组装PPTX...")
    try:
        from app.services.ppt.pptx_renderer_html import PPTXRendererHTML
        renderer = PPTXRendererHTML()

        outline = {
            "pages": [
                {
                    "page_index": i + 1,
                    "section": first_5_pages[i].get("section", f"第{i+1}页"),
                    "layout": "full_text_page",
                    "html_content": html_pages[i]
                }
                for i in range(len(html_pages))
            ]
        }

        pptx_path = os.path.join(output_dir, "ai_generated_5pages.pptx")
        await renderer.render(outline, theme_name, pptx_path)
        print(f"    ✅ PPTX已生成: {pptx_path}")
    except Exception as e:
        print(f"    ⚠️ PPTX生成失败: {e}")

    print("\n" + "="*60)
    print("✅ AI驱动PPT生成完成！")
    print(f"输出目录: {output_dir}")
    print("="*60)

    return html_files


async def main():
    """主函数"""
    print("╔" + "═"*58 + "╗")
    print("║   AI驱动PPT生成测试                                      ║")
    print("║   使用AI生成丰富内容的5页PPT                             ║")
    print("╚" + "═"*58 + "╝")

    await generate_with_ai()


if __name__ == '__main__':
    asyncio.run(main())
