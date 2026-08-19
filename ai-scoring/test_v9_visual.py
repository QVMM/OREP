"""
V9 组件系统 - 5页PPT可视化测试
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ppt.assembly_engine import AssemblyEngine
from app.services.ppt.components.base import ThemeContext

# 输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "test_v9_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 5页测试内容
content_json = [
    {
        "layout": "cover_layout",
        "title": "智能PPT生成系统",
        "subtitle": "AI驱动的演示文稿自动化方案，10倍效率提升",
        "team": "OREP技术团队"
    },
    {
        "layout": "toc_layout",
        "sections": ["项目背景", "痛点分析", "解决方案", "技术架构", "团队介绍"]
    },
    {
        "layout": "two_column_layout",
        "title": "市场痛点 vs 我们的方案",
        "left": {
            "title": "当前痛点",
            "content": "• 制作一份专业PPT平均需要4-8小时\n• 设计质量依赖个人审美，参差不齐\n• 内容组织缺乏逻辑框架\n• 模板套用导致千篇一律"
        },
        "right": {
            "title": "AI解决方案",
            "content":"• 填写问卷即可自动生成完整PPT\n• 基于锐普设计Token保证视觉质量\n• 15项评分标准驱动内容结构\n• 7个行业主题，个性化定制"
        }
    },
    {
        "layout": "data_layout",
        "title": "核心指标",
        "metrics": [
            {"name": "效率提升", "value": "10x", "desc": "从8小时缩短至30分钟"},
            {"name": "成本降低", "value": "80%", "desc": "无需聘请专业设计师"},
            {"name": "质量评分", "value": "95", "desc": "Token合规率"},
            {"name": "用户满意度", "value": "98%", "desc": "基于100+测试用户"}
        ]
    },
    {
        "layout": "ending_layout",
        "title": "感谢聆听"
    }
]

# 测试不同主题
themes = ["deep-blue-tech", "black-gold", "fresh-green"]

for theme_name in themes:
    print(f"\n=== 生成 {theme_name} 主题 ===")
    engine = AssemblyEngine(theme_name)
    html_pages = engine.assemble_pages(content_json)

    theme_dir = os.path.join(OUTPUT_DIR, theme_name)
    os.makedirs(theme_dir, exist_ok=True)

    for i, html in enumerate(html_pages):
        file_path = os.path.join(theme_dir, f"page_{i+1}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ page_{i+1}.html")

print(f"\n输出目录: {OUTPUT_DIR}")
print("请用浏览器打开HTML文件查看效果")
