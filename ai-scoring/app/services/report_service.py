"""
PDF 报告生成器 — 咨询风板式（对齐「笔墨传妆完整版」）
海军蓝章节徽章 · 左栏提示 · 双栏卡片 · 深表头 · 行动 #N 卡
使用 reportlab 生成
"""
import json
import os
import re
from datetime import datetime

from reportlab.lib import colors
HexColor = colors.HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Image, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont

# ── 注册中文字体 ──
_SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SERVICE_DIR, '..', '..'))


def _font_candidates():
    shared_override = os.getenv('OREP_PDF_FONT_PATH')
    regular_override = os.getenv('OREP_REPORT_FONT_REGULAR')
    bold_override = os.getenv('OREP_REPORT_FONT_BOLD')
    if shared_override:
        yield shared_override, bold_override or shared_override
    if regular_override:
        yield regular_override, bold_override or regular_override

    # Prefer locally bundled fonts when present, then common Linux/macOS/Windows
    # CJK fonts.  ReportLab silently falls back to Helvetica when no CJK font is
    # registered, which makes Chinese text render as boxes in the final PDF.
    yield os.path.join(_PROJECT_ROOT, 'assets', 'fonts', 'NotoSansCJKsc-Regular.otf'), os.path.join(_PROJECT_ROOT, 'assets', 'fonts', 'NotoSansCJKsc-Bold.otf')
    yield os.path.join(_PROJECT_ROOT, 'fonts', 'NotoSansCJKsc-Regular.otf'), os.path.join(_PROJECT_ROOT, 'fonts', 'NotoSansCJKsc-Bold.otf')
    yield '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
    yield '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf', '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Bold.otf'
    yield '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc'
    yield '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
    yield '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
    yield '/System/Library/Fonts/STHeiti Light.ttc', '/System/Library/Fonts/STHeiti Medium.ttc'
    yield '/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/PingFang.ttc'
    yield '/System/Library/Fonts/Supplemental/Songti.ttc', '/System/Library/Fonts/Supplemental/Songti.ttc'
    yield '/Library/Fonts/Arial Unicode.ttf', '/Library/Fonts/Arial Unicode.ttf'
    yield 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/msyhbd.ttc'
    yield 'C:/Windows/Fonts/simsun.ttc', 'C:/Windows/Fonts/simsun.ttc'


def _try_register_ttf(alias: str, font_path: str, subfont_index: int = 0) -> bool:
    if not font_path or not os.path.exists(font_path):
        return False
    try:
        kwargs = {'subfontIndex': subfont_index} if font_path.lower().endswith('.ttc') else {}
        pdfmetrics.registerFont(TTFont(alias, font_path, **kwargs))
        return True
    except Exception:
        return False


def _register_report_fonts():
    for regular_path, bold_path in _font_candidates():
        if not _try_register_ttf('CnFont', regular_path, 0):
            continue
        bold_registered = _try_register_ttf('CnFontBold', bold_path, 0)
        if not bold_registered and regular_path.lower().endswith('.ttc'):
            bold_registered = _try_register_ttf('CnFontBold', regular_path, 1)
        if not bold_registered:
            bold_registered = _try_register_ttf('CnFontBold', regular_path, 0)
        if bold_registered:
            registerFontFamily(
                'CnFont',
                normal='CnFont',
                bold='CnFontBold',
                italic='CnFont',
                boldItalic='CnFontBold',
            )
            print(f'[PdfReport] 使用中文字体: {regular_path}')
            return 'CnFont', 'CnFontBold'

    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        registerFontFamily(
            'STSong-Light',
            normal='STSong-Light',
            bold='STSong-Light',
            italic='STSong-Light',
            boldItalic='STSong-Light',
        )
        print('[PdfReport] 未找到可嵌入中文字体，已使用内置中文字体。建议配置 OREP_PDF_FONT_PATH。')
        return 'STSong-Light', 'STSong-Light'
    except Exception:
        print('[PdfReport] 未找到中文字体，PDF 中文可能无法正常显示。')
        return 'Helvetica', 'Helvetica-Bold'


_CN_FONT, _CN_FONT_BOLD = _register_report_fonts()

# ── 品牌（对外统一竞赛大脑；公司署名启发教育科技） ──
BRAND_PRODUCT = '竞赛大脑'
BRAND_COMPANY = '启发教育科技有限公司'
BRAND_WEBSITE = 'https://www.jingsaidanao.com'
BRAND_REPORT_TITLE = f'{BRAND_PRODUCT} · 路演评分报告'
BRAND_MODEL_NAME = f'{BRAND_PRODUCT}官方五维评分模型'


def _brand_logo_path() -> str | None:
    candidates = [
        os.path.join(_PROJECT_ROOT, 'assets', 'brand', 'competition-brain-logo.svg'),
        os.path.join(_PROJECT_ROOT, 'assets', 'brand', 'competition-brain-logo.png'),
        os.path.join(os.path.dirname(_PROJECT_ROOT), 'frontend', 'user', 'public', 'brand', 'competition-brain-logo.svg'),
        os.getenv('OREP_REPORT_LOGO_PATH') or '',
        os.path.join(_PROJECT_ROOT, 'assets', 'brand', 'qifa-jixue-logo.png'),
        os.path.join(settings_upload_brand_fallback(), 'qifa-jixue-logo.png'),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def settings_upload_brand_fallback() -> str:
    try:
        from app.config import settings
        return os.path.join(getattr(settings, 'UPLOAD_DIR', '/app/uploads'), 'brand')
    except Exception:
        return os.path.join(_PROJECT_ROOT, 'uploads', 'brand')


class _SectionCounter:
    """按实际渲染顺序生成 01/02/…，避免条件章节导致序号错乱。"""

    def __init__(self):
        self.n = 0

    def next(self) -> str:
        self.n += 1
        return f'{self.n:02d}'


def _jury_enabled(result: dict) -> bool:
    return bool(result.get('jury_enabled') or result.get('juryEnabled'))


def _normalize_jury_session_to_package(session: dict) -> dict | None:
    """把 jury_session_*.json 规范成 PDF 用的评审团包（members + score_cards + 汇总）。"""
    if not isinstance(session, dict):
        return None
    status = str(session.get('status') or '').lower()
    reports = session.get('judge_reports') or []
    members_raw = session.get('members') or []
    aggregate = session.get('aggregate') if isinstance(session.get('aggregate'), dict) else {}
    if not reports and not members_raw and not aggregate:
        return None
    # 未完成且无任何有效报告时不渲染
    successful = [
        r for r in reports
        if isinstance(r, dict) and r.get('status') == 'completed' and r.get('overall_score') is not None
    ]
    if not successful and status not in ('completed', 'done', 'success', ''):
        if not aggregate.get('trimmed_average_score') and not aggregate.get('raw_average_score'):
            return None

    reports_by_code = {
        str(r.get('persona_code') or r.get('code') or ''): r
        for r in reports if isinstance(r, dict)
    }
    members = []
    for m in members_raw:
        if not isinstance(m, dict):
            continue
        code = str(m.get('code') or m.get('persona_code') or '')
        members.append({
            'code': code,
            'seat_no': m.get('seat_no') or m.get('member_id'),
            'role_label': m.get('role_label') or m.get('name') or m.get('display_name') or code,
            'name': m.get('name') or m.get('display_name') or '',
            'focus_dimensions': m.get('focus_dimensions') or m.get('rubric_focus') or [],
            'short_label': m.get('short_label') or '',
        })

    score_cards = []
    for r in reports:
        if not isinstance(r, dict):
            continue
        if r.get('status') and r.get('status') != 'completed':
            continue
        code = str(r.get('persona_code') or r.get('code') or '')
        view = r.get('persona_view') if isinstance(r.get('persona_view'), dict) else {}
        concerns = view.get('top_concerns') or r.get('critical_issues') or []
        if isinstance(concerns, str):
            concerns = [concerns]
        comment = (
            _value_text(r.get('summary') or r.get('comment'))
            or (str(concerns[0]) if concerns else '')
            or _value_text((r.get('highlights') or [None])[0] if isinstance(r.get('highlights'), list) else '')
        )
        # 评委短评：认可 + 担忧
        recognition = _value_text(view.get('recognition') or '')
        concern_txt = _value_text(view.get('concern') or (concerns[0] if concerns else ''))
        if recognition or concern_txt:
            parts = []
            if recognition:
                parts.append(f'认可：{recognition}')
            if concern_txt:
                parts.append(f'担忧：{concern_txt}')
            if comment and comment not in concern_txt:
                parts.append(comment)
            comment = ' '.join(parts) if parts else comment
        member = next((m for m in members if m.get('code') == code), {})
        role_label = r.get('role_label') or r.get('persona_name') or member.get('role_label') or ''
        if re.fullmatch(r'[A-Z]{4}', str(role_label or '')):
            role_label = '评委'
        score_cards.append({
            'code': code,
            'judge_code': code,
            'role_label': role_label or '评委',
            'overall_score': r.get('overall_score') if r.get('overall_score') is not None else r.get('score'),
            'score': r.get('overall_score') if r.get('overall_score') is not None else r.get('score'),
            'top_concerns': list(concerns)[:4] if concerns else [],
            'short_label': member.get('short_label') or '',
            'focus': member.get('short_label') or _value_text(view.get('rubric_focus') or ''),
            'highlights': [x for x in (r.get('highlights') or []) if x][:4],
            'critical_issues': [x for x in (r.get('critical_issues') or concerns or []) if x][:4],
            'improvement_priorities': [
                x for x in (r.get('improvement_priorities') or []) if x
            ][:4],
            'persona_view': view,
            'score_reasoning_style': _value_text(view.get('score_reasoning_style') or ''),
            'optimization_angle': _value_text(view.get('optimization_angle') or ''),
            'comment': comment,
            'summary': comment,
            'dimensions': r.get('dimensions') or {},
            'status': r.get('status') or 'completed',
        })

    # 若只有 members 无 reports，不造假分
    judge_count = (
        session.get('judge_count')
        or aggregate.get('judge_count')
        or len(score_cards)
        or len(members)
    )
    pkg = {
        'judge_count': judge_count,
        'members': members,
        'score_cards': score_cards,
        'reviews': score_cards,
        'dimension_stats': aggregate.get('dimension_stats') or [],
        'consensus_issues': aggregate.get('consensus_issues') or [],
        'raw_average_score': aggregate.get('raw_average_score') or session.get('jury_raw_avg'),
        'trimmed_average_score': (
            aggregate.get('trimmed_average_score')
            or session.get('jury_trimmed_avg')
        ),
        'trimmed_total_score': aggregate.get('trimmed_total_score'),
        'highest_score': aggregate.get('highest_score'),
        'lowest_score': aggregate.get('lowest_score'),
        'score_diff_from_official': (
            aggregate.get('score_diff_from_official')
            or session.get('score_diff_from_official')
        ),
        'official_score': session.get('official_score'),
        'status': session.get('status') or 'completed',
        'jury_session_id': session.get('jury_session_id'),
        'meeting_id': session.get('meeting_id'),
    }
    if not pkg['score_cards'] and not pkg['members'] and pkg['trimmed_average_score'] is None:
        return None
    return pkg


def _load_jury_session_from_disk(meeting_id: str) -> dict | None:
    """从 uploads/results/jury 加载本场真实评审团会话。"""
    if not meeting_id and meeting_id != 0:
        return None
    mid = str(meeting_id).strip()
    if not mid:
        return None
    try:
        from app.services.jury.scoring_service import get_latest_jury_session
        session = get_latest_jury_session(mid)
        if isinstance(session, dict) and session.get('status') == 'completed':
            return session
        if isinstance(session, dict) and (session.get('judge_reports') or session.get('aggregate')):
            return session
    except Exception:
        pass
    # 直接读文件（rerender / 无完整依赖时）
    upload_dir = os.getenv('UPLOAD_DIR') or ''
    if not upload_dir:
        try:
            from app.config import settings
            upload_dir = getattr(settings, 'UPLOAD_DIR', '/app/uploads')
        except Exception:
            upload_dir = '/app/uploads'
    jury_dir = os.path.join(upload_dir, 'results', 'jury')
    latest = os.path.join(jury_dir, f'latest_jury_{mid}.json')
    if not os.path.isfile(latest):
        return None
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            index = json.load(f)
        session_id = index.get('jury_session_id')
        if not session_id:
            return None
        sp = os.path.join(jury_dir, f'jury_session_{session_id}.json')
        if not os.path.isfile(sp):
            return None
        with open(sp, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _real_jury_package(result: dict) -> dict | None:
    """仅使用真实评审团结果；禁止 LLM 生成的 ai_score.jury_review 冒充。

    数据优先级：
    1) result 上已挂载的 jury / ai_jury / jury_summary
    2) 磁盘 jury_session（web 端同款来源）
    """
    if not _jury_enabled(result):
        return None
    for key in ('jury_summary', 'ai_jury', 'jury'):
        pkg = result.get(key)
        if isinstance(pkg, dict) and (
            pkg.get('members') or pkg.get('score_cards') or pkg.get('reviews') or pkg.get('judge_count')
            or pkg.get('trimmed_average_score') is not None
        ):
            # 若只有均分无 cards，仍返回（后续章节可展示汇总）
            if pkg.get('score_cards') or pkg.get('reviews') or pkg.get('members'):
                return pkg
            # 规范化浅包
            if pkg.get('trimmed_average_score') is not None or pkg.get('raw_average_score') is not None:
                return pkg
    # 从磁盘加载本场评审团
    mid = result.get('meeting_id') or result.get('session_id') or result.get('sessionId')
    session = _load_jury_session_from_disk(mid)
    if not session:
        return None
    return _normalize_jury_session_to_package(session)


def _attach_jury_package(result: dict) -> dict:
    """确保 result 上挂有真实评审团包，供封面类型与各章节使用。"""
    if not isinstance(result, dict):
        return result
    if not _jury_enabled(result):
        return result
    existing = None
    for key in ('jury_summary', 'ai_jury', 'jury'):
        pkg = result.get(key)
        if isinstance(pkg, dict) and (pkg.get('score_cards') or pkg.get('members') or pkg.get('reviews')):
            existing = pkg
            break
    if existing:
        return result
    pkg = _real_jury_package(result)
    if not pkg:
        return result
    out = dict(result)
    out['jury'] = pkg
    out['jury_summary'] = pkg
    return out


# ── 设计系统（对齐笔墨传妆完整版：海军蓝 + 大量留白 + 深表头） ──
BLACK = colors.HexColor('#0F172A')
DARK = colors.HexColor('#0F172A')
NAVY = colors.HexColor('#0F172A')
NAVY_SOFT = colors.HexColor('#1E293B')
GRAY_900 = colors.HexColor('#1E293B')
GRAY_700 = colors.HexColor('#475569')
GRAY_500 = colors.HexColor('#94A3B8')
GRAY_400 = colors.HexColor('#CBD5E1')
GRAY_300 = colors.HexColor('#E2E8F0')
GRAY_100 = colors.HexColor('#F1F5F9')
GRAY_50 = colors.HexColor('#F8FAFC')
WHITE = colors.HexColor('#FFFFFF')
# 主色改为海军蓝（参考板式）；橙仅作品牌点缀必要时使用
ACCENT = colors.HexColor('#0F172A')
ACCENT_DARK = colors.HexColor('#0F172A')
SUCCESS = colors.HexColor('#16A34A')
SUCCESS_BG = colors.HexColor('#F0FDF4')
SUCCESS_BORDER = colors.HexColor('#BBF7D0')
WARNING = colors.HexColor('#EA580C')
DANGER = colors.HexColor('#DC2626')
DANGER_BG = colors.HexColor('#FEF2F2')
DANGER_BORDER = colors.HexColor('#FECACA')
TIP_BG = colors.HexColor('#F8FAFC')
TIP_BAR = colors.HexColor('#94A3B8')

# 章节英文副标题（与参考 PDF 一致）
_SECTION_EN = {
    '评分总览': 'Score Overview',
    '证据摘要': 'Evidence Summary',
    '维度详情': 'Dimension Details',
    '语音表达': 'Voice Expression',
    '亮点与关键问题': 'Highlights & Key Issues',
    '评审团独立评审': 'Independent Jury Review',
    '音视频融合分析': 'Audio-Video Fusion',
    '路演结构对标分析': 'Pitch Structure Benchmark',
    '综合改进行动计划': 'Action Plan',
    '团队分工优化路线图': 'Team Optimization Roadmap',
    '选手角色与能力画像': 'Character Profile',
    '综合结论': 'Final Verdict',
    '证据补强清单': 'Evidence Checklist',
}


def _styles():
    """咨询风板式：干净层级、深表头、左栏提示。"""
    s = {}

    s['cover_title'] = ParagraphStyle(
        'CoverTitle', fontName=_CN_FONT_BOLD, fontSize=28, leading=36,
        alignment=TA_CENTER, spaceAfter=10, textColor=NAVY,
    )
    s['cover_subtitle'] = ParagraphStyle(
        'CoverSubtitle', fontName=_CN_FONT, fontSize=11, leading=16,
        alignment=TA_CENTER, spaceAfter=6, textColor=GRAY_700,
    )
    s['cover_label'] = ParagraphStyle(
        'CoverLabel', fontName=_CN_FONT, fontSize=9, leading=14,
        alignment=TA_LEFT, spaceAfter=2, textColor=GRAY_500,
    )
    s['section_num'] = ParagraphStyle(
        'SectionNum', fontName=_CN_FONT_BOLD, fontSize=11, leading=14,
        alignment=TA_CENTER, textColor=WHITE,
    )
    s['section_title'] = ParagraphStyle(
        'SectionTitle', fontName=_CN_FONT_BOLD, fontSize=16, leading=22,
        spaceBefore=0, spaceAfter=0, textColor=NAVY,
    )
    s['section_en'] = ParagraphStyle(
        'SectionEn', fontName=_CN_FONT, fontSize=9, leading=12,
        textColor=GRAY_500,
    )
    s['section_desc'] = ParagraphStyle(
        'SectionDesc', fontName=_CN_FONT, fontSize=9, leading=13.5,
        spaceAfter=0, textColor=GRAY_700,
    )
    s['h2'] = ParagraphStyle(
        'H2', fontName=_CN_FONT_BOLD, fontSize=11.5, leading=16,
        spaceBefore=10, spaceAfter=5, textColor=NAVY,
    )
    s['body'] = ParagraphStyle(
        'Body', fontName=_CN_FONT, fontSize=9.5, leading=14.5,
        alignment=TA_LEFT, spaceAfter=4, textColor=GRAY_900,
    )
    s['body_small'] = ParagraphStyle(
        'BodySmall', fontName=_CN_FONT, fontSize=8.5, leading=12.5,
        textColor=GRAY_700,
    )
    s['bullet'] = ParagraphStyle(
        'Bullet', fontName=_CN_FONT, fontSize=9, leading=13.5,
        leftIndent=10, bulletIndent=0, spaceAfter=3, textColor=GRAY_900,
    )
    s['mono'] = ParagraphStyle(
        'Mono', fontName='Courier', fontSize=8.5, leading=12, textColor=GRAY_700,
    )
    s['caption'] = ParagraphStyle(
        'Caption', fontName=_CN_FONT, fontSize=7.5, leading=10.5,
        textColor=GRAY_500, alignment=TA_LEFT,
    )
    return s


# ════════════════════════════════════════
#  工具函数
# ════════════════════════════════════════

def _draw_divider(width=16.5*cm):
    """极细分隔线"""
    from reportlab.graphics.shapes import Drawing, Line
    d = Drawing(width, 4)
    d.add(Line(0, 2, width, 2, strokeColor=GRAY_300, strokeWidth=0.5))
    return d


def _score_text(score, max_score=100):
    """分数文案：不再用 █░（中文字体常渲染成空方块，显得像坏掉的 PDF）"""
    try:
        sc = float(score or 0)
        mx = float(max_score or 0)
    except Exception:
        sc, mx = 0.0, 0.0
    if mx > 0:
        pct = int(round(sc / mx * 100))
        return f'<font color="#212121"><b>{sc:g}</b></font><font color="#9E9E9E"> / {mx:g}</font>  <font color="#616161">{pct}%</font>'
    return f'<font color="#212121"><b>{sc:g}</b></font>'


def _score_bar_table(score, max_score, width_cm=4.2):
    """海军蓝进度条（参考板式：单色填充 + 浅轨）。"""
    try:
        sc = float(score or 0)
        mx = float(max_score or 0)
    except Exception:
        sc, mx = 0.0, 0.0
    ratio = max(0.0, min(1.0, sc / mx if mx > 0 else 0.0))
    fill_w = max(0.08, width_cm * ratio) * cm
    empty_w = max(0.01, width_cm * cm - fill_w)
    t = Table([['', '']], colWidths=[fill_w, empty_w], rowHeights=[0.22 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), NAVY),
        ('BACKGROUND', (1, 0), (1, 0), GRAY_100),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


# 版心宽：A4 左右边距 2cm → 约 17cm，统一 16.5 避免表格溢出变形
CONTENT_W = 16.5


def _para(text: str, style: ParagraphStyle) -> Paragraph:
    """统一 Paragraph：CJK 换行。只改「 A / B 」式分隔，绝不碰 HTML 标签里的 /。"""
    t = _clean_inline(text)
    # 仅替换两侧有空格的斜杠，避免把 </b> 弄坏
    t = re.sub(r'\s+/\s+', '、', t)
    return Paragraph(t, style)


def _callout_box(text: str, s, width_cm: float = CONTENT_W) -> Table:
    """左海军蓝竖条 + 浅底提示块（宽度与版心一致，避免右缘裁切换行）。"""
    body = _para(text, ParagraphStyle(
        'CalloutBody', parent=s['body'], fontSize=9, leading=13.5, textColor=GRAY_900,
        wordWrap='CJK',
    ))
    # 左竖条用独立窄列，正文占满剩余宽度
    bar = Table([['']], colWidths=[0.12 * cm], rowHeights=[0.1 * cm])
    bar.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    body_cell = Table([[body]], colWidths=[(width_cm - 0.35) * cm])
    body_cell.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    wrap = Table([[bar, body_cell]], colWidths=[0.22 * cm, (width_cm - 0.22) * cm])
    wrap.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BACKGROUND', (0, 0), (0, 0), NAVY),
    ]))
    return wrap


def _side_card(text: str, tone: str, s, width_cm: float = 7.4) -> Table:
    """双栏证据卡：绿/红左边 + 浅底。"""
    if tone == 'good':
        bar, bg, border = SUCCESS, SUCCESS_BG, SUCCESS_BORDER
    else:
        bar, bg, border = DANGER, DANGER_BG, DANGER_BORDER
    body = Paragraph(_clean_inline(text), ParagraphStyle(
        f'SideCard{tone}', parent=s['body_small'], fontSize=8.5, leading=12.5, textColor=GRAY_900,
    ))
    card = Table([[body]], colWidths=[width_cm * cm])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 0.4, border),
        ('LINEBEFORE', (0, 0), (0, -1), 2.8, bar),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return card


