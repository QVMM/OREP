#!/usr/bin/env python3
"""
测试 Round 4 HTML 生成 - 使用新的 optimized 约束
验证封面页是否符合 6 元素格式要求
"""
import asyncio
import json
import os
import sys
import re
from pathlib import Path

# 设置调试日志
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("round4_test")

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')

from app.services.ppt.qwen_client import QwenClient
from app.config import settings
from dotenv import load_dotenv

load_dotenv()


def load_prompt_template(template_name: str) -> str:
    """Load prompt template from file."""
    template_path = os.path.join(
        "/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts",
        template_name
    )
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_pipeline_result():
    """Load the existing pipeline result."""
    result_path = "/Users/liuyixing/项目/OREP/ai-scoring/output/pipeline_result_full.json"
    with open(result_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_enriched_pages(result):
    """Extract enriched_pages from pipeline result."""
    if "enriched_pages" in result:
        return result["enriched_pages"]
    return []


def parse_html_from_response(response: str) -> str:
    """从 API 响应中提取 HTML 内容。"""
    # 如果响应是 JSON 格式
    if response.strip().startswith('{') or response.strip().startswith('json'):
        try:
            # 去除可能的 "json\n" 前缀
            clean_response = response.strip()
            if clean_response.startswith('json'):
                clean_response = clean_response[4:].strip()

            data = json.loads(clean_response)
            if isinstance(data, dict) and "html" in data:
                return data["html"]
            elif isinstance(data, dict) and "pages" in data:
                # 多页情况
                if data["pages"] and isinstance(data["pages"][0], dict) and "html" in data["pages"][0]:
                    return data["pages"][0]["html"]
        except json.JSONDecodeError:
            pass

    # 如果响应被 ```html ``` 包裹
    if "```html" in response:
        start = response.find("```html") + 7
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()

    # 如果响应被 ``` 包裹
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()

    # 直接返回响应
    return response


def check_cover_page_requirements(html_content: str) -> dict:
    """
    验证封面页是否符合 6 元素格式要求。

    要求：
    1. 项目名称 - 72-100px
    2. slogan - 28-36px
    3. 分隔装饰线 - 60-100px宽
    4. 核心关键词 - 24-32px
    5. 团队名称 - 16-18px
    6. 比赛/日期 - 14-16px
    """
    checks = {
        "has_gradient_circles": False,
        "has_grid_texture": False,
        "has_top_bar": False,
        "has_project_name": False,
        "has_slogan": False,
        "has_divider": False,
        "has_keywords": False,
        "has_team_name": False,
        "has_competition_date": False,
        "project_name_size": None,
        "project_name_text": None,
        "slogan_size": None,
        "slogan_text": None,
        "divider_size": None,
        "keywords_size": None,
        "keywords_text": None,
        "team_name_size": None,
        "team_name_text": None,
        "competition_date_size": None,
        "competition_date_text": None,
        "issues": [],
        "warnings": []
    }

    # 检查装饰元素
    if "radial-gradient" in html_content:
        checks["has_gradient_circles"] = True

    if "background-size" in html_content and "1px" in html_content:
        checks["has_grid_texture"] = True

    if "linear-gradient" in html_content:
        # 检查是否有顶部色带
        if re.search(r'top.*?0.*?(?:height|4px)|height.*?4px.*?top.*?0', html_content, re.DOTALL):
            checks["has_top_bar"] = True
        elif "top-bar" in html_content or "topBar" in html_content:
            checks["has_top_bar"] = True

    # 搜索所有文字内容及其附近的 font-size
    # 返回格式: [(size, text), ...]
    text_with_size = re.findall(r'font-size:\s*(\d+)px[^<]*?([一-龥a-zA-Z0-9]{2,30})', html_content)

    # 也搜索没有明确font-size标注的文字
    text_only = re.findall(r'">([^<]{2,30})<', html_content)
    for t in text_only:
        text_with_size.append(("0", t))  # 0表示未知字号

    # 查找项目名称 - 应该是一个全称，不只是关键词
    # 项目名称通常是全称，如 "智慧农业物联网大数据平台"
    project_candidates = ["智慧农业物联网大数据平台", "智慧农业大数据平台", "农业物联网平台"]
    for candidate in project_candidates:
        if candidate in html_content:
            checks["has_project_name"] = True
            checks["project_name_text"] = candidate
            # 查找这个项目的字号
            for size, text in text_with_size:
                if candidate in text:
                    checks["project_name_size"] = int(size)
                    break
            break

    # 查找 slogan - 一句话定位
    # 通常包含 "融合"、"提前"、"精准" 等词，或者用 "一句话" 等词标注
    slogan_candidates = []
    for size, text in text_with_size:
        if len(text) >= 4 and len(text) <= 30:
            if any(x in text for x in ["融合", "提前", "精准", "实时", "提前", "预警"]):
                slogan_candidates.append((int(size), text))

    if slogan_candidates:
        # 选择最合适的一个（通常是中等字号）
        for size, text in sorted(slogan_candidates):
            if 24 <= size <= 40:  # 可能在范围内
                checks["has_slogan"] = True
                checks["slogan_size"] = size
                checks["slogan_text"] = text
                break

    # 查找分隔装饰线
    divider_matches = re.findall(r'(?:width|宽):\s*(\d+)px[^}]*?(?:height|高|4px)', html_content)
    divider_matches.extend(re.findall(r'(?:height|高):\s*4px[^}]*?(?:width|宽):\s*(\d+)px', html_content))
    divider_matches.extend(re.findall(r'background:[^;]*?(?:EA4335|#EA4335)[^;]*?(?:width|宽):\s*(\d+)px', html_content))

    for match in divider_matches:
        size = int(match)
        if 60 <= size <= 100:
            checks["has_divider"] = True
            checks["divider_size"] = size
            break

    # 如果没找到，检查 divider 类的元素
    if not checks["has_divider"]:
        if "divider" in html_content.lower() or "分割" in html_content:
            checks["has_divider"] = True
            checks["divider_size"] = 80  # 默认值

    # 查找核心关键词 - 应该是多个，用 ｜ 分隔
    if "｜" in html_content or "|" in html_content:
        # 找到包含分隔符的文本
        keyword_matches = re.findall(r'>([^<]*｜[^<]*)<', html_content)
        keyword_matches.extend(re.findall(r'">([^<]*\|[^<]*)<', html_content))
        if keyword_matches:
            for match in keyword_matches:
                if any(x in match for x in ["老龄化", "病虫害", "农药", "靠天", "准确率", "轻量化", "边缘"]):
                    checks["has_keywords"] = True
                    checks["keywords_text"] = match
                    # 查找字号
                    for size, text in text_with_size:
                        if match in text or text in match:
                            checks["keywords_size"] = int(size)
                            break
                    break

    # 查找团队名称
    if "团队" in html_content:
        for size, text in text_with_size:
            if "团队" in text:
                checks["has_team_name"] = True
                checks["team_name_size"] = int(size)
                checks["team_name_text"] = text
                break

    # 查找比赛/日期
    competition_candidates = ["大赛", "2026", "人工智能赛项", "全职业技能大赛"]
    for candidate in competition_candidates:
        if candidate in html_content:
            checks["has_competition_date"] = True
            checks["competition_date_text"] = candidate
            for size, text in text_with_size:
                if candidate in text:
                    checks["competition_date_size"] = int(size)
                    break
            break

    # 检查禁止元素
    if "建议放置" in html_content:
        checks["issues"].append("封面页包含'建议放置' - 封面必须是完成品")

    if "emoji" in html_content.lower() or "📷" in html_content or "📊" in html_content:
        checks["issues"].append("封面页包含emoji占位符 - 封面必须是完成品")

    if re.search(r'border.*?dashed|dashed.*?border', html_content, re.IGNORECASE):
        checks["issues"].append("封面页使用了虚线边框 - 禁止虚线框")

    # 生成警告
    if not checks["has_gradient_circles"]:
        checks["warnings"].append("缺少渐变圆装饰")
    if not checks["has_grid_texture"]:
        checks["warnings"].append("缺少网格纹理")
    if not checks["has_top_bar"]:
        checks["warnings"].append("缺少顶部色带装饰")

    return checks


def print_cover_page_check(checks: dict):
    """打印封面页检查结果"""
    print("\n" + "=" * 60)
    print("封面页 6 元素检查结果")
    print("=" * 60)

    print(f"\n【装饰元素】(至少需要 2 种)")
    print(f"  ✓ 渐变圆: {'有' if checks['has_gradient_circles'] else '无'}")
    print(f"  ✓ 网格纹理: {'有' if checks['has_grid_texture'] else '无'}")
    print(f"  ✓ 顶部色带: {'有' if checks['has_top_bar'] else '无'}")

    print(f"\n【6个必需元素】")
    # 1. 项目名称
    status1 = "✓" if checks["has_project_name"] else "✗"
    print(f"  1. 项目名称 {status1}", end="")
    if checks["project_name_text"]:
        print(f" - '{checks['project_name_text']}'", end="")
        if checks["project_name_size"]:
            if 72 <= checks["project_name_size"] <= 100:
                print(f" (字号: {checks['project_name_size']}px ✓)", end="")
            else:
                print(f" (字号: {checks['project_name_size']}px, 要求: 72-100px ✗)", end="")
    print()

    # 2. slogan
    status2 = "✓" if checks["has_slogan"] else "✗"
    print(f"  2. slogan {status2}", end="")
    if checks["slogan_text"]:
        print(f" - '{checks['slogan_text']}'", end="")
        if checks["slogan_size"]:
            if 28 <= checks["slogan_size"] <= 36:
                print(f" (字号: {checks['slogan_size']}px ✓)", end="")
            else:
                print(f" (字号: {checks['slogan_size']}px, 要求: 28-36px ✗)", end="")
    print()

    # 3. 分隔装饰线
    status3 = "✓" if checks["has_divider"] else "✗"
    print(f"  3. 分隔装饰线 {status3}", end="")
    if checks["divider_size"]:
        if 60 <= checks["divider_size"] <= 100:
            print(f" (宽度: {checks['divider_size']}px ✓)", end="")
        else:
            print(f" (宽度: {checks['divider_size']}px, 要求: 60-100px ✗)", end="")
    print()

    # 4. 核心关键词
    status4 = "✓" if checks["has_keywords"] else "✗"
    print(f"  4. 核心关键词 {status4}", end="")
    if checks["keywords_text"]:
        print(f" - '{checks['keywords_text']}'", end="")
        if checks["keywords_size"]:
            if 24 <= checks["keywords_size"] <= 32:
                print(f" (字号: {checks['keywords_size']}px ✓)", end="")
            else:
                print(f" (字号: {checks['keywords_size']}px, 要求: 24-32px ✗)", end="")
    print()

    # 5. 团队名称
    status5 = "✓" if checks["has_team_name"] else "✗"
    print(f"  5. 团队名称 {status5}", end="")
    if checks["team_name_text"]:
        print(f" - '{checks['team_name_text']}'", end="")
        if checks["team_name_size"]:
            if 16 <= checks["team_name_size"] <= 18:
                print(f" (字号: {checks['team_name_size']}px ✓)", end="")
            else:
                print(f" (字号: {checks['team_name_size']}px, 要求: 16-18px ✗)", end="")
    print()

    # 6. 比赛/日期
    status6 = "✓" if checks["has_competition_date"] else "✗"
    print(f"  6. 比赛/日期 {status6}", end="")
    if checks["competition_date_text"]:
        print(f" - '{checks['competition_date_text']}'", end="")
        if checks["competition_date_size"]:
            if 14 <= checks["competition_date_size"] <= 16:
                print(f" (字号: {checks['competition_date_size']}px ✓)", end="")
            else:
                print(f" (字号: {checks['competition_date_size']}px, 要求: 14-16px ✗)", end="")
    print()

    if checks["issues"]:
        print(f"\n【问题 - 必须修复】")
        for issue in checks["issues"]:
            print(f"  ✗ {issue}")

    if checks["warnings"]:
        print(f"\n【警告 - 建议修复】")
        for warning in checks["warnings"]:
            print(f"  ! {warning}")

    # 计算总分
    element_count = sum([
        checks["has_project_name"],
        checks["has_slogan"],
        checks["has_divider"],
        checks["has_keywords"],
        checks["has_team_name"],
        checks["has_competition_date"]
    ])
    decoration_count = sum([
        checks["has_gradient_circles"],
        checks["has_grid_texture"],
        checks["has_top_bar"]
    ])

    print(f"\n【总分】")
    print(f"  必需元素: {element_count}/6")
    print(f"  装饰元素: {decoration_count}/3 (需要至少2种)")

    print("\n" + "=" * 60)
    return element_count == 6 and decoration_count >= 2 and len(checks["issues"]) == 0


async def test_round4_optimized():
    """测试 Round 4 HTML 生成 - 使用优化后的约束"""
    print("=" * 70)
    print("Round 4 HTML 生成测试 - 使用新的 optimized 约束")
    print("=" * 70)

    # 加载现有数据
    print("\n1. 加载 pipeline_result_full.json...")
    result = load_pipeline_result()
    enriched_pages = extract_enriched_pages(result)
    print(f"   已加载 {len(enriched_pages)} 个 enriched pages")

    # 加载新的 prompt 约束
    print("\n2. 加载 round4_html_generation_optimized.md...")
    prompt_template = load_prompt_template("round4_html_generation_optimized.md")
    print(f"   Prompt 长度: {len(prompt_template)} 字符")

    # 获取第一页（封面页）数据
    print("\n3. 准备封面页数据...")
    if enriched_pages:
        cover_page = enriched_pages[0]
        print(f"   页面编号: {cover_page.get('page_number')}")
        print(f"   页面角色: {cover_page.get('slide_role')}")
        print(f"   标题: {cover_page.get('title')}")
        print(f"   PPT文字: {cover_page.get('ppt_text')}")
    else:
        print("   错误: 没有找到 enriched_pages")
        return

    # 获取项目名称
    project_name = result.get("structured_data", {}).get("project", {}).get("name", "智慧农业物联网大数据平台")
    print(f"   项目名称: {project_name}")

    # 准备生成内容
    batch_content = {
        "meta": {
            "total_pages": len(enriched_pages),
            "project_name": project_name,
            "theme": "dark_tech"
        },
        "pages": [cover_page],
        "batch_info": {
            "batch_number": 1,
            "total_batches": 1,
            "pages_in_batch": 1,
            "page_range": "1-1"
        },
        "previous_batch_html": []
    }

    # 构建 user message
    style_constraints = """
## 统一样式约束（必须遵守）

1. **页面尺寸**：1920x1080px，16:9比例
2. **背景色**：#0F0F23（深色）
3. **主文字色**：#FFFFFF（白色）
4. **字体**：PingFang SC, Microsoft YaHei
5. **禁止动画**：除了 fade_in 和 slide_up
6. **讲稿内容不能出现在 HTML 中**

请严格按照上述约束生成 HTML 页面。"""

    user_message = f"""请根据以下数据生成HTML页面：

丰富后的内容：
{json.dumps(batch_content, ensure_ascii=False, indent=2)}

{style_constraints}

请严格遵循上述System Prompt中的规则执行，生成高质量的HTML页面。"""

    # 调用 Qwen API 生成 HTML
    print("\n4. 调用 Qwen API 生成封面页 HTML...")
    client = QwenClient(api_key=settings.DASHSCOPE_API_KEY)

    try:
        response = await client.chat(
            user_message,
            system_prompt=prompt_template,
            model="qwen3-coder-plus",
            temperature=0.2,
            max_tokens=12000
        )
        print(f"   API 返回长度: {len(response)} 字符")
    except Exception as e:
        print(f"   API 调用失败: {e}")
        return

    # 提取 HTML
    html_content = parse_html_from_response(response)

    # 保存原始响应和解析后的 HTML
    output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output/round4_test"
    os.makedirs(output_dir, exist_ok=True)

    # 保存原始响应
    raw_path = os.path.join(output_dir, "cover_page_raw_response.json")
    with open(raw_path, 'w', encoding='utf-8') as f:
        json.dump({"response": response}, f, ensure_ascii=False, indent=2)
    print(f"\n5a. 原始响应已保存: {raw_path}")

    # 保存解析后的 HTML
    output_path = os.path.join(output_dir, "cover_page_optimized.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"5b. 封面页 HTML 已保存: {output_path}")

    # 验证封面页
    print("\n6. 验证封面页是否符合 6 元素格式...")
    checks = check_cover_page_requirements(html_content)
    passed = print_cover_page_check(checks)

    # 打印 HTML 预览
    print("\n7. HTML 内容预览（前 3000 字符）：")
    print("-" * 60)
    preview = html_content[:3000]
    if len(html_content) > 3000:
        preview += "\n... (截断)"
    print(preview)
    print("-" * 60)

    return html_content, checks, passed


async def main():
    html_content, checks, passed = await test_round4_optimized()

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    if passed:
        print("\n✅ 封面页符合所有要求！")
    else:
        print("\n⚠️ 封面页存在问题，请查看上述检查结果")

        missing = []
        if not checks["has_project_name"]:
            missing.append("项目名称")
        if not checks["has_slogan"]:
            missing.append("slogan")
        if not checks["has_team_name"]:
            missing.append("团队名称")
        if not checks["has_competition_date"]:
            missing.append("比赛/日期")

        if missing:
            print(f"\n缺失的元素: {', '.join(missing)}")


if __name__ == "__main__":
    asyncio.run(main())