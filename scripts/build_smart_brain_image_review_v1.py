from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs" / "product_brochure" / "image_review_v1"
ASSET_DIR = ROOT / "outputs" / "product_brochure" / "smart_brain_image2_assets"

W, H = 1600, 2264

FONT_REG = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"

NAVY = "#061B44"
BLUE = "#0B4DBA"
BRIGHT = "#1B7CFF"
CYAN = "#00A6FF"
INK = "#132238"
MUTED = "#637286"
LINE = "#D5E0EF"
SOFT = "#F5F8FC"
PALE = "#EAF3FF"
GREEN = "#0E7C70"
GOLD = "#B7791F"
WHITE = "#FDFEFF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def text(
    d: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    s: str,
    size: int,
    fill: str,
    bold: bool = False,
    max_chars: int | None = None,
    line_gap: int = 14,
) -> int:
    x, y = xy
    f = font(size, bold)
    lines: list[str] = []
    for para in s.split("\n"):
        if max_chars:
            while len(para) > max_chars:
                cut = max_chars
                for mark in "，。；、： ":
                    pos = para.rfind(mark, 0, max_chars + 1)
                    if pos > max_chars * 0.55:
                        cut = pos + 1
                        break
                lines.append(para[:cut])
                para = para[cut:]
        lines.append(para)
    for line in lines:
        d.text((x, y), line, font=f, fill=fill)
        box = d.textbbox((x, y), line or "口", font=f)
        y += box[3] - box[1] + line_gap
    return y