def _priority_pill(priority: str) -> Table:
    """P0/P1/P2 小胶囊。"""
    p = str(priority or '—').upper()
    if p in ('P0', 'HIGH'):
        bg, fg = HexColor('#FEE2E2'), HexColor('#B91C1C')
    elif p in ('P1', 'MEDIUM'):
        bg, fg = HexColor('#FFEDD5'), HexColor('#C2410C')
    else:
        bg, fg = HexColor('#DCFCE7'), HexColor('#15803D')
    cell = Paragraph(f'<b>{_clean_inline(p)}</b>', ParagraphStyle(
        'PriPill', fontName=_CN_FONT_BOLD, fontSize=8, leading=10,
        textColor=fg, alignment=TA_CENTER,
    ))
    t = Table([[cell]], colWidths=[1.15 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _tag_row(label: str, tags: list[str], tone: str, s) -> Table:
    """亮点/关键问题标签行（左色条 + 短标签串联）。"""
    if tone == 'good':
        bar, bg = SUCCESS, SUCCESS_BG
    else:
        bar, bg = DANGER, DANGER_BG
    body = Paragraph(
        f'<b>{_clean_inline(label)}</b>  '
        + '  ·  '.join(_clean_inline(_value_text(t)[:22]) for t in tags[:6]),
        ParagraphStyle(
            f'TagRow{tone}', parent=s['body_small'], fontSize=8.5, leading=12.5, textColor=GRAY_900,
        ),
    )
    card = Table([[body]], colWidths=[15.5 * cm])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('LINEBEFORE', (0, 0), (0, -1), 3.0, bar),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return card


def _clean_inline(text):
    """清理内联 Markdown 为 ReportLab XML 安全文本"""
    text = str(text or '')
    # 行内代码 `metric` → 加粗指标名（去掉反引号糙感）
    text = re.sub(r'`([^`]+)`', r'<b>\1</b>', text)
    # Markdown bold → HTML bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    # 残留未配对 **
    text = text.replace('**', '')
    # <br> → 保留为换行（表格内 meta 用）
    text = re.sub(r'<br\s*/?>', '<br/>', text)
    # 去掉其他 HTML 标签（保留 <b></b> 与 <br/>）
    text = re.sub(r'<(?!/?b\b)(?!br\s*/?>)[^>]+>', '', text)
    # HTML 转义（先保护 br）
    text = text.replace('<br/>', '§BR§')
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 恢复 <b> 和 </b>
    text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    text = text.replace('§BR§', '<br/>')
    # 压空白，但保留 br
    parts = text.split('<br/>')
    text = '<br/>'.join(re.sub(r'\s+', ' ', p).strip() for p in parts)
    return text.strip()


def _pdf_cell_text(text):
    """表格单元格文本：减少编号/单位被硬拆行"""
    text = _clean_inline(text)
    # 标准编号粘住
    text = re.sub(r'(GB/T)\s*([A-Za-z0-9\-]+)', r'\1&nbsp;\2', text)
    text = re.sub(r'(ISO)\s*([A-Za-z0-9\-]+)', r'\1&nbsp;\2', text)
    # 数字与单位粘住
    text = re.sub(r'(\d+(?:\.\d+)?)\s*(秒|分|分钟|字/分钟|%|次)', r'\1\2', text)
    # 示例占位符
    text = re.sub(r'(GB/T)&nbsp;XXXX', r'GB/T&nbsp;XXXX', text)
    text = text.replace('GB/T XXXX', 'GB/T&nbsp;XXXX')
    return text


def _dim_cell_style(s, leading=14):
    return ParagraphStyle(
        'DimCell',
        parent=s['body_small'],
        fontSize=9,
        leading=leading,
        textColor=GRAY_900,
    )


def _dim_label_style(s):
    return ParagraphStyle(
        'DimLabel',
        parent=s['body_small'],
        fontName=_CN_FONT_BOLD,
        fontSize=9,
        leading=13,
        textColor=GRAY_900,
    )


# ════════════════════════════════════════
#  页面框架
# ════════════════════════════════════════

def _header_footer(canvas, doc):
    """页眉页脚：参考笔墨传妆 — 左品牌 · 右 CONFIDENTIAL；底居中 PAGE。"""
    canvas.saveState()
    # 页眉
    canvas.setStrokeColor(GRAY_300)
    canvas.setLineWidth(0.6)
    y_line = A4[1] - 1.45 * cm
    canvas.line(2.0 * cm, y_line, A4[0] - 2.0 * cm, y_line)
    canvas.setFont(_CN_FONT, 7.5)
    canvas.setFillColor(GRAY_500)
    canvas.drawString(2.0 * cm, A4[1] - 1.25 * cm, BRAND_REPORT_TITLE)
    canvas.drawRightString(A4[0] - 2.0 * cm, A4[1] - 1.25 * cm, 'CONFIDENTIAL')
    # 页脚
    canvas.setFont(_CN_FONT, 7)
    canvas.setFillColor(GRAY_500)
    footer = f'{BRAND_PRODUCT} AI SCORING REPORT  ·  PAGE {doc.page}'
    canvas.drawCentredString(A4[0] / 2, 1.15 * cm, footer)
    canvas.restoreState()


def _section_heading(story, sections: _SectionCounter, title: str, desc: str, s, en: str | None = None):
    """
    章节头：海军蓝数字徽章 + 中文标题 + 英文副标题 + 底线。
    desc 若给出，渲染为下方左栏 callout（与参考一致）。
    """
    num = sections.next()
    en_text = en if en is not None else _SECTION_EN.get(title, '')
    badge = Table(
        [[Paragraph(num, s['section_num'])]],
        colWidths=[0.85 * cm], rowHeights=[0.72 * cm],
    )
    badge.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    title_line = Paragraph(
        f'{_clean_inline(title)}'
        + (f'  <font color="#94A3B8" size="9">{_clean_inline(en_text)}</font>' if en_text else ''),
        s['section_title'],
    )
    head = Table([[badge, title_line]], colWidths=[1.05 * cm, 14.45 * cm])
    head.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 6),
        ('LEFTPADDING', (1, 0), (1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(head)
    story.append(Spacer(1, 0.18 * cm))
    story.append(HRFlowable(
        width='100%', thickness=0.8, color=GRAY_300,
        spaceBefore=0, spaceAfter=0,
    ))
    story.append(Spacer(1, 0.28 * cm))
    if desc:
        story.append(_callout_box(desc, s))
        story.append(Spacer(1, 0.28 * cm))


# ════════════════════════════════════════
#  各章节
# ════════════════════════════════════════

def _resolve_project_name(result: dict) -> str:
    project = (
        result.get('project_name')
        or (result.get('project_info') or {}).get('project_name')
        or (result.get('project_info') or {}).get('name')
        or ''
    )
    if (not project) or re.match(r'^(Session|会话)\s', str(project), re.I) or re.match(r'^SC-\d+', str(project)):
        profile = result.get('character_profile') or {}
        if isinstance(profile, dict):
            alt = (
                profile.get('project_name')
                or profile.get('projectName')
                or (profile.get('meta') or {}).get('project_name')
            )
            if alt:
                project = alt
        if (not project) or re.match(r'^(Session|会话)\s', str(project), re.I) or re.match(r'^SC-\d+', str(project)):
            md = ''
            if isinstance(profile, dict):
                md = str(
                    profile.get('profile_markdown')
                    or profile.get('markdown')
                    or profile.get('report')
                    or profile.get('content')
                    or ''
                )
            elif isinstance(profile, str):
                md = profile
            m = re.search(r'项目名称[：:]\s*([^\n]{2,80})', md)
            if m:
                project = m.group(1).strip()
            if (not project) or re.match(r'^(Session|会话)\s', str(project), re.I) or re.match(r'^SC-\d+', str(project)):
                asr = result.get('asr') or {}
                transcript = str(asr.get('transcript') or '')[:800]
                m2 = re.search(
                    r'(?:带来的是|参赛项目是|项目是|项目名称为?)\s*([^\s，。,.]{4,40}?项目)',
                    transcript,
                )
                if m2:
                    project = m2.group(1).strip()
    return str(project or '').strip()


def _add_cover(story, result, s):
    """封面：参考笔墨传妆 — logo + 居中标题 + 灰标签元信息。"""
    # 顶部呼吸 + 启发继学 logo
    story.append(Spacer(1, 1.8 * cm))
    logo = _brand_logo_path()
    if logo:
        try:
            img = Image(logo)
            max_w, max_h = 4.2 * cm, 1.5 * cm
            iw = float(getattr(img, 'imageWidth', 0) or 0)
            ih = float(getattr(img, 'imageHeight', 0) or 0)
            if iw > 0 and ih > 0:
                scale = min(max_w / iw, max_h / ih)
                img.drawWidth = iw * scale
                img.drawHeight = ih * scale
            else:
                img.drawWidth, img.drawHeight = max_w, max_h
            # 居中
            wrap = Table([[img]], colWidths=[CONTENT_W * cm])
            wrap.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(wrap)
            story.append(Spacer(1, 0.45 * cm))
        except Exception:
            story.append(Spacer(1, 0.3 * cm))
    else:
        story.append(Spacer(1, 1.2 * cm))

    story.append(Paragraph(
        f'{BRAND_PRODUCT} · 多维度路演评分报告',
        ParagraphStyle(
            'CoverTop', fontName=_CN_FONT, fontSize=7.5, leading=10,
            alignment=TA_CENTER, textColor=GRAY_500,
        ),
    ))
    story.append(Spacer(1, 0.18 * cm))
    story.append(HRFlowable(width=6 * cm, thickness=0.6, color=GRAY_300, spaceBefore=2, spaceAfter=10, hAlign='CENTER'))
    story.append(Paragraph(
        '  ·  '.join(list(BRAND_PRODUCT)),
        ParagraphStyle(
            'CoverBrandLetters', fontName=_CN_FONT, fontSize=10, leading=14,
            alignment=TA_CENTER, textColor=GRAY_500, spaceAfter=14,
        ),
    ))
    story.append(Paragraph('多维度路演评分报告', s['cover_title']))

    project = _resolve_project_name(result)
    track = (
        result.get('track')
        or result.get('track_name')
        or (result.get('project_info') or {}).get('track')
        or ''
    )
    meeting_id = result.get('meeting_id', '—')
    session_no = result.get('session_no') or result.get('sessionNo') or ''
    duration_s = (result.get('asr') or {}).get('duration') or result.get('duration') or 0
    try:
        duration_s = float(duration_s)
    except Exception:
        duration_s = 0
    duration_txt = f'{duration_s / 60:.1f} 分钟' if duration_s > 0 else '—'

    completed = result.get('completed_at', '')
    if completed:
        try:
            dt = datetime.fromisoformat(str(completed).replace('Z', '+00:00').split('+')[0])
            date_str = dt.strftime('%Y-%m-%d')
        except Exception:
            date_str = str(completed)[:10]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')

    report_type = 'AI 官方五维评分复盘'
    if _jury_enabled(result) and _real_jury_package(result):
        report_type = 'AI 评分流 + 评审团 + 多模态复盘'
    elif _jury_enabled(result):
        report_type = 'AI 官方五维评分（评审团进行中）'

    subtitle_bits = [x for x in [track or None, project[:12] if project and len(project) > 12 else project, '完整复盘版'] if x]
    story.append(Paragraph(
        ' · '.join(subtitle_bits) if subtitle_bits else '完整复盘版',
        s['cover_subtitle'],
    ))
    story.append(Spacer(1, 0.8 * cm))

    meta = [
        ['项目名称', project or '—'],
        ['参赛赛道', track or '—'],
        ['会话编号', session_no or f'Session {meeting_id}'],
        ['路演时长', duration_txt],
        ['报告类型', report_type],
        ['生成时间', date_str],
    ]
    label_s = ParagraphStyle(
        'CoverMetaL', parent=s['body_small'], fontName=_CN_FONT,
        textColor=GRAY_500, fontSize=9.5, leading=14, alignment=TA_LEFT,
    )
    value_s = ParagraphStyle(
        'CoverMetaV', parent=s['body_small'], fontName=_CN_FONT_BOLD,
        textColor=NAVY, fontSize=9.5, leading=14, alignment=TA_LEFT,
    )
    meta_data = [[Paragraph(k, label_s), Paragraph(_clean_inline(str(v)), value_s)] for k, v in meta]
    meta_table = Table(meta_data, colWidths=[3.2 * cm, 9.5 * cm])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))
    # 居中放元信息表
    wrap = Table([[meta_table]], colWidths=[15.5 * cm])
    wrap.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.4 * cm),
    ]))
    story.append(wrap)
    story.append(PageBreak())


def _add_overview(story, result, s, sections: _SectionCounter):
    """评分总览：参考笔墨传妆 — 诊断 callout → 大号分数 → 双列进度条 → 深表头指标表 → 标签行。"""
    ai_score = result.get('ai_score', {})
    overall = ai_score.get('overall_score', 0)
    dimensions = ai_score.get('dimensions', {})
    overview = ai_score.get('score_overview') or {}

    diagnosis = overview.get('diagnosis') or ai_score.get('summary') or ''
    diag = _humanize_dimension_tokens(_value_text(diagnosis))
    diag = re.sub(r'权威总分', '本场总分', diag)
    # 章节头不塞长 desc；诊断单独 callout
    _section_heading(story, sections, '评分总览', '', s)
    if diag:
        story.append(_callout_box(diag, s))
        story.append(Spacer(1, 0.35 * cm))

    try:
        overall_f = float(overall or 0)
    except Exception:
        overall_f = 0.0

    # 居中大号分数
    story.append(Paragraph(f'{overall_f:g}', ParagraphStyle(
        'OvHero', fontName=_CN_FONT_BOLD, fontSize=42, leading=48,
        textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
    )))
    story.append(Paragraph('AI 基准分 / 100', ParagraphStyle(
        'OvHeroCap', fontName=_CN_FONT, fontSize=9, leading=12,
        textColor=GRAY_500, alignment=TA_CENTER, spaceAfter=12,
    )))

    # 双列进度条（参考：左 3 右 2）
    dim_items = []
    for dim_key, dim in (dimensions or {}).items():
        if not isinstance(dim, dict):
            continue
        name = _dimension_display_name(dim_key, dim.get('name', ''))
        try:
            sc_f = float(dim.get('score') or 0)
            mx_f = float(dim.get('max_score') or 0)
        except Exception:
            sc_f, mx_f = 0.0, 0.0
        dim_items.append((name, sc_f, mx_f))

    if dim_items:
        name_s = ParagraphStyle('DimBarName', parent=s['body_small'], fontSize=8.5, leading=11, textColor=GRAY_700)
        sc_s = ParagraphStyle('DimBarSc', parent=s['body_small'], fontSize=8.5, leading=11, textColor=NAVY, alignment=TA_RIGHT)
        left_n = (len(dim_items) + 1) // 2
        left_dims, right_dims = dim_items[:left_n], dim_items[left_n:]

        def _bar_col(items):
            rows = []
            for name, sc, mx in items:
                rows.append([
                    Paragraph(_clean_inline(name), name_s),
                    _score_bar_table(sc, mx, width_cm=3.2),
                    Paragraph(f'{sc:g}/{mx:g}' if mx else f'{sc:g}', sc_s),
                ])
            t = Table(rows, colWidths=[2.2 * cm, 3.4 * cm, 1.8 * cm])
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ]))
            return t

        bars = Table(
            [[_bar_col(left_dims), _bar_col(right_dims) if right_dims else '']],
            colWidths=[7.7 * cm, 7.7 * cm],
        )
        bars.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(bars)
        story.append(Spacer(1, 0.35 * cm))

    # 指标表（深表头）
    asr = result.get('asr') or {}
    seg_count = asr.get('segment_count') or len(asr.get('segments') or [])
    transcript_len = len(str(asr.get('transcript') or ''))
    frames = result.get('visual_frames') or result.get('frames') or []
    duration = asr.get('duration') or 0
    try:
        duration = float(duration)
    except Exception:
        duration = 0
    metric_rows = [
        ['AI 基准总分', f'{overall_f:g} / 100', '综合五维加权结果'],
    ]
    jury_pkg = _real_jury_package(result) if _jury_enabled(result) else None
    if jury_pkg:
        trimmed = jury_pkg.get('trimmed_average_score')
        raw_avg = jury_pkg.get('raw_average_score')
        n_j = jury_pkg.get('judge_count') or len(jury_pkg.get('score_cards') or []) or 0
        if trimmed is not None:
            try:
                metric_rows.append([
                    f'评审团去高低均分（{n_j} 人）',
                    f'{float(trimmed):g} / 100',
                    '去掉最高与最低后的评委均分',
                ])
            except Exception:
                metric_rows.append([f'评审团去高低均分（{n_j} 人）', str(trimmed), '去掉最高与最低后的评委均分'])
        if raw_avg is not None:
            try:
                metric_rows.append(['评审团原始均分', f'{float(raw_avg):g} / 100', '全部有效评委平均'])
            except Exception:
                pass
        # 分差按当前 AI 总分（含画面局部重评）重算，避免沿用 jury 快照里的旧基准
        diff = None
        if trimmed is not None and overall is not None:
            try:
                diff = float(trimmed) - float(overall)
            except Exception:
                diff = jury_pkg.get('score_diff_from_official')
        else:
            diff = jury_pkg.get('score_diff_from_official')
        if diff is not None:
            try:
                d = float(diff)
                metric_rows.append(['评委与基准分差', f'{d:+.1f}', '正值表示评审团均分高于 AI 基准'])
            except Exception:
                pass
    if seg_count:
        metric_rows.append(['有效转写', f'{seg_count} 段 · {transcript_len} 字', '可支撑语音表达与结构复盘'])
    # 不在对外 PDF 暴露抽帧/画面识别内部过程与计数
    if duration > 0:
        metric_rows.append(['路演时长', f'{duration / 60:.1f} 分钟', '以实际音视频时长计'])
    _append_simple_table(story, ['指标', '结果', '解释'], metric_rows, s, [4.2 * cm, 3.5 * cm, (CONTENT_W - 7.7) * cm])

    # 亮点/关键问题标签行
    highlights = _as_text_list(ai_score.get('highlights') or overview.get('highlights'), limit=4)
    key_issues = _as_text_list(ai_score.get('critical_issues') or overview.get('key_issues'), limit=4)
    # 标签尽量短：取句首 12 字
    def _short_tags(items):
        out = []
        for t in items:
            t = re.split(r'[：:，,。]', t)[0].strip()
            out.append(t[:14] if t else '')
        return [x for x in out if x]

    if highlights:
        story.append(_tag_row('亮点', _short_tags(highlights) or highlights, 'good', s))
        story.append(Spacer(1, 0.15 * cm))
    if key_issues:
        story.append(_tag_row('关键问题', _short_tags(key_issues) or key_issues, 'bad', s))


