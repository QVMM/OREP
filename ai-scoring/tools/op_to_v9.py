#!/usr/bin/env python3
"""
OpenPencil (.op) → V9 组件转换工具

用法:
    python op_to_v9.py input.op --output component.py
    python op_to_v9.py input.op --preview
"""
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any


class OpToV9Converter:
    """将 OpenPencil .op 文件转换为 V9 Python 组件"""

    def __init__(self, op_data: Dict):
        self.op_data = op_data
        self.variables = self._parse_variables()

    def _parse_variables(self) -> Dict[str, str]:
        """解析 .op 文件中的变量"""
        variables = {}
        for var in self.op_data.get("variables", []):
            variables[var["name"]] = var["value"]
        return variables

    def _resolve_color(self, color: str) -> str:
        """解析颜色值（支持变量引用）"""
        if color.startswith("$"):
            var_name = color[1:]
            return self.variables.get(var_name, color)
        return color

    def _convert_fill(self, fill: Any) -> str:
        """转换填充样式为 CSS"""
        if isinstance(fill, str):
            return self._resolve_color(fill)

        if isinstance(fill, dict):
            fill_type = fill.get("type", "SOLID")

            if fill_type == "SOLID":
                return self._resolve_color(fill.get("color", "#000000"))

            elif fill_type == "GRADIENT_LINEAR":
                stops = fill.get("stops", [])
                if len(stops) >= 2:
                    color_stops = ", ".join(
                        f"{self._resolve_color(s['color'])} {int(s['offset'] * 100)}%"
                        for s in stops
                    )
                    return f"linear-gradient(135deg, {color_stops})"

            elif fill_type == "GRADIENT_RADIAL":
                stops = fill.get("stops", [])
                if len(stops) >= 2:
                    color_stops = ", ".join(
                        f"{self._resolve_color(s['color'])} {int(s['offset'] * 100)}%"
                        for s in stops
                    )
                    return f"radial-gradient(circle, {color_stops})"

        return "transparent"

    def _convert_node_to_css(self, node: Dict, theme_var: str = "theme") -> str:
        """将单个节点转换为 HTML/CSS"""
        node_type = node.get("type", "")
        node_id = node.get("id", "node")
        x = node.get("x", 0)
        y = node.get("y", 0)
        width = node.get("width", 100)
        height = node.get("height", 100)
        opacity = node.get("opacity", 1)

        # 基础样式
        styles = [
            f"position:absolute",
            f"left:{x}px",
            f"top:{y}px",
            f"width:{width}px",
            f"height:{height}px",
            f"opacity:{opacity}",
        ]

        # 填充（对于非文本节点）
        fill = node.get("fill")
        if fill and node_type != "TEXT":
            fill_value = self._convert_fill(fill)
            # 如果是渐变，使用 background，否则尝试使用 theme 变量
            if "gradient" in fill_value:
                styles.append(f"background:{fill_value}")
            else:
                # 尝试映射到 theme 变量
                styles.append(f"background:{fill_value}")

        # 描边
        stroke = node.get("stroke")
        if stroke:
            stroke_width = node.get("strokeWidth", 1)
            styles.append(f"border:{stroke_width}px solid {self._resolve_color(stroke)}")

        # 圆角
        border_radius = node.get("borderRadius")
        if border_radius:
            if node_type == "ELLIPSE":
                styles.append("border-radius:50%")
            else:
                styles.append(f"border-radius:{border_radius}px")

        # 文本特定样式
        if node_type == "TEXT":
            font_size = node.get("fontSize", 16)
            font_weight = node.get("fontWeight", 400)
            font_family = node.get("fontFamily", "sans-serif")
            text = node.get("text", "")

            styles.extend([
                f"font-size:{font_size}px",
                f"font-weight:{font_weight}",
                f"font-family:{font_family}",
                f"color:{self._resolve_color(fill) if fill else '#000000'}",
            ])

            # 根据字号选择标签
            if font_size >= 48:
                tag = "h1"
            elif font_size >= 32:
                tag = "h2"
            elif font_size >= 24:
                tag = "h3"
            else:
                tag = "p"

            style_str = ";".join(styles)
            return f'<{tag} style="{style_str};margin:0;">{text}</{tag}>'

        # 椭圆特殊处理
        if node_type == "ELLIPSE":
            styles.append("border-radius:50%")

        style_str = ";".join(styles)
        return f'<div style="{style_str};"></div>'

    def _map_to_theme(self, css: str) -> str:
        """尝试将硬编码颜色映射到 theme 变量"""
        color_mappings = {
            "#0a0a1a": "{theme.bg_primary}",
            "#0a1b3d": "{theme.bg_secondary}",
            "#0056d3": "{theme.accent}",
            "rgba(0,86,211,0.4)": "{theme.glow_color}",
            "#FFFFFF": "{theme.text_primary}",
            "rgba(255,255,255,0.85)": "{theme.text_body}",
        }

        for hardcoded, theme_var in color_mappings.items():
            css = css.replace(hardcoded, theme_var)

        return css

    def convert_page(self, page_index: int = 0) -> str:
        """转换单个页面"""
        pages = self.op_data.get("pages", [])
        if page_index >= len(pages):
            return ""

        page = pages[page_index]
        nodes = page.get("nodes", [])

        # 转换所有节点
        elements = []
        for node in nodes:
            element = self._convert_node_to_css(node)
            element = self._map_to_theme(element)
            elements.append(element)

        return "\n".join(elements)

    def generate_component_class(self, component_id: str = None,
                                  component_name: str = None) -> str:
        """生成完整的 V9 组件 Python 类"""
        name = self.op_data.get("name", "CustomComponent")
        if component_id is None:
            component_id = name.lower().replace(" ", "_")
        if component_name is None:
            component_name = name

        # 生成页面内容
        page_content = self.convert_page(0)

        # 分析使用的数据字段
        data_fields = self._analyze_data_fields()

        # 生成数据获取代码
        data_code = self._generate_data_code(data_fields)

        component_code = f'''"""
V9 组件 - {component_name}
从 OpenPencil 设计文件自动生成
"""
from typing import Dict
from .base import BaseComponent, ThemeContext


class {self._to_class_name(component_id)}Component(BaseComponent):
    component_id = "{component_id}"
    component_name = "{component_name}"

    def render(self, data: Dict, theme: ThemeContext,
               page_index: int = 1, total_pages: int = 1) -> str:
{data_code}

        body = f\'\'\'
{page_content}
{{self._get_page_number(theme, page_index, total_pages)}}\'\'\'

        return self._wrap_full_page(body, theme)
'''

        return component_code

    def _to_class_name(self, snake_case: str) -> str:
        """将 snake_case 转换为 PascalCase"""
        return "".join(word.capitalize() for word in snake_case.split("_"))

    def _sanitize_var_name(self, name: str) -> str:
        """将名称转换为有效的 Python 变量名"""
        # 替换连字符和其他非法字符为下划线
        sanitized = name.replace("-", "_").replace(" ", "_")
        # 确保以字母或下划线开头
        if sanitized and sanitized[0].isdigit():
            sanitized = "_" + sanitized
        return sanitized

    def _analyze_data_fields(self) -> List[str]:
        """分析设计中可能需要的数据字段"""
        fields = []
        for page in self.op_data.get("pages", []):
            for node in page.get("nodes", []):
                if node.get("type") == "TEXT":
                    text = node.get("text", "")
                    if text:
                        # 简单启发式：如果看起来像占位符，标记为数据字段
                        if any(keyword in text.lower() for keyword in
                               ["标题", "title", "项目", "团队", "team", "名称"]):
                            node_id = node.get("id", "text")
                            # 转换为有效的 Python 变量名
                            safe_id = self._sanitize_var_name(node_id)
                            fields.append(safe_id)
        return fields

    def _generate_data_code(self, fields: List[str]) -> str:
        """生成数据获取代码"""
        if not fields:
            return '        title = data.get("title", "默认标题")'

        lines = []
        for field in fields:
            lines.append(f'        {field} = data.get("{field}", "")')
        return "\n".join(lines)

    def preview(self) -> str:
        """生成预览 HTML"""
        page_content = self.convert_page(0)

        preview_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1280">
    <title>{self.op_data.get("name", "Preview")}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            width: 1280px;
            height: 720px;
            position: relative;
            overflow: hidden;
            background: #0a0a1a;
            font-family: "Noto Sans SC", sans-serif;
        }}
    </style>
</head>
<body>
{page_content}
</body>
</html>'''

        return preview_html


def main():
    parser = argparse.ArgumentParser(
        description="将 OpenPencil .op 文件转换为 V9 组件"
    )
    parser.add_argument("input", help="输入的 .op 文件路径")
    parser.add_argument("--output", "-o", help="输出的 Python 组件文件路径")
    parser.add_argument("--preview", "-p", action="store_true",
                       help="生成预览 HTML 而不是 Python 组件")
    parser.add_argument("--component-id", help="自定义组件 ID")
    parser.add_argument("--component-name", help="自定义组件名称")

    args = parser.parse_args()

    # 读取 .op 文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在 - {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        op_data = json.load(f)

    # 创建转换器
    converter = OpToV9Converter(op_data)

    if args.preview:
        # 生成预览
        preview_html = converter.preview()
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(preview_html, encoding="utf-8")
            print(f"预览已保存到: {output_path}")
        else:
            print(preview_html)
    else:
        # 生成组件
        component_code = converter.generate_component_class(
            args.component_id,
            args.component_name
        )

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(component_code, encoding="utf-8")
            print(f"组件已保存到: {output_path}")
        else:
            print(component_code)


if __name__ == "__main__":
    main()
