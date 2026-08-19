#!/usr/bin/env python3
"""
V9 组件 → OpenPencil (.op) 转换工具

用法:
    python v9_to_op.py component_name --output preview.op
    python v9_to_op.py cover --theme deep-blue-tech
"""
import json
import argparse
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


# 主题颜色映射
THEME_COLORS = {
    "deep-blue-tech": {
        "bg-primary": "#0a0a1a",
        "bg-secondary": "#0a1b3d",
        "accent": "#0056d3",
        "glow-color": "rgba(0,86,211,0.4)",
        "text-primary": "#FFFFFF",
        "text-body": "rgba(255,255,255,0.85)",
    },
    "black-gold": {
        "bg-primary": "#0a0a0a",
        "bg-secondary": "#1a1a1a",
        "accent": "#d4af37",
        "glow-color": "rgba(212,175,55,0.4)",
        "text-primary": "#FFFFFF",
        "text-body": "rgba(255,255,255,0.85)",
    },
    "fresh-green": {
        "bg-primary": "#0a1a0a",
        "bg-secondary": "#0a2a0a",
        "accent": "#00d356",
        "glow-color": "rgba(0,211,86,0.4)",
        "text-primary": "#FFFFFF",
        "text-body": "rgba(255,255,255,0.85)",
    },
    "sky-blue-tech": {
        "bg-primary": "#0a0a1a",
        "bg-secondary": "#0a1a3d",
        "accent": "#00a6ff",
        "glow-color": "rgba(0,166,255,0.4)",
        "text-primary": "#FFFFFF",
        "text-body": "rgba(255,255,255,0.85)",
    },
}