def _add_evidence_summary(story, result, s, sections: _SectionCounter):
    """证据摘要：有什么、缺什么，不重复总览分数。兼容多套字段名。"""
    ai_score = result.get('ai_score', {}) or {}
    overview = ai_score.get('score_overview') or {}
    # 注意顺序：优先 list；_as_text_list 兼容 str，禁止 list(str) 拆字
    highlights = _as_text_list(ai_score.get('highlights') or overview.get('highlights'), limit=6)
    issues = _as_text_list(ai_score.get('critical_issues') or overview.get('key_issues'), limit=6)
    audit = ai_score.get('evidence_audit') or []

    strong, weak, missing, contradict = [], [], [], []
    for item in audit if isinstance(audit, list) else []:
        if not isinstance(item, dict):
            continue
        level = str(
            item.get('level')
            or item.get('strength')
            or item.get('type')
            or item.get('currentEvidenceLevel')
            or item.get('evidence_level')
            or ''
        ).lower()
        text = _value_text(
            item.get('summary')
            or item.get('title')
            or item.get('description')
            or item.get('gapDescription')
            or item.get('gap')
            or item.get('evidence')
            or item.get('requiredEvidence')
        )
        required = _value_text(item.get('requiredEvidence') or item.get('required_evidence') or '')
        if not text or len(text) <= 1:
            continue
        # 展示给人看：缺口说明 + 需补材料；不暴露 O02 等内部观测码
        display = text
        if required and required not in text:
            display = f'{text} 需补：{required}'
        # E0/E1 严重缺失，E2 偏弱，E3+ 可支撑
        if level in ('e3', 'e4', 'e5') or 'strong' in level or '强' in level:
            strong.append(display)
        elif level in ('e0',) or 'missing' in level or '缺' in level or '无' in level or '完全无' in text:
            missing.append(display)
        elif 'contradict' in level or '矛盾' in level:
            contradict.append(display)
        else:
            if level in ('e1', 'e2') or 'gap' in level:
                missing.append(display)
            else:
                weak.append(display)

    frames = result.get('visual_frames') or result.get('frames') or []
    asr = result.get('asr') or {}
    seg_count = asr.get('segment_count') or len(asr.get('segments') or [])
    transcript_len = len(str(asr.get('transcript') or ''))
    duration = asr.get('duration') or 0
    try:
        duration = float(duration)
    except Exception:
        duration = 0

    if not any([highlights, issues, strong, weak, missing, contradict, seg_count, frames, duration]):
        return

    story.append(PageBreak())
    _section_heading(story, sections, '证据摘要', '', s)

    # 关键扣分优先用 critical_issues（语义完整）；audit 缺口作补充
    left = highlights[:4] if highlights else strong[:4]
    right = issues[:4] if issues else missing[:4]
    # 若 issues 空再用 missing；若两边都来自 audit，去掉过长「需补」噪声截断
    if not left and strong:
        left = strong[:4]
    if not right and missing:
        right = missing[:4]

    col_w = (CONTENT_W - 0.4) / 2
    col_title = ParagraphStyle(
        'EvColT', parent=s['body'], fontName=_CN_FONT_BOLD, fontSize=10,
        leading=14, textColor=NAVY, spaceAfter=4, wordWrap='CJK',
    )
    if left or right:
        max_n = max(len(left), len(right), 1)
        left_cells = [_side_card(t, 'good', s, col_w) for t in left]
        right_cells = [_side_card(t, 'bad', s, col_w) for t in right]
        titles = Table(
            [[Paragraph('核心亮点', col_title), Paragraph('关键扣分', col_title)]],
            colWidths=[col_w * cm + 0.2 * cm, col_w * cm + 0.2 * cm],
        )
        titles.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(titles)

        for i in range(max_n):
            l = left_cells[i] if i < len(left_cells) else ''
            r = right_cells[i] if i < len(right_cells) else ''
            row = Table([[l, r]], colWidths=[(col_w + 0.2) * cm, (col_w + 0.2) * cm])
            row.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('RIGHTPADDING', (0, 0), (0, 0), 4),
                ('LEFTPADDING', (1, 0), (1, 0), 4),
                ('RIGHTPADDING', (1, 0), (1, 0), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(row)
        story.append(Spacer(1, 0.3 * cm))

    metrics = []
    if seg_count:
        metrics.append(['有效转写', f'{seg_count} 段 · 约 {transcript_len} 字', '可支撑语音与结构复盘'])
    if duration > 0:
        metrics.append(['路演时长', f'{duration / 60:.1f} 分钟', '以实际音视频计'])
    if metrics:
        story.append(Paragraph('材料覆盖', s['h2']))
        _append_simple_table(
            story, ['类型', '结果', '评分价值'], metrics, s,
            [3.2 * cm, 6.5 * cm, (CONTENT_W - 9.7) * cm],
        )

    if weak or contradict:
        story.append(Paragraph('证据质量提示', s['h2']))
        for text in (contradict + weak)[:6]:
            story.append(_para(f'● {text}', s['bullet']))
        story.append(Spacer(1, 0.2 * cm))

    story.append(_callout_box(
        '证据质量判断：高分路演要求关键结论落到「时间点、原文、画面、数据来源」之一；'
        '仅口头断言、无可核验材料时，评分会保守处理。',
        s,
        width_cm=CONTENT_W,
    ))


def _dim_aliases(dim_key: str, name: str) -> list[str]:
    """判断用别名（可稍宽）。匹配行动计划时用更严的 _dim_action_keys。"""
    aliases = {
        'skill_level': ['技能水平', '技能熟练', '熟练度', '工程深度', '操作路径'],
        'professionalism': ['职业素养', '专业性', '职业道德', '行为规范', '合规', '伦理', '授权'],
        'application_value': ['应用价值', '经济性', '实用性', '可持续', '用户验证', '落地场景'],
        'teamwork': ['团队协作', '团队精神', '沟通协作', '分工', '联调'],
        'innovation': ['创新能力', '创新意识', '创新成效', '技术先进', '差异化', '技术选型'],
    }.get(str(dim_key), [name])
    if name and name not in aliases:
        aliases = [name] + list(aliases)
    return aliases


def _dim_action_keys(dim_key: str, name: str) -> list[str]:
    """行动计划严格匹配键：避免「工程/IDE」把技能动作误挂到应用价值。"""
    strict = {
        'skill_level': ['技能水平', '技能熟练', '熟练度', '工程深度', '操作规范性', '任务难易'],
        'professionalism': ['职业素养', '职业道德', '行为规范', '专业性', '安全意识', '工匠精神'],
        'application_value': ['应用价值', '经济性', '实用性', '可持续', '单品经济', '用户验证', 'ROI'],
        'teamwork': ['团队协作', '团队精神', '沟通协作', '协作过程', '分工优化'],
        'innovation': ['创新能力', '创新意识', '创新成效', '技术先进', '标准化流程', '技术选型'],
    }.get(str(dim_key), [name] if name else [])
    return [k for k in strict if k]


def _summarize_improvement(text: str, max_len: int = 90) -> str:
    """改进方向摘要：完整句优先，避免窄列把英文/中文硬切碎。"""
    t = _humanize_dimension_tokens(re.sub(r'\s+', ' ', text or '').strip())
    if not t:
        return ''
    # 保护英文标识，减少断词观感（展示层用）
    t = re.sub(r'\b([A-Za-z][A-Za-z0-9_.-]+\.[A-Za-z0-9]+)\b', r'\1', t)
    if len(t) <= max_len:
        return t
    # 优先在顿号/分号/句号处截断
    cut = t[:max_len]
    for sep in ('。', '；', '；', '，', '、', '；', ';', ','):
        pos = cut.rfind(sep)
        if pos >= int(max_len * 0.45):
            return cut[: pos + 1]
    return cut.rstrip('，,;； ') + '…'


def _dimension_judgment(dim_key: str, name: str, sc_f: float, mx_f: float, dim: dict, ai_score: dict) -> tuple[str, str]:
    """返回 (本维判断, 改进方向摘要)。改进只绑严格匹配的行动项。"""
    note = _value_text(
        dim.get('reason') or dim.get('summary') or dim.get('comment')
        or dim.get('analysis') or ''
    )
    if note and len(note) > 8:
        note = _humanize_dimension_tokens(note)
        tip = _value_text(dim.get('improvement') or dim.get('suggestion') or '')
        return note, _summarize_improvement(tip) if tip else ''
    # 合同：不得用总览/扣分项回填每一维，避免同一事故复读
    return '', ''


def _add_dimension_detail(story, result, s, sections: _SectionCounter):
    """维度详情：有细项展开；无细项用「每维一卡」全宽排版，避免窄列硬断词。"""
    ai_score = result.get('ai_score', {})
    dimensions = ai_score.get('dimensions', {})
    if not dimensions:
        return

    parsed = []
    any_items = False
    for dim_key, dim in dimensions.items():
        if not isinstance(dim, dict):
            continue
        name = _dimension_display_name(dim_key, dim.get('name', ''))
        try:
            sc_f = float(dim.get('score') or 0)
            mx_f = float(dim.get('max_score') or 0)
        except Exception:
            sc_f, mx_f = 0.0, 0.0
        items = [it for it in (dim.get('items') or []) if isinstance(it, dict)]
        if items:
            any_items = True
        parsed.append((dim_key, name, sc_f, mx_f, items, dim))

    if not parsed:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '维度详情', '', s)

    body_s = ParagraphStyle(
        'DimItemBody', parent=s['body_small'], fontSize=8.5, leading=12.5,
        textColor=GRAY_900, wordWrap='CJK',
    )
    item_name_s = ParagraphStyle(
        'DimItemName', parent=s['body_small'], fontName=_CN_FONT_BOLD,
        fontSize=9, leading=12, textColor=NAVY, wordWrap='CJK',
    )
    item_sc_s = ParagraphStyle(
        'DimItemSc', parent=s['body_small'], fontName=_CN_FONT_BOLD,
        fontSize=9, leading=12, textColor=GRAY_700, alignment=TA_RIGHT,
    )
    name_s = ParagraphStyle(
        'DimOuterName', parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=11, leading=14, textColor=NAVY,
    )
    score_s = ParagraphStyle(
        'DimOuterSc', parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=11, leading=14, textColor=NAVY, alignment=TA_RIGHT,
    )
    lab_s = ParagraphStyle(
        'DimLab', parent=s['body_small'], fontName=_CN_FONT_BOLD,
        fontSize=8, leading=11, textColor=GRAY_500,
    )
    val_s = ParagraphStyle(
        'DimVal', parent=s['body_small'], fontSize=8.5, leading=12.5,
        textColor=GRAY_900, wordWrap='CJK',
    )

    def _tip_box(text: str) -> Table:
        p = _para(text, ParagraphStyle(
            'DimTip', parent=s['body_small'], fontSize=8, leading=11.5,
            textColor=GRAY_700, wordWrap='CJK',
        ))
        t = Table([[p]], colWidths=[(CONTENT_W - 2.2) * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), TIP_BG),
            ('LINEBEFORE', (0, 0), (0, -1), 2.4, TIP_BAR),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return t

    # 无细项：每维一卡（标题得分 + 判断 + 改进全宽）
    if not any_items:
        for dim_key, name, sc_f, mx_f, items, dim in parsed:
            judgment, tip = _dimension_judgment(dim_key, name, sc_f, mx_f, dim, ai_score)
            pct = int(round(sc_f / mx_f * 100)) if mx_f > 0 else 0
            score_txt = f'{sc_f:g} / {mx_f:g}（{pct}%）' if mx_f else f'{sc_f:g}'
            header = Table([[
                Paragraph(_clean_inline(name), name_s),
                Paragraph(_clean_inline(score_txt), score_s),
            ]], colWidths=[(CONTENT_W - 4.2) * cm, 4.2 * cm])
            header.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            rows = [
                [Paragraph('本维判断', lab_s), _para(judgment, val_s)],
            ]
            if tip:
                rows.append([Paragraph('改进方向', lab_s), _para(tip, val_s)])
            body = Table(rows, colWidths=[2.0 * cm, (CONTENT_W - 2.0) * cm])
            body.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_300),
                ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ]))
            card = Table([[header], [body]], colWidths=[CONTENT_W * cm])
            card.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.55, GRAY_300),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(KeepTogether([card, Spacer(1, 0.2 * cm)]))
        return

    # 有细项：外框 + 子项
    for dim_key, name, sc_f, mx_f, items, dim in parsed:
        header = Table([[
            Paragraph(_clean_inline(name), name_s),
            Paragraph(f'{sc_f:g} / {mx_f:g}' if mx_f else f'{sc_f:g}', score_s),
        ]], colWidths=[(CONTENT_W - 3.5) * cm, 3.5 * cm])
        header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        inners = [header]
        for item in items:
            item_name = _value_text(item.get('name', '评分项'))
            reason = _value_text(item.get('reason') or item.get('summary') or '')
            tip = _value_text(item.get('improvement') or item.get('suggestion') or '')
            if tip and (
                len(tip) < 10
                or re.fullmatch(r'补充.+的?证据。?', tip)
                or re.fullmatch(r'建议补充.+', tip)
            ):
                tip = ''
            sc_txt = f'{item.get("score", "")} / {item.get("max_score", "")}'
            head = Table([[
                Paragraph(_clean_inline(item_name), item_name_s),
                Paragraph(_clean_inline(sc_txt), item_sc_s),
            ]], colWidths=[(CONTENT_W - 4.0) * cm, 2.8 * cm])
            head.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            parts = [[head]]
            if reason:
                parts.append([_para(reason, body_s)])
            if tip:
                parts.append([_tip_box(_summarize_improvement(tip, 120))])
            blk = Table(parts, colWidths=[(CONTENT_W - 1.0) * cm])
            blk.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            inners.append(Spacer(1, 0.1 * cm))
            inners.append(blk)

        card = Table([[x] for x in inners], colWidths=[CONTENT_W * cm])
        card.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.55, GRAY_300),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('LEFTPADDING', (0, 1), (-1, -1), 8),
            ('RIGHTPADDING', (0, 1), (-1, -1), 8),
        ]))
        story.append(KeepTogether([card, Spacer(1, 0.22 * cm)]))


def _draw_pause_timeline(pause_details: list, total_duration: float):
    """
    绘制停顿分布时间轴（优化布局，避免文字重叠）
    - X轴：会议时间（分钟）
    - 圆点：停顿发生位置，大小按时长缩放
    - 红色=严重(>5s)  橙色=明显(3-5s)  灰色=轻微(2-3s)
    - 圆点交替上下偏移，避免密集时重叠
    """
    from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect
    from reportlab.lib.colors import HexColor, white as _white

    if not pause_details or total_duration <= 0:
        return None

    total_min = total_duration / 60
    W = 16.5 * cm
    H = 4.5 * cm  # 加高画布避免重叠
    ml = 1.0 * cm   # 左边距
    mr = 0.6 * cm   # 右边距
    usable_w = W - ml - mr

    # 垂直分区
    title_y = H - 14          # 标题行
    legend_y = H - 28         # 图例行
    track_y = H * 0.48        # 时间轴
    label_y = track_y - 16    # X轴标签

    d = Drawing(W, H)

    # 背景
    d.add(Rect(0, 0, W, H, fillColor=HexColor('#FAFBFC'),
               strokeColor=None, rx=6, ry=6))

    # 标题（独立一行，不与图例重叠）
    d.add(String(ml, title_y,
                 f'停顿分布（共 {len(pause_details)} 次 · {total_min:.0f} 分钟）',
                 fontSize=8, fillColor=HexColor('#374151'),
                 fontName=_CN_FONT))

    # 图例（独立一行）
    lx = ml
    for sev, color, label in [('严重(>5s)', HexColor('#EF4444'), '●'),
                               ('明显(3-5s)', HexColor('#F59E0B'), '●'),
                               ('轻微(2-3s)', HexColor('#D1D5DB'), '●')]:
        d.add(Circle(lx + 4, legend_y, 3, fillColor=color, strokeColor=None))
        d.add(String(lx + 10, legend_y - 3, sev,
                     fontSize=6.5, fillColor=HexColor('#6B7280'), fontName=_CN_FONT))
        lx += len(sev) * 6.5 + 22

    # 主轴线
    d.add(Line(ml, track_y, W - mr, track_y,
               strokeColor=HexColor('#D1D5DB'), strokeWidth=1))

    # X轴刻度（自适应，确保不重叠）
    max_ticks = 10
    raw_step = total_min / max_ticks
    # 取整到合理的步长
    for candidate in [1, 2, 5, 10, 15, 20, 30]:
        if candidate >= raw_step:
            step = candidate
            break
    else:
        step = 60

    for m in range(0, int(total_min) + 1, step):
        x = ml + (m / total_min) * usable_w
        # 刻度线
        d.add(Line(x, track_y - 3, x, track_y + 3,
                   strokeColor=HexColor('#9CA3AF'), strokeWidth=0.5))
        # 标签
        label_text = f'{m}′' if m % 5 == 0 else f'{m}'
        d.add(String(x, label_y, label_text,
                     fontSize=6, fillColor=HexColor('#9CA3AF'),
                     textAnchor='middle', fontName='Helvetica'))

    # 停顿圆点（交替上下偏移，避免密集重叠）
    color_map = {
        '严重': HexColor('#EF4444'),
        '明显': HexColor('#F59E0B'),
        '轻微': HexColor('#D1D5DB'),
    }
    # 按位置排序
    sorted_pauses = sorted(pause_details, key=lambda p: p.get('position_seconds', 0))
    prev_x = -999  # 上一个圆点的x坐标

    for i, p in enumerate(sorted_pauses):
        pos = p.get('position_seconds', 0)
        dur = p.get('duration', 2)
        sev = p.get('severity', '轻微')
        x = ml + (pos / total_duration) * usable_w

        # 交替上下偏移（当前后圆点距离<8pt时）
        if x - prev_x < 8:
            y_offset = (6 if i % 2 == 0 else -6)
        else:
            y_offset = 0

        r = min(max(2, dur * 0.6), 6)  # 半径按时长缩放
        color = color_map.get(sev, HexColor('#D1D5DB'))
        d.add(Circle(x, track_y + y_offset, r,
                     fillColor=color, strokeColor=WHITE, strokeWidth=0.5))
        prev_x = x

    return d


def _add_speech_quality(story, result, s, sections: _SectionCounter):
    """语音表达 — 参考笔墨传妆：四格指标卡 + 问题表。"""
    sq = result.get('speech_quality', {})
    if not sq:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '语音表达', '', s)
    story.append(_callout_box(
        '基于 ASR 与时长数据：看语速、停顿与填充词是否影响评委消化关键信息。',
        s,
    ))
    story.append(Spacer(1, 0.25 * cm))

    sr = sq.get('speech_rate', {}) or {}
    pauses = sq.get('pauses', {}) or {}
    fillers = sq.get('fillers', {}) or {}
    duration = sq.get('duration', result.get('asr', {}).get('duration', 0))
    try:
        duration_f = float(duration or 0)
    except Exception:
        duration_f = 0.0

    cpm = sr.get('global_chars_per_minute', '—')
    try:
        cpm_f = float(cpm)
        rate_label = '偏快' if cpm_f > 250 else ('偏慢' if cpm_f < 180 else '正常')
        rate_color = WARNING if cpm_f > 250 or cpm_f < 180 else SUCCESS
    except Exception:
        rate_label, rate_color = sr.get('global_rating', '—') or '—', GRAY_500

    pause_n = pauses.get('total_pauses', 0)
    filler_n = fillers.get('total_fillers', 0)
    rate = fillers.get('filler_rate_percent')
    try:
        rate_f = float(rate)
        if rate_f < 5:
            filler_label, filler_color = '优秀', SUCCESS
        elif rate_f <= 15:
            filler_label, filler_color = '一般', WARNING
        else:
            filler_label, filler_color = '偏多', DANGER
    except Exception:
        filler_label, filler_color = fillers.get('rating', '—') or '—', GRAY_500

    pause_label = pauses.get('rating') or ('需优化' if int(pause_n or 0) > 20 else '正常')
    pause_color = WARNING if '优' in str(pause_label) or '需' in str(pause_label) else GRAY_500

    def _metric_tile(value, unit, caption, status, status_color):
        v = Paragraph(str(value), ParagraphStyle(
            'MtV', fontName=_CN_FONT_BOLD, fontSize=18, leading=22,
            textColor=NAVY, alignment=TA_CENTER,
        ))
        u = Paragraph(f'{_clean_inline(unit)}<br/>{_clean_inline(caption)}', ParagraphStyle(
            'MtU', fontName=_CN_FONT, fontSize=7.5, leading=10,
            textColor=GRAY_500, alignment=TA_CENTER,
        ))
        st = Paragraph(_clean_inline(str(status)), ParagraphStyle(
            'MtS', fontName=_CN_FONT_BOLD, fontSize=8, leading=11,
            textColor=status_color, alignment=TA_CENTER,
        ))
        t = Table([[v], [u], [st]], colWidths=[3.6 * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
            ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -2), 2),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    tiles = Table([[
        _metric_tile(cpm, '字/分钟', '平均语速', rate_label, rate_color),
        _metric_tile(pause_n, '次', '停顿', pause_label, pause_color),
        _metric_tile(filler_n, '次', '填充词', filler_label, filler_color),
        _metric_tile(f'{duration_f / 60:.1f}' if duration_f else '—', '分钟', '总时长', '实测', SUCCESS),
    ]], colWidths=[3.85 * cm] * 4)
    tiles.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(tiles)
    story.append(Spacer(1, 0.35 * cm))

    # 表达问题简表（若有数据可推导）
    training_rows = []
    try:
        if float(cpm) > 250:
            training_rows.append(['语速偏快', '关键数据与结论容易被带过', '目标 200–245 字/分钟，数字后停顿 2 秒'])
    except Exception:
        pass
    try:
        if float(rate) > 10:
            training_rows.append(['填充词偏多', '削弱专业感', '把「然后、就是、这个」换成短停顿'])
    except Exception:
        pass
    if int(pause_n or 0) > 30:
        training_rows.append(['停顿偏多', '节奏被打断，评委注意力下降', '合并碎句，关键结论后才长停顿'])
    if training_rows:
        _append_simple_table(
            story, ['表达问题', '影响', '训练方法'], training_rows, s,
            [2.8 * cm, 5.5 * cm, 7.2 * cm],
        )

    story.append(Spacer(1, 0.25 * cm))

    # ── 停顿时间轴可视化 ──
    pause_details = pauses.get('details', [])

    # 如果 pauses.details 为空，从 fusion.timeline 重建
    if not pause_details:
        timeline = result.get('fusion', {}).get('timeline', [])
        if timeline and duration > 0:
            rebuilt = []
            for item in timeline:
                pc = item.get('pause_count', 0)
                if pc > 0:
                    t_sec = item.get('time_min', 0) * 60
                    severity = '严重' if pc >= 3 else '明显' if pc >= 2 else '轻微'
                    rebuilt.append({
                        'position_seconds': round(t_sec, 1),
                        'duration': round(pc * 2.5, 1),
                        'severity': severity,
                        'context_before': item.get('text_preview', '')[:30],
                        'context_after': '',
                    })
            if rebuilt:
                pause_details = rebuilt
                sq['pauses'] = {**pauses, 'details': rebuilt}

    if pause_details and duration > 0:
        story.append(Paragraph('停顿分布时间轴', s['h2']))
        story.append(Spacer(1, 0.3*cm))
        timeline_drawing = _draw_pause_timeline(pause_details, duration)
        if timeline_drawing:
            story.append(timeline_drawing)
            story.append(Spacer(1, 0.3*cm))

            # 停顿详情：优先严重，按时长取 Top10，避免长视频表淹没主叙事
            severe_pauses = [p for p in pause_details if p.get('severity') in ('严重', '明显')]
            severe_pauses = sorted(
                severe_pauses,
                key=lambda p: float(p.get('duration') or 0),
                reverse=True,
            )[:10]
            if severe_pauses:
                total_severe = len([p for p in pause_details if p.get('severity') in ('严重', '明显')])
                story.append(Paragraph(
                    f'显著停顿（共 {total_severe} 次，下表列时长最长的 {len(severe_pauses)} 次）',
                    s['section_desc'],
                ))
                story.append(Spacer(1, 0.2*cm))
                p_header = [
                    Paragraph('<b>时间</b>', s['body_small']),
                    Paragraph('<b>时长</b>', s['body_small']),
                    Paragraph('<b>严重度</b>', s['body_small']),
                    Paragraph('<b>上下文</b>', s['body_small']),
                ]
                p_rows = [p_header]
                for p in severe_pauses:
                    pos = p.get('position_seconds', 0)
                    m, sec = int(pos // 60), int(pos % 60)
                    ctx = f'…{p.get("context_before", "")} → {p.get("context_after", "")}…'
                    severity = p.get('severity', '')
                    sev_color = '#C0392B' if severity == '严重' else '#7F8C8D' if severity == '轻微' else '#616161'
                    p_rows.append([
                        Paragraph(f'{m:02d}:{sec:02d}', s['body_small']),
                        Paragraph(f'{p.get("duration", 0):.1f}s', s['body_small']),
                        Paragraph(f'<font color="{sev_color}">{severity}</font>', s['body_small']),
                        Paragraph(ctx[:80], s['body_small']),
                    ])
                pt = Table(p_rows, colWidths=[2*cm, 2*cm, 2*cm, 8*cm])
                pt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), GRAY_100),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, GRAY_300),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_100]),
                ]))
                story.append(pt)
                story.append(Spacer(1, 0.6*cm))

    # ── 口头禅详情 ──
    filler_types = fillers.get('filler_types', [])
    if filler_types:
        story.append(Paragraph('口头禅识别明细', s['h2']))
        story.append(Spacer(1, 0.3*cm))

        # 生成口头禅展示：嗯*12  啊*30  那个*8 ...
        # filler_types 可能是 list[{word,count}] / list[[word,count]] / dict
        pairs = []
        if isinstance(filler_types, dict):
            pairs = [(str(k), v) for k, v in filler_types.items()]
        elif isinstance(filler_types, list):
            for row in filler_types:
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    pairs.append((str(row[0]), row[1]))
                elif isinstance(row, dict):
                    pairs.append((
                        str(row.get('word') or row.get('token') or row.get('text') or ''),
                        row.get('count') or row.get('times') or 0,
                    ))
        pairs = [(w, c) for w, c in pairs if w]
        pairs.sort(key=lambda x: int(x[1] or 0), reverse=True)
        if pairs:
            filler_display = '　'.join([f'{word} ×{count}' for word, count in pairs[:20]])
            story.append(Paragraph(_clean_inline(filler_display), s['body']))

        story.append(Spacer(1, 0.2*cm))
        total_w = fillers.get('total_words', 0)
        rate = fillers.get('filler_rate_percent', 0)
        story.append(Paragraph(
            f'共检测到 {fillers.get("total_fillers", 0)} 次口头禅，'
            f'占总词数 {total_w} 的 {rate}%'
            + ('（<5% 为优秀，5-15% 为一般，>15% 需改进）' if total_w > 0 else ''),
            s['section_desc']
        ))
    elif fillers.get('total_fillers', 0) > 0:
        # 降级：只有总数没有分类时
        story.append(Paragraph('口头禅', s['h2']))
        story.append(Paragraph(
            f'共检测到 {fillers.get("total_fillers", 0)} 次口头禅（详细分类数据未保留）',
            s['body']
        ))

    story.append(Spacer(1, 0.6*cm))


def _split_point_and_time(text: str) -> tuple[str, str]:
    """拆出文末时间戳，便于版式上做成次要信息。"""
    raw = _value_text(text)
    if not raw:
        return '', ''
    m = re.search(r'[（(]([^）)]*\d{1,2}:\d{2}[^）)]*)[）)]\s*$', raw)
    if m:
        return raw[: m.start()].strip(' ，,;；'), m.group(1).strip()
    return raw, ''


