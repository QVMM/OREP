#!/usr/bin/env python3
"""
测试 PPT 风格的 HTML 生成
确保生成的是幻灯片，而不是网页
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')


async def test_ppt_style_html():
    """测试 PPT 风格的 HTML 生成"""
    from app.services.ppt.qwen_client import QwenClient
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 60)
    print("测试 PPT 风格 HTML 生成")
    print("=" * 60)

    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # PPT 风格系统提示词
    system_prompt = """你是一个专业的 PPT 视觉设计师，擅长将路演内容转化为高质量 HTML 幻灯片。

## 核心认知：这是 PPT，不是网页！

**PPT 幻灯片的特征**：
1. **固定尺寸**：16:9 (1920x1080px)
2. **每页独立**：不是滚动页面，每页就是一个完整画面
3. **标题栏**：每页必须有标题（可能还有副标题）
4. **页码**：右下角或右下角显示 "01 / 12" 这样的页码
5. **统一的视觉风格**：所有页面风格一致，像同一个 PPT 文件

## 页面类型规范

| 页面类型 | 特征 | 示例 |
|---------|------|------|
| 封面页 | 大标题居中 + 副标题 + 团队/日期 | 首页 |
| 目录页 | "目录" 大标题 + 章节列表 | 目录 |
| 章节页 | 章节号 + 章节标题（大字） | 章节过渡 |
| 内容页 | 标题 + 副标题 + 正文/图表 | 主要内容 |
| 结束页 | "谢谢" 或 "Q&A" | 最后一页 |

## 内容页标准结构

```
+------------------------------------------+
|  [页码]                        [章节名]  |
|                                    01 / 12 |
|  标题                                        |
|  副标题                                      |
|                                            |
|  内容区域                                    |
|                                            |
|                                            |
+------------------------------------------+
```

## 统一视觉规范

- **背景**：深色渐变 (#0F0F23 → #1A1A3E)
- **标题**：白色，56-72px，加粗
- **副标题**：灰色，28-36px
- **正文**：白色/浅灰，20-24px
- **页码**：右下角，白色半透明
- **字体**：PingFang SC, Microsoft YaHei

## 图表规范（数据展示页）

- 柱状图/折线图必须坐标轴对齐
- Y轴刻度清晰标注
- 数据标签紧跟数据点
- 图例清晰

## 禁止

- ❌ 滚动条
- ❌ 导航栏/菜单
- ❌ 弹出窗口
- ❌ 复杂动画（只允许 fade_in）

## 输出格式

直接输出 HTML 代码，不要 markdown 包装，每个页面是独立的 1920x1080 幻灯片。
"""

    # 测试封面页
    cover_page = {
        "page_type": "cover",
        "page_number": 1,
        "total_pages": 12,
        "title": "智慧农业物联网大数据平台",
        "subtitle": "田野智联团队",
        "team": "华东职业技术学院",
        "date": "2026年"
    }

    # 测试目录页
    toc_page = {
        "page_type": "toc",
        "page_number": 2,
        "total_pages": 12,
        "title": "目录",
        "chapters": [
            {"num": "01", "name": "项目背景与意义"},
            {"num": "02", "name": "市场调研与分析"},
            {"num": "03", "name": "技术方案与实现"},
            {"num": "04", "name": "成果展示与展望"}
        ]
    }

    # 测试章节页
    section_page = {
        "page_type": "section",
        "page_number": 3,
        "total_pages": 12,
        "section_num": "01",
        "title": "项目背景与意义",
        "subtitle": "为什么做这个项目"
    }

    # 测试内容页
    content_page = {
        "page_type": "content",
        "page_number": 4,
        "total_pages": 12,
        "title": "行业背景",
        "subtitle": "智慧农业发展态势",
        "content": [
            "市场规模持续增长，2024年达到约6000亿元",
            "年增长率超过15%",
            "国家政策大力支持"
        ]
    }

    pages = [cover_page, toc_page, section_page, content_page]

    for i, page in enumerate(pages):
        print(f"\n{'='*60}")
        print(f"生成第 {i+1} 页：{page['page_type']}")
        print(f"{'='*60}")

        user_prompt = f"""请生成以下 PPT 页面的 HTML（1920x1080，16:9）：

页面类型：{page['page_type']}
页码：{page['page_number']} / {page['total_pages']}

{json.dumps(page, ensure_ascii=False, indent=2)}

要求：
1. 这是 PPT 幻灯片，不是网页
2. 每页必须有页码（右下角）
3. 风格统一
4. 直接输出 HTML 代码"""

        try:
            response = await client.chat(
                user_prompt,
                system_prompt=system_prompt,
                max_tokens=8000
            )

            print(f"AI 返回长度: {len(response)} 字符")

            # 保存
            output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output"
            os.makedirs(output_dir, exist_ok=True)

            html_content = response
            if "```html" in response:
                start = response.find("```html") + 7
                end = response.find("```", start)
                html_content = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                html_content = response[start:end].strip()

            output_file = os.path.join(output_dir, f"ppt_page_{page['page_number']}_{page['page_type']}.html")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            print(f"✅ 已保存: {output_file}")
            print(f"\n预览前500字符：\n{html_content[:500]}")

        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    asyncio.run(test_ppt_style_html())
    print("\n" + "=" * 60)
    print("PPT 风格 HTML 生成测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
