#!/usr/bin/env python3
"""
PPT Token合规测试脚本
测试5页PPT生成的Token合规分数
"""
import os
import sys
import json
import asyncio
import logging

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


# 示例设计稿数据（5页）
SAMPLE_DESIGN_DRAFT = [
    {
        "page_index": 1,
        "section": "封面",
        "design": {
            "title": {"text": "智慧城市AI数据平台", "font_size": "52px", "color": "#FFFFFF"},
            "subtitle": {"text": "基于人工智能的城市数据治理解决方案", "font_size": "22px"},
            "layout": "cover",
            "elements": [
                {"type": "text", "content": "团队：智慧城市创新组"},
                {"type": "text", "content": "项目类型：数据治理"}
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
                {"type": "text", "content": "国家战略需求：《十四五规划》明确提出数字化转型目标"},
                {"type": "text", "content": "行业趋势：智慧城市市场规模预计2025年达到万亿级别"},
                {"type": "text", "content": "社会需求：城市管理效率提升30%，居民满意度提高20%"}
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
                {"type": "card", "title": "数据采集层", "content": "IoT传感器网络，实时采集城市运行数据"},
                {"type": "card", "title": "数据处理层", "content": "分布式计算框架，支持PB级数据处理"},
                {"type": "card", "title": "AI分析层", "content": "深度学习模型，智能识别城市问题"}
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
                {"type": "text", "content": "技术创新：首次将联邦学习应用于城市数据治理"},
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


async def test_token_validation():
    """测试Token验证逻辑"""
    print("\n" + "="*60)
    print("🧪 测试1: Token验证逻辑")
    print("="*60)

    token_manager = get_token_manager()

    # 测试颜色匹配
    test_cases = [
        {
            "name": "标准格式",
            "html": '<div style="background: #0a0a1a; color: #0056d3;">测试</div>',
            "expected": True
        },
        {
            "name": "RGBA格式（有空格）",
            "html": '<div style="background: rgba(0, 86, 211, 0.4);">测试</div>',
            "expected": True
        },
        {
            "name": "RGBA格式（无空格）",
            "html": '<div style="background: rgba(0,86,211,0.4);">测试</div>',
            "expected": True
        },
        {
            "name": "RGB格式",
            "html": '<div style="background: rgb(0, 86, 211);">测试</div>',
            "expected": True
        },
    ]

    for case in test_cases:
        # 测试accent颜色匹配
        accent_match = token_manager._color_in_html("#0056d3", case["html"])
        # 测试glow颜色匹配
        glow_match = token_manager._color_in_html("rgba(0,86,211,0.4)", case["html"])

        result = accent_match or glow_match
        status = "✅" if result == case["expected"] else "❌"
        print(f"  {status} {case['name']}: accent={accent_match}, glow={glow_match}")


async def test_html_generation():
    """测试HTML生成和Token合规"""
    print("\n" + "="*60)
    print("🧪 测试2: HTML生成和Token合规")
    print("="*60)

    # 获取主题
    theme = get_theme_by_industry("ai_iot")
    print(f"  使用主题: {theme.get('name', 'unknown')}")

    # 获取Token管理器
    token_manager = get_token_manager()
    theme_name = theme.get('name', 'deep-blue-tech')

    # 创建Qwen客户端
    qwen_client = QwenClient(api_key=settings.DASHSCOPE_API_KEY)

    # 创建HTML生成器
    html_generator = HTMLGenerator(qwen_client=qwen_client)

    scores = []
    for i, page_design in enumerate(SAMPLE_DESIGN_DRAFT):
        page_index = i + 1
        print(f"\n  生成第{page_index}页: {page_design.get('section', '')}")

        try:
            # 生成HTML
            html = await html_generator._generate_single_page(page_design, theme, page_index, len(SAMPLE_DESIGN_DRAFT))

            if html and len(html) > 500:
                # 验证Token合规
                token_result = token_manager.validate_html_compliance(html, theme_name)
                score = token_result.get("percentage", 0)
                scores.append(score)

                print(f"    Token分数: {score}%")
                print(f"    检查详情: {json.dumps(token_result.get('checks', {}), ensure_ascii=False)}")
            else:
                print(f"    ❌ HTML生成失败或长度不足")
                scores.append(0)

        except Exception as e:
            print(f"    ❌ 生成失败: {e}")
            scores.append(0)

    # 计算平均分
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\n  平均Token分数: {avg_score:.1f}%")
        print(f"  达标页面: {sum(1 for s in scores if s >= 90)}/{len(scores)}")

        if avg_score >= 90:
            print("  ✅ 平均分数达到90%目标!")
        else:
            print(f"  ⚠️ 平均分数未达到90%目标，差距: {90 - avg_score:.1f}%")

    return scores


async def test_without_ai():
    """不使用AI生成，直接测试模板HTML的Token合规"""
    print("\n" + "="*60)
    print("🧪 测试3: 模板HTML的Token合规")
    print("="*60)

    # 获取主题
    theme = get_theme_by_industry("ai_iot")
    theme_name = theme.get('name', 'deep-blue-tech')
    print(f"  使用主题: {theme_name}")

    # 获取Token管理器
    token_manager = get_token_manager()

    # 创建HTML生成器（不使用AI）
    html_generator = HTMLGenerator()

    scores = []
    for i, page_design in enumerate(SAMPLE_DESIGN_DRAFT):
        page_index = i + 1
        print(f"\n  生成第{page_index}页: {page_design.get('section', '')}")

        try:
            # 使用模板生成HTML
            html = html_generator._generate_page_from_design(page_design, theme, page_index, len(SAMPLE_DESIGN_DRAFT))

            if html and len(html) > 500:
                # 验证Token合规
                token_result = token_manager.validate_html_compliance(html, theme_name)
                score = token_result.get("percentage", 0)
                scores.append(score)

                print(f"    Token分数: {score}%")
                print(f"    检查详情: {json.dumps(token_result.get('checks', {}), ensure_ascii=False)}")
            else:
                print(f"    ❌ HTML生成失败或长度不足")
                scores.append(0)

        except Exception as e:
            print(f"    ❌ 生成失败: {e}")
            scores.append(0)

    # 计算平均分
    if scores:
        avg_score = sum(scores) / len(scores)
        print(f"\n  平均Token分数: {avg_score:.1f}%")
        print(f"  达标页面: {sum(1 for s in scores if s >= 90)}/{len(scores)}")

    return scores


async def main():
    """主测试函数"""
    print("╔" + "═"*58 + "╗")
    print("║   PPT Token合规测试                                      ║")
    print("║   测试5页PPT生成的Token合规分数                          ║")
    print("╚" + "═"*58 + "╝")

    # 测试1: Token验证逻辑
    await test_token_validation()

    # 测试2: 模板HTML的Token合规（不需要API）
    template_scores = await test_without_ai()

    # 测试3: AI生成HTML的Token合规（需要API）
    # 注意：这会调用API，如果不想调用可以注释掉
    # ai_scores = await test_html_generation()

    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    if template_scores:
        avg = sum(template_scores) / len(template_scores)
        print(f"模板HTML平均Token分数: {avg:.1f}%")
        if avg >= 90:
            print("✅ 模板HTML达到90%目标!")
        else:
            print(f"⚠️ 模板HTML未达到90%目标")


if __name__ == '__main__':
    asyncio.run(main())