def _highlight_item_block(index: int, text: str, tone: str, s) -> Table:
    """单条亮点/问题卡片。tone: good | risk"""
    body, time_tag = _split_point_and_time(text)
    if tone == 'good':
        idx_bg = HexColor('#E8F7EF')
        idx_fg = HexColor('#0F6B4C')
        bar = HexColor('#12B76A')
        card_bg = HexColor('#FBFFFC')
        border = HexColor('#CDEADB')
    else:
        idx_bg = HexColor('#FFF1EE')
        idx_fg = HexColor('#B42318')
        bar = HexColor('#F04438')
        card_bg = HexColor('#FFFBFA')
        border = HexColor('#F9D2CB')

    idx_style = ParagraphStyle(
        f'HiIdx{tone}{index}', parent=s['body_small'],
        fontName=_CN_FONT_BOLD, fontSize=9, leading=12,
        textColor=idx_fg, alignment=TA_CENTER,
    )
    body_style = ParagraphStyle(
        f'HiBody{tone}{index}', parent=s['body_small'],
        fontName=_CN_FONT, fontSize=9, leading=13.5,
        textColor=GRAY_900,
    )
    time_style = ParagraphStyle(
        f'HiTime{tone}{index}', parent=s['caption'],
        fontSize=7.5, leading=10, textColor=GRAY_500, spaceBefore=2,
    )

    left = Table(
        [[Paragraph(f'{index:02d}', idx_style)]],
        colWidths=[0.85 * cm], rowHeights=[0.85 * cm],
    )
    left.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), idx_bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BOX', (0, 0), (-1, -1), 0.4, border),
    ]))

    right_flow = [Paragraph(_pdf_cell_text(body), body_style)]
    if time_tag:
        right_flow.append(Paragraph(f'⏱ {_clean_inline(time_tag)}', time_style))
    right = Table([[x] for x in right_flow], colWidths=[6.1 * cm])
    right.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    card = Table([[left, right]], colWidths=[1.0 * cm, 6.2 * cm])
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), card_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border),
        ('LINEBEFORE', (0, 0), (0, -1), 2.2, bar),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, -1), 4),
        ('RIGHTPADDING', (0, 0), (0, -1), 4),
        ('LEFTPADDING', (1, 0), (1, -1), 6),
        ('RIGHTPADDING', (1, 0), (1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    return card


def _column_stack(title: str, items: list, tone: str, s) -> Table:
    """一列：标题条 + 编号卡片列表。"""
    if tone == 'good':
        title_bg = HexColor('#ECFDF3')
        title_fg = HexColor('#067647')
        title_border = HexColor('#ABEFC6')
        title_text = f'核心亮点 · {len(items)}'
    else:
        title_bg = HexColor('#FEF3F2')
        title_fg = HexColor('#B42318')
        title_border = HexColor('#FECDCA')
        title_text = f'关键问题 · {len(items)}'

    title_style = ParagraphStyle(
        f'ColTitle{tone}', parent=s['body_small'],
        fontName=_CN_FONT_BOLD, fontSize=10.5, leading=14,
        textColor=title_fg, alignment=TA_LEFT,
    )
    title_cell = Table(
        [[Paragraph(title_text, title_style)]],
        colWidths=[7.4 * cm],
    )
    title_cell.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), title_bg),
        ('BOX', (0, 0), (-1, -1), 0.5, title_border),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))

    rows = [[title_cell]]
    if not items:
        empty = ParagraphStyle(
            f'ColEmpty{tone}', parent=s['body_small'],
            fontSize=8.5, leading=12, textColor=GRAY_500,
        )
        rows.append([Paragraph('暂无条目', empty)])
    else:
        for i, item in enumerate(items[:6], 1):
            # items 已是完整句子列表时直接用；对象则再抽取
            body = item if isinstance(item, str) else _value_text(item)
            if not body or len(body.strip()) <= 1:
                continue
            rows.append([_highlight_item_block(i, body, tone, s)])
            rows.append([Spacer(1, 0.18 * cm)])

    col = Table(rows, colWidths=[7.4 * cm])
    col.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return col


def _add_highlights(story, result, s, sections: _SectionCounter):
    """亮点 / 关键问题：简化双栏列表（避免嵌套卡片撑破变形）+ 追问表。"""
    ai_score = result.get('ai_score', {}) or {}
    overview = ai_score.get('score_overview') or {}
    highlights = _as_text_list(ai_score.get('highlights') or overview.get('highlights'), limit=6)
    issues = _as_text_list(ai_score.get('critical_issues') or overview.get('key_issues'), limit=8)
    questions = ai_score.get('judge_questioning') or []

    if not highlights and not issues and not questions:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '亮点与关键问题', '', s)

    col_w = (CONTENT_W - 0.4) / 2
    item_s = ParagraphStyle(
        'HiSimple', parent=s['body_small'], fontSize=8.5, leading=12.5,
        textColor=GRAY_900, wordWrap='CJK',
    )
    title_s = ParagraphStyle(
        'HiColTitle', parent=s['body'], fontName=_CN_FONT_BOLD, fontSize=10,
        leading=13, textColor=NAVY,
    )

    def _simple_col(title: str, items: list, tone: str) -> Table:
        if tone == 'good':
            bar, bg, border, head_fg = SUCCESS, SUCCESS_BG, SUCCESS_BORDER, SUCCESS
        else:
            bar, bg, border, head_fg = DANGER, DANGER_BG, DANGER_BORDER, DANGER
        title_color = '067647' if tone == 'good' else 'B91C1C'
        rows = [[Paragraph(
            f'<font color="#{title_color}"><b>{_clean_inline(title)} · {len(items)}</b></font>',
            title_s,
        )]]
        if not items:
            rows.append([Paragraph('暂无', s['caption'])])
        else:
            for i, raw in enumerate(items[:6], 1):
                body = raw if isinstance(raw, str) else _value_text(raw)
                body, _ = _split_point_and_time(body)
                rows.append([_para(f'{i:02d}. {body}', item_s)])
        t = Table(rows, colWidths=[col_w * cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('BOX', (0, 0), (-1, -1), 0.5, border),
            ('LINEBEFORE', (0, 0), (0, -1), 3.0, bar),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), WHITE),
        ]))
        return t

    if highlights or issues:
        dual = Table(
            [[_simple_col('核心亮点', highlights, 'good'),
              _simple_col('关键问题', issues, 'risk')]],
            colWidths=[(col_w + 0.2) * cm, (col_w + 0.2) * cm],
        )
        dual.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, -1), 4),
            ('LEFTPADDING', (1, 0), (1, -1), 4),
            ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ]))
        story.append(dual)
        story.append(Spacer(1, 0.4 * cm))

    q_rows = []
    for item in questions if isinstance(questions, list) else []:
        if isinstance(item, dict):
            q = _value_text(item.get('question') or item.get('challenge_question') or item.get('text'))
            focus = _value_text(item.get('focus') or item.get('angle') or '综合')
            why = _value_text(
                item.get('why_it_matters') or item.get('why') or item.get('related_issue') or item.get('reason')
            )
            prep = _value_text(item.get('prep_evidence') or item.get('evidence') or '')
            if q:
                q_rows.append((focus, q, why, prep))
        elif item:
            q_rows.append(('综合', str(item), '', ''))
    if not q_rows and issues:
        for issue in issues[:5]:
            text = _value_text(issue)
            if text:
                body, _ = _split_point_and_time(text)
                q_rows.append(('证据补强', f'请用可核验材料说明：{body}', '对应关键扣分项', '截图、数据来源、检测报告'))

    if not q_rows:
        return

    story.append(Paragraph('评委可能追问', s['h2']))
    story.append(_para(
        '不编造评委人格。以下问题直接对应证据缺口，建议按序号在彩排中逐条对答。',
        s['section_desc'],
    ))
    story.append(Spacer(1, 0.1 * cm))

    table_rows = []
    for i, (focus, q, why, prep) in enumerate(q_rows[:6], 1):
        meta = why or ''
        if prep:
            meta = (meta + '；' if meta else '') + f'准备：{prep}'
        table_rows.append([f'{i:02d}', focus or '综合', q, meta or '—'])
    _append_simple_table(
        story,
        ['#', '关注角度', '可能追问', '为何重要 / 应准备'],
        table_rows,
        s,
        [1.0 * cm, 2.4 * cm, 7.2 * cm, (CONTENT_W - 10.6) * cm],
    )


# 官方五维：key → 中文（PDF/Web 一致，禁止裸英文 key 出给学生）
_DIMENSION_ZH = {
    'skill_level': '技能水平',
    'professionalism': '职业素养',
    'application_value': '应用价值',
    'teamwork': '团队合作',
    'innovation': '创新创意',
    'skill': '技能水平',
    'professional': '职业素养',
    'application': '应用价值',
    'team': '团队合作',
    'innovate': '创新创意',
    'creativity': '创新创意',
}


def _dimension_display_name(key, name='') -> str:
    k = str(key or '').strip()
    explicit = str(name or '').strip()
    if k in _DIMENSION_ZH:
        if (not explicit) or explicit == k or re.fullmatch(r'[a-z][a-z0-9_]*', explicit):
            return _DIMENSION_ZH[k]
        if explicit in _DIMENSION_ZH:
            return _DIMENSION_ZH[explicit]
        return explicit
    if explicit in _DIMENSION_ZH:
        return _DIMENSION_ZH[explicit]
    if explicit and not re.fullmatch(r'[a-z][a-z0-9_]*', explicit):
        return explicit
    return _DIMENSION_ZH.get(k) or explicit or k or '维度'


def _format_focus_dimensions_zh(value) -> str:
    """关注维度列表 → 中文「、」连接，禁止 skill_level 等裸字段。"""
    items: list[str] = []
    if value is None:
        return '—'
    if isinstance(value, str):
        # 可能是 "a、b" / "a, b" / 单 key
        parts = re.split(r'[,，、/;|]+', value)
        items = [p.strip() for p in parts if p.strip()]
    elif isinstance(value, (list, tuple)):
        for v in value:
            if isinstance(v, dict):
                items.append(_value_text(v.get('name') or v.get('key') or v.get('label') or v))
            else:
                items.append(str(v).strip())
    else:
        items = [str(value).strip()]
    zh_list = []
    for it in items:
        if not it:
            continue
        zh_list.append(_dimension_display_name(it, it))
    return '、'.join(zh_list) if zh_list else '—'


def _humanize_dimension_tokens(text: str) -> str:
    """正文里的 skill_level 等替换为中文，避免总评读不懂。"""
    s = str(text or '')
    if not s:
        return s
    # 长 key 优先
    for key in sorted(_DIMENSION_ZH.keys(), key=len, reverse=True):
        zh = _DIMENSION_ZH[key]
        s = re.sub(rf'\b{re.escape(key)}\b', zh, s)
        s = s.replace(f'（{key}）', f'（{zh}）').replace(f'({key})', f'（{zh}）')
    # 只清括号里的维度别名，不得把观测点「技能熟练度」改成「技能水平」
    s = re.sub(r'技能熟练度（技能水平）', '技能熟练度', s)
    s = re.sub(r'专业性（职业素养）', '职业素养', s)
    s = re.sub(r'创新性（创新能力）', '创新创意', s)
    s = s.replace('技能熟练度维度', '技能水平')
    s = s.replace('团队协作维度', '团队合作')
    s = s.replace('创新能力维度', '创新创意')
    s = s.replace('专业性、', '职业素养、')
    s = s.replace('、团队协作', '、团队合作')
    s = s.replace('团队协作和', '团队合作和')
    s = s.replace('和创新均', '和创新创意均')
    return s


def _value_text(value, default=''):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '；'.join(t for t in (_value_text(item) for item in value) if t)
    if isinstance(value, dict):
        # 常见对象字段优先，避免把整个 dict 的 key dump 给学生
        for field in (
            'title', 'text', 'summary', 'description', 'issue', 'problem',
            'suggestion', 'improvement', 'action', 'content', 'name', 'label',
        ):
            if value.get(field):
                return _value_text(value.get(field), default)
        return '；'.join(
            f'{_dimension_display_name(k) if k in _DIMENSION_ZH else k}: {_value_text(v)}'
            for k, v in value.items() if _value_text(v)
        )
    return _humanize_dimension_tokens(str(value).strip())


def _as_text_list(value, limit: int | None = None) -> list[str]:
    """
    把 highlights / issues 等字段规范成「完整句子」列表。
    绝不能对中文 str 做 list(str) 或 str[:n] 再按元素遍历——那会拆成单字。
    """
    if value is None or value is False:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # 优先按编号/换行拆成多条完整句子
        parts = re.split(r'(?:^|\n)\s*(?:\d+[\.、\)］)]\s+)', text)
        parts = [p.strip() for p in parts if p and p.strip()]
        if len(parts) >= 2:
            items = parts
        else:
            # 单段或用分号分隔
            if '；' in text or ';' in text:
                items = [p.strip() for p in re.split(r'[；;]+', text) if p.strip()]
            else:
                items = [text]
    elif isinstance(value, (list, tuple)):
        items = []
        for item in value:
            t = _value_text(item)
            if t:
                items.append(t)
    elif isinstance(value, dict):
        t = _value_text(value)
        items = [t] if t else []
    else:
        t = str(value).strip()
        items = [t] if t else []

    # 过滤过短噪声（单字、纯标点）
    cleaned = []
    for t in items:
        t = _humanize_dimension_tokens(re.sub(r'\s+', ' ', t).strip())
        if not t:
            continue
        if len(t) <= 1 and not re.search(r'[\u4e00-\u9fffA-Za-z0-9]', t):
            continue
        cleaned.append(t)
    if limit is not None:
        return cleaned[: max(0, int(limit))]
    return cleaned


def _append_simple_table(story, headers, rows, s, col_widths=None):
    """深海军蓝表头 + 斑马行（参考笔墨传妆）。"""
    if not rows:
        return
    head_style = ParagraphStyle(
        'TblHead', parent=s['body_small'], fontName=_CN_FONT_BOLD,
        fontSize=8.5, leading=11, textColor=WHITE, wordWrap='CJK',
    )
    cell_style = ParagraphStyle(
        'TblCell', parent=s['body_small'], fontSize=8.5, leading=12.5,
        textColor=GRAY_900, wordWrap='CJK',
    )
    table_rows = [[Paragraph(_clean_inline(h), head_style) for h in headers]]
    for row in rows:
        cells = []
        for cell in row:
            raw = _value_text(cell)
            # 允许调用方预置 <br/>
            if isinstance(cell, str) and ('<br/>' in cell or '<br>' in cell):
                cells.append(Paragraph(cell.replace('<br>', '<br/>'), cell_style))
            else:
                cells.append(Paragraph(_clean_inline(raw), cell_style))
        table_rows.append(cells)

    if col_widths is None:
        col_widths = [CONTENT_W * cm / max(len(headers), 1)] * len(headers)
    t = Table(table_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_50]),
        ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, GRAY_300),
        ('LINEBELOW', (0, 0), (-1, 0), 0, NAVY),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.32 * cm))


def _split_long_text(text, chunk_size=900):
    cleaned = re.sub(r'\s+', ' ', text or '').strip()
    if not cleaned:
        return []
    chunks = []
    for i in range(0, len(cleaned), chunk_size):
        chunks.append(cleaned[i:i + chunk_size])
    return chunks


def _clean_profile_markdown(md_text):
    """清洗画像 Markdown：去掉 LLM 开场白、重复标题、冗余元信息。"""
    cleaned = md_text or ''
    llm_noise_patterns = [
        r'好的，作为一名.*?选手团队能力画像报告》?[。.]',
        r'好的，作为一名.*?分析师[，,。]?',
        r'我将为你生成这份.*?报告[。.]?',
        r'我将根据您提供的.*?选手团队能力画像报告》?[。.]',
        r'我将基于您.*?数据[，,]',
        r'为您.*?报告[。.]',
        r'本报告为定性分析.*?[。.]',
        r'旨在深入解读.*?[。.]',
        r'与五维评分结果.*?[。.]',
        r'本报告基于路演全程的音视频融合数据[，,].*?描述性分析[。.]',
        r'报告内容独立于量化分数[，,].*?描述性分析[。.]',
        r'---\s*\n\s*###\s*\*\*选手团队能力画像报告\*\*',
        r'###\s*\*\*选手团队能力画像报告\*\*',
        r'###\s*选手团队能力画像报告',
        r'##\s*\*\*选手团队能力画像报告\*\*',
    ]
    for pattern in llm_noise_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)

    # 元信息单独渲染，正文里去掉重复行
    metadata_patterns = [
        r'^\s*\*\*项目名称\*\*[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*项目名称：[^\n]*(?:\n|$)',
        r'^\s*项目名称[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*赛道\*\*[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*赛道：[^\n]*(?:\n|$)',
        r'^\s*赛道[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*团队人数\*\*[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*团队人数：[^\n]*(?:\n|$)',
        r'^\s*团队人数[：:][^\n]*(?:\n|$)',
        r'^\s*\*\*评估分析师：\*\*[^\n]*(?:\n|$)',
    ]
    for pattern in metadata_patterns:
        cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE)

    # 压多余空行
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _add_deep_analysis_sections(story, result, s):
    """05 深度证据分析 - render evidence-backed content from the LLM contract."""
    ai_score = result.get('ai_score', {})
    evidence_audit = ai_score.get('evidence_audit') or []
    structure = ai_score.get('pitch_structure_benchmark') or []
    questions = ai_score.get('judge_questioning') or []
    action_plan = ai_score.get('action_plan') or []
    verdict = ai_score.get('final_verdict') or {}

    if not any([evidence_audit, structure, questions, action_plan, verdict]):
        return

    story.append(PageBreak())
    story.append(Paragraph('05', s['section_num']))
    story.append(Paragraph('深度证据分析', s['section_title']))
    story.append(Paragraph('围绕证据链、路演结构、评委追问和下一轮行动进行综合判断', s['section_desc']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5 * cm))

    summary = _value_text(verdict.get('summary') if isinstance(verdict, dict) else '')
    if summary:
        story.append(Paragraph(summary, ParagraphStyle(
            'DeepVerdict', parent=s['body'], fontName=_CN_FONT_BOLD,
            fontSize=10, leading=16, textColor=GRAY_900, spaceAfter=8)))

    if isinstance(verdict, dict):
        verdict_rows = []
        if verdict.get('defensible_strengths'):
            verdict_rows.append(['站得住脚的优势', verdict.get('defensible_strengths')])
        if verdict.get('critical_deductions'):
            verdict_rows.append(['关键扣分项', verdict.get('critical_deductions')])
        if verdict.get('next_round_focus'):
            verdict_rows.append(['下一轮优先补齐', verdict.get('next_round_focus')])
        _append_simple_table(story, ['类型', '结论'], verdict_rows, s, [3.2 * cm, 12.3 * cm])

    if evidence_audit:
        story.append(Paragraph('证据审计', s['h2']))
        rows = []
        for item in evidence_audit[:10]:
            if not isinstance(item, dict):
                continue
            rows.append([
                item.get('level', ''),
                item.get('claim', ''),
                item.get('source', ''),
                item.get('impact', ''),
            ])
        _append_simple_table(
            story,
            ['证据等级', '结论/问题', '来源', '影响'],
            rows,
            s,
            [2.2 * cm, 4.4 * cm, 5.2 * cm, 3.7 * cm],
        )

    if structure:
        story.append(Paragraph('路演结构对标', s['h2']))
        rows = []
        for item in structure[:8]:
            if not isinstance(item, dict):
                continue
            rows.append([
                item.get('stage', ''),
                item.get('score', ''),
                item.get('actual', ''),
                item.get('gap', ''),
                item.get('fix', ''),
            ])
        _append_simple_table(
            story,
            ['阶段', '评分', '实际表现', '差距', '改进'],
            rows,
            s,
            [2.2 * cm, 1.4 * cm, 4.0 * cm, 3.8 * cm, 4.1 * cm],
        )

    if questions:
        story.append(Paragraph('评委可能追问', s['h2']))
        rows = []
        for item in questions[:8]:
            if not isinstance(item, dict):
                continue
            rows.append([
                item.get('judge_type', ''),
                item.get('focus', ''),
                item.get('question', ''),
                item.get('prep_evidence', ''),
            ])
        _append_simple_table(
            story,
            ['评委视角', '关注点', '可能追问', '准备证据'],
            rows,
            s,
            [2.8 * cm, 3.0 * cm, 5.2 * cm, 4.5 * cm],
        )

    if action_plan:
        story.append(Paragraph('行动计划', s['h2']))
        rows = []
        for item in action_plan[:10]:
            if not isinstance(item, dict):
                continue
            rows.append([
                item.get('priority', ''),
                item.get('title', ''),
                item.get('method', ''),
                f'{item.get("owner", "")} / {item.get("timebox", "")}',
                item.get('acceptance', ''),
            ])
        _append_simple_table(
            story,
            ['优先级', '行动', '做法', '负责/时间', '验收'],
            rows,
            s,
            [1.4 * cm, 3.0 * cm, 5.0 * cm, 3.0 * cm, 3.1 * cm],
        )


