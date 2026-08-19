#!/usr/bin/env python3
"""
快速渲染截图测试 - 从已有的HTML文件生成截图
"""
import os
import sys
import asyncio

sys.path.insert(0, os.path.expanduser("~/项目/OREP/ai-scoring"))

from app.services.ppt.html_renderer import HTMLRenderer

async def render_existing_html():
    """渲染已有的HTML文件为截图"""
    output_dir = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/ppt_ai_test")
    screenshots_dir = os.path.join(output_dir, "screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    renderer = HTMLRenderer()
    await renderer.init_browser()

    for i in range(1, 6):
        html_file = os.path.join(output_dir, f"page_{i}.html")
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()

            page_data = {
                "html_content": html_content,
                "layout": "ai_generated"
            }

            screenshot_path = await renderer.render_page(
                page_data=page_data,
                theme="deep-blue-tech",
                page_index=i,
                total_pages=5
            )

            if screenshot_path:
                print(f"✅ 第{i}页截图: {screenshot_path}")
            else:
                print(f"❌ 第{i}页截图失败")
        else:
            print(f"⚠️ 第{i}页HTML文件不存在")

    await renderer.close_browser()

if __name__ == '__main__':
    asyncio.run(render_existing_html())
