#!/usr/bin/env python3
"""
测试新 Pipeline HTML生成 - 简化为单页测试
"""
import asyncio
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')


async def test_html_generation():
    """测试 HTML 生成"""
    from app.services.ppt.qwen_client import QwenClient
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 60)
    print("测试 HTML 生成（简化版）")
    print("=" * 60)

    # 创建 Qwen 客户端
    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 单页测试数据
    single_page_content = {
        "page_number": 1,
        "title": "智慧农业物联网大数据平台",
        "subtitle": "田野智联团队",
        "section": "项目介绍",
        "content": {
            "main_text": "本项目旨在通过物联网传感器和AI算法，提高农业生产效率。",
            "key_points": [
                "物联网传感器实时监测",
                "AI算法优化种植方案",
                "产量预测准确率达92%"
            ]
        },
        "chart_data": {
            "type": "bar",
            "title": "产量对比",
            "data": [100, 120, 135, 150]
        }
    }

    # 构建 prompt
    prompt = f"""请根据以下内容生成一个精美的HTML页面：

{json.dumps(single_page_content, ensure_ascii=False, indent=2)}

要求：
1. 使用HTML5 + CSS3
2. 风格：科技感、现代农业主题
3. 包含实际内容，不是占位符
4. 响应式设计
5. 直接输出HTML代码，不需要markdown包装

请生成完整的HTML页面代码："""

    print("\n正在调用 Qwen API 生成 HTML...")
    print(f"输入内容：{json.dumps(single_page_content, ensure_ascii=False, indent=2)[:500]}...")

    try:
        response = await client.chat(prompt, system_prompt="你是一个专业的HTML开发者，生成高质量的HTML页面。", max_tokens=8000)

        print(f"\nAI 返回长度: {len(response)} 字符")

        # 保存HTML
        output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output"
        os.makedirs(output_dir, exist_ok=True)

        # 清理可能的 markdown 包装
        html_content = response
        if "```html" in response:
            start = response.find("```html") + 7
            end = response.find("```", start)
            html_content = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            html_content = response[start:end].strip()

        output_file = os.path.join(output_dir, "test_single_page.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n✅ HTML 已保存到: {output_file}")
        print(f"\n前1000字符预览：")
        print(html_content[:1000])

        return html_content

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    result = asyncio.run(test_html_generation())
    if result:
        print("\n" + "=" * 60)
        print("HTML 生成测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    main()