def _add_jury_independent_review(story, result, s, sections: _SectionCounter):
    """仅当用户开启评审团且存在真实评审团结果时渲染。禁止 LLM 假评委。"""
    if not _jury_enabled(result):
        return
    jury_pkg = _real_jury_package(result)
    if not jury_pkg:
        return

    # 优先真实 score_cards / members；不回退 ai_score.jury_review
    cards = jury_pkg.get('score_cards') or jury_pkg.get('reviews') or []
    members = {
        str(m.get('code') or m.get('seat_no')): m
        for m in (jury_pkg.get('members') or []) if isinstance(m, dict)
    }
    n_judges = int(jury_pkg.get('judge_count') or len(cards) or len(members) or 0)

    story.append(PageBreak())
    _section_heading(
        story, sections, '评审团独立意见',
        f'本场已启用 AI 评审团，共 {n_judges} 位评委独立打分与点评。',
        s,
    )

    # 汇总条：AI 基准 vs 评审团去高低均分
    # 优先当前 ai_score（含 skill 画面局部重评后的分），勿被 jury 快照里旧 official_score 锁死
    official = (result.get('ai_score') or {}).get('overall_score')
    if official is None:
        official = jury_pkg.get('official_score')
    trimmed = jury_pkg.get('trimmed_average_score')
    raw_avg = jury_pkg.get('raw_average_score')
    diff = None
    if trimmed is not None and official is not None and official != '':
        try:
            diff = float(trimmed) - float(official)
        except Exception:
            diff = jury_pkg.get('score_diff_from_official')
    else:
        diff = jury_pkg.get('score_diff_from_official')
    summary_rows = []
    if official is not None and official != '':
        try:
            summary_rows.append(['AI 基准总分', f'{float(official):g} / 100'])
        except Exception:
            summary_rows.append(['AI 基准总分', str(official)])
    if trimmed is not None:
        try:
            summary_rows.append(['评审团去高低均分', f'{float(trimmed):g} / 100'])
        except Exception:
            summary_rows.append(['评审团去高低均分', str(trimmed)])
    if raw_avg is not None and trimmed is not None:
        try:
            summary_rows.append(['评审团原始均分', f'{float(raw_avg):g} / 100'])
        except Exception:
            pass
    if diff is not None:
        try:
            d = float(diff)
            summary_rows.append(['与基准分差', f'{d:+.1f}' if d != 0 else '0'])
        except Exception:
            summary_rows.append(['与基准分差', str(diff)])
    if summary_rows:
        _append_simple_table(
            story, ['指标', '结果'], summary_rows, s,
            [5.0 * cm, (CONTENT_W - 5.0) * cm],
        )

    if cards:
        story.append(Paragraph('各评委独立意见', s['h2']))
        for card in cards[:12]:
            if not isinstance(card, dict):
                continue
            code = str(card.get('code') or card.get('judge_code') or '')
            member = members.get(code) or {}
            role = (
                card.get('role_label')
                or member.get('role_label')
                or card.get('judge_type')
                or '评委'
            )
            title = f'{code + "　" if code else ""}{role}'.strip()
            score = card.get('overall_score', card.get('score', ''))
            try:
                score_txt = f'{float(score):g}' if score not in (None, '') else '—'
            except Exception:
                score_txt = _value_text(score) or '—'
            focus = _value_text(
                card.get('top_concerns') or card.get('focus') or member.get('focus_dimensions')
            )
            comment = _value_text(card.get('comment') or card.get('summary'))
            name_s = ParagraphStyle(
                'JuryCardName', parent=s['body'], fontName=_CN_FONT_BOLD,
                fontSize=10, leading=14, textColor=NAVY,
            )
            score_s = ParagraphStyle(
                'JuryCardScore', parent=s['body'], fontName=_CN_FONT_BOLD,
                fontSize=14, leading=16, alignment=TA_RIGHT, textColor=NAVY,
            )
            body_s = ParagraphStyle(
                'JuryCardBody', parent=s['body_small'], fontSize=8.5, leading=12.5,
                textColor=GRAY_900, wordWrap='CJK',
            )
            rows = [[
                Paragraph(_clean_inline(title), name_s),
                Paragraph(score_txt, score_s),
            ]]
            if focus:
                rows.append([_para(f'关注：{focus}', body_s), ''])
            if comment:
                rows.append([_para(comment, body_s), ''])
            style_cmds = [
                ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
                ('BACKGROUND', (0, 0), (-1, 0), GRAY_50),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]
            for row_idx in range(1, len(rows)):
                style_cmds.append(('SPAN', (0, row_idx), (1, row_idx)))
            card_t = Table(rows, colWidths=[(CONTENT_W - 2.6) * cm, 2.6 * cm])
            card_t.setStyle(TableStyle(style_cmds))
            story.append(KeepTogether([card_t, Spacer(1, 0.22 * cm)]))
    else:
        # 仅有 members 列表时展示阵容，不编造分数
        _add_jury_summary(story, result, s, sections, standalone=False)

    # 分歧度等汇总表（不另起章节号）
    if jury_pkg.get('dimension_stats') or (cards and jury_pkg.get('members')):
        # 确保 package 写回 result 供 summary 使用
        if not result.get('jury'):
            result['jury'] = jury_pkg
        _add_jury_summary(story, result, s, sections, standalone=False)


def _derive_structure_fix(comment: str) -> str:
    """从结构评价中抽出改进方向（转折后半句），不编造时间。"""
    t = (comment or '').strip()
    if not t:
        return ''
    # 优先取「但/然而/不过」之后
    m = re.search(r'[，,]?\s*(?:但|然而|不过|可是)\s*(.+)$', t)
    if m and len(m.group(1).strip()) >= 8:
        fix = m.group(1).strip()
        if not fix.endswith(('。', '！', '？')):
            fix += '。'
        return fix
    # 再找「缺少/未/无」起始的半句
    m2 = re.search(r'((?:缺少|未|无|缺乏).{8,})$', t)
    if m2:
        fix = m2.group(1).strip()
        if not fix.endswith(('。', '！', '？')):
            fix += '。'
        return fix
    return ''


def _add_pitch_structure_benchmark(story, result, s, sections: _SectionCounter):
    """结构对标：按本场路演叙事阶段展示评级与改进（用户可读，无内部字段名）。"""
    ai_score = result.get('ai_score', {})
    structure = ai_score.get('pitch_structure_benchmark') or []
    if not structure:
        return

    rows = []
    weakest = None
    weakest_severity = -1
    level_rank = {'优秀': 1, '良好': 2, '合格': 3, '待优化': 4, '薄弱': 5, '差': 6}
    has_any_time = False

    for item in structure[:10]:
        if not isinstance(item, dict):
            continue
        stage = _value_text(
            item.get('stage') or item.get('section') or item.get('name') or item.get('title')
        )
        actual = _value_text(
            item.get('actual') or item.get('comment') or item.get('performance')
            or item.get('description') or item.get('summary')
        )
        fix = _value_text(
            item.get('fix') or item.get('gap') or item.get('improvement')
            or item.get('suggestion') or item.get('action')
        )
        if not fix:
            fix = _derive_structure_fix(actual)
        score_raw = item.get('score')
        if score_raw in (None, ''):
            score_raw = item.get('score_or_level') or item.get('level') or item.get('rating')
        score_txt = _value_text(score_raw) if score_raw not in (None, '') else ''
        time_txt = _value_text(item.get('time_range') or item.get('time') or item.get('range'))
        if time_txt:
            has_any_time = True

        if not stage and not actual and not fix and not score_txt:
            continue
        if not (actual or fix or score_txt):
            continue
        rows.append({
            'stage': stage or '—',
            'time': time_txt or '',
            'score': score_txt or '—',
            'actual': actual or '—',
            'fix': fix or '—',
            '_raw': item,
            '_score_raw': score_raw,
        })
        if isinstance(score_raw, (int, float)):
            severity = 100.0 - float(score_raw)
        else:
            severity = float(level_rank.get(str(score_raw).strip(), 0))
        if severity > weakest_severity:
            weakest, weakest_severity = item, severity

    if not rows:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '路演结构对标分析', '', s)
    story.append(_callout_box(
        '按本场路演叙事阶段对照常见评审结构，标出评级、实际表现与改进方向，便于下一轮彩排补强。',
        s,
    ))
    story.append(Spacer(1, 0.2 * cm))

    if has_any_time:
        table_rows = [[r['stage'], r['time'] or '—', r['score'], r['actual'], r['fix']] for r in rows]
        _append_simple_table(
            story,
            ['阶段', '时间', '评级', '实际表现', '改进方向'],
            table_rows,
            s,
            [2.2 * cm, 1.8 * cm, 1.4 * cm, 5.6 * cm, (CONTENT_W - 11.0) * cm],
        )
    else:
        table_rows = [[r['stage'], r['score'], r['actual'], r['fix']] for r in rows]
        _append_simple_table(
            story,
            ['阶段', '评级', '实际表现', '改进方向'],
            table_rows,
            s,
            [2.4 * cm, 1.6 * cm, 6.8 * cm, (CONTENT_W - 10.8) * cm],
        )

    if weakest:
        w_stage = _value_text(
            weakest.get('stage') or weakest.get('section') or weakest.get('name')
        )
        w_score = _value_text(
            weakest.get('score') if weakest.get('score') not in (None, '')
            else weakest.get('score_or_level') or weakest.get('level')
        )
        w_note = _value_text(
            weakest.get('gap') or weakest.get('fix') or weakest.get('comment')
            or weakest.get('actual') or weakest.get('improvement')
        )
        story.append(_para(
            f'最大短板：{w_stage}'
            + (f'（{w_score}）' if w_score else '')
            + '。'
            + w_note,
            ParagraphStyle(
                'WeakestStructure', parent=s['body'], fontName=_CN_FONT_BOLD,
                textColor=DANGER, leading=14, fontSize=9.5, spaceBefore=6, wordWrap='CJK',
            ),
        ))


def _add_action_plan(story, result, s, sections: _SectionCounter):
    """行动计划：左侧固定序号徽章 + 标题 + 右侧 P0 胶囊（序号永不跑到行尾）。"""
    ai_score = result.get('ai_score', {})
    action_plan = ai_score.get('action_plan') or []
    if not action_plan:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '综合改进行动计划', '', s)

    title_s = ParagraphStyle(
        'ActTitle', parent=s['body'], fontName=_CN_FONT_BOLD, fontSize=10,
        leading=14, textColor=NAVY, wordWrap='CJK',
    )
    body_s = ParagraphStyle(
        'ActBody', parent=s['body_small'], fontSize=8.5, leading=12.5,
        textColor=GRAY_900, wordWrap='CJK',
    )
    muted_s = ParagraphStyle(
        'ActMuted', parent=s['body_small'], fontSize=8, leading=11.5,
        textColor=GRAY_500, wordWrap='CJK',
    )
    num_s = ParagraphStyle(
        'ActNum', fontName=_CN_FONT_BOLD, fontSize=10, leading=12,
        textColor=WHITE, alignment=TA_CENTER,
    )

    for idx, item in enumerate(action_plan[:10], 1):
        if not isinstance(item, dict):
            continue
        title = _value_text(item.get('title') or '改进动作')
        priority = str(item.get('priority') or '—').upper()
        if priority == 'HIGH':
            priority = 'P0'
        elif priority == 'MEDIUM':
            priority = 'P1'
        elif priority == 'LOW':
            priority = 'P2'

        # 左：序号徽章（固定宽）  中：标题  右：优先级胶囊
        num_badge = Table(
            [[Paragraph(f'{idx:02d}', num_s)]],
            colWidths=[0.85 * cm], rowHeights=[0.72 * cm],
        )
        num_badge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        header = Table([[
            num_badge,
            Paragraph(_clean_inline(title), title_s),
            _priority_pill(priority),
        ]], colWidths=[1.05 * cm, (CONTENT_W - 2.7) * cm, 1.35 * cm])
        header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 6),
            ('LEFTPADDING', (1, 0), (1, 0), 4),
            ('RIGHTPADDING', (1, 0), (1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))

        lines = [header]
        problem = _value_text(item.get('problem'))
        method = _value_text(item.get('method') or item.get('action'))
        expected = _value_text(
            item.get('expected') or item.get('expected_gain') or item.get('acceptance')
        )
        owner = _value_text(item.get('owner'))
        timebox = _value_text(item.get('timebox'))
        if problem:
            lines.append(_para(f'问题：{problem}', body_s))
        if method:
            lines.append(_para(f'动作：{method}', body_s))
        if owner or timebox:
            meta = ' · '.join(x for x in [
                f'负责人：{owner}' if owner else '',
                f'时限：{timebox}' if timebox else '',
            ] if x)
            lines.append(_para(meta, muted_s))
        if expected:
            lines.append(_para(f'预期：{expected}', muted_s))

        card = Table([[x] for x in lines], colWidths=[CONTENT_W * cm])
        card.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
            ('BACKGROUND', (0, 0), (-1, -1), WHITE),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ]))
        story.append(KeepTogether([card, Spacer(1, 0.16 * cm)]))


def _add_team_optimization(story, result, s, sections: _SectionCounter):
    ai_score = result.get('ai_score', {})
    routes = ai_score.get('team_optimization') or ai_score.get('team_role_optimization') or []
    if not routes:
        return

    rows = []
    for item in routes[:12]:
        if not isinstance(item, dict):
            continue
        role = _value_text(
            item.get('role') or item.get('owner') or item.get('member') or item.get('name')
        )
        issue = _value_text(
            item.get('issue') or item.get('currentIssue') or item.get('weakness')
            or item.get('gap') or item.get('problem')
        )
        training = _value_text(
            item.get('training') or item.get('optimizationAction') or item.get('action')
            or item.get('method') or item.get('suggestion')
        )
        target = _value_text(
            item.get('target') or item.get('goal') or item.get('expected') or item.get('outcome')
        )
        priority = _value_text(item.get('priority') or item.get('level') or item.get('rank'))
        # 至少要有角色 + 一项实质内容
        if not role and not (issue or training or target):
            continue
        if not (issue or training or target):
            continue
        rows.append([priority or '—', role or '—', issue or '—', training or '—', target or '—'])
    if not rows:
        return

    story.append(PageBreak())
    _section_heading(
        story, sections, '团队分工优化路线图',
        '按角色拆解训练动作，强化分工协同与临场补位能力。',
        s,
    )
    _append_simple_table(
        story,
        ['优先级', '角色', '短板', '训练动作', '目标'],
        rows,
        s,
        [1.5 * cm, 3.0 * cm, 3.5 * cm, 5.0 * cm, 2.5 * cm],
    )


def _verdict_cell_text(value) -> str:
    """结论表格单元格：列表分行，避免一长串挤在一行。"""
    if value is None:
        return ''
    if isinstance(value, list):
        parts = []
        for i, item in enumerate(value, 1):
            t = _value_text(item)
            if t:
                parts.append(f'{i}. {t}')
        return '<br/>'.join(parts)
    if isinstance(value, dict):
        return _value_text(value)
    text = _humanize_dimension_tokens(str(value).strip())
    # 分号拆成多行，便于阅读
    if '；' in text or ';' in text:
        bits = [b.strip() for b in re.split(r'[；;]+', text) if b.strip()]
        if len(bits) >= 2:
            return '<br/>'.join(f'· {b}' for b in bits)
    return text


def _add_final_verdict(story, result, s, sections: _SectionCounter):
    ai_score = result.get('ai_score', {})
    verdict = ai_score.get('final_verdict') or {}
    if not verdict:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '综合结论', '', s)

    has_real_jury = bool(_real_jury_package(result))
    summary = _value_text(verdict.get('summary') or (verdict.get('jury_summary') if has_real_jury else ''))
    if not summary and has_real_jury:
        summary = _value_text(verdict.get('jury_summary'))
    if summary:
        story.append(Paragraph(
            '综合判定' if not has_real_jury else '评审团与系统综合判定',
            s['h2'],
        ))
        story.append(_callout_box(_humanize_dimension_tokens(summary), s))
        story.append(Spacer(1, 0.25 * cm))

    rows = []
    if verdict.get('defensible_strengths'):
        rows.append(['站得住脚的优势', _verdict_cell_text(verdict.get('defensible_strengths'))])
    if verdict.get('critical_deductions'):
        rows.append(['关键扣分项', _verdict_cell_text(verdict.get('critical_deductions'))])
    if verdict.get('next_round_focus'):
        rows.append(['下一轮优先补齐', _verdict_cell_text(verdict.get('next_round_focus'))])
    if rows:
        # 直接用 Paragraph 表格，内容已含 <br/>
        head_style = ParagraphStyle(
            'VHead', parent=s['body_small'], fontName=_CN_FONT_BOLD,
            fontSize=8.5, leading=11, textColor=WHITE,
        )
        cell_style = ParagraphStyle(
            'VCell', parent=s['body_small'], fontSize=8.5, leading=12.5,
            textColor=GRAY_900, wordWrap='CJK',
        )
        tdata = [[
            Paragraph('类型', head_style),
            Paragraph('内容', head_style),
        ]]
        for lab, val in rows:
            tdata.append([
                Paragraph(_clean_inline(lab), cell_style),
                Paragraph(_clean_inline(str(val).replace('<br>', '<br/>')), cell_style),
            ])
        t = Table(tdata, colWidths=[3.2 * cm, (CONTENT_W - 3.2) * cm], repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_50]),
            ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, GRAY_300),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3 * cm))

    priority_actions = verdict.get('priority_actions') or []
    if priority_actions:
        rows = []
        for item in priority_actions[:8]:
            if not isinstance(item, dict):
                continue
            rows.append([
                item.get('priority', ''),
                item.get('item', ''),
                item.get('owner', ''),
                item.get('expected_gain', ''),
            ])
        if rows:
            story.append(Paragraph('优先动作', s['h2']))
            _append_simple_table(
                story, ['优先级', '改进项', '负责人', '预期提升'], rows, s,
                [2.0 * cm, 6.0 * cm, 3.5 * cm, (CONTENT_W - 11.5) * cm],
            )


def _add_priorities(story, result, s):
    """05 改进建议 — 统一 PRIORITY 格式，覆盖全部5个维度"""
    ai_score = result.get('ai_score', {})
    priorities = ai_score.get('improvement_priorities', [])
    dimensions = ai_score.get('dimensions', {})

    story.append(Spacer(1, 0.8*cm))
    story.append(Paragraph('06', s['section_num']))
    story.append(Paragraph('改进建议与训练计划', s['section_title']))
    story.append(Paragraph('按优先级排序的各维度改进方向，每项包含具体行动步骤', s['section_desc']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    tag_colors = {1: '#FF1744', 2: '#FF9100', 3: '#2196F3', 4: '#4CAF50', 5: '#9C27B0'}

    # 构建完整列表：先放 LLM 标注的高优先级，再补充缺失维度
    dim_order = ['skill_level', 'professionalism', 'application_value', 'teamwork', 'innovation']

    # 已被 LLM priorities 覆盖的维度
    covered_dims = set()
    merged = []

    # 按 priority 排序，转为统一结构（兼容字符串列表和对象列表）
    if priorities and isinstance(priorities[0], str):
        for i, text in enumerate(priorities):
            merged.append({'dimension': '', 'issue': '', 'suggestion': text})
    else:
        sorted_priorities = sorted(priorities, key=lambda x: x.get('priority', 99) if isinstance(x, dict) else 99)
        for p_item in sorted_priorities:
            if not isinstance(p_item, dict):
                merged.append({'dimension': '', 'issue': '', 'suggestion': str(p_item)})
                continue
            dim_name = p_item.get('dimension', '')
            covered_dims.add(dim_name)
            merged.append({
                'dimension': dim_name,
                'issue': p_item.get('issue', ''),
                'suggestion': p_item.get('suggestion', ''),
            })

    # 补充 LLM 未覆盖的维度（从 items 的 improvement 字段聚合）
    dim_name_to_key = {v.get('name', ''): k for k, v in dimensions.items()}
    for dim_key in dim_order:
        dim = dimensions.get(dim_key, {})
        dim_name = dim.get('name', '')
        if dim_name in covered_dims:
            continue
        items = dim.get('items', [])
        improvements = [item.get('improvement', '') for item in items if item.get('improvement', '').strip()]
        if improvements:
            merged.append({
                'dimension': dim_name,
                'issue': '',
                'suggestion': '；'.join(improvements),
            })

    # 统一渲染（P1-P5）
    for i, item in enumerate(merged):
        priority = i + 1
        tag_color = tag_colors.get(priority, '#2196F3')

        # 卡片式布局
        card_rows = []
        # 标题行
        card_rows.append([Paragraph(
            f'<font color="{tag_color}"><b>P{priority} {item["dimension"]}</b></font>',
            ParagraphStyle('PriorityTitle', parent=s['body'], fontName=_CN_FONT_BOLD,
                           fontSize=11, leading=16, textColor=HexColor(tag_color))
        )])

        if item['issue']:
            card_rows.append([Paragraph(
                f'<b>问题：</b>{item["issue"]}',
                ParagraphStyle('Issue', parent=s['body_small'], fontName=_CN_FONT,
                               fontSize=9, leading=14, textColor=GRAY_900)
            )])

        if item['suggestion']:
            card_rows.append([Paragraph(
                f'<b>建议：</b>{item["suggestion"]}',
                ParagraphStyle('Suggestion', parent=s['body_small'], fontName=_CN_FONT,
                               fontSize=9, leading=14, textColor=GRAY_700)
            )])

        # 渲染为卡片
        if card_rows:
            card = Table(card_rows, colWidths=[15.5*cm])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GRAY_100),
                ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
                ('LINEBEFORE', (0, 0), (0, -1), 3, HexColor(tag_color)),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(card)
            story.append(Spacer(1, 0.4*cm))


def _draw_fusion_chart(trends: dict, timeline: list, total_duration: float):
    """
    绘制音视频融合趋势图（双图）
    上图：肢体/表情/眼神/融合分（1-10分）
    下图：语速 + 停顿次数（不同量纲）
    """
    from reportlab.graphics.shapes import Drawing, Line, Circle, String, Rect, Polygon, Group
    from reportlab.lib.colors import HexColor

    if not trends or total_duration <= 0:
        return None

    # ── 参数 ──
    W = 16.5 * cm
    chart_h = 3.5 * cm     # 每个图高度
    gap = 0.8 * cm         # 图间距
    H = chart_h * 2 + gap + 2.8 * cm  # 总高度（含标题+图例+间距）
    ml = 1.2 * cm          # 左边距
    mr = 0.6 * cm          # 右边距
    usable_w = W - ml - mr
    total_min = total_duration / 60

    d = Drawing(W, H)

    # 背景
    # 背景
    d.add(Rect(0, 0, W, H, fillColor=HexColor("#FAFBFC"),
               strokeColor=None))
    # ── 标题（独立一行，顶部留足空间）──
    title_y = H - 16
    d.add(String(ml, title_y, '音视频融合趋势分析',
                 fontSize=9, fillColor=HexColor('#1F2937'),
                 fontName=_CN_FONT))

    # ── 颜色方案 ──
    COLORS = {
        'gesture':     HexColor('#3B82F6'),  # blue
        'expression':  HexColor('#10B981'),  # green
        'eye_contact': HexColor('#F59E0B'),  # amber
        'fusion':      HexColor('#8B5CF6'),  # purple
        'speech_rate': HexColor('#EF4444'),  # red
        'pauses':      HexColor('#6366F1'),  # indigo
    }
    LABELS = {
        'gesture': '肢体语言', 'expression': '表情自信',
        'eye_contact': '眼神接触', 'fusion': '融合总分',
        'speech_rate': '语速', 'pauses': '停顿次数',
    }

    # ── 数据聚合：将原始窗口合并为约 30 个点 ──
    def _aggregate(values, window=4):
        if not values:
            return []
        result = []
        for i in range(0, len(values), window):
            chunk = values[i:i+window]
            avg = sum(chunk) / len(chunk)
            result.append(round(avg, 1))
        return result

    agg_trends = {}
    for dim, data in trends.items():
        vals = data.get('values', [])
        if vals:
            agg_trends[dim] = _aggregate(vals, window=4)

    num_points = max((len(v) for v in agg_trends.values()), default=0)
    if num_points == 0:
        return None

    # ── Helper: 绘制折线 ──
    def _plot_line(chart_x, chart_y, chart_w, chart_h_val, values, color, y_min, y_max, dashed=False):
        n = len(values)
        if n < 2:
            return
        pts = []
        for i, v in enumerate(values):
            x = chart_x + (i / (n - 1)) * chart_w
            y = chart_y + ((v - y_min) / max(y_max - y_min, 1)) * chart_h_val
            pts.append((x, y))

        # 绘制面积填充（半透明效果通过浅色实现）
        fill_pts = [(pts[0][0], chart_y)]
        fill_pts.extend(pts)
        fill_pts.append((pts[-1][0], chart_y))
        fill_color = HexColor(color.hexval() + '20') if hasattr(color, 'hexval') else color
        try:
            d.add(Polygon(
                [coord for p in fill_pts for coord in p],
                fillColor=color, fillOpacity=0.08,
                strokeColor=None
            ))
        except:
            pass

        # 绘制折线
        for i in range(len(pts) - 1):
            d.add(Line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                       strokeColor=color, strokeWidth=1.5,
                       strokeDashArray=[3, 2] if dashed else None))

    # ── Helper: 绘制网格和轴 ──
    def _draw_axes(chart_x, chart_y, chart_w, chart_h_val, y_min, y_max, y_label, x_step_min=10):
        # 外框
        d.add(Line(chart_x, chart_y, chart_x + chart_w, chart_y,
                   strokeColor=HexColor('#E5E7EB'), strokeWidth=0.5))
        d.add(Line(chart_x, chart_y, chart_x, chart_y + chart_h_val,
                   strokeColor=HexColor('#E5E7EB'), strokeWidth=0.5))

        # Y轴刻度
        y_range = y_max - y_min
        if y_range <= 5:
            y_step = 1
        elif y_range <= 10:
            y_step = 2
        else:
            y_step = 5
        y_val = y_min
        while y_val <= y_max:
            yy = chart_y + ((y_val - y_min) / max(y_range, 1)) * chart_h_val
            d.add(Line(chart_x - 2, yy, chart_x + chart_w, yy,
                       strokeColor=HexColor('#F3F4F6'), strokeWidth=0.3))
            d.add(String(chart_x - 6, yy - 3, f'{y_val:.0f}',
                         fontSize=6, fillColor=HexColor('#9CA3AF'),
                         textAnchor='end', fontName='Helvetica'))
            y_val += y_step

        # X轴刻度（分钟）
        for m in range(0, int(total_min) + 1, x_step_min):
            xx = chart_x + (m / total_min) * chart_w
            d.add(Line(xx, chart_y - 2, xx, chart_y + chart_h_val,
                       strokeColor=HexColor('#F9FAFB'), strokeWidth=0.3))
            d.add(String(xx, chart_y - 12, f'{m}′',
                         fontSize=5.5, fillColor=HexColor('#9CA3AF'),
                         textAnchor='middle', fontName='Helvetica'))

        # Y轴标签
        d.add(String(chart_x - 8, chart_y + chart_h_val + 2, y_label,
                     fontSize=6, fillColor=HexColor('#6B7280'),
                     textAnchor='end', fontName=_CN_FONT))

    # ═══ 上图：评分维度（1-10）═══
    top_y = title_y - chart_h - 0.8 * cm
    top_h = chart_h - 0.3 * cm
    _draw_axes(ml, top_y, usable_w, top_h, 0, 10, '评分', x_step_min=10)

    score_dims = ['gesture', 'expression', 'eye_contact', 'fusion']
    for dim in score_dims:
        vals = agg_trends.get(dim, [])
        if vals:
            dashed = (dim == 'fusion')
            _plot_line(ml, top_y, usable_w, top_h, vals, COLORS[dim], 0, 10, dashed=dashed)

    # 上图标题 + 图例（在上图上方，不与主标题重叠）
    legend_y = top_y + top_h + 6
    d.add(String(ml, legend_y, '评分维度 (1-10分)',
                 fontSize=7, fillColor=HexColor('#374151'), fontName=_CN_FONT))
    lx = ml + 3.5 * cm
    for i, dim in enumerate(score_dims):
        x = lx + i * 2.8 * cm
        d.add(Line(x, legend_y + 3, x + 10, legend_y + 3, strokeColor=COLORS[dim], strokeWidth=1.5))
        d.add(String(x + 12, legend_y, LABELS[dim],
                     fontSize=6, fillColor=HexColor('#4B5563'), fontName=_CN_FONT))

    # ═══ 下图：语速 + 停顿 ═══
    bot_y = top_y - chart_h - gap + 0.3 * cm
    bot_h = chart_h - 0.3 * cm

    # 下图标题 + 图例（在下图上方）
    bot_legend_y = bot_y + bot_h + 6
    d.add(String(ml, bot_legend_y, '语速 & 停顿趋势',
                 fontSize=7, fillColor=HexColor('#374151'), fontName=_CN_FONT))
    lx2 = ml + 3.5 * cm
    for i, dim in enumerate(['speech_rate', 'pauses']):
        x = lx2 + i * 2.8 * cm
        d.add(Line(x, bot_legend_y + 3, x + 10, bot_legend_y + 3, strokeColor=COLORS[dim], strokeWidth=1.5))
        d.add(String(x + 12, bot_legend_y, LABELS[dim],
                     fontSize=6, fillColor=HexColor('#4B5563'), fontName=_CN_FONT))

    _draw_axes(ml, bot_y, usable_w, bot_h, 0, 10, '', x_step_min=10)

    # 语速（归一化到 0-10：200=0, 300=10）
    sr_vals = agg_trends.get('speech_rate', [])
    if sr_vals:
        sr_norm = [max(0, min(10, (v - 200) / 10)) for v in sr_vals]
        _plot_line(ml, bot_y, usable_w, bot_h, sr_norm, COLORS['speech_rate'], 0, 10)
        # 标注理想区间 (200-250 → 0-5)
        ideal_top_y = bot_y + 5 / 10 * bot_h
        ideal_bot_y = bot_y
        d.add(Rect(ml, ideal_bot_y, usable_w, ideal_top_y - ideal_bot_y,
                   fillColor=HexColor('#22C55E'), fillOpacity=0.06,
                   strokeColor=None))
        d.add(String(ml + 2, ideal_bot_y + 2, '理想区间 200-250',
                     fontSize=5, fillColor=HexColor('#16A34A'), fontName=_CN_FONT))

    # 停顿次数（归一化到 0-10：0=0, max=10）
    pause_vals = agg_trends.get('pauses', [])
    if pause_vals:
        p_max = max(pause_vals) if max(pause_vals) > 0 else 5
        p_norm = [v / p_max * 10 for v in pause_vals]
        _plot_line(ml, bot_y, usable_w, bot_h, p_norm, COLORS['pauses'], 0, 10, dashed=True)

    return d


