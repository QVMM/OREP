#!/usr/bin/env python3
"""
测试封面页的 Round 3 + Round 4 流程
只测试第一页（封面页/hook）
"""
import asyncio
import json
import os
import sys
import re

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


async def test_cover_page():
    """测试封面页的 Round 3 + Round 4 流程"""
    print("=" * 70)
    print("测试封面页 cover_elements 生成")
    print("=" * 70)

    # 读取问卷数据
    questionnaire_path = "/Users/liuyixing/项目/OREP/ai-scoring/output/test_questionnaire_智慧农业.json"
    with open(questionnaire_path, 'r', encoding='utf-8') as f:
        questionnaire_data = json.load(f)

    print(f"\n问卷数据: {questionnaire_data.get('project_name')}")
    print(f"团队: {questionnaire_data.get('team_name')}")
    print(f"学校: {questionnaire_data.get('school_name')}")

    # 构造 structured_data（简化版，用于测试）
    structured_data = {
        "project": {
            "name": questionnaire_data.get("project_name", "智慧农业物联网大数据平台")
        },
        "stories": {
            "elevator_pitch": questionnaire_data.get("project_significance", "用AI让种地更精准")
        },
        "tech": {},
        "industry": {}
    }

    # 构造 original_data（包含 competition 信息）
    original_data = {
        "project": structured_data["project"],
        "stories": structured_data["stories"],
        "tech": structured_data["tech"],
        "industry": structured_data["industry"],
        "competition": {
            "team_name": questionnaire_data.get("team_name", ""),
            "school_name": questionnaire_data.get("school_name", ""),
            "competition_name": "全职业技能大赛",
            "year": 2026
        }
    }

    # 封面页框架
    cover_page_framework = {
        "page_number": 1,
        "phase": "开场路演",
        "slide_role": "hook",
        "title": "靠天吃饭的时代",
        "ppt_text": "老龄化加剧｜病虫害滞后｜农药滥用｜靠天收"
    }

    print("\n" + "-" * 50)
    print("Step 1: Round 3 - 生成 cover_elements")
    print("-" * 50)

    # 加载 Round 3 prompt
    round3_prompt = load_prompt_template("round3_enrich.md")

    user_message_round3 = f"""请丰富以下页面内容：

确认的叙事框架（第1页，共1页）：
{json.dumps({"meta": {"total_pages": 1}, "pages": [cover_page_framework]}, ensure_ascii=False, indent=2)}

原始数据参考：
{json.dumps(original_data, ensure_ascii=False, indent=2)}

请严格遵循上述System Prompt中的规则执行。"""

    client = QwenClient(api_key=settings.DASHSCOPE_API_KEY)

    print("\n调用 Qwen API 生成 cover_elements...")
    try:
        response_round3 = await client.chat(
            user_message_round3,
            system_prompt=round3_prompt,
            model="qwen3.6-plus",
            temperature=0.3,
            max_tokens=8000,
            json_mode=True
        )
        print(f"Round 3 返回长度: {len(response_round3)} 字符")
    except Exception as e:
        print(f"Round 3 API 调用失败: {e}")
        return

    # 解析 Round 3 结果
    enriched_page = None
    try:
        # 清理响应
        clean_response = response_round3.strip()
        if clean_response.startswith('```json'):
            start = clean_response.find('```json') + 7
            end = clean_response.find('```', start)
            if end > start:
                clean_response = clean_response[start:end].strip()
        elif clean_response.startswith('```'):
            start = clean_response.find('```') + 3
            end = clean_response.find('```', start)
            if end > start:
                clean_response = clean_response[start:end].strip()

        data_round3 = json.loads(clean_response)

        # 提取第一页
        if "pages" in data_round3 and len(data_round3["pages"]) > 0:
            enriched_page = data_round3["pages"][0]
        elif "page_number" in data_round3:
            enriched_page = data_round3

    except json.JSONDecodeError as e:
        print(f"Round 3 JSON 解析失败: {e}")
        print(f"原始响应: {response_round3[:500]}...")
        return

    # 检查 cover_elements
    print("\n检查 cover_elements 字段:")
    print("-" * 50)

    if enriched_page and "cover_elements" in enriched_page:
        cover = enriched_page["cover_elements"]
        print("✓ cover_elements 存在")

        fields = ["project_name", "slogan", "keywords", "team_name", "competition_info", "school_name"]
        for field in fields:
            if field in cover:
                value = cover[field]
                if isinstance(value, list):
                    print(f"  ✓ {field}: {value}")
                else:
                    print(f"  ✓ {field}: {value}")
            else:
                print(f"  ✗ {field}: 缺失")

        # 保存 Round 3 结果
        output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output/cover_test"
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "round3_result.json"), 'w', encoding='utf-8') as f:
            json.dump(enriched_page, f, ensure_ascii=False, indent=2)
        print(f"\nRound 3 结果已保存: {output_dir}/round3_result.json")

    else:
        print("✗ cover_elements 字段不存在!")
        print(f"\nenriched_page 内容: {json.dumps(enriched_page, ensure_ascii=False, indent=2)[:1000]}")

        # 保存原始响应
        output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output/cover_test"
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "round3_raw.json"), 'w', encoding='utf-8') as f:
            json.dump({"response": response_round3}, f, ensure_ascii=False, indent=2)
        return

    # Round 4 测试
    print("\n" + "-" * 50)
    print("Step 2: Round 4 - 生成封面页 HTML")
    print("-" * 50)

    # 加载 Round 4 prompt
    round4_prompt = load_prompt_template("round4_html_generation_optimized.md")

    # 准备 Round 4 的批次数据
    batch_content = {
        "meta": {
            "total_pages": 1,
            "project_name": structured_data["project"]["name"],
            "theme": "dark_tech"
        },
        "pages": [enriched_page],
        "batch_info": {
            "batch_number": 1,
            "total_batches": 1,
            "pages_in_batch": 1,
            "page_range": "1-1"
        },
        "previous_batch_html": []
    }

    style_constraints = """
## 统一样式约束（必须遵守）

1. **页面尺寸**：1920x1080px，16:9比例
2. **背景色**：#0F0F23（深色）
3. **主文字色**：#FFFFFF（白色）
4. **字体**：PingFang SC, Microsoft YaHei
5. **禁止动画**：除了 fade_in 和 slide_up
6. **讲稿内容不能出现在 HTML 中**

请严格按照上述约束生成 HTML 页面。"""

    user_message_round4 = f"""请根据以下数据生成HTML页面：

丰富后的内容：
{json.dumps(batch_content, ensure_ascii=False, indent=2)}

{style_constraints}

请严格遵循上述System Prompt中的规则执行，生成高质量的HTML页面。"""

    print("\n调用 Qwen API 生成封面页 HTML...")
    try:
        response_round4 = await client.chat(
            user_message_round4,
            system_prompt=round4_prompt,
            model="qwen3-coder-plus",
            temperature=0.2,
            max_tokens=12000
        )
        print(f"Round 4 返回长度: {len(response_round4)} 字符")
    except Exception as e:
        print(f"Round 4 API 调用失败: {e}")
        return

    # 提取 HTML
    html_content = response_round4
    if "```html" in response_round4:
        start = response_round4.find("```html") + 7
        end = response_round4.find("```", start)
        if end > start:
            html_content = response_round4[start:end].strip()
    elif "```" in response_round4:
        start = response_round4.find("```") + 3
        end = response_round4.find("```", start)
        if end > start:
            html_content = response_round4[start:end].strip()
    elif "{" in response_round4:
        # JSON 格式响应
        try:
            data_r4 = json.loads(response_round4.strip())
            if isinstance(data_r4, dict):
                if "html" in data_r4:
                    html_content = data_r4["html"]
                elif "pages" in data_r4 and len(data_r4["pages"]) > 0:
                    if "html" in data_r4["pages"][0]:
                        html_content = data_r4["pages"][0]["html"]
        except:
            pass

    # 保存 HTML
    html_path = os.path.join(output_dir, "cover_page.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"\n封面页 HTML 已保存: {html_path}")

    # 验证 HTML 内容
    print("\n" + "-" * 50)
    print("验证封面页 HTML 内容")
    print("-" * 50)

    checks = {
        "has_project_name": False,
        "has_slogan": False,
        "has_keywords": False,
        "has_team_name": False,
        "has_competition_info": False,
        "issues": []
    }

    # 检查各元素
    cover_elements = enriched_page.get("cover_elements", {})

    # project_name
    project_name = cover_elements.get("project_name", "")
    if project_name and project_name in html_content:
        checks["has_project_name"] = True
        print(f"✓ 项目名称: {project_name}")

    # slogan
    slogan = cover_elements.get("slogan", "")
    if slogan and slogan in html_content:
        checks["has_slogan"] = True
        print(f"✓ slogan: {slogan}")

    # keywords
    keywords = cover_elements.get("keywords", [])
    if keywords:
        found_keywords = []
        for kw in keywords:
            if kw in html_content:
                found_keywords.append(kw)
        if found_keywords:
            checks["has_keywords"] = True
            print(f"✓ 关键词: {found_keywords}")

    # team_name
    team_name = cover_elements.get("team_name", "")
    if team_name and team_name in html_content:
        checks["has_team_name"] = True
        print(f"✓ 团队名称: {team_name}")

    # competition_info
    competition_info = cover_elements.get("competition_info", "")
    if competition_info and competition_info in html_content:
        checks["has_competition_info"] = True
        print(f"✓ 比赛信息: {competition_info}")

    # 检查禁止元素
    if "建议放置" in html_content or "📷" in html_content:
        checks["issues"].append("包含占位符提示")

    if checks["issues"]:
        print(f"\n问题: {checks['issues']}")

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    all_passed = all([
        checks["has_project_name"],
        checks["has_slogan"],
        checks["has_keywords"],
        checks["has_team_name"],
        checks["has_competition_info"]
    ])

    if all_passed and not checks["issues"]:
        print("\n✅ 封面页测试通过!")
    else:
        print("\n⚠️ 封面页测试存在问题:")
        if not checks["has_project_name"]:
            print("  - 缺少项目名称")
        if not checks["has_slogan"]:
            print("  - 缺少 slogan")
        if not checks["has_keywords"]:
            print("  - 缺少关键词")
        if not checks["has_team_name"]:
            print("  - 缺少团队名称")
        if not checks["has_competition_info"]:
            print("  - 缺少比赛信息")


if __name__ == "__main__":
    asyncio.run(test_cover_page())