class V9ToOpConverter:
    """将 V9 组件转换为 OpenPencil .op 文件"""

    def __init__(self, theme_name: str = "deep-blue-tech"):
        self.theme_name = theme_name
        self.theme = THEME_COLORS.get(theme_name, THEME_COLORS["deep-blue-tech"])

    def _create_gradient_linear(self, colors: List[str], angle: int = 135) -> Dict:
        """创建线性渐变"""
        stops = []
        for i, color in enumerate(colors):
            offset = i / (len(colors) - 1) if len(colors) > 1 else 0
            stops.append({"offset": offset, "color": color})
        return {
            "type": "GRADIENT_LINEAR",
            "stops": stops
        }

    def _create_gradient_radial(self, colors: List[str]) -> Dict:
        """创建径向渐变"""
        stops = []
        for i, color in enumerate(colors):
            offset = i / (len(colors) - 1) if len(colors) > 1 else 0
            stops.append({"offset": offset, "color": color})
        return {
            "type": "GRADIENT_RADIAL",
            "stops": stops
        }

    def create_cover_page(self, title: str = "智能PPT生成系统",
                          subtitle: str = "AI驱动的演示文稿自动化方案",
                          team: str = "OREP团队") -> Dict:
        """创建封面页"""
        page = {
            "id": "page-1",
            "name": "Cover Page",
            "width": 1280,
            "height": 720,
            "nodes": [
                # 背景
                {
                    "id": "bg",
                    "type": "RECT",
                    "x": 0,
                    "y": 0,
                    "width": 1280,
                    "height": 720,
                    "fill": self._create_gradient_linear(
                        [self.theme["bg-primary"], self.theme["bg-secondary"]]
                    )
                },
                # 发光球体
                {
                    "id": "glow",
                    "type": "ELLIPSE",
                    "x": 880,
                    "y": 210,
                    "width": 280,
                    "height": 280,
                    "fill": self._create_gradient_radial([
                        self.theme["glow-color"],
                        "transparent"
                    ]),
                    "opacity": 0.4
                },
                # 同心圆装饰
                {
                    "id": "circle1",
                    "type": "ELLIPSE",
                    "x": 580,
                    "y": 60,
                    "width": 600,
                    "height": 600,
                    "stroke": self.theme["accent"],
                    "strokeWidth": 1,
                    "fill": "transparent",
                    "opacity": 0.08
                },
                {
                    "id": "circle2",
                    "type": "ELLIPSE",
                    "x": 620,
                    "y": 100,
                    "width": 520,
                    "height": 520,
                    "stroke": self.theme["accent"],
                    "strokeWidth": 1,
                    "fill": "transparent",
                    "opacity": 0.12
                },
                # 标题装饰条
                {
                    "id": "title-accent",
                    "type": "RECT",
                    "x": 80,
                    "y": 180,
                    "width": 4,
                    "height": 100,
                    "fill": self.theme["accent"],
                    "borderRadius": 2
                },
                # 标题
                {
                    "id": "title",
                    "type": "TEXT",
                    "x": 100,
                    "y": 200,
                    "width": 650,
                    "text": title,
                    "fontSize": 56,
                    "fontWeight": 900,
                    "fill": self.theme["text-primary"],
                    "fontFamily": "Noto Sans SC"
                },
                # 副标题
                {
                    "id": "subtitle",
                    "type": "TEXT",
                    "x": 100,
                    "y": 360,
                    "width": 600,
                    "text": subtitle,
                    "fontSize": 20,
                    "fontWeight": 400,
                    "fill": self.theme["text-body"],
                    "fontFamily": "Noto Sans SC"
                },
                # 团队图标背景
                {
                    "id": "team-bg",
                    "type": "ELLIPSE",
                    "x": 100,
                    "y": 592,
                    "width": 48,
                    "height": 48,
                    "fill": self.theme["accent"]
                },
                # 团队名称
                {
                    "id": "team-name",
                    "type": "TEXT",
                    "x": 168,
                    "y": 610,
                    "width": 200,
                    "text": team,
                    "fontSize": 18,
                    "fontWeight": 500,
                    "fill": self.theme["text-primary"],
                    "fontFamily": "Noto Sans SC"
                }
            ]
        }
        return page

    def create_toc_page(self, sections: List[str]) -> Dict:
        """创建目录页"""
        nodes = [
            # 背景
            {
                "id": "bg",
                "type": "RECT",
                "x": 0,
                "y": 0,
                "width": 1280,
                "height": 720,
                "fill": self._create_gradient_linear(
                    [self.theme["bg-primary"], self.theme["bg-secondary"]]
                )
            },
            # 标题
            {
                "id": "title",
                "type": "TEXT",
                "x": 100,
                "y": 80,
                "width": 300,
                "text": "目录",
                "fontSize": 48,
                "fontWeight": 800,
                "fill": self.theme["text-primary"],
                "fontFamily": "Noto Sans SC"
            }
        ]

        # 添加章节项
        for i, section in enumerate(sections[:8]):  # 最多8个章节
            y_pos = 180 + i * 65
            nodes.extend([
                {
                    "id": f"section-num-{i}",
                    "type": "TEXT",
                    "x": 100,
                    "y": y_pos,
                    "width": 50,
                    "text": f"{i + 1:02d}",
                    "fontSize": 24,
                    "fontWeight": 700,
                    "fill": self.theme["accent"],
                    "fontFamily": "Noto Sans SC"
                },
                {
                    "id": f"section-title-{i}",
                    "type": "TEXT",
                    "x": 170,
                    "y": y_pos,
                    "width": 500,
                    "text": section,
                    "fontSize": 24,
                    "fontWeight": 500,
                    "fill": self.theme["text-primary"],
                    "fontFamily": "Noto Sans SC"
                }
            ])

        page = {
            "id": "page-toc",
            "name": "Table of Contents",
            "width": 1280,
            "height": 720,
            "nodes": nodes
        }
        return page

    def create_ending_page(self, title: str = "感谢聆听") -> Dict:
        """创建结束页"""
        page = {
            "id": "page-ending",
            "name": "Ending Page",
            "width": 1280,
            "height": 720,
            "nodes": [
                # 背景
                {
                    "id": "bg",
                    "type": "RECT",
                    "x": 0,
                    "y": 0,
                    "width": 1280,
                    "height": 720,
                    "fill": self._create_gradient_linear(
                        [self.theme["bg-primary"], self.theme["bg-secondary"]]
                    )
                },
                # 装饰圆
                {
                    "id": "deco-circle",
                    "type": "ELLIPSE",
                    "x": 440,
                    "y": 160,
                    "width": 400,
                    "height": 400,
                    "stroke": self.theme["accent"],
                    "strokeWidth": 1,
                    "fill": "transparent",
                    "opacity": 0.15
                },
                # 标题
                {
                    "id": "title",
                    "type": "TEXT",
                    "x": 0,
                    "y": 300,
                    "width": 1280,
                    "text": title,
                    "fontSize": 72,
                    "fontWeight": 900,
                    "fill": self.theme["text-primary"],
                    "fontFamily": "Noto Sans SC"
                }
            ]
        }
        return page

    def convert_component(self, component_name: str) -> Dict:
        """根据组件名称生成对应的 .op 数据"""
        name_lower = component_name.lower()

        if "cover" in name_lower:
            return self._create_op_data([self.create_cover_page()], "Cover Page")
        elif "toc" in name_lower or "table" in name_lower:
            sections = ["项目背景", "问题分析", "解决方案", "技术实现", "团队介绍"]
            return self._create_op_data([self.create_toc_page(sections)], "Table of Contents")
        elif "ending" in name_lower or "thank" in name_lower:
            return self._create_op_data([self.create_ending_page()], "Ending Page")
        else:
            # 默认创建一个空白页
            return self._create_op_data([self.create_cover_page()], component_name)

    def _create_op_data(self, pages: List[Dict], name: str) -> Dict:
        """创建完整的 .op 数据结构"""
        return {
            "version": "0.7.0",
            "name": name,
            "pages": pages,
            "variables": [
                {"name": "bg-primary", "type": "color", "value": self.theme["bg-primary"]},
                {"name": "bg-secondary", "type": "color", "value": self.theme["bg-secondary"]},
                {"name": "accent", "type": "color", "value": self.theme["accent"]},
                {"name": "glow-color", "type": "color", "value": self.theme["glow-color"]},
                {"name": "text-primary", "type": "color", "value": self.theme["text-primary"]},
                {"name": "text-body", "type": "color", "value": self.theme["text-body"]},
            ]
        }