def _add_fusion(story, result, s, sections: _SectionCounter):
    """音视频融合"""
    fusion = result.get('fusion', {})
    ai_fusion = result.get('ai_score', {}).get('audio_visual_fusion') or {}
    if (not fusion or 'error' in fusion) and not ai_fusion:
        return
    timeline = fusion.get('timeline', []) if fusion else []
    if not timeline and not ai_fusion:
        return

    duration = result.get('asr', {}).get('duration', 0)

    story.append(PageBreak())
    _section_heading(
        story, sections, '音视频融合分析',
        ai_fusion.get('summary') or '多模态矛盾检测：说的内容与现场呈现是否一致',
        s,
    )

    if ai_fusion and not timeline:
        contradictions = ai_fusion.get('contradictions') or []
        if contradictions:
            rows = []
            for item in contradictions[:10]:
                if not isinstance(item, dict):
                    continue
                rows.append([
                    item.get('time', ''),
                    item.get('description', ''),
                    item.get('audio_score', ''),
                    item.get('visual_score', ''),
                    item.get('gap', ''),
                ])
            _append_simple_table(story, ['时间', '矛盾描述', '音频分', '视觉分', '差距'], rows, s, [2.0*cm, 6.5*cm, 2.0*cm, 2.0*cm, 3.0*cm])
        metrics = ai_fusion.get('metrics') or []
        if metrics:
            rows = []
            for item in metrics[:8]:
                if not isinstance(item, dict):
                    continue
                rows.append([
                    item.get('name', ''),
                    item.get('average', ''),
                    item.get('low', ''),
                    item.get('high', ''),
                    item.get('trend', ''),
                ])
            _append_simple_table(story, ['指标', '均值/结论', '最低/风险', '最高/亮点', '趋势'], rows, s, [3.0*cm, 3.2*cm, 3.2*cm, 3.2*cm, 2.9*cm])
        return

    # ── 趋势图 ──
    trends = fusion.get('trends', {})
    if trends and duration > 0:
        chart = _draw_fusion_chart(trends, timeline, duration)
        if chart:
            story.append(chart)
            story.append(Spacer(1, 0.5*cm))

    # ── 音视频矛盾 ──
    contradictions = fusion.get('contradictions', [])
    if contradictions:
        story.append(Paragraph('音视频矛盾检测', s['h2']))
        story.append(Paragraph('当语音质量数据与视觉表现数据在同一时间窗口出现显著差异时触发矛盾检测，用于发现"说的与表现不一致"的情况，帮助评委从多维度理解选手的真实状态。', s['body']))
        story.append(Spacer(1, 0.3*cm))

        # 修正时间戳：原始数据 time_min 可能不准，用 timeline 总长重算
        total_fused = len(timeline)
        total_minutes = duration / 60 if duration > 0 else total_fused * 0.5

        # 去重 + 按时间排序
        seen = set()
        unique_contradictions = []
        for i, c in enumerate(contradictions):
            desc = c.get('description', '')
            key = desc[:30]
            if key not in seen:
                seen.add(key)
                # 根据在整个 contradictions 列表中的位置推算真实时间
                corrected_min = round(i / max(len(contradictions) - 1, 1) * total_minutes, 1)
                unique_contradictions.append({
                    'time_min': corrected_min,
                    'description': desc,
                    'audio_score': c.get('audio_score', 0),
                    'visual_score': c.get('visual_score', 0),
                })

        # 取间距均匀的前 8 条（避免全是开头的）
        if len(unique_contradictions) > 8:
            step = len(unique_contradictions) / 8
            sampled = [unique_contradictions[int(i * step)] for i in range(8)]
        else:
            sampled = unique_contradictions

        # 表格展示
        c_header = [
            Paragraph('<b>时间</b>', s['body_small']),
            Paragraph('<b>矛盾描述</b>', s['body_small']),
            Paragraph('<b>音频分</b>', s['body_small']),
            Paragraph('<b>视觉分</b>', s['body_small']),
            Paragraph('<b>差距</b>', s['body_small']),
        ]
        c_rows = [c_header]
        for c in sampled:
            t = c['time_min']
            m, sec = int(t), int((t % 1) * 60)
            desc = c['description']
            # 提取分数
            import re
            nums = re.findall(r'[\d.]+', desc)
            audio_s = nums[0] if len(nums) >= 1 else str(c.get('audio_score', '—'))
            visual_s = nums[1] if len(nums) >= 2 else str(c.get('visual_score', '—'))
            diff = round(float(audio_s) - float(visual_s), 1) if nums else 0
            diff_color = '#333333' if abs(diff) > 3 else '#616161'

            # 精简描述
            short_desc = desc.replace('语音表现好', '音频高').replace('视觉表现差', '视觉低')

            c_rows.append([
                Paragraph(f'{m:02d}:{sec:02d}', s['body_small']),
                Paragraph(short_desc, s['body_small']),
                Paragraph(f'<b>{audio_s}</b>', s['body_small']),
                Paragraph(f'<b>{visual_s}</b>', s['body_small']),
                Paragraph(f'<font color="{diff_color}"><b>{diff:+.1f}</b></font>', s['body_small']),
            ])

        ct = Table(c_rows, colWidths=[1.8*cm, 7*cm, 2*cm, 2*cm, 2*cm])
        ct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_100),
            ('LINEBELOW', (0, 0), (-1, 0), 1, GRAY_300),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_100]),
        ]))
        story.append(ct)

        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f'共检测到 {len(unique_contradictions)} 个矛盾点（已去重），'
            f'以上展示分布均匀的 {len(sampled)} 个',
            s['section_desc']
        ))
        story.append(Spacer(1, 0.5*cm))

    # ── 摘要统计 ──
    summary = fusion.get('summary', {})
    if summary:
        story.append(Paragraph('综合统计', s['h2']))
        story.append(Spacer(1, 0.3*cm))

        s_rows = [[
            Paragraph('<b>指标</b>', s['body_small']),
            Paragraph('<b>均值</b>', s['body_small']),
            Paragraph('<b>最低</b>', s['body_small']),
            Paragraph('<b>最高</b>', s['body_small']),
            Paragraph('<b>趋势</b>', s['body_small']),
        ]]
        for dim, label in [('gesture', '肢体语言'), ('expression', '表情自信'),
                           ('eye_contact', '眼神接触'), ('fusion', '融合总分')]:
            data = trends.get(dim, {})
            if data:
                avg_v = data.get('avg', 0)
                trend_icon = '↗' if avg_v >= 7 else '→' if avg_v >= 5 else '↘'
                s_rows.append([
                    Paragraph(label, s['body_small']),
                    Paragraph(f'{avg_v}', s['body_small']),
                    Paragraph(f'{data.get("min", 0)}', s['body_small']),
                    Paragraph(f'{data.get("max", 0)}', s['body_small']),
                    Paragraph(trend_icon, s['body_small']),
                ])
        st = Table(s_rows, colWidths=[3*cm, 2*cm, 2*cm, 2*cm, 2*cm])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_100),
            ('LINEBELOW', (0, 0), (-1, 0), 1, GRAY_300),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_100]),
        ]))
        story.append(st)

    story.append(Spacer(1, 0.6*cm))


def _add_character_profile(story, result, s, sections: _SectionCounter):
    """选手/角色能力画像：先渲染元信息表，再结构化 Markdown。"""
    profile = result.get('character_profile', {})
    raw_md = (profile.get('profile_markdown') or '') if profile else ''
    if not profile or 'error' in profile or not raw_md:
        return

    story.append(PageBreak())
    _section_heading(story, sections, '选手角色与能力画像', '', s)

    # 元信息：从原文抽取，做成干净两列表
    meta_rows = []
    for label, patterns in [
        ('项目名称', [r'项目名称[：:\*]*\s*([^\n]{2,80})']),
        ('赛道', [r'赛道[：:\*]*\s*([^\n]{2,40})']),
        ('团队人数', [r'团队人数[：:\*]*\s*([^\n]{1,20})']),
    ]:
        val = ''
        for p in patterns:
            m = re.search(p, raw_md)
            if m:
                val = re.sub(r'[\*\#]+', '', m.group(1)).strip()
                break
        if not val and label == '项目名称':
            val = _resolve_project_name(result)
        if val:
            meta_rows.append([label, val])
    if meta_rows:
        _append_simple_table(
            story, ['项', '内容'], meta_rows, s,
            [2.8 * cm, (CONTENT_W - 2.8) * cm],
        )

    profile_text = _clean_profile_markdown(raw_md)
    duration_min = 0
    try:
        duration_min = float((result.get('asr') or {}).get('duration') or 0) / 60
    except Exception:
        duration_min = 0

    before_count = len(story)
    _render_profile_markdown(story, profile_text, s, duration_min)

    if len(story) == before_count:
        for paragraph in _split_long_text(profile_text, 700)[:12]:
            cleaned = _clean_inline(paragraph)
            if cleaned:
                story.append(_para(cleaned, ParagraphStyle(
                    'ProfFallback', parent=s['body'], fontSize=9, leading=13.5, wordWrap='CJK',
                )))
                story.append(Spacer(1, 0.15 * cm))

    story.append(Spacer(1, 0.4 * cm))


def _add_personal_training_plan(story, result, s):
    """Retired: hidden per-speaker numeric scores are not a valid report source."""
    return

    # Kept temporarily as unreachable legacy layout code for old report migrations.
    speaker_scores = result.get('speaker_scores', [])
    if not speaker_scores:
        return

    story.append(PageBreak())
    story.append(Paragraph('08', s['section_num']))
    story.append(Paragraph('个人训练计划', s['section_title']))
    story.append(Paragraph('基于每位选手的路演表现，提供针对性的训练建议', s['section_desc']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    # 训练计划模板
    training_templates = {
        '表达': {
            'weak': '每天练习5分钟即兴演讲，录音回听，重点控制语速在200-250字/分钟',
            'medium': '准备演讲稿时标注重点词句，练习时用停顿代替填充词',
            'strong': '尝试用不同风格讲解同一内容，提升表达的适应性'
        },
        '逻辑': {
            'weak': '使用"总-分-总"结构组织内容，每段开头用一句话概括要点',
            'medium': '准备路演时画出逻辑流程图，确保每个论点都有证据支撑',
            'strong': '练习在答辩环节快速识别问题类型，用"定义-分析-结论"三步回答'
        },
        '创新': {
            'weak': '收集3个竞品案例，分析它们的创新点，找出差异化方向',
            'medium': '用"问题-方案-验证"三段式描述创新点，补充对比数据',
            'strong': '准备"创新日志"，记录每次迭代的动机、过程和效果'
        },
        '答辩': {
            'weak': '准备10个常见问题的标准答案，每天练习一遍',
            'medium': '模拟答辩时，先复述问题再回答，确保理解准确',
            'strong': '练习"承认不足+补充亮点"的回答策略，展示学习能力'
        },
        '团队': {
            'weak': '明确每位成员的发言时间和衔接话术，避免冷场',
            'medium': '设计2-3个团队互动环节，展示成员间的默契配合',
            'strong': '练习在演示故障时的团队配合，确保能快速切换角色'
        }
    }

    for speaker in speaker_scores:
        name = speaker.get('speakerLabel', '未知')
        role = speaker.get('normalizedRole', speaker.get('claimedRole', ''))
        dims = speaker.get('dimensions', {})

        # 选手卡片
        card_rows = []
        card_rows.append([Paragraph(
            f'<b>{name}</b>　<font color="#6B7280">{role}</font>',
            ParagraphStyle('SpeakerTitle', parent=s['body'], fontName=_CN_FONT_BOLD,
                           fontSize=11, leading=16, textColor=BLACK)
        )])

        # 各维度评分和训练建议
        for dim_name, score in dims.items():
            if score >= 80:
                level = 'strong'
                level_text = '优秀'
                level_color = '#00C853'
            elif score >= 60:
                level = 'medium'
                level_text = '良好'
                level_color = '#FF9100'
            else:
                level = 'weak'
                level_text = '待提升'
                level_color = '#FF1744'

            training = training_templates.get(dim_name, {}).get(level, '')

            card_rows.append([Paragraph(
                f'<b>{dim_name}</b>　<font color="{level_color}">{score}分 ({level_text})</font>',
                ParagraphStyle('DimScore', parent=s['body_small'], fontName=_CN_FONT,
                               fontSize=9, leading=13, textColor=GRAY_900)
            )])
            if training:
                card_rows.append([Paragraph(
                    f'训练建议：{training}',
                    ParagraphStyle('Training', parent=s['body_small'], fontName=_CN_FONT,
                                   fontSize=8.5, leading=12, textColor=GRAY_700, leftIndent=10)
                )])

        # 渲染为卡片
        if len(card_rows) > 1:
            card = Table(card_rows, colWidths=[15.5*cm])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GRAY_100),
                ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                # 标题行样式
                ('BACKGROUND', (0, 0), (-1, 0), WHITE),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, GRAY_300),
            ]))
            story.append(card)
            story.append(Spacer(1, 0.4*cm))

    story.append(Spacer(1, 0.6*cm))


