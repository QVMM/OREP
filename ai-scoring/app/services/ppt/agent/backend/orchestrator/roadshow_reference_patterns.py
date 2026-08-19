"""Reference pattern library for vocational competition roadshow decks."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RoadshowPattern:
    pattern_id: str
    purpose: str
    primary_object: str
    layout_rule: str
    avoid: str


ROADSHOW_PATTERNS: tuple[RoadshowPattern, ...] = (
    RoadshowPattern(
        "competition_cover_identity",
        "建立作品身份、场景和技术方向",
        "项目名 + 场景视觉 + 一句话任务",
        "中部项目名，底部一句任务，背景只服务场景识别",
        "空泛科技背景、无场景封面、个人/学校信息",
    ),
    RoadshowPattern(
        "field_route_agenda",
        "给评委一张现场理解路线图",
        "背景-研发-实施-创新-价值五段路线",
        "左侧路线或中轴时间线，右侧每段只写理解目标",
        "目录堆长句、展示评分/采分逻辑",
    ),
    RoadshowPattern(
        "policy_problem_project_fit",
        "证明项目不是凭空设想，而是回应真实场景",
        "政策/行业/用户痛点到项目切入点的因果链",
        "时事-政策-市场-痛点四段问题地图，最后落到本项目任务",
        "只摘政策原文、只讲宏大背景",
    ),
    RoadshowPattern(
        "policy_news_market_motive",
        "把时事新闻、政策导向和市场调研转成研发动因",
        "时事新闻-政策背景-市场考察-研发动因链路",
        "左侧外部背景，右侧本项目切入点，中间用因果箭头连接",
        "只有口号、没有来源年份、把联网资料写成项目自有事实",
    ),
    RoadshowPattern(
        "school_enterprise_research_path",
        "说明研发不是闭门造车，而来自产教融合和真实调研",
        "校企合作-现场调研-痛点提炼-策略匹配",
        "用路径图展示调研对象、发现问题、对应策略，不出现学校或企业隐私",
        "暴露学校/企业联系人、只写团队努力不写发现",
    ),
    RoadshowPattern(
        "problem_strategy_one_to_one",
        "把行业痛点和解决策略做成一一对应",
        "痛点-成因-策略-落地模块",
        "四列映射或左右对照，突出每个策略对应一个模块或动作",
        "痛点泛泛而谈、策略和问题脱节",
    ),
    RoadshowPattern(
        "role_task_skill_output",
        "把团队工作转成职业岗位能力",
        "岗位-任务-技能-产出矩阵",
        "横向岗位链或矩阵，强调产出物而非姓名",
        "真实姓名、学校、联系方式、口令角色",
    ),
    RoadshowPattern(
        "system_runs_like_this",
        "让评委一眼看懂系统如何跑起来",
        "设备/输入-处理-判断-展示-记录主流程",
        "主流程占 65% 以上，节点旁挂运行记录或后续页码",
        "五张并列卡片、纯技术栈列表",
    ),
    RoadshowPattern(
        "module_value_tech_test_summary",
        "把一个核心模块拆成可展示技能链",
        "价值-技术-测试-小结链条",
        "同模块多页连续使用，页内突出当前链条位置",
        "一页讲完模块、泛泛功能介绍",
    ),
    RoadshowPattern(
        "code_walkthrough_with_output",
        "证明关键功能不是概念，而有实现细节",
        "关键函数/接口/SQL/配置 + 运行输出",
        "左侧代码或逻辑片段，右侧解释输入输出和异常处理",
        "整页堆代码、无输出结果",
    ),
    RoadshowPattern(
        "live_demo_input_action_output_evidence",
        "服务现场实操闭环",
        "输入-操作-输出-记录四段闭环",
        "中间真实系统/设备画面，四周用标注说明闭环",
        "只画流程、不显示运行记录或结果状态",
    ),
    RoadshowPattern(
        "test_record_dashboard",
        "用测试记录支撑可靠性",
        "测试用例、结果、日志、异常复测",
        "仪表盘或表格看板，显式区分已验证与待采集",
        "无来源百分比、虚构报告编号",
    ),
    RoadshowPattern(
        "support_material_wall",
        "集中展示项目真实痕迹",
        "截图、日志、代码、证书、调研或反馈",
        "材料看板，按来源类型分组，每项附短标签",
        "把 PDF 页面裁图当正式材料、无来源拼贴",
    ),
    RoadshowPattern(
        "stakeholder_value_matrix",
        "说明项目对不同对象的价值",
        "用户/企业/学校/团队/社会价值",
        "矩阵或分层漏斗，每格写一个可验证价值点",
        "空泛价值口号、无来源的夸大 KPI",
    ),
    RoadshowPattern(
        "industry_employment_value_map",
        "说明项目帮助了哪些行业、岗位和就业能力",
        "行业对象-岗位能力-就业带动-人才培养",
        "用行业链或岗位地图展示项目对企业、学校和学生能力成长的作用",
        "只写社会价值口号、不落到行业或岗位",
    ),
    RoadshowPattern(
        "ip_cooperation_growth_map",
        "说明知识产权、合作协议和团队成长的延伸价值",
        "知识产权-合作应用-课程转化-团队技能成长",
        "四象限或递进路线，所有数量和协议状态必须标注来源口径",
        "编造专利/软著/协议编号或合作数量",
    ),
    RoadshowPattern(
        "innovation_delta",
        "讲清创新不是口号，而是差异和成效",
        "传统方式-本项目方式-变化-验证方式",
        "左右对比或三段递进，中间强调差异点",
        "只列技术名词、不讲改变了什么",
    ),
)

PATTERN_IDS = tuple(pattern.pattern_id for pattern in ROADSHOW_PATTERNS)
_PATTERN_ID_SET = {pattern.lower() for pattern in PATTERN_IDS}
_PATTERN_ALIAS_MAP = {
    "cover_scene": "competition_cover_identity",
    "agenda_timeline": "field_route_agenda",
    "problem_map": "problem_strategy_one_to_one",
    "solution_map": "problem_strategy_one_to_one",
    "architecture_map": "system_runs_like_this",
    "data_flow": "system_runs_like_this",
    "technical_mechanism": "module_value_tech_test_summary",
    "rule_tree": "module_value_tech_test_summary",
    "live_demo_board": "live_demo_input_action_output_evidence",
    "operation_flow": "live_demo_input_action_output_evidence",
    "code_explain_board": "code_walkthrough_with_output",
    "support_material_flow": "support_material_wall",
    "test_dashboard": "test_record_dashboard",
    "result_dashboard": "test_record_dashboard",
    "risk_fallback": "live_demo_input_action_output_evidence",
    "team_handoff": "role_task_skill_output",
    "policy_market_map": "policy_news_market_motive",
    "industry_value_map": "industry_employment_value_map",
    "employment_role_map": "industry_employment_value_map",
    "school_enterprise_map": "school_enterprise_research_path",
    "innovation_map": "innovation_delta",
    "conclusion_map": "stakeholder_value_matrix",
    "policy_problem_map": "policy_problem_project_fit",
    "market_motive": "policy_news_market_motive",
}


def normalize_pattern_id(value: str) -> str:
    """Normalize common LLM pattern drift back to the registered library ids."""
    text = (value or "").strip()
    text = re.sub(r"^[`'\"{\[\(]+|[`'\"}\]\),.;，。；：:]+$", "", text).strip()
    text = re.sub(r"\s+", "_", text)
    lowered = text.lower()
    if lowered in _PATTERN_ID_SET:
        return lowered
    if lowered in _PATTERN_ALIAS_MAP:
        return _PATTERN_ALIAS_MAP[lowered]
    for pattern_id in PATTERN_IDS:
        if pattern_id.lower() in lowered:
            return pattern_id
    return lowered


def roadshow_pattern_library_prompt_block() -> str:
    lines = [
        "## Reference Pattern Library",
        "",
        "每页必须选择一个 `visual_pattern.pattern_id`。这些 pattern 来自真实职业院校技能大赛路演 PPT 的通用结构，"
        "只能学习页面功能和证明逻辑，不能照抄样式、姓名、学校、赛事年份或联系方式。",
        "",
        "| pattern_id | purpose | primary_object | layout_rule | avoid |",
        "| --- | --- | --- | --- | --- |",
    ]
    for pattern in ROADSHOW_PATTERNS:
        lines.append(
            f"| {pattern.pattern_id} | {pattern.purpose} | {pattern.primary_object} | "
            f"{pattern.layout_rule} | {pattern.avoid} |"
        )
    return "\n".join(lines)


def allowed_pattern_ids_text() -> str:
    return ", ".join(PATTERN_IDS)
