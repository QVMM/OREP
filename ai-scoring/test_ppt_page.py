#!/usr/bin/env python3
"""
测试新 Pipeline HTML生成 - 正确的PPT页面格式
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
    print("测试 PPT HTML 生成（正确格式）")
    print("=" * 60)

    # 创建 Qwen 客户端
    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 正确的 PPT 页面数据格式
    page_content = {
        "page_number": 1,
        "phase": "开场路演",
        "slide_role": "hook",
        "title": "每8秒，一次停机",
        "ppt_text": "8秒｜一次停机｜损失200万+",
        "chart": {"needed": False},
        "image": {"needed": False}
    }

    # 第二个页面 - 带图表
    page2_content = {
        "page_number": 4,
        "phase": "问题与市场",
        "slide_role": "industry_overview",
        "title": "工业设备维护：3200亿市场",
        "ppt_text": "市场规模3200亿元（2024）｜年增长率25%｜政策加持",
        "chart": {
            "needed": True,
            "type": "bar",
            "definition": {
                "type": "bar",
                "title": "工业设备维护市场规模",
                "x_axis": {"label": "年份", "values": [2020, 2021, 2022, 2023, 2024]},
                "y_axis": {"label": "市场规模(亿元)", "range": [0, 4000], "unit": "亿元"},
                "series": [{"name": "市场规模", "values": [2100, 2500, 2800, 3000, 3200]}],
                "source_note": "中国工业互联网研究院（待核实）"
            }
        },
        "image": {"needed": False}
    }

    # 构建 prompt - 明确告知只生成 PPT 内容，不要讲稿
    system_prompt = """你是一个专业的 PPT 视觉设计师。

## 重要约束

1. **只生成 PPT 页面的 HTML，不要包含任何讲稿/演讲稿内容**
2. **使用 1920x1080 尺寸（16:9比例）**
3. **背景色：#0F0F23（深色），文字色：白色**
4. **字体：PingFang SC, Microsoft YaHei**
5. **图表必须对齐，使用标准数据表格规范**：
   - 柱状图/折线图的坐标轴刻度要对齐
   - 数据标签要紧跟数据点
   - 图例要清晰
6. **输出完整 HTML，包含内联 CSS**
7. **不要使用 markdown 包装，直接输出 HTML 代码**

## 允许的动画
- fade_in：淡入，600ms，ease-out
- slide_up：上滑进入，500ms

## 禁止的动画
- 旋转、弹跳、闪烁、百叶窗、棋盘式

## 页面角色与布局
- hook/closing: 全幅居中，大标题
- industry_overview: 左文右图（45%:55%）
- tech_architecture: 全幅架构图
- comparison_table: 对比表格"""

    user_prompt = f"""请生成以下 PPT 页面的 HTML：

页面 {page_content['page_number']}
角色：{page_content['slide_role']}
标题：{page_content['title']}
内容：{page_content['ppt_text']}

要求：
1. 只包含页面内容，不要讲稿
2. 图表要对齐
3. 风格统一"""

    print("\n正在调用 Qwen API 生成 HTML...")
    print(f"页面内容：{json.dumps(page_content, ensure_ascii=False, indent=2)[:500]}...")

    try:
        response = await client.chat(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=8000
        )

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

        output_file = os.path.join(output_dir, "test_ppt_page1.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n✅ Page 1 HTML 已保存到: {output_file}")
        print(f"\n前1000字符预览：")
        print(html_content[:1000])

        # 测试第二个页面
        print("\n" + "=" * 60)
        print("测试 Page 2（带图表）...")
        print("=" * 60)

        user_prompt2 = f"""请生成以下 PPT 页面的 HTML：

页面 {page2_content['page_number']}
角色：{page2_content['slide_role']}
标题：{page2_content['title']}
内容：{page2_content['ppt_text']}
图表类型：{page2_content['chart']['type']}
图表数据：{json.dumps(page2_content['chart']['definition'], ensure_ascii=False)}

要求：
1. 只包含页面内容，不要讲稿
2. 图表要对齐，符合数据可视化规范
3. 风格统一"""

        response2 = await client.chat(
            user_prompt2,
            system_prompt=system_prompt,
            max_tokens=8000
        )

        print(f"\nAI 返回长度: {len(response2)} 字符")

        # 清理并保存
        html_content2 = response2
        if "```html" in response2:
            start = response2.find("```html") + 7
            end = response2.find("```", start)
            html_content2 = response2[start:end].strip()
        elif "```" in response2:
            start = response2.find("```") + 3
            end = response2.find("```", start)
            html_content2 = response2[start:end].strip()

        output_file2 = os.path.join(output_dir, "test_ppt_page2.html")
        with open(output_file2, "w", encoding="utf-8") as f:
            f.write(html_content2)

        print(f"\n✅ Page 2 HTML 已保存到: {output_file2}")
        print(f"\n前1000字符预览：")
        print(html_content2[:1000])

        return [html_content, html_content2]

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
        print("\n生成的文件：")
        print("1. /Users/liuyixing/项目/OREP/ai-scoring/output/test_ppt_page1.html")
        print("2. /Users/liuyixing/项目/OREP/ai-scoring/output/test_ppt_page2.html")


if __name__ == "__main__":
    main()
