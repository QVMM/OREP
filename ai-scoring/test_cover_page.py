#!/usr/bin/env python3
"""
测试 PPT 封面页设计
首页需要更好的视觉效果
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')


async def test_cover_design():
    """测试封面页设计"""
    from app.services.ppt.qwen_client import QwenClient
    from dotenv import load_dotenv

    load_dotenv()

    print("=" * 60)
    print("测试 PPT 封面页设计")
    print("=" * 60)

    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # PPT 封面页系统提示词
    system_prompt = """你是一个专业的 PPT 视觉设计师，擅长设计精美的封面页。

## PPT 封面页设计规范

### 布局结构（推荐）

```
+-------------------------------------------------------+
|  [章节/赛项标识]                          [页码] 01    |
|                                                       |
|                                                       |
|                    [主标题]                           |
|                  大气、有冲击力                        |
|                                                       |
|                    [副标题]                           |
|                  说明项目方向                           |
|                                                       |
|                  [团队名称]                          |
|                  [学校/日期]                         |
|                                                       |
+-------------------------------------------------------+
```

### 设计要点

1. **主标题**：最大号字体，72-96px，居中或偏左
2. **副标题**：说明项目方向，28-36px
3. **团队信息**：学校名称 + 日期，小号字体
4. **装饰元素**：
   - 底部或侧边的渐变色块/光效
   - 科技感的几何装饰
   - 但不能喧宾夺主

### 背景设计

- 深色背景 (#0F0F23 或更深)
- 可以有渐变或光晕效果
- 添加科技感网格或线条装饰
- 但要保持简洁大气

### 风格参考

封面要有"冲击力"和"专业感"，让人眼前一亮但不过于花哨。

## 禁止

- ❌ 过多颜色
- ❌ 复杂图案
- ❌ 卡通风格
- ❌ 滚动条

## 输出

直接输出 HTML 代码，1920x1080px，每个元素都要有精确定位。
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

    print("\n正在生成封面页...")
    print(f"数据：{json.dumps(cover_data, ensure_ascii=False, indent=2)}")

    user_prompt = f"""请设计一个精美的 PPT 封面页：

{json.dumps(cover_data, ensure_ascii=False, indent=2)}

要求：
1. 大气、有冲击力
2. 专业、科技感
3. 突出项目名称
4. 团队和学校信息清晰
5. 1920x1080px"""

    try:
        response = await client.chat(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=8000
        )

        print(f"\nAI 返回长度: {len(response)} 字符")

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

        output_file = os.path.join(output_dir, "ppt_cover_v2.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n✅ 封面页已保存: {output_file}")
        print(f"\n预览：\n{html_content[:800]}")

        return html_content

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    asyncio.run(test_cover_design())
    print("\n封面页设计测试完成！")


if __name__ == "__main__":
    main()
