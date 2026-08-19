"""通用查询锚点：地理/主题提示 + 轻护栏（Grok 主路径下不做硬绑架）。

设计原则：
- **不写死**任何省份、赛道、机构名表
- 行政区划靠形态：…省|市|自治区|…（拒绝疑问/比较等功能前缀误抽）
- 主题靠用户问题中的非地理长短语 / 核心词
- 默认 soft：排序与轻过滤；offtopic（旅游/百科门户）仍可硬否决
- 多地理：单条 hit 命中任一地理即可（对比题两侧都能进池）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_GEO_SUFFIX = r"特别行政区|自治区|地区|盟|州|省|市|县|区"
# 短词干+后缀：避免「比较一下…省」整段吞并
_GEO_RE = re.compile(rf"([\u4e00-\u9fff]{{2,4}}(?:{_GEO_SUFFIX}))")
# 功能/疑问/连词：不是地名词干
_GEO_BAD_PREFIX = re.compile(
    r"^(比较|对比|对照|有什么|是什么|什么|哪些|如何|怎么|一下|区别|之间|以及|还有|关于|与|和|及|的|在)"
)
_GEO_BAD_CONTAIN = re.compile(r"比较|有什么|是什么|区别|怎么样|哪些|如何|一下")
_STOP_ORAL = re.compile(
    r"网上有没有|有没有|能不能|可不可以|帮我搜|帮我找|帮我|请给我|请问|谢谢|"
    r"搜一下|查一下|查找|搜索|找一下|查查|信息|相关|资料|"
    r"请基于官方来源回答|请基于官方来源|若搜不到请如实说明|请如实说明|"
    r"基于官方来源回答|基于官方来源|如实说明|官方来源"
)
# 短语级口语尾巴/整段指令
_PHRASE_ORAL = re.compile(
    r"(是什么|怎么样|有哪些|如何|请基于.*|若搜不到.*|请如实.*|帮我.*|谢谢)$"
)
_PHRASE_ORAL_FULL = re.compile(
    r"^(请基于|若搜不到|请如实|帮我|请问|谢谢|是什么|怎么样|有哪些|如何|"
    r"官方来源|如实说明|回答)"
)
_YEAR_RE = re.compile(r"20\d{2}")
_SOFT_ONLY = frozenset(
    {
        "信息",
        "相关",
        "资料",
        "内容",
        "情况",
        "结果",
        "名单",
        "公示",
        "通知",
        "官网",
        "最新",
        "关于",
        "一下",
        "搜索",
        "查找",
    }
)
# 用户问题若含这些主题信号，命中结果不得是明显离题页
_TOPIC_SIGNAL_RE = re.compile(
    r"技能|大赛|竞赛|赛项|备赛|获奖|路演|职教|职业院校|实训|规程|报名"
)
# 结果侧离题信号（通用噪声，非业务白名单）
_OFFTOPIC_RE = re.compile(
    r"旅游|旅行|游记|景点|景区|酒店|美食|百科|天气预报|房产|买房|股票|彩票|"
    r"相亲|娱乐|明星|购物|机票|火车票|地图导览|必玩|好玩景点"
)
# 仅门户/频道首页、无主题时易误伤；与主题信号组合否决
_PORTAL_HOME_RE = re.compile(
    r"人民政府门户|政务服务网|频道_|新闻网$|首页$|百度百科|互动百科"
)
# open 选链：门户/考试院「壳页」形态（非业务白名单）
_PORTAL_SHELL_TITLE_RE = re.compile(
    r"(?:人民政府(?:门户网站)?|门户网站|教育考试院|招生考试院|"
    r"政务服务网|考生服务平台|网站首页)(?:官网)?$"
)
_PORTAL_SHELL_LOOSE_RE = re.compile(
    r"人民政府$|教育考试院|招生考试院|考生服务平台|普通高校招生|"
    r"门户网站|政务公开$|服务平台$"
)
# 实质内容页信号（有则不算壳）
_SUBSTANTIVE_PAGE_RE = re.compile(
    r"通知|公示|名单|公告|办法|意见|决定|职责|职能|纲要|规划|"
    r"报告|赛道|获奖|技能大赛|竞赛|规程|报名|附件|文号|"
    r"金奖|银奖|铜奖|三定|机构设置|主要职责"
)
_HOME_PATH_RE = re.compile(
    r"^https?://[^/]+/?(?:index(?:\.(?:html?|shtml|jsp|aspx))?|home(?:\.html?)?)?$",
    re.I,
)
_FULL_LIST_DEMAND_RE = re.compile(
    r"(全部|完整|逐条|逐队|逐个|一份不漏|不得遗漏|必须列出|完整名单|金奖队伍完整)"
)
_LIST_INTENT_RE = re.compile(r"名单|队伍|金奖|银奖|铜奖|获奖")


@dataclass
class QueryAnchors:
    required: list[str] = field(default_factory=list)  # 地理提示（可多选，单 hit 命中任一即可）
    content_phrases: list[str] = field(default_factory=list)  # 主题长短语
    content_tokens: list[str] = field(default_factory=list)
    years: list[str] = field(default_factory=list)
    topic_required: bool = False  # 问题是否带明确主题（大赛/技能…）

    def is_empty(self) -> bool:
        return not self.required and not self.content_phrases and not self.content_tokens


def _stem_geo(phrase: str) -> str:
    s = (phrase or "").strip()
    s = re.sub(
        r"(特别行政区|壮族自治区|回族自治区|维吾尔自治区|自治区|地区|盟|州|省|市|县|区)$",
        "",
        s,
    )
    return s if len(s) >= 2 else phrase


def _is_clean_geo_phrase(g: str) -> bool:
    """地名形态校验：拒绝疑问/比较整段误抽。"""
    g = (g or "").strip()
    # 剥书名号/引号/括号等外壳
    g = re.sub(r"^[「『\"'“‘（(\[【]+", "", g)
    g = re.sub(r"[」』\"'”’）)\]】]+$", "", g)
    g = g.strip()
    if len(g) < 2 or len(g) > 12:
        return False
    stem = _stem_geo(g)
    if len(stem) < 2 or len(stem) > 6:
        return False
    if _GEO_BAD_PREFIX.search(stem) or _GEO_BAD_PREFIX.search(g):
        return False
    if _GEO_BAD_CONTAIN.search(g):
        return False
    # 纯「什么区/哪个市」类
    if stem in ("什么", "哪个", "哪些", "有关", "相关", "地区", "区域"):
        return False
    # 残片：以引号/标点开头
    if re.search(r"^[「『\"'“‘\W]", g) or re.search(r"\W$", stem):
        return False
    return True


def extract_geo_phrases(user_query: str) -> list[str]:
    """从问题中抽出干净行政区划列表（可多个）。

    在后缀处回看 2～4 字词干，避免「一下河南省」被整段吞掉。
    """
    raw = user_query or ""
    found: list[str] = []
    occupied: list[tuple[int, int]] = []
    suffix_re = re.compile(_GEO_SUFFIX)
    for m in suffix_re.finditer(raw):
        end = m.end()
        # 从短词干到长词干，先命中更干净的「河南+省」
        picked = ""
        pick_s = -1
        for stem_len in (2, 3, 4):
            s = m.start() - stem_len
            if s < 0:
                continue
            g = raw[s:end]
            if _is_clean_geo_phrase(g):
                picked = g
                pick_s = s
                break
        if not picked:
            continue
        # 规范化外壳（与 _is_clean_geo_phrase 一致）
        cleaned = re.sub(r"^[「『\"'“‘（(\[【]+", "", picked)
        cleaned = re.sub(r"[」』\"'”’）)\]】]+$", "", cleaned).strip()
        if not cleaned or not _is_clean_geo_phrase(cleaned):
            continue
        if any(not (end <= a or pick_s >= b) for a, b in occupied):
            continue
        if cleaned not in found:
            found.append(cleaned)
            occupied.append((pick_s, end))
        if len(found) >= 4:
            break
    return found


def _strip_geo_prefix(phrase: str, required: list[str]) -> str:
    """从短语前剥掉已识别的行政区划，得到纯主题段。"""
    p = phrase or ""
    for g in required:
        if p.startswith(g):
            p = p[len(g) :]
        stem = _stem_geo(g)
        if stem and p.startswith(stem):
            p = p[len(stem) :]
    return p


def clean_content_phrase(phrase: str) -> str:
    """清洗主题短语：去口语尾巴与指令碎片。"""
    p = (phrase or "").strip()
    if not p:
        return ""
    p = _STOP_ORAL.sub("", p)
    p = _PHRASE_ORAL.sub("", p)
    p = re.sub(r"(是什么|怎么样|有哪些|如何)[？?！!。.\s]*", "", p)
    p = re.sub(r"[?？!！。，,\s]+", "", p)
    if _PHRASE_ORAL_FULL.search(p):
        return ""
    if p in _SOFT_ONLY or len(p) < 2:
        return ""
    return p


def extract_query_anchors(user_query: str) -> QueryAnchors:
    raw = (user_query or "").strip()
    years = list(dict.fromkeys(_YEAR_RE.findall(raw)))
    topic_required = bool(_TOPIC_SIGNAL_RE.search(raw))

    required = extract_geo_phrases(raw)

    t = _STOP_ORAL.sub(" ", raw)
    t = re.sub(r"(是什么|怎么样|有哪些|如何)[？?！!。.\s]*", " ", t)
    t = _YEAR_RE.sub(" ", t)
    t = re.sub(r"[?？!！。，,、；;：:\"'“”‘’]", " ", t)
    t = re.sub(r"[的了吗呢吧啊呀]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    phrases: list[str] = []
    for m in re.finditer(r"[\u4e00-\u9fff]{4,}", t):
        p = m.group()
        p = re.sub(r"^[年月日号位]+", "", p)
        p = re.sub(r"[年月日]+$", "", p)
        p = clean_content_phrase(p)
        if len(p) < 4 or p in _SOFT_ONLY:
            continue
        if p in required:
            continue
        # 去掉地理前缀，避免把「地名+主题」整段当地名
        topic_p = _strip_geo_prefix(p, required)
        topic_p = re.sub(r"^[年月日号位]+", "", topic_p)
        topic_p = clean_content_phrase(topic_p)
        if len(topic_p) >= 4 and topic_p not in _SOFT_ONLY:
            if topic_p not in phrases and len(topic_p) <= 16:
                phrases.append(topic_p)
            if len(topic_p) > 8:
                short8 = clean_content_phrase(topic_p[:8])
                if short8 and short8 not in phrases and len(short8) >= 4:
                    phrases.append(short8)
        elif p not in phrases and len(p) <= 16:
            phrases.append(p)
        if len(phrases) >= 8:
            break

    # 若主题信号存在但短语仍空，从信号词合成
    if topic_required and not phrases:
        for sig in ("职业院校技能大赛", "技能大赛", "职业院校", "竞赛"):
            if sig in raw.replace(" ", "") or all(c in raw for c in sig[:2]):
                if sig in raw or sig[:4] in raw:
                    phrases.append(sig if sig in raw else "技能大赛")
                    break
        if not phrases and "技能" in raw and "大赛" in raw:
            phrases.append("技能大赛")

    tokens: list[str] = []
    for m in re.finditer(r"[\u4e00-\u9fff]{2,3}|[A-Za-z0-9_]{2,}", t):
        tok = m.group()
        if _YEAR_RE.fullmatch(tok):
            continue
        if tok in _SOFT_ONLY:
            continue
        if _PHRASE_ORAL_FULL.search(tok):
            continue
        # 跳过纯地理词干
        if any(tok == _stem_geo(g) or tok == g for g in required):
            continue
        if tok not in tokens:
            tokens.append(tok)

    return QueryAnchors(
        required=required,
        content_phrases=phrases,
        content_tokens=tokens,
        years=years,
        topic_required=topic_required,
    )


def _blob_of(hit: dict[str, Any]) -> str:
    title = str(hit.get("title") or "")
    snip = str(hit.get("snippet") or hit.get("pageText") or "")
    return f"{title} {snip}"


def _required_matched(blob: str, req: str) -> bool:
    if not req:
        return True
    if req in blob:
        return True
    stem = _stem_geo(req)
    if stem and stem != req and stem in blob:
        return True
    return False


def _geo_matched_any(blob: str, anchors: QueryAnchors) -> bool:
    """多地理：命中任一即可；单地理：必须命中。无地理：True。"""
    if not anchors.required:
        return True
    return any(_required_matched(blob, r) for r in anchors.required)


def _topic_matched(blob: str, anchors: QueryAnchors) -> bool:
    """主题是否命中：长短语优先，含同义扩展，否则多个主题 token。"""
    if not anchors.content_phrases and not anchors.content_tokens:
        return not anchors.topic_required
    # 同义扩展：职业院校技能大赛 ↔ 高等职业教育技能大赛 等
    expanded: list[str] = []
    for p in anchors.content_phrases:
        if p:
            expanded.append(p)
            expanded.extend(_topic_synonyms(p, p))
    for p in expanded:
        if p and len(p) >= 4 and p in blob:
            return True
    # 关键主题碎片：技能+大赛 / 竞赛 / 职教 等
    strong = [t for t in anchors.content_tokens if t in (
        "技能", "大赛", "竞赛", "赛项", "备赛", "职教", "获奖", "路演", "规程", "报名"
    ) or (len(t) >= 3 and t in blob)]
    hit_strong = sum(1 for t in strong if t in blob)
    if hit_strong >= 2:
        return True
    if hit_strong >= 1 and any(
        x in blob
        for x in (
            "技能大赛",
            "职业院校",
            "高等职业教育",
            "高职",
            "竞赛",
            "赛项",
            "获奖名单",
        )
    ):
        return True
    # 短语子串：技能大赛 拆开都在
    if "技能" in blob and "大赛" in blob and (
        any("技能" in (p or "") for p in anchors.content_phrases)
        or "技能" in " ".join(anchors.content_tokens)
        or anchors.topic_required
    ):
        return True
    token_hits = sum(
        1 for tok in anchors.content_tokens if len(tok) >= 2 and tok in blob
    )
    # 主题 query 需要更严：不能只靠一个虚 token
    need = 2 if anchors.topic_required else 1
    return token_hits >= need


def _is_offtopic_for_query(query: str, blob: str, anchors: QueryAnchors) -> bool:
    if not anchors.topic_required and not _TOPIC_SIGNAL_RE.search(query or ""):
        return False
    if _OFFTOPIC_RE.search(blob):
        return True
    if _PORTAL_HOME_RE.search(blob) and not _topic_matched(blob, anchors):
        return True
    return False


def hit_passes_anchors(
    hit: dict[str, Any],
    anchors: QueryAnchors | None,
    *,
    strict: bool = True,
) -> bool:
    """相关性判断。

    strict=True：主题问句要主题；单地理要该地理；多地理命中任一地理即可。
    strict=False：更松，仍否决明显 offtopic。
    """
    if anchors is None or anchors.is_empty():
        return True
    blob = _blob_of(hit)
    if not blob.strip():
        return False

    fake_q = " ".join(anchors.required + anchors.content_phrases)
    if _is_offtopic_for_query(fake_q, blob, anchors):
        return False

    geo_ok = _geo_matched_any(blob, anchors)
    topic_ok = _topic_matched(blob, anchors)
    phrase_hits = sum(1 for p in anchors.content_phrases if p and p in blob)
    token_hits = sum(
        1 for tok in anchors.content_tokens if len(tok) >= 2 and tok in blob
    )

    if anchors.years:
        has_year = any(y in blob for y in anchors.years)
        if has_year and not topic_ok and not anchors.required and not phrase_hits:
            return False

    if not strict:
        # soft：单地理仍要求地理（防错省）；多地理命中任一；无地理则主题/英文 token
        if len(anchors.required) == 1 and not geo_ok:
            # 无地理命中：仅当像英文文档（无中文主题大赛语境）才放行
            if anchors.topic_required:
                return False
            return token_hits >= 2
        if anchors.topic_required or anchors.content_phrases:
            if topic_ok:
                return True
            if anchors.required and geo_ok and (phrase_hits + token_hits) >= 1:
                return True
            return token_hits >= 2 or phrase_hits >= 1
        if anchors.required:
            return geo_ok or token_hits >= 1
        return phrase_hits >= 1 or token_hits >= 1

    # strict：防错省糊弄 —— 单地理必须命中该地理；多地理命中任一
    if anchors.required and not geo_ok:
        return False
    if anchors.required and (anchors.topic_required or anchors.content_phrases):
        return topic_ok
    if anchors.required:
        return topic_ok or phrase_hits >= 1 or token_hits >= 1
    if anchors.topic_required or anchors.content_phrases:
        return topic_ok
    return phrase_hits >= 1 or token_hits >= min(
        2, max(1, len(anchors.content_tokens) // 3 or 1)
    )


def filter_hits_by_anchors(
    hits: list[dict[str, Any]] | None,
    anchors: QueryAnchors | None,
    *,
    strict: bool = True,
) -> list[dict[str, Any]]:
    if not hits:
        return []
    return [h for h in hits if isinstance(h, dict) and hit_passes_anchors(h, anchors, strict=strict)]


def looks_like_portal_shell(hit: dict[str, Any] | None) -> bool:
    """是否像门户/考试院首页壳（无通知/名单等实质标题）。

    形态规则：有实质信号则不算壳；不写死省份域名。
    """
    if not isinstance(hit, dict):
        return False
    title = str(hit.get("title") or "").strip()
    snip = str(hit.get("snippet") or hit.get("pageText") or "")[:200]
    url = str(hit.get("url") or "").strip()
    blob = f"{title} {snip}"
    if _SUBSTANTIVE_PAGE_RE.search(blob):
        return False
    if _PORTAL_SHELL_TITLE_RE.search(title) or _PORTAL_SHELL_LOOSE_RE.search(title):
        return True
    if _HOME_PATH_RE.match(url) and (
        _PORTAL_SHELL_LOOSE_RE.search(title) or len(title) <= 12
    ):
        return True
    # 标题极短且 URL 像站点根
    if len(title) <= 8 and re.search(r"^https?://[^/]+/?$", url, re.I):
        return True
    return False


def portal_shell_rank_penalty(hit: dict[str, Any] | None, query: str = "") -> int:
    """排序扣分：主题问句下门户壳大幅降权（open 选链用）。"""
    if not looks_like_portal_shell(hit):
        return 0
    q = query or ""
    # 问职责/域名时官网首页可接受，轻罚
    if re.search(r"域名|官网|职责|职能|是什么部门|门户", q) and not re.search(
        r"名单|通知|公示|赛道|获奖|规模|完整|全部", q
    ):
        return 2
    # 名单/通知/政策类：重罚，避免先 open 考试院/政府首页
    if re.search(r"名单|通知|公示|大赛|技能|赛道|获奖|政策|报告|对比|比较", q):
        return 14
    return 6


def is_full_list_demand(user_query: str) -> bool:
    """用户是否要求完整/逐条名单（C19 类），非业务表。"""
    q = user_query or ""
    if not _FULL_LIST_DEMAND_RE.search(q):
        return False
    return bool(_LIST_INTENT_RE.search(q))


def _evidence_has_pdf(e: dict[str, Any]) -> bool:
    url = str(e.get("url") or "").lower()
    if ".pdf" in url:
        return True
    atts = e.get("attachments") if isinstance(e.get("attachments"), list) else []
    return any(
        isinstance(a, dict) and ".pdf" in str(a.get("url") or "").lower() for a in atts
    )


def _title_is_list_notice(title: str) -> bool:
    t = title or ""
    if not re.search(r"名单|公示|公布", t):
        return False
    # 须像正式通知/公示，而非纯门户
    return bool(re.search(r"通知|公示|公布|办公室|教育厅|教育部|关于", t)) or (
        "名单" in t and re.search(r"获奖|拟获奖|大赛|竞赛", t)
    )


def evidence_has_list_notice_with_pdf(
    evidence: list[dict[str, Any]] | None,
) -> bool:
    """是否同时具备「名单类通知/公示」与 PDF 附件（可 enough 写「名单见 PDF」）。

    形态规则：不写死机构域名。
    """
    has_notice = False
    has_pdf = False
    for e in evidence or []:
        if not isinstance(e, dict):
            continue
        title = str(e.get("title") or "")
        if looks_like_portal_shell(e) and not _title_is_list_notice(title):
            # 纯壳不计入通知；壳上挂 PDF 极少见
            if _evidence_has_pdf(e):
                has_pdf = True
            continue
        if _title_is_list_notice(title) or (
            "附件" in title and re.search(r"名单|公示|获奖", title)
        ):
            has_notice = True
        if _evidence_has_pdf(e):
            has_pdf = True
        # 同页：通知标题 + 附件 PDF
        if _title_is_list_notice(title) and _evidence_has_pdf(e):
            return True
    return has_notice and has_pdf


def evidence_has_list_substance(
    evidence: list[dict[str, Any]] | None,
    *,
    require_enumerable: bool = False,
) -> bool:
    """证据是否具备可引用的名单实质（正文/PDF），非仅门户或空通知壳。

    require_enumerable=True（完整/逐条名单需求）：须 PDF/附件，或正文含多条奖项/队名，
    不能仅靠「公布名单」短通知标题。
    """
    if evidence_has_list_notice_with_pdf(evidence):
        return True
    for e in evidence or []:
        if not isinstance(e, dict):
            continue
        title = str(e.get("title") or "")
        text = str(e.get("pageText") or e.get("snippet") or "")
        if _evidence_has_pdf(e):
            return True
        if looks_like_portal_shell(e):
            continue
        award_n = text.count("金奖") + text.count("银奖") + text.count("铜奖")
        # 多条奖项/队伍信号即视为名单实质
        if award_n >= 2 or re.search(r"(第一名|一等奖|拟获奖)", text):
            return True
        if len(text) >= 200 and (
            text.count("\n") >= 6 or "获奖名单" in text or "名单如下" in text
        ):
            return True
        if require_enumerable:
            # 完整名单：短通知标题不够
            continue
        if e.get("fetched") and len(text) >= 120 and (
            "名单" in title or "公示" in title or "公布" in title
        ):
            return True
    return False


def rank_hits_soft(
    hits: list[dict[str, Any]] | None,
    anchors: QueryAnchors | None,
    query: str = "",
) -> list[dict[str, Any]]:
    """Grok 主路径：不过度硬滤，按相关度排序；仅丢掉明显 offtopic；门户壳降权。"""
    if not hits:
        return []
    a = anchors or extract_query_anchors(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for h in hits:
        if not isinstance(h, dict):
            continue
        blob = _blob_of(h)
        fake_q = " ".join(a.required + a.content_phrases) or (query or "")
        if _is_offtopic_for_query(fake_q, blob, a):
            continue
        geo_ok = _geo_matched_any(blob, a)
        # 单地理问句：他省/全国主题页不进池（防糊弄）；多地理则任一侧可进
        if len(a.required) == 1 and not geo_ok and (a.topic_required or a.content_phrases):
            continue
        topic_ok = _topic_matched(blob, a)
        sc = 0
        if geo_ok:
            sc += 5
        if topic_ok:
            sc += 6
        for p in a.content_phrases[:4]:
            if p and p in blob:
                sc += 3
        for y in a.years:
            if y in blob:
                sc += 2
        latin_hit = 0
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]{1,}", query or ""):
            if len(tok) >= 2 and tok.lower() in blob.lower():
                sc += 4
                latin_hit += 1
        url = str(h.get("url") or "").lower()
        if ".gov.cn" in url or ".edu.cn" in url or "openai.com" in url:
            sc += 3
        if "baidu.com/link" in url:
            sc -= 8
        # 门户/考试院首页壳：open 排序降权（名单/通知类尤重）
        sc -= portal_shell_rank_penalty(h, query)
        # 实质页小幅加权
        if _SUBSTANTIVE_PAGE_RE.search(blob) and not looks_like_portal_shell(h):
            sc += 4
        # 仅年份/公报/百科噪声：无主题且无有效地理命中、无英文专名
        geo_signal = bool(a.required) and geo_ok
        if sc > 0 and not topic_ok and not geo_signal and latin_hit == 0:
            if any(k in blob for k in ("统计公报", "国民经济", "百度百科", "居民收入", "Year in Review")):
                continue
            if sc <= 5:  # 仅年份+gov 外壳
                continue
        scored.append((sc, h))
    scored.sort(key=lambda x: -x[0])
    positive = [h for s, h in scored if s > 0]
    if positive:
        return positive
    # 勿用过松 soft 回灌错省；单地理主题问保持空
    if len(a.required) == 1 and (a.topic_required or a.content_phrases):
        return []
    return filter_hits_by_anchors(hits, a, strict=False)


def _topic_synonyms(topic: str, raw: str) -> list[str]:
    """主题同义扩展（形态规则，不写死省名/机构表）。

    例：职业院校技能大赛 ↔ 高等职业教育技能大赛 / 高职技能大赛
    """
    t = (topic or "").strip()
    blob = f"{t} {raw or ''}"
    alts: list[str] = []
    if not t and ("技能" in blob and "大赛" in blob):
        t = "技能大赛"
    if not t:
        return []
    alts.append(t)
    # 职业院校 ↔ 高等职业教育 / 高职
    if "职业院校技能大赛" in t or "职业院校技能大赛" in blob:
        alts.append("高等职业教育技能大赛")
        alts.append("高职技能大赛")
    elif "高等职业教育技能大赛" in t or "高等职业教育技能" in blob:
        alts.append("职业院校技能大赛")
        alts.append("高职技能大赛")
    elif "技能大赛" in t:
        if "职业" in blob or "职教" in blob or "高职" in blob:
            alts.append("高等职业教育技能大赛")
            alts.append("职业院校技能大赛")
    # 名单类补「拟获奖/公示/通知」不替换主题
    return list(dict.fromkeys([x for x in alts if x and len(x) >= 4]))


_COMPARE_RE = re.compile(
    r"比较|对比|对照|相比|vs\.?|VS|之间的区别|有何区别|有什么区别|"
    r"(?:与|和|及).{0,12}(?:与|和|及).{0,20}(?:比较|对比|区别|差异|规模)"
)
# 泛主题：不当作「必须出现在证据里」的专名
_GENERIC_ENTITY_STOP = frozenset(
    {
        "获奖名单",
        "技能大赛",
        "职业院校",
        "高等职业教育",
        "职业教育",
        "职业院校技能大赛",
        "高等职业教育技能大赛",
        "政府工作报告",
        "官方来源",
        "主要目标",
        "主要职责",
        "主要表述",
        "招生简章",
        "原文链接",
        "完整名单",
        "金奖队伍",
        "公开解读",
        "最近一年",
        "最近一次",
        "有哪些",
        "是什么",
        "如何区分",
        "标明来源",
        "请基于",
        "如实说明",
        "帮我搜索",
        "帮我查找",
        "招生简章原文链接",
    }
)
_NAMED_ORG_RE = re.compile(
    r"(?:职业中专|中等专业学校|职业技术学院|职业学院|大学|学院|中学|小学|公司|集团|研究所|研究院)$"
)
_NAMED_MAJOR_RE = re.compile(r"专业$")


def is_comparison_query(user_query: str) -> bool:
    """是否为对比/两侧题。须有比较信号词，不能仅因出现两个地名。"""
    q = user_query or ""
    if _COMPARE_RE.search(q):
        return True
    # 「河南省与山东省…规模/区别」类
    geos = extract_geo_phrases(q)
    if len(geos) >= 2 and re.search(r"与|和|及|对照|对比|比较|区别|差异|规模", q):
        # 排除「郑州市金水区」同省嵌套：两地名词干不同且句中有连接
        stems = {_stem_geo(g) for g in geos}
        if len(stems) >= 2:
            return True
    return False


def extract_distinctive_entities(user_query: str, *, min_len: int = 5) -> list[str]:
    """抽取「专名级」片段：机构/专业/含序号的长专名。

    用于查无判定；泛主题（技能大赛等）不进入，避免误杀正常名单题。
    """
    a = extract_query_anchors(user_query)
    raw = (user_query or "").strip()
    t = re.sub(r"https?://\S+", " ", raw)
    t = _STOP_ORAL.sub(" ", t)
    t = re.sub(r"[「」『』\"'“”‘’]", "", t)
    t = re.sub(r"(是什么|怎么样|有哪些|如何|请基于.*|若搜不到.*|请如实.*)$", " ", t)
    t = re.sub(r"[?？!！。，,、；;：:（）()【】\[\]]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    out: list[str] = []

    def add(p: str) -> None:
        p = clean_content_phrase(p or "")
        if len(p) < 4 or p in _GENERIC_ENTITY_STOP or p in _SOFT_ONLY:
            return
        if p in a.required or p in {_stem_geo(g) for g in a.required}:
            return
        stripped = clean_content_phrase(_strip_geo_prefix(p, a.required))
        cand = stripped if len(stripped) >= 4 else p
        if cand in _GENERIC_ENTITY_STOP:
            return
        if cand not in out:
            out.append(cand)

    # 机构名
    for m in re.finditer(
        r"[\u4e00-\u9fff0-9]{2,16}(?:职业中专|中等专业学校|职业技术学院|职业学院|大学|学院|中学|小学|公司|集团)",
        t,
    ):
        add(m.group())
    # 专业名
    for m in re.finditer(r"[\u4e00-\u9fff0-9]{2,12}专业", t):
        p = m.group()
        if p not in ("本专业", "该专业", "相关专业", "开设专业"):
            add(p)
    # 含数字序号的长专名（第七十二…）
    for m in re.finditer(r"[\u4e00-\u9fff]*[0-9一二三四五六七八九十百千]{1,6}[\u4e00-\u9fff]{2,12}", t):
        p = m.group()
        if len(p) >= 6 and not any(x in p for x in ("2024", "2025", "2026", "2027", "2035")):
            add(p)
        # 年份夹在中间的机构：…2027年火星殖民专业 已由专业规则覆盖
        elif re.search(r"中专|学院|大学|学校", p):
            add(p)

    # 过滤：只要机构/专业形态，或长度≥8 且非纯主题 content_phrase
    filtered: list[str] = []
    for e in out:
        if _NAMED_ORG_RE.search(e) or _NAMED_MAJOR_RE.search(e):
            filtered.append(e)
            continue
        if len(e) >= 8 and e not in (a.content_phrases or []) and e not in _GENERIC_ENTITY_STOP:
            # 排除整段主题
            if not re.fullmatch(r".*(技能大赛|获奖名单|职业教育).*", e) or re.search(
                r"中专|学院|大学|专业|公司", e
            ):
                filtered.append(e)
    return filtered[:8]


def evidence_blob(evidence: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for e in evidence or []:
        if not isinstance(e, dict):
            continue
        parts.append(str(e.get("title") or ""))
        parts.append(str(e.get("snippet") or ""))
        parts.append(str(e.get("pageText") or "")[:1200])
        parts.append(str(e.get("url") or ""))
    return "\n".join(parts)


def evidence_covers_distinctive_entities(
    user_query: str,
    evidence: list[dict[str, Any]] | None,
) -> bool:
    """证据是否覆盖问题中的专名级实体。

    - 无专名可抽 → True（不据此否决，避免误杀主题题）
    - 有专名但证据全无 → False（查无/虚构/门户壳）
    """
    ents = extract_distinctive_entities(user_query)
    if not ents:
        return True
    if not evidence:
        return False
    blob = evidence_blob(evidence)
    if not blob.strip():
        return False
    for e in ents:
        if e and e in blob:
            return True
        # 机构名去地理后的核心 ≥4 字
        core = re.sub(
            r"^(?:[\u4e00-\u9fff]{2,4}(?:省|市|区|县|州|盟))",
            "",
            e,
        )
        if len(core) >= 4 and core in blob:
            return True
        # 专业关键词（去「专业」后缀）
        if e.endswith("专业") and len(e) >= 4:
            stem = e[:-2]
            if len(stem) >= 2 and stem in blob:
                return True
    return False


def comparison_sides_covered(
    user_query: str,
    evidence: list[dict[str, Any]] | None,
) -> tuple[list[str], list[str]]:
    """对比题：返回 (已覆盖地理, 未覆盖地理)。"""
    geos = extract_geo_phrases(user_query)
    if len(geos) < 2:
        return [], []
    blob = evidence_blob(evidence)
    covered: list[str] = []
    missing: list[str] = []
    for g in geos:
        stem = _stem_geo(g)
        if g in blob or (stem and stem in blob):
            covered.append(g)
        else:
            missing.append(g)
    return covered, missing


def build_search_query_variants(
    user_query: str,
    *,
    max_n: int = 5,
    prior_queries: list[str] | None = None,
) -> list[str]:
    """启发式多路检索（LLM planner 失败时的兜底，非业务规则表）。

    - 多地理：每个地理各生成假设（对比题）
    - 保留英文/数字 token
    - 去口语，禁止与 prior 重复
    """
    a = extract_query_anchors(user_query)
    out: list[str] = []
    year = a.years[0] if a.years else ""
    geos = list(a.required) or [""]
    topic = a.content_phrases[0] if a.content_phrases else ""
    if not topic and a.topic_required:
        topic = "技能大赛" if "大赛" in (user_query or "") else ""
    topics = _topic_synonyms(topic, user_query or "")
    if not topics and topic:
        topics = [topic]
    if not topics:
        topics = [""]
    priors = {re.sub(r"\s+", " ", (p or "").strip()) for p in (prior_queries or [])}
    # 英文专名原样保留
    latin = re.findall(r"[A-Za-z][A-Za-z0-9_./+]{1,}", user_query or "")

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip())
        s = re.sub(r"(是什么|怎么样|有哪些|最近)[？?]?$", "", s).strip()
        s = re.sub(r"^(最近|有哪些|帮我|请)\s*", "", s).strip()
        if not s or len(s) < 2:
            return
        s = s[:48]
        if s in out or s in priors:
            return
        out.append(s)

    # 对比题：优先「每侧独立完整假设」（地理+主题+年份），避免糊成一句
    if len(geos) >= 2 and (topics and topics[0]):
        for geo in geos[:3]:
            tp = topics[0]
            add(" ".join(p for p in (geo, year, tp) if p))
            add(f"{_stem_geo(geo)} {tp} 规模 赛道".strip()[:48])
            add(f"{geo} {tp} 通知 公示".strip()[:48])

    # 多地理 × 主题
    for geo in geos[:3]:
        stem = _stem_geo(geo) if geo else ""
        for tp in topics[:3]:
            parts = [p for p in (geo, year, tp) if p]
            if parts:
                add(" ".join(parts))
            if geo and tp:
                add(f"{stem or geo} {tp}".strip())
            if geo and year and tp:
                add(f"{geo}{year}{tp}")

    for tok in latin[:4]:
        add(tok if not year else f"{tok} {year}")
        if a.content_phrases:
            add(f"{tok} {a.content_phrases[0][:12]}")

    # 用户原句去口语
    cleaned = _STOP_ORAL.sub(" ", user_query or "")
    cleaned = re.sub(r"https?://\S+", " ", cleaned)
    cleaned = re.sub(r"(是什么|怎么样|有哪些|请基于.*|列\d+条.*)$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned:
        add(cleaned[:48])

    # 中文政务召回：尽早插入 site: / 通知公示，避免被 max_n 挤掉（不写省域表）
    official_sig = re.search(
        r"通知|公示|名单|政策|教育厅|政府|大赛|获奖|官方|官网|办法|条例",
        user_query or "",
    )
    if official_sig or a.required:
        seed = " ".join(
            p
            for p in (
                geos[0] if geos and geos[0] else "",
                year,
                topics[0] if topics and topics[0] else "",
            )
            if p
        ).strip()
        if not seed:
            seed = cleaned[:32] if cleaned else ""
        if seed:
            gov_q = f"{seed} site:gov.cn"[:48]
            pub_q = (
                f"{seed} 通知 公示"[:48]
                if not re.search(r"通知|公示|名单", seed)
                else ""
            )
            # 插到前部：主假设之后、同义改写之前的位置优先
            insert_at = min(2, len(out))
            for extra in (gov_q, pub_q):
                if not extra or extra in out or extra in priors:
                    continue
                out.insert(insert_at, extra)
                insert_at += 1
    return out[:max_n]


def next_unused_query(
    user_query: str,
    prior_queries: list[str] | None,
    *,
    max_n: int = 8,
) -> str | None:
    """取下一条未用过的检索假设；用尽返回 None。"""
    variants = build_search_query_variants(
        user_query, max_n=max_n, prior_queries=prior_queries
    )
    return variants[0] if variants else None
