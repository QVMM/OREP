#!/usr/bin/env python3
"""
测试 PPT 封面页设计 - 修复字体重叠
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')


async def test_cover_fixed():
    """测试封面页设计 - 修复重叠"""
    from app.services.ppt.qwen_client import QwenClient
    from dotenv import load_dotenv

    load_dotenv()

    print("测试封面页 - 修复字体重叠")
    print("=" * 60)

    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    system_prompt = """你是一个专业的 PPT 视觉设计师，擅长设计精美的封面页。

## PPT 封面页设计规范

### 关键：字体不能重叠！

1. **主标题**：72-80px，font-weight: 800，line-height: 1.3，两行要分开
2. **副标题**：28-32px，与主标题保持足够间距（60-80px）
3. **分隔线**：与下方内容保持40px间距
4. **团队信息**：与分隔线保持50px间距

### 主标题布局（重要）

如果标题太长需要换行，要：
- line-height 至少 1.3（推荐1.4-1.5）
- 或者用两个独立的 div 分别放置两行文字
- 确保两行不会重叠

### 布局参考

```
顶部：赛项标识 --------------------------------- 页码

                  [主标题第一行]
                  [主标题第二行]  ← 足够行高

                  [副标题]     ← 距离主标题60px

                  ─────────

                  [团队名称]  ← 距离分隔线50px
                  [学校/日期]
```

## 输出

直接输出 HTML 代码，1920x1080px。
"""

    cover_data = {
        "page_type": "cover",
        "page_number": 1,
        "total_pages": 12,
        "title": "智慧农业物联网大数据平台",
        "subtitle": "基于物联网与AI的现代农业解决方案",
        "team": "田野智联团队",
        "school": "华东职业技术学院",
        "competition": "2026年职业技能大赛",
        "date": "2026年4月"
    }

    print(f"\n数据：{json.dumps(cover_data, ensure_ascii=False, indent=2)}")

    user_prompt = f"""请设计一个精美的 PPT 封面页（确保字体不重叠）：

{json.dumps(cover_data, ensure_ascii=False, indent=2)}

重要：
1. 主标题 72-80px，line-height: 1.4
2. 两行主标题之间要有足够间距（至少 1.4 倍行高）
3. 副标题距离主标题至少 60px
4. 1920x1080px"""

    try:
        response = await client.chat(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=8000
        )

        print(f"AI 返回: {len(response)} 字符")

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

        output_file = os.path.join(output_dir, "ppt_cover_v3.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ 已保存: {output_file}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    asyncio.run(test_cover_fixed())
    print("\n完成！")


if __name__ == "__main__":
    main()
