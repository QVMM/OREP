from __future__ import annotations

from pathlib import Path
import textwrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "product_brochure" / "OREP_腾讯式克制版宣传手册样张_v3.png"
FONT_REG = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def wrap_cn(text: str, max_chars: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        while len(para) > max_chars:
            cut = max_chars
            for mark in "，。；、 ":
                pos = para.rfind(mark, 0, max_chars + 1)
                if pos > max_chars * 0.55:
                    cut = pos + 1
                    break
            lines.append(para[:cut])
            para = para[cut:]
        lines.append(para)
    return lines


def draw_text(draw, xy, text, size=28, fill="#182033", bold=False, max_chars=None, line_gap=10):
    x, y = xy
    f = font(size, bold)
    lines = wrap_cn(text, max_chars) if max_chars else text.split("\n")
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill)
        bbox = draw.textbbox((x, y), line or "口", font=f)
        y += bbox[3] - bbox[1] + line_gap
    return y


def rounded(draw, box, radius=16, fill="#ffffff", outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def card(draw, box, title, body, accent="#1A73E8"):
    rounded(draw, box, 12, fill="#FFFFFF", outline="#D8E3F0", width=2)
    x1, y1, x2, y2 = box
    draw.rectangle((x1, y1, x1 + 8, y2), fill=accent)
    draw_text(draw, (x1 + 30, y1 + 22), title, size=26, fill="#0B3D91", bold=True)
    draw_text(draw, (x1 + 30, y1 + 66), body, size=21, fill="#4B5B6D", max_chars=19, line_gap=8)


def main():
    W, H = 1600, 2260
    img = Image.new("RGB", (W, H), "#F6F8FB")
    draw = ImageDraw.Draw(img)

    # Paper
    margin = 82
    rounded(draw, (margin, 54, W - margin, H - 54), 8, fill="#FFFFFF", outline="#E5EAF2", width=2)

    # Header
    draw_text(draw, (140, 118), "OREP 产品宣传手册 / Product Brochure", size=24, fill="#64748B", bold=True)
    draw.line((140, 170, 1460, 170), fill="#E4EAF3", width=2)

    # Hero
    draw_text(draw, (140, 236), "在线路演评审平台", size=68, fill="#071B46", bold=True)
    draw_text(
        draw,
        (140, 330),
        "让路演评审从一次活动，升级为可组织、可追溯、可复盘、可持续运营的数字化成长体系。",
        size=30,
        fill="#334155",
        max_chars=35,
        line_gap=12,
    )
    rounded(draw, (1120, 232, 1435, 428), 14, fill="#EBF4FF", outline="#C8DCF8", width=2)
    draw_text(draw, (1150, 260), "核心对象", size=22, fill="#0B3D91", bold=True)
    for i, t in enumerate(["高校 / 赛事", "园区 / 孵化器", "评委 / 指导老师", "参赛团队"]):
        y = 305 + i * 30
        draw.ellipse((1150, y + 8, 1160, y + 18), fill="#1A73E8")
        draw_text(draw, (1176, y), t, size=20, fill="#1E293B")

    # Pain -> solution
    draw_text(draw, (140, 510), "为什么需要 OREP", size=38, fill="#0B3D91", bold=True)
    card(draw, (140, 585, 505, 790), "组织分散", "会议、资料、评委、学生与结果分散在多个工具中。")
    card(draw, (550, 585, 915, 790), "评分难追溯", "分数、扣分依据、问题反馈和复盘证据难沉淀。")
    card(draw, (960, 585, 1325, 790), "成长反馈弱", "学生只得到结果，难知道表达、材料和演示如何改。")
    draw.polygon([(1355, 665), (1430, 690), (1355, 715)], fill="#1A73E8")
    rounded(draw, (1328, 600, 1460, 778), 14, fill="#0B3D91")
    draw_text(draw, (1352, 638), "一体化\n评审闭环", size=25, fill="#FFFFFF", bold=True, line_gap=10)

    # Closed loop
    draw_text(draw, (140, 875), "平台闭环：赛前、赛中、赛后、运营", size=38, fill="#0B3D91", bold=True)
    loop_y = 958
    steps = [
        ("赛前准备", "PPT生成 / 素材证据 / 讲稿训练"),
        ("赛中评审", "在线会议 / 专家评分 / 录制留痕"),
        ("赛后复盘", "AI画像 / 评分报告 / 问题闭环"),
        ("持续运营", "后台治理 / 数据监控 / 私有化部署"),
    ]
    step_w, gap = 305, 28
    for i, (title, body) in enumerate(steps):
        x = 140 + i * (step_w + gap)
        rounded(draw, (x, loop_y, x + step_w, loop_y + 180), 12, fill="#F8FAFE", outline="#D6E2F2", width=2)
        draw_text(draw, (x + 24, loop_y + 28), title, size=28, fill="#071B46", bold=True)
        draw_text(draw, (x + 24, loop_y + 82), body, size=21, fill="#4B5B6D", max_chars=14, line_gap=8)
        if i < 3:
            ax = x + step_w + 5
            draw.line((ax, loop_y + 90, ax + 18, loop_y + 90), fill="#1A73E8", width=4)
            draw.polygon([(ax + 18, loop_y + 82), (ax + 34, loop_y + 90), (ax + 18, loop_y + 98)], fill="#1A73E8")

    # Ability map
    draw_text(draw, (140, 1240), "平台能力地图", size=38, fill="#0B3D91", bold=True)
    rounded(draw, (140, 1312, 1460, 1716), 16, fill="#FAFCFF", outline="#D8E3F0", width=2)
    center = (800, 1514)
    modules = [
        ((210, 1350, 520, 1458), "在线会议协同", "#EAF3FF"),
        ((1080, 1350, 1390, 1458), "专家评分评审", "#EAF3FF"),
        ((210, 1570, 520, 1678), "AI评分画像", "#EAFBF8"),
        ((1080, 1570, 1390, 1678), "PPT与讲稿", "#FFF7E6"),
        ((620, 1648, 980, 1698), "后台治理与交付", "#F5F7FA"),
    ]
    for box, title, fill in modules:
        x1, y1, x2, y2 = box
        draw.line((center[0], center[1], (x1 + x2) // 2, (y1 + y2) // 2), fill="#D8E2EE", width=3)
    for box, title, fill in modules:
        rounded(draw, box, 12, fill=fill, outline="#C9D8EA", width=2)
        x1, y1, x2, y2 = box
        draw_text(draw, (x1 + 28, y1 + 33), title, size=27, fill="#0B3D91", bold=True)
    rounded(draw, (642, 1432, 958, 1596), 18, fill="#0B3D91")
    draw_text(draw, (682, 1465), "OREP", size=42, fill="#FFFFFF", bold=True)
    draw_text(draw, (682, 1520), "数字评审基础设施", size=25, fill="#DBEAFE", bold=True)

    # Trust strip
    draw_text(draw, (140, 1818), "为什么可信", size=38, fill="#0B3D91", bold=True)
    trust = [
        ("流程可信", "会议、评分、问题、报告全链路留痕"),
        ("证据可信", "转写、语音、视觉、材料证据支撑反馈"),
        ("交付可信", "Spring Boot / Vue / FastAPI / LiveKit / Docker"),
    ]
    for i, (title, body) in enumerate(trust):
        x = 140 + i * 440
        rounded(draw, (x, 1890, x + 400, 2038), 12, fill="#FFFFFF", outline="#D8E3F0", width=2)
        draw_text(draw, (x + 26, 1918), title, size=27, fill="#071B46", bold=True)
        draw_text(draw, (x + 26, 1965), body, size=20, fill="#4B5B6D", max_chars=16, line_gap=8)

    draw.line((140, 2112, 1460, 2112), fill="#E4EAF3", width=2)
    draw_text(draw, (140, 2152), "会议协同 · 专家评分 · AI 画像 · PPT 智能生成 · 后台治理 · 私有化部署", size=23, fill="#64748B")
    draw_text(draw, (1245, 2152), "正式手册样张 v3", size=22, fill="#94A3B8")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, quality=95)
    print(OUT)


if __name__ == "__main__":
    main()