def main():
    parser = argparse.ArgumentParser(
        description="将 V9 组件转换为 OpenPencil .op 文件"
    )
    parser.add_argument("component", help="组件名称 (cover, toc, ending 等)")
    parser.add_argument("--output", "-o", help="输出的 .op 文件路径")
    parser.add_argument("--theme", "-t", default="deep-blue-tech",
                       choices=list(THEME_COLORS.keys()),
                       help="主题名称")
    parser.add_argument("--title", help="自定义标题")
    parser.add_argument("--subtitle", help="自定义副标题")
    parser.add_argument("--team", help="自定义团队名称")

    args = parser.parse_args()

    # 创建转换器
    converter = V9ToOpConverter(args.theme)

    # 生成 .op 数据
    op_data = converter.convert_component(args.component)

    # 应用自定义参数
    if args.title and op_data["pages"]:
        for node in op_data["pages"][0].get("nodes", []):
            if node.get("id") == "title" and node.get("type") == "TEXT":
                node["text"] = args.title

    if args.subtitle and op_data["pages"]:
        for node in op_data["pages"][0].get("nodes", []):
            if node.get("id") == "subtitle" and node.get("type") == "TEXT":
                node["text"] = args.subtitle

    if args.team and op_data["pages"]:
        for node in op_data["pages"][0].get("nodes", []):
            if node.get("id") == "team-name" and node.get("type") == "TEXT":
                node["text"] = args.team

    # 输出结果
    json_str = json.dumps(op_data, indent=2, ensure_ascii=False)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_str, encoding="utf-8")
        print(f".op 文件已保存到: {output_path}")
        print(f"可以在 OpenPencil 中打开此文件进行编辑")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