def _render_profile_markdown(story, md_text, s, duration_min=0):
    """将画像 Markdown 渲染为 PDF 元素"""
    from reportlab.platypus import Table, TableStyle

    # ── 预处理：清理LLM废话 ──
    md_text = _clean_profile_markdown(md_text)

    # ── 预处理：修正时间戳（基于实际会议时长）──
    if duration_min > 2:
        time_pattern = re.compile(r'(\(0[\-–]\d+(?:\.\d+)?min.*?\))')
        old_ranges = time_pattern.findall(md_text)
        if old_ranges:
            phases = [
                (f'0-{duration_min*0.25:.0f}min'),
                (f'{duration_min*0.25:.0f}-{duration_min*0.5:.0f}min'),
                (f'{duration_min*0.5:.0f}-{duration_min*0.75:.0f}min'),
                (f'{duration_min*0.75:.0f}-{duration_min:.0f}min'),
            ]
            md_text = re.sub(r'\*\*预热期\s*\([\d.\-–]+min[^)]*\)', f'**预热期 ({phases[0]})', md_text)
            md_text = re.sub(r'\*\*高潮期\s*\([\d.\-–]+min[^)]*\)', f'**高潮期 ({phases[1]})', md_text)
            md_text = re.sub(r'\*\*分化期\s*\([\d.\-–]+min[^)]*\)', f'**分化期 ({phases[2]})', md_text)
            md_text = re.sub(r'\*\*收尾期\s*\([\d.\-–]+min[^)]*\)', f'**收尾期 ({phases[3]})', md_text)

    lines = md_text.split('\n')

    # ── 样式定义 ──
    stage_title_style = ParagraphStyle('StageTitle',
        parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=10, leading=15, spaceAfter=2,
        textColor=WHITE)

    stage_desc_style = ParagraphStyle('StageDesc',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=8.5, leading=13, spaceAfter=4,
        textColor=HexColor('#374151'),
        leftIndent=4)

    insight_style = ParagraphStyle('Insight',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=9, leading=14, spaceAfter=6,
        textColor=HexColor('#1F2937'),
        backColor=HexColor('#F9FAFB'),
        borderColor=HexColor('#D1D5DB'),
        borderWidth=0.5, borderPadding=8,
        leftIndent=4, rightIndent=4)

    # 阶段颜色 — SpaceX 风格：深灰阶，无鲜艳色彩
    STAGE_COLORS = {
        '预热期': HexColor('#374151'),   # gray-700
        '高潮期': HexColor('#1F2937'),   # gray-800
        '分化期': HexColor('#4B5563'),   # gray-600
        '收尾期': HexColor('#6B7280'),   # gray-500
    }

    def _render_numbered_section_block(sec_title: str, start_i: int) -> int:
        """将「7. 关键洞察 / 8. 改进建议」及其 1.2.3. 条目渲染为卡片块。"""
        tone = 'risk' if any(k in sec_title for k in ('问题', '短板', '风险', '扣分')) else (
            'action' if any(k in sec_title for k in ('改进', '建议', '行动', '训练')) else 'insight'
        )
        if tone == 'action':
            head_bg, head_fg, border, accent = HexColor('#FFF4EE'), ACCENT_DARK, HexColor('#F0D2C2'), ACCENT
        elif tone == 'risk':
            head_bg, head_fg, border, accent = HexColor('#FEF3F2'), HexColor('#B42318'), HexColor('#FECDCA'), HexColor('#F04438')
        else:
            head_bg, head_fg, border, accent = HexColor('#F4F4F5'), GRAY_900, GRAY_300, HexColor('#52525B')

        # 收集有序条目（支持续行）
        items = []
        j = start_i + 1
        while j < len(lines):
            raw = lines[j].rstrip()
            st = raw.strip()
            if not st:
                j += 1
                continue
            # 下一短标题节（如 8. 改进建议）
            if re.match(r'^(?:#{1,4}\s*)?\d{1,2}\.\s+.{2,24}$', st) and len(st) <= 30:
                break
            if st.startswith('## ') or st.startswith('### ') or st.startswith('#### '):
                break
            if st.startswith('---') or st.startswith('|'):
                break
            nm = re.match(r'^(\d+)\.\s*(.+)$', st)
            if nm:
                items.append(nm.group(2).strip())
                j += 1
                # 续行（空行允许续写一段）
                blank_streak = 0
                while j < len(lines):
                    cont = lines[j].rstrip()
                    cst = cont.strip()
                    if not cst:
                        blank_streak += 1
                        if blank_streak >= 2:
                            break
                        j += 1
                        continue
                    blank_streak = 0
                    if re.match(r'^\d+\.\s*', cst) or cst.startswith('#') or cst.startswith('---') or cst.startswith('|'):
                        break
                    if re.match(r'^(?:#{1,4}\s*)?\d{1,2}\.\s+.{2,24}$', cst) and len(cst) <= 36:
                        break
                    items[-1] = items[-1] + cst
                    j += 1
                continue
            # 非编号正文 → 收口
            break

        head = ParagraphStyle(
            'NumSecHead', parent=s['body_small'], fontName=_CN_FONT_BOLD,
            fontSize=11, leading=15, textColor=head_fg,
        )
        body = ParagraphStyle(
            'NumSecBody', parent=s['body_small'], fontSize=9, leading=13.5, textColor=GRAY_900,
        )
        idx_s = ParagraphStyle(
            'NumSecIdx', parent=s['body_small'], fontName=_CN_FONT_BOLD,
            fontSize=9, leading=12, textColor=head_fg, alignment=TA_CENTER,
        )

        story.append(Spacer(1, 0.28 * cm))
        title_bar = Table(
            [[Paragraph(_clean_inline(sec_title), head)]],
            colWidths=[15.5 * cm],
        )
        title_bar.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), head_bg),
            ('BOX', (0, 0), (-1, -1), 0.5, border),
            ('LINEBEFORE', (0, 0), (0, -1), 3, accent),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(title_bar)
        story.append(Spacer(1, 0.16 * cm))

        if not items:
            return j

        for n, item in enumerate(items[:8], 1):
            # 支持 **标题**：正文 / 标题：正文
            title_part, body_part = '', ''
            raw_item = item.strip()
            bold_m = re.match(r'^\*\*(.+?)\*\*\s*[：:]\s*(.+)$', raw_item, re.DOTALL)
            if bold_m:
                title_part, body_part = bold_m.group(1).strip(), bold_m.group(2).strip()
            else:
                for sep in ('：', ':'):
                    if sep in raw_item[:40]:
                        left, right = raw_item.split(sep, 1)
                        left_plain = re.sub(r'\*+', '', left).strip().strip('“”"')
                        if 2 <= len(left_plain) <= 32 and right.strip():
                            title_part, body_part = left_plain, right.strip()
                            break
            if not body_part:
                body_part = raw_item
                title_part = f'要点 {n}'
            title_part = re.sub(r'\*+', '', title_part).strip()
            # 仅去掉整段包裹引号，避免 strip('“”') 吃掉标题内引号
            if len(title_part) >= 2 and (
                (title_part[0] == '“' and title_part[-1] == '”')
                or (title_part[0] == '"' and title_part[-1] == '"')
                or (title_part[0] == '‘' and title_part[-1] == '’')
            ):
                title_part = title_part[1:-1].strip()

            idx_cell = Table(
                [[Paragraph(f'{n:02d}', idx_s)]],
                colWidths=[0.9 * cm], rowHeights=[0.9 * cm],
            )
            idx_cell.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), head_bg),
                ('BOX', (0, 0), (-1, -1), 0.4, border),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            text_flow = [
                Paragraph(f'<b>{_clean_inline(title_part)}</b>', ParagraphStyle(
                    'NumItemTitle', parent=body, fontName=_CN_FONT_BOLD, fontSize=9.5, leading=13, spaceAfter=2,
                )),
                Paragraph(_clean_inline(body_part), body),
            ]
            text_cell = Table([[x] for x in text_flow], colWidths=[13.8 * cm])
            text_cell.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            card = Table([[idx_cell, text_cell]], colWidths=[1.1 * cm, 14.0 * cm])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), WHITE),
                ('BOX', (0, 0), (-1, -1), 0.45, border),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            story.append(card)
            story.append(Spacer(1, 0.14 * cm))
        story.append(Spacer(1, 0.2 * cm))
        return j

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 空行
        if not line:
            i += 1
            continue

        # --- 分隔线
        if line.startswith('---'):
            i += 1
            continue

        # ## / ### 章节标题（统一海军蓝小节条）
        if line.startswith('## ') or line.startswith('### ') or line.startswith('#### '):
            title_text = re.sub(r'^#{2,4}\s*', '', line).strip()
            title_text = re.sub(r'^\*\*(.+)\*\*$', r'\1', title_text).strip()
            # 选手卡片
            if '选手' in title_text and not re.match(r'^\d{1,2}\.', title_text):
                lines[i] = '### ' + title_text
                i = _render_player_profiles(story, lines, i, s)
                continue
            # 带序号的洞察/画像等 → 编号块
            sec_m = re.match(r'^\d{1,2}\.\s*(.+)$', title_text)
            if sec_m and any(k in sec_m.group(1) for k in (
                '洞察', '改进', '建议', '结论', '画像', '表现', '关联', '分工', '语音', '视觉', '协作', '节奏'
            )):
                i = _render_numbered_section_block(sec_m.group(1).strip(), i)
                continue
            # 普通小节标题条
            story.append(Spacer(1, 0.28 * cm))
            bar = Table(
                [[Paragraph(
                    _clean_inline(title_text),
                    ParagraphStyle(
                        'ProfSecBar', parent=s['body'], fontName=_CN_FONT_BOLD,
                        fontSize=10.5, leading=14, textColor=NAVY,
                    ),
                )]],
                colWidths=[CONTENT_W * cm],
            )
            bar.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
                ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
                ('LINEBEFORE', (0, 0), (0, -1), 3.0, NAVY),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ]))
            story.append(bar)
            story.append(Spacer(1, 0.12 * cm))
            i += 1
            continue

        # 纯序号小节：1. 路演整体节奏分析 / 7. 关键洞察
        short_sec = re.match(r'^(\d{1,2})\.\s*(.{2,40})$', line)
        if short_sec and any(k in short_sec.group(2) for k in (
            '洞察', '改进', '建议', '结论', '画像', '表现', '关联', '分工', '语音', '视觉', '协作', '节奏', '分析'
        )):
            # 节奏分析等大节：用标题条 + 后续列表，不用强制编号卡片
            if any(k in short_sec.group(2) for k in ('节奏', '分析', '画像', '表现', '关联', '分工')):
                story.append(Spacer(1, 0.28 * cm))
                bar = Table(
                    [[Paragraph(
                        _clean_inline(short_sec.group(2).strip()),
                        ParagraphStyle(
                            'ProfSecBar2', parent=s['body'], fontName=_CN_FONT_BOLD,
                            fontSize=10.5, leading=14, textColor=NAVY,
                        ),
                    )]],
                    colWidths=[CONTENT_W * cm],
                )
                bar.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
                    ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
                    ('LINEBEFORE', (0, 0), (0, -1), 3.0, NAVY),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                ]))
                story.append(bar)
                story.append(Spacer(1, 0.12 * cm))
                i += 1
                continue
            i = _render_numbered_section_block(short_sec.group(2).strip(), i)
            continue

        # 有序列表（不在上述小节内时，仍卡片化）
        num_item = re.match(r'^(\d+)\.\s+(.+)$', line)
        if num_item and len(line) > 12:
            # 合成临时小节
            fake_title = '要点'
            # look ahead - if many numbered items, render as block starting here
            # simpler: single card
            n = int(num_item.group(1))
            content = num_item.group(2).strip()
            # gather continuation
            j = i + 1
            while j < len(lines):
                cont = lines[j].rstrip()
                cst = cont.strip()
                if not cst or re.match(r'^\d+\.\s+', cst) or cst.startswith('#') or cst.startswith('---'):
                    break
                if cont.startswith(' ') or cont.startswith('\t') or not re.match(r'^[0-9#\-\*|]', cst):
                    content += cst
                    j += 1
                    continue
                break
            card_rows = [[
                Paragraph(f'<b>{n:02d}</b>', ParagraphStyle('LoneIdx', parent=s['body_small'], fontName=_CN_FONT_BOLD, textColor=ACCENT_DARK)),
                Paragraph(_clean_inline(content), ParagraphStyle('LoneBody', parent=s['body_small'], fontSize=9, leading=13.5)),
            ]]
            ct = Table(card_rows, colWidths=[1.0 * cm, 14.5 * cm])
            ct.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FAFAFA')),
                ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(ct)
            story.append(Spacer(1, 0.12 * cm))
            i = j
            continue

        # 表格开始
        if line.startswith('|'):
            i = _render_table(story, lines, i, s)
            continue

        # 列表项（含阶段卡：热身期 / 特征 / 数据支撑）
        if line.startswith('- ') or line.startswith('* ') or re.match(r'^\*\s+', line):
            raw_item = re.sub(r'^[\*\-]\s+', '', line).strip()
            content = _clean_inline(raw_item)

            # 阶段标题：**名称 (时间)**： 或 **名称**：
            stage_match = re.match(
                r'^<b>(.+?)</b>\s*(?:\([^)]*\))?\s*[：:]?\s*(.*)$',
                content, re.DOTALL,
            )
            # 也匹配「热身与上升期 (0.0min - 3.0min)」无 bold 的情况
            phase_plain = re.match(
                r'^(.+?(?:期|阶段))\s*(\([^)]+\))?\s*[：:]?\s*$',
                re.sub(r'</?b>', '', content),
            )

            is_phase = False
            raw_name = ''
            stage_desc = ''
            if stage_match:
                raw_name = stage_match.group(1).strip()
                stage_desc = (stage_match.group(2) or '').strip()
                if any(k in raw_name for k in ('期', '阶段', '上升', '深潜', '收尾', '热身', '波动', '升华')):
                    is_phase = True
            elif phase_plain and any(k in phase_plain.group(1) for k in ('期', '阶段')):
                is_phase = True
                raw_name = phase_plain.group(1).strip()
                if phase_plain.group(2):
                    raw_name = f'{raw_name} {phase_plain.group(2)}'

            if is_phase:
                # 收集子项：特征 / 数据支撑
                child_rows = []
                if stage_desc:
                    child_rows.append(['说明', stage_desc])
                i += 1
                while i < len(lines):
                    sl = lines[i].strip()
                    if not sl:
                        i += 1
                        # 允许一个空行
                        if i < len(lines) and not lines[i].strip():
                            break
                        continue
                    if sl.startswith('##') or sl.startswith('###') or re.match(r'^\d+\.\s+', sl):
                        break
                    if sl.startswith('* ') or sl.startswith('- ') or re.match(r'^\*\s+', sl):
                        child_raw = re.sub(r'^[\*\-]\s+', '', sl).strip()
                        child_c = _clean_inline(child_raw)
                        plain_child = re.sub(r'</?b>', '', child_c)
                        # 下一阶段标题：不得吸入本阶段子表
                        phase_kw = ('期', '阶段', '上升', '深潜', '收尾', '热身', '波动', '升华')
                        cm2 = re.match(r'^<b>(.+?)</b>\s*[：:]?\s*(.*)$', child_c, re.DOTALL)
                        if cm2:
                            lab, val = cm2.group(1).strip(), (cm2.group(2) or '').strip()
                            if any(k in lab for k in phase_kw) and len(val) < 4:
                                break  # 不 i+=1，外层重开阶段卡
                            # 特征 / 数据支撑 等
                            child_rows.append([lab, val])
                            i += 1
                            while i < len(lines):
                                cont = lines[i].rstrip()
                                cst = cont.strip()
                                if not cst:
                                    break
                                if cst.startswith('*') or cst.startswith('-') or cst.startswith('#') or re.match(r'^\d+\.', cst):
                                    break
                                if cont.startswith(' ') or cont.startswith('\t') or not re.match(r'^[0-9#\-\*]', cst):
                                    child_rows[-1][1] = child_rows[-1][1] + cst
                                    i += 1
                                    continue
                                break
                            continue
                        if any(k in plain_child for k in phase_kw) and len(plain_child) < 48:
                            break
                        child_rows.append(['要点', plain_child])
                        i += 1
                        continue
                    break

                # 渲染阶段卡片
                head_p = Paragraph(
                    f'<b>{_clean_inline(raw_name)}</b>',
                    ParagraphStyle(
                        'PhaseHead', parent=s['body'], fontName=_CN_FONT_BOLD,
                        fontSize=9.5, leading=13, textColor=WHITE,
                    ),
                )
                header_bar = Table([[head_p]], colWidths=[CONTENT_W * cm])
                header_bar.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), NAVY_SOFT),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ]))
                story.append(header_bar)
                if child_rows:
                    lab_s = ParagraphStyle(
                        'PhaseLab', parent=s['body_small'], fontName=_CN_FONT_BOLD,
                        fontSize=8, leading=11, textColor=GRAY_500,
                    )
                    val_s = ParagraphStyle(
                        'PhaseVal', parent=s['body_small'], fontSize=8.5, leading=12.5,
                        textColor=GRAY_900, wordWrap='CJK',
                    )
                    body_data = [[
                        Paragraph(_clean_inline(a), lab_s),
                        _para(b, val_s),
                    ] for a, b in child_rows]
                    body_t = Table(body_data, colWidths=[1.8 * cm, (CONTENT_W - 1.8) * cm])
                    body_t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
                        ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_300),
                    ]))
                    story.append(body_t)
                story.append(Spacer(1, 0.18 * cm))
                continue

            # 普通列表：区分「分组副标题」与「条目内容卡」
            lab_match = re.match(r'^<b>(.+?)</b>\s*[：:]\s*(.*)$', content, re.DOTALL)
            item_lab = ParagraphStyle(
                'ProfItemLab', parent=s['body_small'], fontName=_CN_FONT_BOLD,
                fontSize=8.5, leading=12, textColor=NAVY, wordWrap='CJK',
            )
            item_body = ParagraphStyle(
                'ProfItemBody', parent=s['body_small'], fontSize=8.5, leading=12.5,
                textColor=GRAY_900, wordWrap='CJK',
            )
            sub_head_s = ParagraphStyle(
                'ProfSubHead', parent=s['body'], fontName=_CN_FONT_BOLD,
                fontSize=9.5, leading=13, textColor=NAVY, spaceBefore=6, spaceAfter=2,
            )

            def _is_group_subtitle(title: str, body: str) -> bool:
                """无正文或标题像分组名（启示/时刻/原因…）→ 副标题，不是内容卡。"""
                t = re.sub(r'[`*]', '', title or '').strip()
                b = (body or '').strip()
                if b and len(b) >= 8:
                    return False
                # 时刻条目本身是内容标题（含 min / 视觉分）
                if re.search(r'\d+\.?\d*\s*min', t, re.I):
                    return False
                if any(k in t for k in (
                    '时刻及启示', '原因及启示', '高度一致', '表现失调',
                    '及启示', '及原因', '总体判断', '综合来看',
                )):
                    return True
                # 空正文 + 较短标题
                if not b and 4 <= len(t) <= 36:
                    return True
                return False

            def _render_group_subtitle(title: str):
                """副标题：浅灰底 + 字重，无左竖条内容卡外观。"""
                t = re.sub(r'[`*]', '', title).strip().rstrip('：:')
                bar = Table(
                    [[Paragraph(_clean_inline(t), sub_head_s)]],
                    colWidths=[CONTENT_W * cm],
                )
                bar.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), HexColor('#EEF2FF')),
                    ('LINEBELOW', (0, 0), (-1, -1), 1.0, HexColor('#C7D2FE')),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(Spacer(1, 0.12 * cm))
                story.append(bar)
                story.append(Spacer(1, 0.08 * cm))

            if lab_match:
                title_t, body_t = lab_match.group(1).strip(), lab_match.group(2).strip()
                # 收集续行（仅当已有正文时）
                i += 1
                if body_t or not _is_group_subtitle(title_t, body_t):
                    while i < len(lines):
                        cont = lines[i].rstrip()
                        cst = cont.strip()
                        if not cst:
                            break
                        if cst.startswith('*') or cst.startswith('-') or cst.startswith('#') or re.match(r'^\d+\.', cst):
                            break
                        if cont.startswith(' ') or cont.startswith('\t') or not re.match(r'^[0-9#\-\*]', cst):
                            body_t = body_t + _clean_inline(cst)
                            i += 1
                            continue
                        break

                if _is_group_subtitle(title_t, body_t):
                    _render_group_subtitle(title_t)
                    continue

                # 内容卡：标题 + 正文
                rows = [[Paragraph(_clean_inline(re.sub(r'[`]', '', title_t)), item_lab)]]
                if body_t:
                    rows.append([_para(body_t, item_body)])
                card = Table(rows, colWidths=[CONTENT_W * cm])
                card.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
                    ('BOX', (0, 0), (-1, -1), 0.35, GRAY_300),
                    ('LINEBEFORE', (0, 0), (0, -1), 2.6, NAVY),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                story.append(card)
                story.append(Spacer(1, 0.1 * cm))
                continue
            else:
                plain = re.sub(r'</?b>', '', content).strip()
                # 「高度一致…：」类
                if plain.endswith('：') or plain.endswith(':'):
                    _render_group_subtitle(plain)
                elif _is_group_subtitle(plain, ''):
                    _render_group_subtitle(plain)
                else:
                    card = Table(
                        [[_para(f'· {plain}', item_body)]],
                        colWidths=[CONTENT_W * cm],
                    )
                    card.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), WHITE),
                        ('BOX', (0, 0), (-1, -1), 0.3, GRAY_300),
                        ('LINEBEFORE', (0, 0), (0, -1), 2.2, GRAY_400),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                    ]))
                    story.append(card)
                    story.append(Spacer(1, 0.08 * cm))
            i += 1
            continue

        # 关键洞察 callout
        if '**关键洞察**' in line or '关键洞察' in line:
            cleaned = _clean_inline(line)
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f'▪ {cleaned}', insight_style))
            story.append(Spacer(1, 0.2*cm))
            i += 1
            continue

        # 普通段落（含「标题：正文」→ 条目卡；空标题行 → 副标题）
        cleaned = _clean_inline(line)
        if cleaned:
            plain_only = re.sub(r'</?b>', '', cleaned).strip()
            # 分组副标题：以冒号结尾且无正文
            if re.match(r'^.{4,40}[：:]\s*$', plain_only) or (
                any(k in plain_only for k in ('时刻及启示', '原因及启示', '高度一致', '表现失调'))
                and len(plain_only) < 40 and 'min' not in plain_only.lower()
            ):
                t = plain_only.rstrip('：:').strip()
                bar = Table(
                    [[Paragraph(
                        _clean_inline(t),
                        ParagraphStyle(
                            'ProfSubHead2', parent=s['body'], fontName=_CN_FONT_BOLD,
                            fontSize=9.5, leading=13, textColor=NAVY,
                        ),
                    )]],
                    colWidths=[CONTENT_W * cm],
                )
                bar.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), HexColor('#EEF2FF')),
                    ('LINEBELOW', (0, 0), (-1, -1), 1.0, HexColor('#C7D2FE')),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(Spacer(1, 0.12 * cm))
                story.append(bar)
                story.append(Spacer(1, 0.08 * cm))
                i += 1
                continue

            # 无 markdown 列表前缀的「标签：长正文」
            plain_lab = re.match(r'^(?:<b>)?([^：:<]{2,24})(?:</b>)?[：:]\s*(.+)$', cleaned, re.DOTALL)
            if plain_lab and len(plain_lab.group(2).strip()) > 12:
                title_t, body_t = plain_lab.group(1).strip(), plain_lab.group(2).strip()
                if title_t not in ('项目名称', '赛道', '团队人数'):
                    item_lab = ParagraphStyle(
                        'ProfParaLab', parent=s['body_small'], fontName=_CN_FONT_BOLD,
                        fontSize=8.5, leading=12, textColor=NAVY, wordWrap='CJK',
                    )
                    item_body = ParagraphStyle(
                        'ProfParaBody', parent=s['body_small'], fontSize=8.5, leading=12.5,
                        textColor=GRAY_900, wordWrap='CJK',
                    )
                    card = Table([
                        [Paragraph(_clean_inline(title_t), item_lab)],
                        [_para(body_t, item_body)],
                    ], colWidths=[CONTENT_W * cm])
                    card.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), GRAY_50),
                        ('BOX', (0, 0), (-1, -1), 0.35, GRAY_300),
                        ('LINEBEFORE', (0, 0), (0, -1), 2.6, NAVY),
                        ('TOPPADDING', (0, 0), (-1, -1), 5),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                        ('LEFTPADDING', (0, 0), (-1, -1), 10),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]))
                    story.append(card)
                    story.append(Spacer(1, 0.1 * cm))
                    i += 1
                    continue
            story.append(_para(cleaned, ParagraphStyle(
                'ProfBody', parent=s['body'], fontSize=9, leading=13.5, wordWrap='CJK', spaceAfter=4,
            )))
        i += 1


def _render_player_profiles(story, lines, start_idx, s):
    """将选手段落（### 选手X + **bold** items）渲染为结构化卡片"""
    from reportlab.platypus import Table, TableStyle

    # 收集选手卡片数据
    players = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()

        # 遇到下一个 ## 标题，停止
        if line.startswith('## ') and i > start_idx:
            break

        # 遇到 ### / #### 但不是选手（如 ### 7. 关键洞察）→ 交回主循环
        if (line.startswith('### ') or line.startswith('#### ')) and i > start_idx:
            title_text = re.sub(r'^#{3,4}\s*', '', line)
            if '选手' not in title_text:
                break

        # 遇到 ### 选手，新建选手
        if (line.startswith('### ') or line.startswith('#### ')) and '选手' in line:
            name = _clean_inline(re.sub(r'^#{3,4}\s*', '', line).strip())
            players.append({'name': name, 'sections': []})
            i += 1
            continue

        if not players:
            i += 1
            continue

        current = players[-1]

        # 收集 bold 列表项作为分区
        if line.startswith('* ') or line.startswith('- '):
            content = _clean_inline(line[2:])
            # 检测 bold 标签: <b>标签</b>: 内容
            m = re.match(r'^<b>(.+?)</b>[：:](.*)', content, re.DOTALL)
            if m:
                current['sections'].append({
                    'label': m.group(1).strip(),
                    'text': m.group(2).strip()
                })
            else:
                # 子项：追加到上一个分区
                if current['sections']:
                    last = current['sections'][-1]
                    last['text'] += '<br/>' + content
            i += 1
            continue

        i += 1

    if not players:
        return i

    # ── 样式 ──
    name_style = ParagraphStyle('PProfName',
        parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=11, leading=16, textColor=BLACK)

    label_style = ParagraphStyle('PProfLabel',
        parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=8, leading=11, textColor=GRAY_900)

    text_style = ParagraphStyle('PProfText',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=8, leading=12, textColor=HexColor('#424242'))

    sep_style = ParagraphStyle('PProfSep',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=7, leading=10, textColor=HexColor('#BDBDBD'))

    # ── 渲染每位选手 ──
    for player in players:
        card_rows = []

        # 卡片标题行
        card_rows.append([Paragraph(f'<b>{player["name"]}</b>', name_style)])

        # 分隔线
        card_rows.append([Paragraph('─' * 50, sep_style)])

        # 各分区
        for sec in player['sections']:
            label = sec['label']
            text = sec['text'].replace('<br/>', '<br/>')

            # label + text 合并在一行
            card_rows.append([
                Paragraph(f'<b>{label}</b>：{text}', text_style)
            ])

        # 渲染为 Table 卡片
        if len(card_rows) <= 1:
            continue

        card = Table(card_rows, colWidths=[15.5*cm])
        card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FAFAFA')),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            # 标题行样式
            ('BACKGROUND', (0, 0), (-1, 0), GRAY_100),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ]))
        story.append(card)
        story.append(Spacer(1, 0.3*cm))

    return i