def rounded(d: ImageDraw.ImageDraw, box, r: int, fill: str, outline: str | None = None, width: int = 2) -> None:
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def crop_fill(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    tw, th = size
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    resized = img.resize((int(sw * scale), int(sh * scale)), Image.Resampling.LANCZOS)
    x = (resized.width - tw) // 2
    y = (resized.height - th) // 2
    return resized.crop((x, y, x + tw, y + th))


def page_base(index: str, title: str, lead: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img, "RGBA")
    text(d, (135, 90), "智慧大脑 Product Brochure", 28, "#6B778A", True)
    text(d, (135, 195), index, 34, BRIGHT, True)
    text(d, (135, 280), title, 72, NAVY, True)
    text(d, (135, 405), lead, 36, MUTED, False, max_chars=34, line_gap=16)
    d.line((135, H - 120, W - 135, H - 120), fill="#E7EEF7", width=2)
    text(d, (W - 400, H - 88), "PNG 审核稿 V1  |  2026", 24, "#7F8DA0", True)
    return img, d


def paste_image(img: Image.Image, path: Path, box: tuple[int, int, int, int], brightness: float = 1.0) -> None:
    src = Image.open(path).convert("RGB")
    src = crop_fill(src, (box[2] - box[0], box[3] - box[1]))
    if brightness != 1.0:
        src = ImageEnhance.Brightness(src).enhance(brightness)
    img.paste(src, (box[0], box[1]))


def card(d, box, title, body, color=BLUE, title_size=34, body_size=25, max_chars=20):
    rounded(d, box, 24, "#FFFFFF", LINE, 3)
    x1, y1, x2, y2 = box
    d.rectangle((x1, y1, x1 + 12, y2), fill=color)
    text(d, (x1 + 42, y1 + 34), title, title_size, color, True)
    text(d, (x1 + 42, y1 + 90), body, body_size, INK, False, max_chars=max_chars, line_gap=10)


def cover() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    paste_image(img, ASSET_DIR / "ai_hero_brain.png", (220, 0, W, 1240), 0.72)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, W, H), fill=(6, 27, 68, 70))
    d.rectangle((0, 1130, W, H), fill=(6, 27, 68, 255))
    d.rectangle((0, 0, 160, H), fill=(8, 38, 95, 255))
    d.rectangle((160, 0, 206, H), fill=(27, 124, 255, 255))
    rounded(d, (270, 160, 640, 225), 20, "#092B68", BRIGHT, 2)
    text(d, (302, 178), "SMART BRAIN", 30, CYAN, True)
    text(d, (270, 350), "智慧大脑", 116, "#FFFFFF", True)
    text(d, (275, 525), "创新创业路演评审与成长训练平台", 45, "#DCEBFF", True)
    text(d, (275, 690), "让每一次路演都成为下一次成长的证据", 50, "#FFFFFF", True)
    text(
        d,
        (275, 830),
        "把路演评审、AI 复盘、21 天训练、考试测评和能力档案连接起来，让组织方看见成长，让学生知道下一轮怎么变得更好。",
        34,
        "#BED7FF",
        False,
        max_chars=30,
        line_gap=16,
    )
    for i, (title, body) in enumerate([
        ("可评审", "标准化组织一次路演"),
        ("可复盘", "把反馈变成证据"),
        ("可训练", "把建议变成每日行动"),
        ("可认证", "把成长沉淀为档案"),
    ]):
        x = 270 + (i % 2) * 520
        y = 1450 + (i // 2) * 220
        rounded(d, (x, y, x + 450, y + 150), 28, "#0C347A", "#2B65C9", 3)
        text(d, (x + 38, y + 32), title, 40, CYAN, True)
        text(d, (x + 38, y + 94), body, 27, "#DCEBFF")
    text(d, (270, 2120), "产品介绍手册审核稿  |  先看图像方向，确认后转可编辑版", 27, "#90ACD8", True)
    return img


def page_why() -> Image.Image:
    img, d = page_base("01", "客户真正会记住什么", "客户不会记住一堆功能名，但会记住这个平台让他们成为什么样的人。")
    rounded(d, (135, 560, W - 135, 800), 30, PALE, "#BFD5F4", 3)
    text(d, (185, 610), "品牌主张", 38, BLUE, True)
    text(
        d,
        (185, 680),
        "智慧大脑不卖“更多系统”，而是帮助学校、赛事和园区把一次路演变成一套持续成长机制。",
        34,
        INK,
        False,
        max_chars=39,
        line_gap=16,
    )
    card(d, (135, 900, 720, 1135), "组织方", "不只是办完一场比赛，而是沉淀一套可复用的评审资产。", BLUE)
    card(d, (780, 900, 1465, 1135), "学生团队", "不只是拿到一个分数，而是知道下一轮该怎么改、怎么练。", GREEN)
    card(d, (135, 1210, 720, 1445), "评委教师", "不只是提交评分，而是把经验转化为可追溯、可复盘的反馈。", GOLD)
    card(d, (780, 1210, 1465, 1445), "技术采购", "不只是上线工具，而是获得私有部署、权限、数据治理的可信基础。", BLUE)
    rounded(d, (135, 1580, 1465, 1835), 26, "#FFFFFF", "#174B9D", 3)
    d.rectangle((135, 1580, 1465, 1645), fill="#144B9E")
    text(d, (180, 1596), "宣传册不应该主讲", 28, "#FFFFFF", True)
    text(d, (840, 1596), "宣传册应该主讲", 28, "#FFFFFF", True)
    text(d, (180, 1690), "技术栈、接口、数据库、后台菜单、功能清单。", 30, INK)
    text(d, (840, 1690), "评审如何留下证据，反馈如何转成行动，成长如何被看见。", 30, INK, max_chars=20)
    return img


def page_loop() -> Image.Image:
    img, d = page_base("02", "一张图看懂智慧大脑", "把评审、复盘、训练、测评和档案连成一个成长飞轮。")
    paste_image(img, ASSET_DIR / "ai_growth_loop.png", (160, 545, 1440, 1240), 1.0)
    center = (800, 1420)
    d.ellipse((center[0] - 170, center[1] - 170, center[0] + 170, center[1] + 170), fill="#EAF3FF", outline="#BFD5F4", width=4)
    text(d, (704, 1362), "成长飞轮", 48, NAVY, True)
    text(d, (676, 1438), "评审不是终点", 30, BLUE, True)
    steps = [
        ("赛前准备", "材料、讲稿、评分点"),
        ("在线路演", "会议、评分、录制留痕"),
        ("AI 复盘", "报告、问题、训练建议"),
        ("21 天训练", "课程、任务、考试"),
        ("能力档案", "雷达、趋势、证书"),
    ]
    positions = [(135, 1310), (1030, 1310), (1080, 1645), (550, 1780), (85, 1645)]
    colors = [BLUE, GREEN, GOLD, BLUE, GREEN]
    for (title, body), (x, y), c in zip(steps, positions, colors):
        card(d, (x, y, x + 385, y + 165), title, body, c, 30, 24, 13)
    return img


def page_training() -> Image.Image:
    img, d = page_base("03", "21 天训练让反馈落地", "把抽象建议拆成每天可完成、可记录、可验证的训练动作。")
    paste_image(img, ASSET_DIR / "ai_21day_journey.png", (135, 540, 1465, 1248), 1.0)
    items = [
        ("第 1 步", "理解问题", "查看 AI 复盘报告，明确短板与训练目标。"),
        ("第 2 步", "补齐基础", "课程学习、资源阅读、每日任务提交。"),
        ("第 3 步", "强化表达", "讲稿训练、打字速度、演示节奏优化。"),
        ("第 4 步", "验证成果", "在线考试、团队评分、能力档案更新。"),
    ]
    for i, (num, title, body) in enumerate(items):
        x = 135 + i * 340
        rounded(d, (x, 1360, x + 305, 1685), 30, "#FFFFFF", LINE, 3)
        text(d, (x + 34, 1404), num, 28, BRIGHT, True)
        text(d, (x + 34, 1462), title, 38, [BLUE, GREEN, GOLD, BLUE][i], True)
        text(d, (x + 34, 1535), body, 25, INK, False, max_chars=10, line_gap=12)
    rounded(d, (135, 1810, 1465, 1965), 26, PALE, "#BFD5F4", 3)
    text(d, (180, 1850), "买方听得懂的表达", 34, BLUE, True)
    text(d, (520, 1850), "训练平台不是课程后台，而是把评审反馈落到每天行动，并把成长结果重新验证的承接系统。", 30, INK, max_chars=32)
    return img


def page_profile() -> Image.Image:
    img, d = page_base("04", "能力档案让成长被看见", "学生、教师和组织方看到的不再只是一个分数，而是一条成长轨迹。")
    paste_image(img, ASSET_DIR / "ai_dashboard.png", (135, 520, 1465, 1185), 1.0)
    labels = [
        ("六维雷达", "解决问题、代码、沟通、团队协作、演讲、创意。", BLUE),
        ("评分趋势", "路演总分与历史评分变化，观察团队表现。", GREEN),
        ("证书认证", "证书模板、颁发、查看与下载，沉淀学习成果。", GOLD),
        ("组织运营", "用户、部门、课程、资源、权限和日志统一管理。", BLUE),
    ]
    for i, (title, body, c) in enumerate(labels):
        x = 135 + (i % 2) * 665
        y = 1290 + (i // 2) * 245
        card(d, (x, y, x + 625, y + 190), title, body, c, 34, 26, 19)
    rounded(d, (135, 1830, 1465, 1988), 26, "#FFFFFF", "#174B9D", 3)
    text(d, (180, 1872), "一句话卖点", 34, BLUE, True)
    text(d, (450, 1872), "智慧大脑让每一次路演留下来的问题、证据和反馈，沉淀成可训练、可复盘、可认证的成长资产。", 30, INK, max_chars=33)
    return img


def page_scenes() -> Image.Image:
    img, d = page_base("05", "谁会需要智慧大脑", "同一套成长闭环，可以服务赛事、课程、园区和训练营。")
    rows = [
        ("创新创业大赛", "赛前准备、在线路演、专家评审、赛后训练", "比赛不是终点，而是下一轮成长的起点"),
        ("课程答辩", "教师创建任务，学生演示，系统沉淀评分与问题", "教学评价可追溯，改进动作可跟踪"),
        ("校内训练营", "多轮路演结合 21 天训练和考试测评", "训练过程被看见，能力变化被证明"),
        ("园区/孵化器", "项目材料打磨、专家评审和成长档案", "项目服务从一次辅导升级为持续陪跑"),
    ]
    y = 575
    for i, (scene, use, value) in enumerate(rows):
        rounded(d, (135, y, 1465, y + 255), 28, "#FFFFFF" if i % 2 else "#F7FAFE", LINE, 3)
        text(d, (185, y + 52), scene, 38, BLUE if i != 3 else GREEN, True)
        text(d, (540, y + 45), "使用方式", 26, "#8090A6", True)
        text(d, (540, y + 92), use, 30, INK, False, max_chars=22)
        text(d, (1030, y + 45), "用户记住什么", 26, "#8090A6", True)
        text(d, (1030, y + 92), value, 30, INK, False, max_chars=15)
        y += 295
    rounded(d, (135, 1808, 1465, 1995), 28, PALE, "#BFD5F4", 3)
    text(d, (185, 1856), "可信边界", 34, BLUE, True)
    text(d, (430, 1856), "主册只讲私有部署、权限治理、数据留痕、多端访问和内容质量保障；详细技术路线放入技术白皮书。", 30, INK, max_chars=36)
    return img


def page_next() -> Image.Image:
    img = Image.new("RGB", (W, H), NAVY)
    paste_image(img, ASSET_DIR / "ai_dashboard.png", (0, 0, W, 1000), 0.58)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((0, 0, W, 1000), fill=(6, 27, 68, 120))
    d.rectangle((0, 850, W, H), fill=(6, 27, 68, 255))
    text(d, (190, 300), "从一次路演", 88, "#FFFFFF", True)
    text(d, (190, 455), "到一套持续成长机制", 88, "#FFFFFF", True)
    text(
        d,
        (195, 1040),
        "智慧大脑不是多一个系统，而是把每一次评审留下来的问题、证据和反馈，转化为可训练、可复盘、可认证的成长资产。",
        40,
        "#DCEBFF",
        False,
        max_chars=30,
        line_gap=18,
    )
    steps = [
        ("1. 选场景", "选择一场创新创业比赛、课程答辩或训练营。"),
        ("2. 跑评审", "完成材料准备、在线路演、专家评分和复盘报告。"),
        ("3. 接训练", "把复盘建议接入 21 天训练任务、课程和测评。"),
        ("4. 沉档案", "查看能力雷达、趋势、证书和组织数据。"),
    ]
    for i, (title, body) in enumerate(steps):
        x = 195 + (i % 2) * 615
        y = 1370 + (i // 2) * 225
        rounded(d, (x, y, x + 540, y + 155), 28, "#FFFFFF", "#C7D7EF", 3)
        text(d, (x + 38, y + 30), title, 34, BLUE, True)
        text(d, (x + 38, y + 88), body, 25, INK, False, max_chars=18)
    text(d, (195, 2055), "适用于：高校创新创业学院、赛事承办方、园区/孵化器、课程答辩与项目训练营", 30, "#AFC8EC", False)
    return img


def contact_sheet(paths: list[Path]) -> None:
    cols = 3
    thumb_w, thumb_h = 360, 520
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "#EEF3F8")
    d = ImageDraw.Draw(sheet)
    for i, path in enumerate(paths):
        im = Image.open(path).convert("RGB")
        im.thumbnail((320, 455))
        x = (i % cols) * thumb_w + (thumb_w - im.width) // 2
        y = (i // cols) * thumb_h + 20
        sheet.paste(im, (x, y))
        d.text(((i % cols) * thumb_w + 20, (i // cols) * thumb_h + 485), path.stem, fill=(30, 50, 80))
    sheet.save(OUT_DIR / "00_整册缩略预览.png")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = [
        ("01_封面.png", cover()),
        ("02_客户记住什么.png", page_why()),
        ("03_成长飞轮.png", page_loop()),
        ("04_21天训练.png", page_training()),
        ("05_能力档案.png", page_profile()),
        ("06_场景与落地.png", page_scenes()),
        ("07_下一步.png", page_next()),
    ]
    paths = []
    for name, im in pages:
        path = OUT_DIR / name
        im.save(path)
        paths.append(path)
    contact_sheet(paths)
    print(OUT_DIR)


if __name__ == "__main__":
    main()