def _render_table(story, lines, start_idx, s):
    """将 Markdown 表格渲染为结构化的选手卡片"""
    # 解析所有表格行
    rows = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line or not line.startswith('|'):
            break
        cells = [c.strip() for c in line.split('|')[1:-1]]
        rows.append(cells)
        i += 1

    if len(rows) < 2:
        return i

    header = rows[0]
    data_rows = []
    for row in rows[1:]:
        if all(re.match(r'^[:\-]+$', c) for c in row):
            continue
        data_rows.append(row)

    # 检查是否是选手表格
    is_player_table = any('选手' in h or '角色' in h for h in header)

    if is_player_table and len(data_rows) > 0:
        _render_player_cards(story, header, data_rows, s)
    else:
        # 普通表格
        for row in data_rows:
            parts = []
            for j, cell in enumerate(row):
                h = header[j] if j < len(header) else ''
                cleaned = _clean_inline(cell)
                if cleaned:
                    parts.append(f'<b>{_clean_inline(h)}</b>: {cleaned}')
            if parts:
                story.append(Paragraph('　｜　'.join(parts), s['body_small']))

    return i


def _render_player_cards(story, header, data_rows, s):
    """将选手表格渲染为专业卡片（带颜色标识的分区布局）"""
    from reportlab.platypus import Table, TableStyle

    sec_colors = {
        '表现特征': HexColor('#F9FAFB'),  # gray-50
        '强项': HexColor('#F9FAFB'),
        '弱项': HexColor('#F9FAFB'),
        '改进建议': HexColor('#F9FAFB'),
    }
    sec_label_colors = {
        '表现特征': HexColor('#374151'),   # gray-700
        '强项': HexColor('#374151'),
        '弱项': HexColor('#6B7280'),      # gray-500
        '改进建议': HexColor('#6B7280'),
    }
    sec_icons = {
        '表现特征': '▪',
        '强项': '▲',
        '弱项': '▽',
        '改进建议': '→',
    }

    name_style = ParagraphStyle('PlayerName',
        parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=12, leading=18, textColor=BLACK)

    role_style = ParagraphStyle('PlayerRole',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=9, leading=13, textColor=HexColor('#6B7280'))

    section_title_style = ParagraphStyle('SecTitle',
        parent=s['body'], fontName=_CN_FONT_BOLD,
        fontSize=8.5, leading=12, textColor=GRAY_900)

    item_style = ParagraphStyle('SecItem',
        parent=s['body'], fontName=_CN_FONT,
        fontSize=8, leading=12, textColor=HexColor('#374151'),
        leftIndent=6)

    for row in data_rows:
        player_name = _clean_inline(row[0]) if len(row) > 0 else '—'
        time_range = _clean_inline(row[1]) if len(row) > 1 else ''
        role = _clean_inline(row[2]) if len(row) > 2 else ''

        # ── 卡片内容 ──
        card_elements = []

        # 头部：选手名 + 角色
        card_elements.append([Paragraph(f'{player_name}', name_style)])
        meta_parts = []
        if role:
            meta_parts.append(f'角色：{role}')
        if time_range:
            meta_parts.append(f'活跃时段：{time_range}')
        if meta_parts:
            card_elements.append([Paragraph('　｜　'.join(meta_parts), role_style)])

        # 各分区
        sections = []
        if len(row) > 3 and row[3]:
            sections.append(('表现特征', row[3]))
        if len(row) > 4 and row[4]:
            sections.append(('强项', row[4]))
        if len(row) > 5 and row[5]:
            sections.append(('弱项', row[5]))
        if len(row) > 6 and row[6]:
            sections.append(('改进建议', row[6]))

        for sec_title, sec_content in sections:
            icon = sec_icons.get(sec_title, '▸')
            label_color = sec_label_colors.get(sec_title, GRAY_900)

            # 分区标题
            card_elements.append([Paragraph(
                f'<font color="{label_color.hexval()}">{icon} {sec_title}</font>',
                section_title_style
            )])

            # 分区内容（按<br>拆分）
            items = re.split(r'<br\s*/?>', sec_content)
            for item in items:
                item = item.strip()
                if not item:
                    continue
                if item.startswith('- '):
                    item = item[2:]
                if item.startswith('* '):
                    item = item[2:]
                cleaned = _clean_inline(item)
                if cleaned:
                    card_elements.append([Paragraph(f'• {cleaned}', item_style)])

        # ── 用 Table 包裹成卡片 ──
        bg_color = GRAY_100
        card_table = Table(card_elements, colWidths=[15.5*cm])
        card_styles = [
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 0.5, GRAY_300),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]

        # 给分区标题行加左侧色条标识
        r = 2  # 前两行是名称和meta
        for sec_title, sec_content in sections:
            if r < len(card_elements):
                sc = sec_label_colors.get(sec_title, GRAY_900)
                card_styles.append(('LINEBEFORE', (0, r), (0, r), 2.5, sc))
            # 跳过分区标题 + items行
            items_count = len([x for x in re.split(r'<br\s*/?>', sec_content) if x.strip()])
            r += 1 + items_count

        card_table.setStyle(TableStyle(card_styles))
        story.append(card_table)
        story.append(Spacer(1, 0.5*cm))


def _add_team_topology(story, result, s):
    """08 团队分工优化路线图 — 极简风格"""
    from app.services.diagram_generator import generate_team_topology

    spec = generate_team_topology(result)
    if not spec:
        return

    story.append(PageBreak())
    story.append(Paragraph('08', s['section_num']))
    story.append(Paragraph('团队分工优化路线图', s['section_title']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    insight = spec.get('key_insight', '')
    if insight:
        story.append(Paragraph(insight, ParagraphStyle(
            'Insight', parent=s['body'], textColor=HexColor('#555555'),
            fontSize=9, spaceAfter=10)))

    _HEADER_STYLE = ParagraphStyle('TH', parent=s['body_small'],
        fontSize=7, textColor=HexColor('#AAAAAA'), fontName='Helvetica')

    for phase in spec.get('phases', []):
        label = f'{phase.get("id","")}  {phase.get("label","")}'
        story.append(Paragraph(f'<b>{label}</b>', ParagraphStyle(
            'PhaseL', parent=s['h2'], fontSize=10, spaceBefore=8, spaceAfter=3)))
        story.append(Spacer(1, 0.1*cm))

        table_data = [
            [Paragraph('行动', _HEADER_STYLE),
             Paragraph('负责', _HEADER_STYLE),
             Paragraph('具体做法', _HEADER_STYLE),
             Paragraph('验收标准', _HEADER_STYLE)],
        ]
        for action in phase.get('actions', []):
            table_data.append([
                Paragraph(action.get('action', ''), s['body_small']),
                Paragraph(action.get('owner', ''), s['body_small']),
                Paragraph(action.get('detail', ''), s['body_small']),
                Paragraph(action.get('metric', ''), s['body_small']),
            ])

        if table_data:
            cw = [2.8*cm, 1.5*cm, 8.2*cm, 3.5*cm]
            t = Table(table_data, colWidths=cw, repeatRows=1)
            t.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#222222')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, HexColor('#222222')),
                ('LINEBELOW', (0, 1), (-1, -2), 0.25, HexColor('#E8E8E8')),
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, HexColor('#CCCCCC')),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.4*cm))


def _add_timeline_flowchart(story, result, s):
    """09 路演结构对标分析 — 极简风格"""
    from app.services.diagram_generator import generate_timeline_flowchart

    spec = generate_timeline_flowchart(result)
    if not spec:
        return

    story.append(PageBreak())
    story.append(Paragraph('09', s['section_num']))
    story.append(Paragraph('路演结构对标分析', s['section_title']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    verdict = spec.get('verdict', '')
    if verdict:
        story.append(Paragraph(verdict, ParagraphStyle(
            'Verdict', parent=s['body'], textColor=HexColor('#555555'),
            fontSize=9, spaceAfter=10)))

    _HEADER_STYLE = ParagraphStyle('TH', parent=s['body_small'],
        fontSize=7, textColor=HexColor('#AAAAAA'), fontName='Helvetica')

    for phase in spec.get('phases', []):
        name = phase.get('name', '')
        time_range = phase.get('time', '')
        score = phase.get('score', '?')
        status = phase.get('status', 'fair')

        status_color = {'excellent':'#000000','good':'#444444','fair':'#888888','weak':'#AAAAAA'}
        sc = status_color.get(status, '#888888')

        story.append(Paragraph(
            f'{name}  <font color="#AAAAAA">{time_range}</font>'
            f'  <font color="{sc}">{score}分</font>',
            ParagraphStyle('PH', parent=s['h2'], fontSize=10,
                           spaceBefore=6, spaceAfter=2)))

        row_data = [
            [Paragraph('黄金标准', _HEADER_STYLE),
             Paragraph('实际表现', _HEADER_STYLE),
             Paragraph('差距', _HEADER_STYLE),
             Paragraph('改进方案', _HEADER_STYLE)],
            [Paragraph(phase.get('gold', ''), s['body_small']),
             Paragraph(phase.get('actual', ''), s['body_small']),
             Paragraph(phase.get('gap', ''), s['body_small']),
             Paragraph(phase.get('fix', ''), s['body_small'])],
        ]
        cw = [3.8*cm, 3.8*cm, 3.8*cm, 4.6*cm]
        t = Table(row_data, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('TEXTCOLOR', (0, 1), (-1, 1), HexColor('#222222')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, HexColor('#222222')),
            ('LINEBELOW', (0, 1), (-1, 1), 0.25, HexColor('#E8E8E8')),
        ]))
        story.append(t)

        example = phase.get('example', '')
        if example:
            story.append(Paragraph(
                f'<font color="#888888">话术示例：</font>'
                f'<font color="#333333"><i>"{example}"</i></font>',
                ParagraphStyle('Ex', parent=s['body_small'], fontSize=7,
                               textColor=HexColor('#333333'), spaceBefore=2)))
        story.append(Spacer(1, 0.4*cm))


def _add_improvement_mindmap(story, result, s):
    """10 综合改进行动计划 — 极简风格"""
    from app.services.diagram_generator import generate_improvement_mindmap

    spec = generate_improvement_mindmap(result)
    if not spec:
        return

    story.append(PageBreak())
    story.append(Paragraph('10', s['section_num']))
    story.append(Paragraph('综合改进行动计划', s['section_title']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    outcome = spec.get('outcome', '')
    if outcome:
        story.append(Paragraph(outcome, ParagraphStyle(
            'Outcome', parent=s['body'], textColor=HexColor('#555555'),
            fontSize=9, spaceAfter=10)))

    # 关键路径
    story.append(Paragraph('<b>关键路径</b>', s['h2']))
    story.append(Spacer(1, 0.2*cm))

    _HEADER_STYLE = ParagraphStyle('TH', parent=s['body_small'],
        fontSize=7, textColor=HexColor('#AAAAAA'), fontName='Helvetica')

    cp_data = [[
        Paragraph('#', _HEADER_STYLE),
        Paragraph('行动', _HEADER_STYLE),
        Paragraph('负责 / 时间', _HEADER_STYLE),
        Paragraph('具体做法', _HEADER_STYLE),
        Paragraph('验收标准', _HEADER_STYLE),
    ]]
    for step in spec.get('critical_path', []):
        cp_data.append([
            Paragraph(f'<font color="#CCCCCC">{step.get("step",""):02d}</font>',
                      ParagraphStyle('N', parent=s['body_small'],
                                     fontSize=8, fontName='Courier')),
            Paragraph(step.get('action', ''), s['body_small']),
            Paragraph(f'{step.get("owner","")} / {step.get("when","")}', s['body_small']),
            Paragraph(step.get('how', ''), s['body_small']),
            Paragraph(step.get('verify', ''), s['body_small']),
        ])

    if cp_data:
        cp_widths = [0.8*cm, 2.5*cm, 2.5*cm, 7.5*cm, 2.7*cm]
        t = Table(cp_data, colWidths=cp_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#222222')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, HexColor('#222222')),
            ('LINEBELOW', (0, 1), (-1, -2), 0.25, HexColor('#E8E8E8')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, HexColor('#CCCCCC')),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

    # 并行任务线
    for track in spec.get('parallel_tracks', []):
        track_name = track.get('track', '')
        story.append(Paragraph(f'<b>{track_name}</b>', ParagraphStyle(
            'Tr', parent=s['h2'], fontSize=9, spaceBefore=6, spaceAfter=3)))

        tdata = [[
            Paragraph('行动', _HEADER_STYLE),
            Paragraph('负责 / 时间', _HEADER_STYLE),
            Paragraph('具体做法', _HEADER_STYLE),
        ]]
        for item in track.get('items', []):
            tdata.append([
                Paragraph(item.get('action', ''), s['body_small']),
                Paragraph(f'{item.get("owner","")} / {item.get("when","")}', s['body_small']),
                Paragraph(item.get('how', ''), s['body_small']),
            ])
        if tdata:
            tw = [3.5*cm, 2.5*cm, 10*cm]
            t = Table(tdata, colWidths=tw, repeatRows=1)
            t.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#222222')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, HexColor('#222222')),
                ('LINEBELOW', (0, 1), (-1, -2), 0.25, HexColor('#E8E8E8')),
                ('LINEBELOW', (0, -1), (-1, -1), 0.5, HexColor('#CCCCCC')),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.4*cm))

    synergy = spec.get('synergy', '')
    if synergy:
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(synergy, ParagraphStyle(
            'Syn', parent=s['body'], textColor=HexColor('#555555'),
            fontSize=8)))

def _add_jury_summary(story, result, s, sections: _SectionCounter | None = None, standalone: bool = True):
    """真实评审团队概览（仅 jury_enabled + 真结果）。"""
    if not _jury_enabled(result):
        return
    jury = _real_jury_package(result)
    if not jury:
        return

    if standalone:
        story.append(PageBreak())
        if sections is None:
            sections = _SectionCounter()
        _section_heading(
            story, sections, '评审团队概览',
            f'{jury.get("judge_count", 0)} 位 AI 评委独立评分（用户已启用评审团）',
            s,
        )

    # 评委列表
    members = jury.get('members', [])
    if members:
        story.append(Paragraph('评委阵容', s['h2']))
        story.append(Spacer(1, 0.3*cm))

        m_header = [
            Paragraph('<b>座位</b>', s['body_small']),
            Paragraph('<b>类型代码</b>', s['body_small']),
            Paragraph('<b>评委类型</b>', s['body_small']),
            Paragraph('<b>关注维度</b>', s['body_small']),
        ]
        m_rows = [m_header]
        for m in members:
            focus_raw = m.get('focus_dimensions') or m.get('rubric_focus') or []
            dim_cn = _format_focus_dimensions_zh(focus_raw)
            m_rows.append([
                Paragraph(str(m.get('seat_no', '')), s['body_small']),
                Paragraph(_clean_inline(str(m.get('code', ''))), s['body_small']),
                Paragraph(_clean_inline(str(m.get('role_label', ''))), s['body_small']),
                Paragraph(_clean_inline(dim_cn), s['body_small']),
            ])
        mt = Table(m_rows, colWidths=[1.5*cm, 2.5*cm, 4*cm, 6*cm])
        mt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('LINEBELOW', (0, 0), (-1, 0), 0, NAVY),
            ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, GRAY_300),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_50]),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.6*cm))

    # 评委评分分布
    score_cards = jury.get('score_cards', [])
    if score_cards:
        story.append(Paragraph('各评委评分', s['h2']))
        story.append(Spacer(1, 0.3*cm))

        sc_header = [
            Paragraph('<b>评委</b>', s['body_small']),
            Paragraph('<b>总分</b>', s['body_small']),
            Paragraph('<b>第一关注点</b>', s['body_small']),
        ]
        sc_rows = [sc_header]
        for card in score_cards:
            concern = ''
            tc = card.get('top_concerns') or []
            if isinstance(tc, list) and tc:
                concern = _value_text(tc[0])
            elif isinstance(tc, str):
                concern = tc
            if not concern:
                concern = _value_text(card.get('comment') or card.get('summary') or '')[:80]
            try:
                sc = float(card.get('overall_score') if card.get('overall_score') is not None else card.get('score') or 0)
                sc_txt = f'{sc:.1f}'
            except Exception:
                sc_txt = _value_text(card.get('overall_score') or card.get('score') or '—')
            sc_rows.append([
                Paragraph(_clean_inline(str(card.get('role_label', ''))), s['body_small']),
                Paragraph(sc_txt, s['body_small']),
                Paragraph(_clean_inline(concern or '—'), s['body_small']),
            ])
        sct = Table(sc_rows, colWidths=[4*cm, 2*cm, 8*cm])
        sct.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, GRAY_300),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_50]),
        ]))
        story.append(sct)
        story.append(Spacer(1, 0.6*cm))

    # 维度分歧分析
    dim_stats = jury.get('dimension_stats', [])
    if dim_stats:
        story.append(Paragraph('维度分歧分析', s['h2']))
        story.append(Paragraph('分歧越大说明评委对该维度的看法差异越大，越值得重点准备', s['section_desc']))
        story.append(Spacer(1, 0.3*cm))

        ds_header = [
            Paragraph('<b>维度</b>', s['body_small']),
            Paragraph('<b>均分</b>', s['body_small']),
            Paragraph('<b>最高</b>', s['body_small']),
            Paragraph('<b>最低</b>', s['body_small']),
            Paragraph('<b>分歧度</b>', s['body_small']),
        ]
        ds_rows = [ds_header]
        for dim in dim_stats:
            range_val = dim.get('range', 0)
            range_color = '#FF1744' if range_val > 5 else '#FF9100' if range_val > 3 else '#616161'
            dim_name = _dimension_display_name(dim.get('key') or '', dim.get('name') or '')
            ds_rows.append([
                Paragraph(_clean_inline(dim_name), s['body_small']),
                Paragraph(f'{dim.get("average_score", 0):.1f}', s['body_small']),
                Paragraph(f'{dim.get("highest_score", 0):.1f}', s['body_small']),
                Paragraph(f'{dim.get("lowest_score", 0):.1f}', s['body_small']),
                Paragraph(f'<font color="{range_color}"><b>{range_val:.1f}</b></font>', s['body_small']),
            ])
        dst = Table(ds_rows, colWidths=[3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm])
        dst.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('BOX', (0, 0), (-1, -1), 0.4, GRAY_300),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, GRAY_300),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_50]),
        ]))
        story.append(dst)

    story.append(Spacer(1, 0.6*cm))


def _add_transcript_appendix(story, result, s):
    """附录 原文"""
    transcript = result.get('asr', {}).get('transcript', '')
    if not transcript:
        return

    story.append(PageBreak())
    story.append(Paragraph('附录', s['section_num']))
    story.append(Paragraph('路演文字记录', s['section_title']))
    story.append(Paragraph('自动整理的路演文字记录，仅用于复盘核对', s['section_desc']))
    story.append(_draw_divider())
    story.append(Spacer(1, 0.5*cm))

    chunk_size = 3000
    for i in range(0, len(transcript), chunk_size):
        chunk = transcript[i:i + chunk_size]
        story.append(Paragraph(chunk, s['body_small']))


# ════════════════════════════════════════
#  入口
# ════════════════════════════════════════

def refresh_report_after_jury(meeting_id: str) -> str:
    """评审团落盘后重出 PDF，否则完成时下载的还是无评委章的报告。"""
    from app.config import settings

    mid = str(meeting_id or "").strip()
    if not mid:
        raise ValueError("meeting_id required")
    result_path = os.path.join(settings.UPLOAD_DIR, "results", f"result_{mid}.json")
    if not os.path.isfile(result_path):
        raise FileNotFoundError(result_path)
    with open(result_path, encoding="utf-8") as handle:
        result = json.load(handle)
    if not isinstance(result, dict):
        raise TypeError("result must be dict")
    result["jury_enabled"] = True
    report_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    report_path = generate_report(result, report_dir)
    result["report_path"] = report_path
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False)
    return report_path


def generate_report(result: dict, output_dir: str) -> str:
    """从评分结果 JSON 生成 PDF。默认走 HTML 排版，失败时回退 reportlab。"""
    if not isinstance(result, dict):
        raise TypeError('result must be dict')
    engine = (os.getenv('OREP_REPORT_ENGINE') or 'html').strip().lower()
    if engine in ('html', 'playwright', 'auto'):
        try:
            from app.services.html_report import generate_html_report
            return generate_html_report(result, output_dir)
        except Exception as exc:
            print(f'[PdfReport] html engine failed, fallback reportlab: {exc}')
            if os.getenv('OREP_REPORT_HTML_REQUIRED') == '1':
                raise
    return _generate_reportlab(result, output_dir)


def _generate_reportlab(result: dict, output_dir: str) -> str:
    """旧版 Platypus PDF。叙事与章节号规则保持不变。"""
    result = dict(result)
    meeting_id = result.get('meeting_id', 'unknown')
    filename = f'report_{meeting_id}.pdf'
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    # 音画证据对齐：历史评分文案消歧（不暴露抽帧机密）
    try:
        from app.services.evidence_alignment_service import sanitize_result_for_report
        result = sanitize_result_for_report(result)
    except Exception as exc:
        print(f'[PdfReport] evidence alignment skipped: {exc}')

    # 未开启评审团：剔除 LLM/backfill 的假评委，防止任何路径误用
    if not _jury_enabled(result):
        ai = result.get('ai_score')
        if isinstance(ai, dict):
            ai = dict(ai)
            ai.pop('jury_review', None)
            fv = ai.get('final_verdict')
            if isinstance(fv, dict):
                fv = dict(fv)
                # 未开评委时不用「九评委」文案字段当主结论标题来源
                if fv.get('summary'):
                    fv.pop('jury_summary', None)
                ai['final_verdict'] = fv
            result['ai_score'] = ai
    else:
        # 开启评审团：从磁盘 jury_session 挂载真实结果（与 web 同源）
        result = _attach_jury_package(result)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=2.0 * cm, rightMargin=2.0 * cm,
        topMargin=1.9 * cm, bottomMargin=1.8 * cm,
    )

    s = _styles()
    story = []
    sections = _SectionCounter()

    _add_cover(story, result, s)
    _add_overview(story, result, s, sections)
    _add_evidence_summary(story, result, s, sections)
    _add_dimension_detail(story, result, s, sections)
    _add_speech_quality(story, result, s, sections)
    _add_highlights(story, result, s, sections)
    _add_jury_independent_review(story, result, s, sections)
    _add_fusion(story, result, s, sections)
    _add_pitch_structure_benchmark(story, result, s, sections)
    _add_action_plan(story, result, s, sections)
    _add_team_optimization(story, result, s, sections)
    _add_character_profile(story, result, s, sections)
    _add_final_verdict(story, result, s, sections)
    include_transcript = result.get('include_transcript_appendix') or os.getenv('OREP_REPORT_INCLUDE_TRANSCRIPT_APPENDIX') == '1'
    if include_transcript:
        _add_transcript_appendix(story, result, s)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)

    file_size = os.path.getsize(filepath)
    print(f'[PdfReport] 报告已生成: {filepath} ({file_size / 1024:.1f} KB) sections={sections.n}')

    return filepath
