"""Competition-roadshow front-half agent.

This module keeps the proven paper-ppt-agent back half intact:
manuscript -> design_spec -> per-page SVG -> export.  It only replaces the
paper-specific research passes with vocational-skills-competition planning.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING

from backend.config import settings
from backend.llm import LLMMessage, LLMProvider, LLMResponse
from backend.orchestrator.provider_guidance import (
    deepseek_research_guidance,
    is_deepseek_provider,
)
from backend.parser.paper_model import ParsedPaper

from .manuscript import page_title, split_manuscript_pages
from .roadshow_asset_binder import (
    build_evidence_asset_report,
    evidence_asset_prompt_block,
)
from .roadshow_asset_registry import IMAGE_ASSET_EXTENSIONS, load_asset_registry
from .roadshow_cards import (
    cards_to_manuscript,
    parse_slide_content_plan,
    project_dir_from_debug_dir,
    validate_cards_for_formal_render,
    write_image2_page_briefs,
    write_image2_page_descriptions,
    write_planning_artifacts,
)
from .roadshow_content_contract import (
    PRIVATE_FIELD_NAMES,
    classify_roadshow_source,
    source_profile_prompt_block,
)
from .roadshow_hard_quality import (
    build_roadshow_quality_repair_instruction,
    ensure_roadshow_manuscript_hard_requirements,
    evaluate_roadshow_manuscript_quality,
)
from .roadshow_quality import (
    apply_locked_facts_to_manuscript,
    extract_locked_facts,
    remove_disallowed_figure_tokens,
    roadshow_figure_token_inventory_block,
    valid_external_findings,
)
from .roadshow_reference_patterns import (
    allowed_pattern_ids_text,
    normalize_pattern_id,
    roadshow_pattern_library_prompt_block,
)
from .roadshow_script_skill import enhance_roadshow_script
from .research_agent import (
    _debug_write_messages,
    _debug_write_text,
    _extract_manuscript_from_review,
    _language_guidance,
    _manuscript_validation_error,
    _normalize_competition_manuscript_structure,
    _structure_retry_prompt,
)

if TYPE_CHECKING:
    from .research_agent import ResearchContext

logger = logging.getLogger(__name__)

PAGE_TYPE_MARKER_RE = re.compile(
    r"(?im)^\s*<!--\s*page_type\s*:\s*(?:cover|chapter|transition|toc|content|ending)\s*-->\s*$"
)
PRIVATE_GROUP_HEADING_RE = re.compile(
    r"(?im)^\s*(?:\*\*)?\s*(?:Slide Content Plan|Visual Planning Fields|Contestant Perspective Fields|Field Execution Fields)\s*:?\s*(?:\*\*)?\s*$"
)
ROADSHOW_FIELD_LABEL_RE = re.compile(r"(?m)^(\s*)\*\*([A-Za-z_][A-Za-z0-9_]*)\*\*\s*:")
ROADSHOW_FIELD_VALUE_RE_TEMPLATE = r"(?ims)^\s*(?:\*\*)?{name}(?:\*\*)?\s*:\s*(.*?)(?=^\s*(?:\*\*)?[A-Za-z_][A-Za-z0-9_]*(?:\*\*)?\s*:|^\s*<!--|^\s*#|\Z)"

ROADSHOW_MAX_TOKENS = 20000
ROADSHOW_PASS1_MAX_TOKENS = 2200
ROADSHOW_LIGHT_PLAN_MAX_TOKENS = 12000
ROADSHOW_CHUNK_MAX_TOKENS = 12000
ROADSHOW_CHUNK_SIZE = 10
# Editable / full planning: keep 35-45 pages, but generate by segments in parallel.
ROADSHOW_LIGHT_PLAN_SEGMENT_SIZE = 8
ROADSHOW_PARALLEL_SEGMENTS = 3
ROADSHOW_MANUSCRIPT_PARALLEL_SEGMENTS = 2
ROADSHOW_IMAGE2_CHUNK_SIZE = 5
ROADSHOW_IMAGE2_CHUNK_RETRY_ATTEMPTS = 3
ROADSHOW_IMAGE2_OUTLINE_RETRY_ATTEMPTS = 2
ROADSHOW_IMAGE2_CHUNK_STALL_SECONDS = 180
ROADSHOW_IMAGE2_OUTLINE_SEGMENT_STALL_SECONDS = 95
ROADSHOW_PASS1_SOURCE_CHAR_BUDGET = 10000
ROADSHOW_SECTION_CHAR_BUDGET = 5000
ROADSHOW_SAFE_PROGRESS_INTERVAL_SECONDS = 12

ROADSHOW_PASS2_SAFE_PROGRESS_MESSAGES = (
    "正在整理五段故事线结构",
    "正在匹配页数区间与板块承载量",
    "正在校验故事线推进关系",
    "正在标记需要真实素材承载的页面类型",
    "正在精简重复信息，保留正式汇报主线",
)

ROADSHOW_PASS3_SAFE_PROGRESS_MESSAGES = (
    "正在编排现场汇报顺序",
    "正在匹配讲解段落与演示环节",
    "正在检查代码还原与测试展示的衔接",
    "正在校验选手交接和口令是否自然",
    "正在压缩重复讲述，保留现场证明链路",
)

ROADSHOW_PASS4_SAFE_PROGRESS_MESSAGES = (
    "正在为每页补充选手讲述意图",
    "正在匹配每页需要证明的支撑对象",
    "正在检查页面信息重点",
    "正在给现场演示页补充承接关系",
    "正在校验页面支撑材料与讲述目标的一致性",
)


def _roadshow_research_stall_retry_seconds() -> int:
    try:
        value = int(getattr(settings, "roadshow_research_llm_stall_retry_seconds", 150) or 0)
    except (TypeError, ValueError):
        value = 150
    return max(0, value)


def _roadshow_research_stall_max_attempts() -> int:
    try:
        value = int(getattr(settings, "roadshow_research_llm_stall_max_attempts", 2) or 0)
    except (TypeError, ValueError):
        value = 2
    return max(1, value)


async def _await_llm_with_safe_progress(
    response_factory: Callable[[], Awaitable[LLMResponse]],
    *,
    on_progress: Callable[[str, float], None] | None,
    messages: tuple[str, ...],
    start_fraction: float,
    end_fraction: float,
    interval_seconds: int = ROADSHOW_SAFE_PROGRESS_INTERVAL_SECONDS,
    stall_retry_seconds: int | None = None,
    retry_message: str | None = None,
    max_attempts: int | None = None,
) -> LLMResponse:
    """Wait for a long LLM call, reissuing silent requests at the same quality."""
    stall_retry_after = max(0, int(stall_retry_seconds if stall_retry_seconds is not None else _roadshow_research_stall_retry_seconds()))
    if max_attempts is None:
        attempt_limit = _roadshow_research_stall_max_attempts()
    else:
        attempt_limit = max(1, int(max_attempts or 0)) if max_attempts else None
    span = max(0.0, end_fraction - start_fraction)
    attempt = 1

    while True:
        task = asyncio.ensure_future(response_factory())
        heartbeat_index = 0
        elapsed_seconds = 0
        try:
            while True:
                try:
                    return await asyncio.wait_for(asyncio.shield(task), timeout=interval_seconds)
                except asyncio.TimeoutError:
                    elapsed_seconds += interval_seconds
                    if stall_retry_after and elapsed_seconds >= stall_retry_after:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        except Exception:
                            pass
                        if attempt_limit and attempt >= attempt_limit:
                            raise RuntimeError(
                                f"当前步骤连接波动，连续 {attempt_limit} 次未收到稳定结果"
                                f"（单次静默上限 {stall_retry_after}s）"
                            )
                        attempt += 1
                        if on_progress:
                            on_progress(
                                retry_message
                                or (
                                    f"当前步骤连接波动，正在重新建立请求并保持原生成要求"
                                    f"（第 {attempt}/{attempt_limit or '?'} 次）"
                                ),
                                min(end_fraction, start_fraction + span * 0.92),
                            )
                        break
                    if not on_progress or not messages:
                        continue
                    message = messages[min(heartbeat_index, len(messages) - 1)]
                    # Honest progress: one model call, not multi-step work.
                    cap_hint = f" / 静默上限 {stall_retry_after}s" if stall_retry_after else ""
                    if heartbeat_index >= len(messages):
                        message = (
                            f"{messages[-1]}（模型生成中 · 第 {attempt} 次 · "
                            f"已 {elapsed_seconds}s{cap_hint}）"
                        )
                    elif elapsed_seconds >= interval_seconds * 2:
                        message = f"{message}（模型生成中 · 已 {elapsed_seconds}s{cap_hint}）"
                    if attempt > 1:
                        message = f"{message} · 重试 {attempt}/{attempt_limit or '?'}"
                    step_count = len(messages) + 1
                    progress_step = min(heartbeat_index + 1, len(messages))
                    fraction = min(end_fraction, start_fraction + span * progress_step / step_count)
                    on_progress(message, fraction)
                    heartbeat_index += 1
        except asyncio.CancelledError:
            task.cancel()
            raise
        continue

PRIMARY_VISUAL_TYPES = (
    "cover_scene",
    "agenda_timeline",
    "problem_map",
    "solution_map",
    "architecture_map",
    "data_flow",
    "technical_mechanism",
    "rule_tree",
    "live_demo_board",
    "code_explain_board",
    "operation_flow",
    "evidence_chain",
    "support_material_flow",
    "test_dashboard",
    "result_dashboard",
    "risk_fallback",
    "team_handoff",
    "policy_market_map",
    "industry_value_map",
    "employment_role_map",
    "school_enterprise_map",
    "innovation_map",
    "conclusion_map",
)

CARD_HEAVY_TERMS = (
    "三列卡片",
    "四张卡片",
    "四个卡片",
    "四行卡片",
    "2x2网格",
    "2x2 网格",
    "等大卡片",
    "卡片式布局",
    "信息卡片",
    "四卡片",
)

FORMAL_VISIBLE_META_TERMS = (
    "我们如何证明",
    "一张图看懂",
    "支撑材料的总链路",
    "路演路线",
    "生成器",
    "内部逻辑",
    "页面任务",
    "现场实操演示准备",
    "演示环境与操作脚本已就绪",
    "演示环境已准备",
    "操作脚本已就绪",
    "演示准备状态",
    "播放录屏",
)

IMPLEMENTATION_EVENT_CHAIN_RULE = """## Implementation Event Chain Rule

实施过程不是模块说明书，必须像发布会现场演示一样围绕“一次真实事件”推进。

35-45页正式稿中，实施过程的中段，尤其第18-24页附近，禁止连续出现“前端开发负责什么、后端开发负责什么、某某模块实现了什么”的项目汇报式页面。

推荐表达：
- 事件总控：选定一个具体事件，例如温度异常、设备异常、预警触发或人工巡检发现问题。
- 输入进入：传感数据、设备状态或人工上报进入系统。
- 判断触发：规则引擎/阈值/接口判断产生预警。
- 处置执行：设备联动、工单生成、移动端确认或人工复核。
- 记录沉淀：日志、工单、趋势图、测试记录完成复盘。
- 机制解释：在事件跑通之后，再解释前端、后端、数据库、规则引擎如何支撑这次闭环。
- 复核结果：用运行记录或测试记录证明闭环可复现。

允许讲模块，但模块必须挂在这次事件上，例如：
- 不写“环境监测模块实现了从人工抄表到自动感知”，改写为“温度异常如何被实时捕捉”。
- 不写“设备联动控制模块实现了从人工开关到规则触发”，改写为“预警触发后设备如何自动响应”。
- 不写“前端开发聚焦于操作界面”，改写为“管理员在大屏和移动端看到什么、确认什么”。
- 不写“后端开发确保业务逻辑可靠”，改写为“接口、规则和日志如何让本次处置可追溯”。
"""

ROADSHOW_STORYLINE_RULE = """## Roadshow Storyline Rule

比赛路演 PPT 必须像发布会一样推进故事线，而不是像项目汇报一样罗列栏目。

可见页面必须遵循“问题出现 -> 方案登场 -> 系统跑通 -> 现场验证 -> 数据复核 -> 创新提炼 -> 价值兑现”的因果链。

硬性禁止：
- 不得生成独立的“现场实操演示准备”“演示环境已就绪”“操作脚本已就绪”“演示准备状态”页面。
- 设备检查、演示环境、操作脚本、录屏备用、网络备用、故障切换只能写入 stage_mode、operator_action、fallback_plan、speaker_notes 或 private_runbook，不能成为 PPT 可见页面。
- 不得先讲测试/运行数据/稳定性，再回头插入“准备开始演示”的页面；现场演示必须嵌入实施过程的证明链。
- 不得把系统功能页和实操演示页做成重复介绍。功能页讲“为什么这样实现”，演示页讲“一次现场事件如何跑通闭环”。
- 不得用“支撑材料总览”替代对应页面的支撑材料；材料应跟随所在结论局部出现，最后只能做极简归档。

推荐实施过程顺序：
业务闭环 -> 一次现场事件总控 -> 监测触发 -> 联动处置 -> 数据复盘/运行记录 -> 技术拆解（前端/后端/规则/数据库） -> 测试与稳定性 -> 模块小结。

每页必须承担推进角色：
- raise_problem: 提出真实矛盾
- reveal_solution: 把矛盾收束为系统方案
- prove_flow: 用一次业务闭环证明系统跑得通
- unpack_mechanism: 解释关键技术为什么能支撑闭环
- verify_result: 用测试/运行记录复核结果
- extract_innovation: 从机制和结果中提炼创新
- land_value: 把结果落到企业、教学、岗位、行业价值

如果某页只是在说“准备好了、接下来演示、材料齐全、流程如下”，它不是正式 PPT 页面，应合并到上一页转场、讲稿或备注。
"""

ROADSHOW_SOURCE_KEEP_HEADINGS = (
    "母稿使用规则",
    "项目锁定信息",
    "一句话定位",
    "赛制",
    "评分",
    "行业痛点",
    "用户场景",
    "需求分析",
    "总体技术",
    "总体方案",
    "Run-of-Show",
    "run-of-show",
    "核心模块",
    "模块一",
    "模块二",
    "模块三",
    "模块四",
    "模块五",
    "测试数据",
    "支撑材料",
    "页面蓝图",
    "页面蓝图",
    "页面生成",
    "团队",
    "风险",
    "故障",
    "导出门禁",
    "素材",
    "质量验收",
    "PPT Agent",
)

ROADSHOW_PDF_NOISE_MARKERS = (
    "GPT-5.5生成母稿",
    "模拟数据仅用于PPT测试",
    "Figure (natural",
    "[Source compacted",
)

ROADSHOW_MOTHER_DRAFT_MARKERS = (
    "职业院校技能大赛路演PPT智能生成母稿",
    "primary_visual",
    "正式导出门禁",
    "private_runbook",
    "Run-of-Show",
    "55 分钟",
)

PRIMARY_VISUAL_CONTRACT = f"""## Primary Visual Contract

Every slide MUST include a `primary_visual:` field immediately after `speaker_goal:` and before field-execution fields.
The value must be a compact structured line or block with these keys:

`type`, `purpose`, `required_elements`, `visual_weight`, `forbidden_layouts`

Allowed `type` values:
{", ".join(PRIMARY_VISUAL_TYPES)}

Rules:
- `primary_visual.type` is the main visual object of the slide, not decoration.
- `primary_visual.visual_weight` should normally be 60%-75% for content pages.
- Do not let `layout_hint` decide the page first. First decide what the judge must understand, then choose the primary visual.
- Pure card/list/table pages are forbidden for technical, demo, support-material and result pages.
- If cards are used, they must be secondary annotations around a primary visual, not the main structure.
- Background pages should use policy_market_map, problem_map, solution_map, school_enterprise_map, or industry_value_map when they discuss policy, market, industry pain points, employment, or school-enterprise cooperation.
- Technical pages must use mechanism diagrams such as architecture_map, data_flow, rule_tree, technical_mechanism, or support_material_flow.
- Live demo pages must use live_demo_board, operation_flow, code_explain_board, test_dashboard, or support_material_flow.
- Result pages must use result_dashboard or test_dashboard and must distinguish verified values from pending values.
- Visible slide copy must not contain the Chinese word “证据”. Use 支撑材料、运行记录、验证结果、成果材料、资料来源 instead.

Example:
primary_visual:
  type: live_demo_board
  purpose: 让评委一眼看懂本页现场操作如何支撑模块有效
  required_elements: 输入数据、操作步骤、预期画面、结果状态、运行记录留存、失败切换
  visual_weight: 70%
  forbidden_layouts: 纯四卡片、纯列表、只有表格
"""

SLIDE_CONTENT_PLAN_CONTRACT = """## Slide Content Plan Contract

每一页必须同时完成“正式页面内容、讲稿、主视觉、素材绑定、缺失处理”，不能只有标题和内部策略字段。

每页可见正文必须先写在页面前部，字段名不得可见。随后必须写下面这些内部字段：

- `page_core_sentence:` 本页正式页面核心句；必须是能放在 PPT 上的自然表述，不得写“我们如何证明”“一张图看懂”“支撑链路”等策划语言。
- `visible_content:` 本页正式可见正文，包含页面要点、图表标签、数据口径；不能只有“详见素材/待补充”。
- `main_visual:` 本页主视觉方案，必须包含 type、asset_source、asset_status、fallback、export_rule。
- `visual_asset_plan:` 说明主视觉如何落版，例如真实截图、产品界面、调研照片、测试图表、证书材料、SVG 架构图、SVG 流程图、生成图。
- `required_assets:` 本页需要的素材清单，必须具体到截图、照片、图表、日志、代码、接口、数据库、调研、证书、协议或公开来源。
- `asset_status:` provided、derivable、missing、not_required、draft_only、blocking 之一。真实截图/证书/测试结果缺失时不得写成已完成事实。
- `fallback_visual:` 缺素材时如何表达。结构类页面可用 SVG；真实运行效果、证书、协议、测试结果缺失时只能写验证方法或阻止正式导出，不能用 SVG 伪造。
- `asset_gap_handling:` 缺失素材如何处理：补采、降级为验证方法、改写为计划、或正式导出拦截。
- `export_gate:` formal_ok、draft_only、blocked_until_assets 之一。
- `speaker_notes:` 正式可直接朗读的本页讲稿，必须像职业院校技能大赛现场路演：尊称自然、逻辑完整、能照着读，包含上页承接、主体论证、项目事实、必要的演示/队友交接话术和自然转场；不要写字段名、提纲、操作备忘、页面分析或“讲解时先说明”这类提示语。
- `main_script:` 主讲稿，说明这页上台主要讲什么。
- `sub_script:` 子稿，说明补充解释、可追问细节或操作提示。
- `transition:` 下一页承接句。

主视觉 type 必须使用以下值之一：
real_image、screenshot、product_ui、chart、certificate、material_photo、generated_image、svg_diagram、none。

使用原则：
- 产品界面、运行效果、测试记录、证书、专利、协议、应用反馈必须优先使用真实素材。
- 已上传的真实图片素材必须通过 `[[ASSET:asset_id]]` 引用，不得直接写中文文件路径。asset_id 来自 Support Material Binder Report / asset_registry.json。
- 当 main_visual.type 为 real_image、screenshot、product_ui、chart、certificate、material_photo 且 asset_status=provided 时，required_assets 必须至少包含一个 `[[ASSET:...]]`；后续页面必须渲染真实 `<image>`。
- 政策背景、痛点归纳、总体思路、系统架构、业务流程、数据流程、技术路线、价值矩阵、未来规划适合用 SVG。
- 封面默认不配图，不使用上传素材、截图、真实场景图或生成图；用标题、副标题、色块、线条、抽象几何和项目关键词完成视觉设计，避免首页图片质量不稳定影响专业感。
- 正式 PPT 可见页面不得出现“占位符”；占位符只允许存在于内部缺失处理字段或草稿门禁。
"""

ROADSHOW_VISIBLE_VOCABULARY_RULE = """## Roadshow Visible Vocabulary Rule

“证据”是系统内部判断概念，不适合作为参赛 PPT 可见文字。PPT 可见标题、正文、图表标签、页脚、SVG 文本均禁止出现“证据”二字。
可见表达统一替换为：支撑材料、验证结果、运行记录、测试记录、成果材料、资料来源、现场记录、应用反馈。
内部字段仍可保留 proof_object/evidence_assets/evidence_chain 等英文名称，但这些字段和值不得逐字渲染到 PPT 上。
"""

ROADSHOW_FULL_LOGIC_FRAME = """## Roadshow Full Logic Frame

生成路演 PPT 时必须围绕下面五段逻辑组织，而不是做资料摘要：

注意：这五段是后台组织骨架，不是机械栏目清单。正式 PPT 必须按故事线推进，让每一页都接住上一页的问题并自然引出下一页的证明动作。

1. 项目背景
- 时事新闻分析：与项目主题相关的近年行业事件、现实问题或社会趋势。
- 政策背景支撑：国家/地方政策、产业规划、标准导向；有联网结果时优先提取来源名和年份。
- 市场考察调研：用户/行业现场调研、竞品或行业方案观察、需求缺口。
- 明确研发动因：把外部背景收束到“为什么必须做这个项目”。

2. 研发历程
- 产教融合（校企合作）：只写合作方式、场景和任务，不写学校/联系人。
- 调研与痛点提炼：把现场问题提炼成可解决的技术任务。
- 问题策略（1:1对应）：每个痛点对应一个策略、模块或操作。
- 技术架构：展示端、边、云/后台、算法、应用、安全闭环。
- 安全与编码规范：权限、日志、数据合规、代码规范、测试规范。
- 团队明确分工：用岗位/模块匿名表达，不出现姓名。

3. 实施过程
- 产品经理（业务逻辑）：用户流程、需求优先级、异常路径。
- 现场演示必须嵌入实施过程：用“一次异常事件”贯穿监测触发、设备联动、工单处置、数据复盘和运行记录；不得单独生成“演示准备页”。
- 前端开发（技术实现）：界面、交互、设备连接、状态展示。
- 后端开发（数据处理）：接口、数据库、任务调度、日志留存。
- 测试工程（质量保障）：测试用例、复测、运行记录、问题闭环。
- 工匠精神（全周期）：规范、安全、迭代、复盘。

4. 创新设计
- 技术应用创新锚点：具体技术组合如何解决传统问题。
- 模式创新与社会价值：服务模式、产教融合、岗位能力、可推广路径。
- 量化创新成效：只用资料或联网公开来源支撑的数值；无来源则展示验证口径。

5. 应用价值
- 企业（经济/合作）：降本增效、合作应用、行业可复制性。
- 学校（教学/课程）：课程转化、实训项目、教学资源沉淀。
- 团队（技能/成长）：岗位能力、职业素养、协作能力。
- 知识产权（专利/协议）：软著、专利、协议、申报状态；没有则写规划路径，不编编号。
- 就业与行业帮助：说明项目帮助哪些行业、带动哪些岗位能力或新职业方向。

联网结果使用要求：若启用外部研究，必须优先服务于“时事新闻分析、政策背景支撑、市场/行业趋势、经济价值、就业岗位、行业帮助、知识产权/标准”这些页面；不得把联网内容写成用户项目自有成果。
"""

ANALYSIS_SYSTEM_PROMPT = """你是职业院校技能大赛作品汇报的资料分析 Agent。

目标不是写论文汇报，而是从用户资料中反推出一套现场可讲、可演示、可验证、能打动评委的比赛作品 PPT 所需素材。

必须遵守：
- 不输出姓名、学校、电话、邮箱、身份证号、精确住址等个人信息。
- 不编造事实、数据、测试结果、团队信息或来源。
- 官方评分要素只能作为后台分析坐标：技能水平60、职业素养10、应用价值10、团队合作10、创新创意10；不要写成 PPT 可见标题或正文。
- 比赛官方总时长60分钟，但方案按约55分钟准备，预留5分钟设备切换、异常处理和评委互动缓冲。
- 选手自带 PPT 和设备到现场讲解并实操，所以必须识别：演示环境、设备清单、操作脚本、支撑材料、团队分工、备用方案。
- 必须识别每个核心功能是否能按“功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结”展示。
- 必须识别成果数据的来源类型：测试记录、用户反馈、基地证明、企业合作、联网来源或待补充。
- 必须识别现场故障处理材料：常见故障、排查动作、修复动作、复测成功判据。
- 必须识别项目背景是否具备：时事新闻分析、政策背景支撑、市场考察调研、明确研发动因。
- 必须识别应用价值是否具备：企业经济/合作、学校教学/课程、团队技能成长、知识产权/协议、就业岗位和行业帮助。
- 如果有联网结果，优先提取政策、行业趋势、市场规模/增长、岗位变化、产业需求、标准导向；不得把联网内容写成项目自有成果。

输出结构：
1. 资料摘要
2. 能力与材料支撑
3. 关键支撑链路
4. 现场实操素材诊断
5. 团队分工素材诊断
6. 核心模块展示链诊断
7. 成果数据来源诊断
8. 故障恢复与备用方案诊断
9. 背景/政策/市场/就业补强诊断
10. 缺口与风险
11. 可进入 PPT 的确定事实
"""

OUTLINE_SYSTEM_PROMPT = """你是职业院校技能大赛作品汇报的大纲与现场执行策划 Agent。

基于资料分析，设计一份35-45页的比赛路演 PPT 大纲。页数由系统根据素材完整度与项目复杂度确定，必须服务于现场55分钟讲解和实操演示，而不是论文答辩。

这不是“项目汇报目录”，而是一条发布会式故事线：先制造真实问题张力，再让方案登场，再通过一次现场事件证明系统跑通，最后用运行记录、创新提炼和应用价值完成收束。

PPT 可见一级结构默认采用更像真实参赛作品的五大板块：
1. 项目背景
2. 研发历程
3. 实施过程
4. 创新设计
5. 应用价值

评分维度、采分逻辑、现场口令和内部角色调度只能作为后台策划依据，不能作为 PPT 可见标题或正文。

必须覆盖：
- 项目背景：时事新闻分析、政策背景支撑、市场考察调研、明确研发动因
- 项目定位、行业/岗位问题、任务挑战、帮助哪些行业或岗位
- 研发历程：产教融合（校企合作）、调研与痛点提炼、问题策略1:1对应、技术架构、安全与编码规范、团队匿名分工
- 技术方案、系统架构、关键技术难点
- 实施过程：必须围绕一次可演示事件组织，先给业务闭环，再现场跑通监测触发、设备联动、工单处置、数据复盘，然后拆解前端、后端、规则引擎、数据库/接口、测试保障
- 现场实操只能出现“操作闭环、输入/操作/输出/记录”，不得出现独立的“现场实操准备/演示准备/操作脚本已就绪”页面
- 每个核心功能模块的“功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结”
- 验证数据、测试环境、来源和验证方法
- 职业素养：规范、安全、质量、知识产权
- 创新设计：技术应用创新锚点、模式创新与社会价值、量化创新成效
- 应用价值：企业（经济/合作）、学校（教学/课程）、团队（技能/成长）、知识产权（专利/协议/软著）、就业与行业帮助、可持续性
- 团队合作：匿名角色分工、讲解与操作交接、异常协作
- 55分钟 run-of-show 和5分钟缓冲（仅用于讲稿/备注/内部执行，不进入可见页面）
- 页面级内容稿必须同时规划正式页面内容、主稿/子稿、主视觉类型、素材绑定、缺失处理和正式导出门禁。

不要出现个人信息。缺失信息只能在内部诊断中标记为“待补充”，PPT 可见页应改成“验证方法/采集清单/待实测口径”，不能补写成事实。
PPT 可见正文禁止出现“证据”二字；用支撑材料、运行记录、验证结果、成果材料、资料来源等参赛表达。
正式 PPT 可见正文不得出现“我们如何证明”“一张图看懂”“路演路线”“支撑材料的总链路”等系统策划语言。
正式 PPT 可见页面不得出现“现场实操演示准备”“演示环境已就绪”“操作脚本已就绪”“播放录屏”等后台准备信息；这些内容只能进入备注、fallback_plan 或 private_runbook。
"""

RUN_OF_SHOW_SYSTEM_PROMPT = """你是职业院校技能大赛现场执行分镜 Agent（FieldRunOfShowAgent）。

你的任务不是写 PPT 正文，而是把资料分析和大纲转成一份 55 分钟现场可执行脚本。它会指导后续 manuscript 每页怎么讲、谁操作、屏幕显示什么、故障时怎么处理。

硬性要求：
- 总时长按 55 分钟设计，允许 50-58 分钟范围，预留约 5 分钟给切屏、设备异常、评委观察和追问。
- 一级结构必须服务于五大可见板块：项目背景、研发历程、实施过程、创新设计、应用价值。
- 技能要点中的每个核心模块必须按：功能价值说明、关键技术/代码还原、产品效果测试、模块小结 来组织。
- 必须包含开场软硬件/安全/应急/环境确认。
- 必须包含匿名岗位角色：讲解角色、操作角色、测试角色、记录角色、应急角色。不得出现姓名、学校、电话、邮箱。
- 必须包含多屏或设备显示计划：main_screen、side_screen、operator_table、device_area。资料不足时写“待补充”。
- 必须包含现场故障恢复脚本：故障类型、排查动作、修复动作、复测成功判据、无法修复时的 fallback。
- 成果数据只允许来自资料或联网来源；无来源数据必须标记为“待补充来源”。

输出 Markdown，包含以下章节。注意：这份 Run-of-show 是私有执行脚本，后续只能进入 speaker_notes/private_runbook，不得作为 PPT 可见正文：
## 1. Site Setup
列出 main_screen、side_screen、operator_table、device_area、network_mode、fallback_assets。

## 2. Competition Blocks
用表格列出五大板块、目标时长、页码范围建议、后台能力支撑。不要使用“评分点/采分点”等可见化表达。

## 3. Module Demo Pattern
用表格列出每个核心模块的功能价值、关键技术/代码还原、产品测试、成功判据、故障恢复。

## 4. Segment Run-of-show
逐段列出：segment、duration_min、page_range、stage_mode、display_target、speaker_role、operator_role、support_role、command_cue、expected_screen_state、acceptance_signal、fallback_plan。

## 5. Support Materials and Result Claims
列出支撑材料 token 建议、成果数据、来源类型、是否可正式导出。注意这份执行脚本可以用内部术语，但 PPT 可见文字禁止出现“证据”二字。
"""

CONTESTANT_PERSPECTIVE_SYSTEM_PROMPT = """你是职业院校技能大赛作品汇报的选手视角策划 Agent（ContestantPerspectiveAgent）。

你的任务不是写 PPT 正文，而是把资料分析、大纲、现场分镜和支撑材料资产，转成每页“选手上台要讲清什么、展示什么、让评委记住什么”的页面策划。

必须遵守：
- 站在参赛选手和现场评委视角，而不是资料分析员视角。
- 像发布会一样设计连续故事线：问题出现、方案登场、系统跑通、现场验证、数据复核、创新提炼、价值兑现。
- 每页先确定 proof_object，再选择 visual_pattern 和 primary_visual；不要先写卡片布局。
- 每页必须同时产出正式页面内容、讲稿、主视觉、素材绑定和缺失处理，不允许只写页面意图。
- 只学习参考 pattern 的页面功能与证明逻辑，不能复制任何姓名、学校、联系方式、赛事年份或外部 PPT 可见内容。
- 评分维度、口令、角色调度和内部执行脚本只能作为后台策划，不得变成可见正文。
- 缺少支撑材料时，proof_object 必须写“验证方法/待采集来源/替代表达”，不得伪造已验证数据。
- PPT 可见文字禁止出现“证据”二字；可见表达使用支撑材料、运行记录、验证结果、成果材料、资料来源。
- 不得策划独立的“现场实操演示准备/演示环境已就绪/操作脚本已就绪”页面；准备信息只能进入备注、fallback_plan 或 private_runbook。
- 现场演示必须是实施过程中的证明动作：用一次具体事件串起输入、操作、输出、运行记录和复盘，而不是在功能介绍后另起一组重复演示页。

输出 Markdown 表格或分节列表，覆盖目标页数。每页必须包含：
- page
- section
- contestant_intent: 选手这页上台要达成的意图
- audience_takeaway: 评委看完这页应该带走的一句话
- visible_claim: 允许出现在 PPT 上的核心主张
- page_core_sentence: 本页正式页面核心句
- visible_content: 本页可见正文要点和图表标签
- proof_object: type/source/must_be_visible/fallback
- visual_pattern: pattern_id + why
- primary_visual_type: 从 Primary Visual Contract 的 allowed type 里选择
- main_visual: type/asset_source/asset_status/fallback/export_rule
- required_assets: 本页需要的截图、照片、图表、日志、代码、证书或公开来源
- asset_gap_handling: 缺素材时是补采、降级、改写为计划，还是阻止正式导出
- speaker_notes: 可直接照读的正式讲稿，包含本页开场、主体论证、必要的演示/队友交接话术和自然转场；禁止出现页面设计、字段解释、主视觉说明或“项目名称、一句定位语”这类内部策划话。
- main_script: 主稿
- sub_script: 子稿
- next_slide_bridge: 这一页如何自然过渡到下一页
- story_role: 本页在发布会式故事线中的推进角色，只能从 raise_problem、reveal_solution、prove_flow、unpack_mechanism、verify_result、extract_innovation、land_value 中选一个

输出只写策划，不写完整 manuscript。
"""

MANUSCRIPT_SYSTEM_PROMPT = """你是职业院校技能大赛作品汇报 PPT 的 Manuscript Agent。

根据资料分析和大纲，生成最终 slide-structured manuscript。后续 SVG Executor 会逐页生成页面，所以你的输出必须稳定、可拆页、可渲染。

硬性规则：
- 输出必须只有完整的幻灯片稿件，不要前言、解释或评分报告。
- 全稿必须像发布会一样形成连续故事线，而不是项目汇报清单。页面顺序必须体现：问题出现 -> 方案登场 -> 系统跑通 -> 现场验证 -> 数据复核 -> 创新提炼 -> 价值兑现。
- 严禁生成独立的“现场实操演示准备”“演示环境已就绪”“操作脚本已就绪”“演示准备状态”页面；这类内容只能进入 transition、fallback_plan、speaker_notes 或 private_runbook。
- 严禁在测试/运行数据/稳定性之后再回头插入“准备演示”页面。现场演示必须放在实施过程内部，并围绕一次具体事件证明系统闭环。
- 功能页和演示页不得重复介绍同一功能：功能页讲实现机制，演示页讲一次现场事件如何从输入到输出再到运行记录。
- 严禁出现可见正文高度重复的页面；如果两页标题、核心句和 visible_content 近似相同，必须合并或改成不同证明对象。
- 对35-45页正式稿，第18-24页附近必须继续承接这次现场事件：输入进入、判断触发、联动处置、移动端/大屏确认、日志/工单复盘、技术机制解释、测试复核；不得连续输出“前端开发/后端开发/某模块实现了”的项目汇报页。
- 每页顶部必须有且只能有一个 page_type 元数据：`<!-- page_type: cover|chapter|content|ending -->`。
- 只允许 cover、chapter、content、ending 四种 page_type。
- 用独立一行 `---` 分隔页面。
- 第1页必须是 cover，最后1页必须是 ending。
- 目录页作为 content 页处理。
- 页面数必须满足用户指定数量；未指定时由系统根据素材完整度与项目复杂度在35-45页内确定。
- 每页内容要短句化，避免整段文字，给后续页面生成留出视觉空间。
- 每页必须先写“可见页面内容”，再写内部策划字段。可见页面内容只能包含评委应该看到的项目事实、结论、图表标签、支撑材料摘要。
- 每页可见页面内容后必须写 Slide Content Plan 字段：page_core_sentence、visible_content、main_visual、visual_asset_plan、required_assets、asset_status、fallback_visual、asset_gap_handling、export_gate、speaker_notes、main_script、sub_script、transition。
- speaker_notes 是给选手上台直接念的正式口播稿，不是页面分析、设计思路、备注或提示词。必须像现场转写稿一样自然连续：称呼评委、承接上一页、说明本页事实、解释系统/数据/材料意义、必要时交接演示同学、自然进入下一页。
- speaker_notes 禁止出现“本页/这一页/这页核心观点”“评委视角”“证明任务”“证明对象”“它的作用是”“讲解时”“可以自然提示”“如果现场进入”“字段”“备注”“待补充”“主视觉”“页面”“版式”“布局”“项目名称、一句定位语”等元思考或设计策划语句。
- speaker_notes 不能写“首先，项目名称……”或“接下来继续汇报目录，把内容落到材料和系统能力上”这类给生成器看的说明；必须改写成选手会真实讲出口的句子，例如“接下来，我们先看本次汇报的整体结构”。
- page_core_sentence 和 visible_content 必须直接给出正式页面内容，不能只写页面用途；不得出现“我们如何证明”“一张图看懂”“路演路线”“支撑材料的总链路”等系统策划语言。
- main_visual 必须包含 type、asset_source、asset_status、fallback、export_rule；真实截图/证书/测试结果缺失时不能用 SVG 或生成图伪造成真实素材。
- 如果 Support Material Binder Report 中有 12 个以上上传图片素材，正式稿至少约一半内容页应绑定 `[[ASSET:asset_id]]`；系统截图、设备现场图、运行图表、应用反馈图和正式材料图有素材时必须优先作为主视觉。
- PPT 可见标题、正文、图表标签、页脚均禁止出现“证据”二字；统一使用支撑材料、运行记录、验证结果、成果材料、资料来源、现场记录。
- 每页必须包含页面视觉策划字段：page_role、judge_focus、visual_strategy、layout_hint、evidence_assets、speaker_goal；这些字段是内部设计依据，不是 PPT 可见正文。
- 每页必须包含选手视角策划字段：contestant_intent、audience_takeaway、proof_object、visual_pattern、next_slide_bridge；这些字段用于让页面像真实参赛选手在现场证明项目，而不是资料摘要。
- 每页必须包含 `story_role:`，只能从 raise_problem、reveal_solution、prove_flow、unpack_mechanism、verify_result、extract_innovation、land_value 中选一个；story_role 只用于内部，不得可见。
- proof_object 必须说明 type、source、must_be_visible、fallback；没有真实支撑材料时，fallback 写验证方法或待采集来源，不得伪造已完成数据。
- visual_pattern.pattern_id 必须来自 Reference Pattern Library，不得自造 pattern。
- 每页必须包含 primary_visual 合同字段，字段中必须写 type、purpose、required_elements、visual_weight、forbidden_layouts。
- primary_visual.type 必须从以下类型中选择：cover_scene、agenda_timeline、problem_map、solution_map、architecture_map、data_flow、technical_mechanism、rule_tree、live_demo_board、code_explain_board、operation_flow、support_material_flow、test_dashboard、result_dashboard、risk_fallback、team_handoff、policy_market_map、industry_value_map、employment_role_map、school_enterprise_map、innovation_map、conclusion_map。
- 技术页、实操页、支撑材料页和成果页必须把 primary_visual 作为画面主体，不得把“三列卡片、四张信息卡片、2x2网格、表格”作为主布局。
- 每页必须包含现场执行字段：stage_mode、display_target、time_budget_sec、speaker_role、operator_role、operator_action、expected_screen_state、fallback_plan、module_flow、acceptance_signal、command_cue；这些字段只用于备注/执行脚本/private_runbook，不得成为 PPT 可见文字。
- 页面视觉策划字段和现场执行字段用于指导设计，不是给观众逐字阅读的正文；字段值必须短、具体、可执行。
- PPT 可见正文禁止出现：证据、评分要素、评分点、评分维度、得分点、采分点、展示映射、操作角色A/B、讲解角色A/B、记录角色、关键节点口令、口令交接、成功信号、正式导出门禁、测试草稿版、草稿态、来源待补充、未核验数据、模拟截图、模拟日志、模拟测试数据、XX职业院校、XX代表队。
- 实操页必须包含：输入、操作者匿名角色、讲解者匿名角色、操作步骤、输出、运行记录、异常预案。实操页标题必须是具体动作或事件，如“温度异常触发与预警生成”“设备联动与工单处置”，不得是“实操准备/演示准备/操作脚本”。
- 核心功能模块必须按“功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结”形成链条，不得只做产品功能介绍。
- 代码还原页只讲关键函数、接口、协议、配置或算法逻辑，不要整屏堆代码。
- 产品测试页必须在内部字段写成功判据 acceptance_signal 和现场口令 command_cue，但 PPT 可见页只能写“测试目标/输入条件/输出结果/运行记录”，不能显示口令或成功信号这类后台词。
- 关键实操页必须写 fallback_plan，说明现场失败时的排查、修复、复测或切换预置材料。
- 团队分工的内部字段可以使用匿名角色；PPT 可见页应使用岗位或模块表达，如“项目统筹、前端实现、设备接入、算法与测试”，不得出现真实姓名或学校，也不要出现“讲解角色A/操作角色B”。
- 背景页必须显式覆盖时事新闻、政策、市场调研、研发动因中的至少一个；不能只写宏大口号。
- 价值页必须显式覆盖企业经济/合作、学校教学/课程、团队技能成长、知识产权或就业/行业帮助中的至少两个；不能只写社会价值口号。
- 数据页必须写来源/验证方法；没有来源的数据必须标注“待补充”，不能编造。
- 正式页面不得出现“占位符”；缺素材只能在 asset_gap_handling/export_gate 中标记，或把可见正文改成验证方法/采集口径。
- 可使用有效的 `[[FIG:...]]` 资料图 token，但只能使用用户资料中真实存在的 token。
"""

VISUAL_PLAN_SYSTEM_PROMPT = """你是职业院校技能大赛路演 PPT 的页面视觉策划 Agent。

你的任务不是重写内容，而是在不改变页数、不改变顺序、不改变事实的前提下，为每一页补充稳定的页面级视觉策划字段，让后续 SVG Executor 明确知道这页应该怎么被设计。

必须保留：
- 原有页数。
- 原有 `---` 分隔。
- 每页顶部的 `<!-- page_type: ... -->`。
- 原有标题、核心内容、支撑材料 token、数据来源和匿名角色。

必须为每一页增加以下字段，字段名保持英文，字段值用中文短句：
- `page_core_sentence:` 本页正式页面核心句，必须可直接放进 PPT。
- `visible_content:` 本页正式可见正文，包括要点、图表标签、数据口径。
- `main_visual:` 本页主视觉方案，必须包含 type、asset_source、asset_status、fallback、export_rule。
- `visual_asset_plan:` 主视觉如何落版，说明使用真实图片、截图、图表、证书、生成图、SVG 或不需要。
- `required_assets:` 本页需要的具体素材清单。
- `asset_status:` provided、derivable、missing、not_required、draft_only、blocking 之一。
- `fallback_visual:` 缺素材时如何表达；结构类页面可用 SVG，真实材料缺失时不得伪造。
- `asset_gap_handling:` 缺素材时如何补采、降级、改写或阻止正式导出。
- `export_gate:` formal_ok、draft_only、blocked_until_assets 之一。
- `page_role:` 这页在路演中的角色，例如“封面建立项目识别”“解释系统怎么跑起来”“展示实操闭环”。
- `judge_focus:` 后台能力支撑，不得作为 PPT 可见文字，例如“技术先进性”“协作闭环”“数据可追溯”。
- `visual_strategy:` 这页的视觉表达方式，例如“大标题叠加抽象设备插画”“五层架构流程图”“输入-操作-输出-记录闭环”“KPI矩阵”。
- `layout_hint:` 具体布局建议，例如“左侧流程主图，右侧运行记录卡片”“顶部结论，下方三列指标”“中间横向时间线”。
- `evidence_assets:` 可用支撑材料或素材，必须来自资料事实；没有就写“待补充”，不要编造截图或数据。
- `speaker_goal:` 讲解这页时要达成的一句话目标。
- `speaker_notes:` 正式可直接照读的讲稿，约 320-520 个中文字符，要像职业院校技能大赛现场汇报：称呼自然、逻辑完整、表述专业，包含上页承接、项目事实、关键材料/系统能力、面向评委的价值说明，以及从当前内容到下一内容的转场；演示、测试、代码页必须包含自然交接话术。禁止写成页面说明、设计思考、备注或内部提示；禁止出现“主视觉、版式、布局、字段、证明对象、项目名称、一句定位语”等内部词。
- `main_script:` 主稿，说明这页上台主要讲什么。
- `sub_script:` 子稿，说明补充解释、可追问细节或操作提示。
- `transition:` 下一页承接句。
- `contestant_intent:` 选手站在台上通过这一页要证明什么。
- `audience_takeaway:` 评委看完这一页应该记住的一句话。
- `proof_object:` 页面证明对象，必须包含 type、source、must_be_visible、fallback；没有来源时写验证方法或待采集来源。
- `visual_pattern:` 参考 pattern，必须包含 pattern_id 和 why；pattern_id 只能来自 Reference Pattern Library。
- `next_slide_bridge:` 这一页如何自然过渡到下一页。
- `story_role:` 本页在发布会式故事线中的推进角色，只能从 raise_problem、reveal_solution、prove_flow、unpack_mechanism、verify_result、extract_innovation、land_value 中选择；不得作为可见正文。
- `primary_visual:` 页面主视觉合同。必须包含 type、purpose、required_elements、visual_weight、forbidden_layouts。type 只能从 cover_scene、agenda_timeline、problem_map、solution_map、architecture_map、data_flow、technical_mechanism、rule_tree、live_demo_board、code_explain_board、operation_flow、support_material_flow、test_dashboard、result_dashboard、risk_fallback、team_handoff、policy_market_map、industry_value_map、employment_role_map、school_enterprise_map、innovation_map、conclusion_map 中选择。
- `stage_mode:` 现场模式，例如 ppt_explain、live_system、code_walkthrough、mobile_mirror、device_demo、material_review、handoff、fault_recovery。
- `display_target:` main_screen、side_screen、both_screens、operator_table、physical_device 或 待补充。
- `time_budget_sec:` 本页建议现场用时，数字秒数。
- `speaker_role:` 匿名讲解角色，内部使用，不得出现在可见正文。
- `operator_role:` 匿名操作角色，内部使用；不涉及则写“待命”。
- `operator_action:` 现场需要执行的动作；不涉及则写“无”。
- `expected_screen_state:` 操作后屏幕/设备应显示的状态。
- `fallback_plan:` 现场失败时的排查、修复、复测或预置材料切换方案。
- `module_flow:` 功能讲解、代码还原、产品测试、故障修复、模块小结、成果汇报等。
- `acceptance_signal:` 本页/本段演示成功时评委应看到什么，内部使用，不能作为可见文字。
- `command_cue:` 讲解者给操作者或测试角色的口令，内部使用，不能作为可见文字；不涉及则写“无”。

字段写法示例：
page_core_sentence: 系统把异常识别、处置反馈和运行记录连成可追溯闭环。
visible_content: 输入环境数据；触发异常识别；生成处置建议；记录处理结果；形成运行记录。
main_visual:
  type: screenshot
  asset_source: 系统异常识别页面截图、接口日志、处置记录
  asset_status: provided
  fallback: 缺截图时改为操作流程 SVG，并将运行效果标为待实测口径。
  export_rule: 正式版必须使用真实截图或真实测试记录。
visual_asset_plan: 中间放系统截图，四周标注输入、操作、输出、记录。
required_assets: 系统页面截图、接口日志、测试记录、异常处理记录。
asset_status: provided
fallback_visual: operation_flow SVG
asset_gap_handling: 缺少真实截图时只保留验证流程，不写成已完成运行效果。
export_gate: formal_ok
page_role: 展示现场实操闭环，让评委快速理解输入、操作、输出和运行记录。
judge_focus: 操作规范性；现场讲解效果；数据可追溯。
visual_strategy: 使用四段闭环呈现输入/操作/输出/记录，记录列用小卡片强调。
layout_hint: 顶部一句结论，中部四列流程表，底部放风险提示和备用方案。
evidence_assets: 设备列表截图、接口日志、工单处理记录；缺失项标记待补充。
speaker_goal: 证明系统不仅能告警，还能完成可追溯处置闭环。
main_script: 本页从一次异常处置开始，说明系统如何完成识别、处理和记录。
sub_script: 讲解时补充输入数据来源、接口日志位置和复测方式。
contestant_intent: 让评委看到选手不是在讲概念，而是在现场完成一次可复核的处置流程。
audience_takeaway: 系统能把异常识别、处理和留证连成闭环。
proof_object:
  type: live_demo
  source: 设备列表截图、接口日志、工单处理记录
  must_be_visible: 前端状态、日志留存、处置结果
  fallback: 若截图缺失，展示验证步骤和待采集材料清单，不写成已完成数据。
visual_pattern:
  pattern_id: live_demo_input_action_output_evidence
  why: 本页需要说明现场输入、操作、输出、记录闭环。
next_slide_bridge: 由处置结果过渡到测试记录和复测证明。
story_role: prove_flow
primary_visual:
  type: live_demo_board
  purpose: 让评委一眼看懂输入、操作、输出、运行记录与备用方案。
  required_elements: 输入数据、操作步骤、预期画面、结果状态、运行记录留存、失败切换。
  visual_weight: 70%
  forbidden_layouts: 纯四卡片、纯列表、只有表格。
stage_mode: live_system
display_target: main_screen + side_screen
time_budget_sec: 120
speaker_role: 讲解角色A
operator_role: 操作角色B
operator_action: 在后台选择设备并触发异常识别。
expected_screen_state: 中央屏显示识别结果，副屏显示操作日志。
fallback_plan: 若现场接口失败，切换预置截图并说明来源，随后执行复测步骤。
module_flow: 产品测试
acceptance_signal: 前端显示环境数据、预警状态和日志记录。
command_cue: 主讲提示操作端触发识别流程。

输出完整 manuscript，不要输出解释、评分报告或额外前言。
再次强调：page_core_sentence、visible_content、main_visual、visual_asset_plan、required_assets、asset_status、fallback_visual、asset_gap_handling、export_gate、speaker_notes、main_script、sub_script、transition、page_role、judge_focus、visual_strategy、layout_hint、story_role、primary_visual、stage_mode、display_target、operator_role、operator_action、fallback_plan、acceptance_signal、command_cue 等字段只能指导后续生成，不能成为 PPT 可见字段名。
"""

LIGHT_SLIDE_CONTENT_PLAN_SYSTEM_PROMPT = """你是职业院校技能大赛 PPT 的轻量页面内容策划 Agent。

你的任务只做第一层 SlideContentPlan，不写完整 manuscript、不写主稿长段、不写现场执行字段。
目标是先稳定确定每一页的正式标题、核心句、页面正文、主视觉类型和素材状态，避免后续一次性生成 40 页详细稿时爆长。

必须输出 exactly 目标页数的 Markdown 表格，字段如下：
page | page_type | section | formal_title | page_core_sentence | visible_content | main_visual_type | required_assets | asset_status | fallback_visual | export_gate

硬性规则：
- 第 1 页 page_type=cover，第 2 页为正式目录 content，最后 1 页 page_type=ending。
- 第 1 页封面不得绑定任何 `[[ASSET:...]]`，main_visual_type 必须为 svg_diagram 或 none，required_assets 写“无”，asset_status 写 not_required；封面用标题、副标题、色块、线条、抽象几何完成，不配图片背景。
- 第 2 页标题用“目录”或“项目大纲”，不要写“路演路线”“我们如何证明”。
- 正式标题和正文不得出现“我们如何证明”“一张图看懂”“支撑材料的总链路”“生成器”“内部逻辑”等系统策划语言。
- 正式标题和正文不得出现“现场实操演示准备”“演示环境已就绪”“操作脚本已就绪”“演示准备状态”“播放录屏”。准备、备用和脚本内容只能进入后续备注/执行字段。
- 页面必须按故事线推进：问题出现 -> 方案登场 -> 系统跑通 -> 现场验证 -> 数据复核 -> 创新提炼 -> 价值兑现；不能把实施过程做成模块清单后再插入一页“准备演示”。
- 不能生成重复页；相邻或隔页出现同一标题、同一核心句、同一正文时，必须合并或改成不同证明对象。
- 35-45页正式稿的第18-24页附近必须延续一次现场事件的输入、判断、处置、记录、复盘；不得连续写成前端/后端/模块职责说明书。
- main_visual_type 只能使用 real_image、screenshot、product_ui、chart、certificate、material_photo、generated_image、svg_diagram、none。
- 产品界面、运行效果、测试记录、证书、专利、协议、应用反馈必须优先绑定真实素材；缺失时 export_gate=draft_only 或 blocked_until_assets。
- 如果表格中的真实素材可用，required_assets 必须写 `[[ASSET:asset_id]]`，不要写中文路径；系统截图、设备照片、数据图表、视频关键帧和成果材料有素材时不得降级成纯 SVG。
- 若可用上传图片素材超过 12 个，至少 45% 页面需要在 required_assets 里绑定真实 `[[ASSET:asset_id]]`，不能把真实素材包闲置成 SVG 摘要稿。
- 政策背景、痛点归纳、总体思路、系统架构、业务流程、数据流程、技术路线、价值矩阵、未来规划可以使用 svg_diagram。
- visible_content 必须是可以直接上 PPT 的正式中文内容，不能只写“说明本页作用”。
"""

IMAGE2_CLEAN_OUTLINE_SYSTEM_PROMPT = """你是职业院校技能大赛路演 PPT 的 image2 干净页纲 Agent。

你的任务是生成适合整页图片模型直接理解的页面规划，而不是生成 SVG 策略、可编辑字段或后台校验字段。

输出必须是 Markdown 表格，列名必须严格服从用户给出的 Image2 Lightweight Outline Contract。

硬性规则：
- 只写正式页面主题、核心信息、可见要点、完整画面场景、素材引用和讲述目标。
- 不得输出 asset_status、export_gate、fallback_visual、layout_hint、primary_visual、proof_object、operator_action、expected_screen_state 等内部字段。
- visible_points 必须是可直接放上 PPT 的正式中文短句，不能写“本页围绕项目事实展开说明”“待补充”“详见素材”等占位话。
- visual_scene 必须描述完整 PPT 页面画面，不要写 SVG 组件方案。
- 第 1 页封面不绑定上传素材，但必须允许 image2 生成完整封面视觉；禁止写“不配图”“空白背景”“只放文字”。
- 使用上传素材时只在 asset_refs 中写 `[[ASSET:asset_id]]`，不要把 asset_id 当成可见页面文字。
"""

REVIEW_SYSTEM_PROMPT = """你是职业院校技能大赛 PPT 评审与合规 Review Agent。

评审维度：
- 技能水平60：规范性、熟练度、任务难度、先进性、现场讲解效果
- 职业素养10：职业道德、工匠精神、安全意识
- 应用价值10：实用性、经济性、可持续性
- 团队合作10：团队精神、沟通协作
- 创新创意10：创新意识、创新成效

如果稿件已经满足要求，输出 `QUALITY_CHECK_PASSED`。
如果存在严重问题，输出完整修订后的 manuscript。严重问题包括：
- 出现个人信息
- 编造数据或来源
- 缺少现场实操环节
- 缺少55分钟执行节奏
- 缺少设备/环境/备用方案
- 缺少团队匿名分工
- 缺少页面视觉策划字段 page_role、judge_focus、visual_strategy、layout_hint、evidence_assets、speaker_goal
- 缺少页面内容稿字段 page_core_sentence、visible_content、main_visual、visual_asset_plan、required_assets、asset_status、fallback_visual、asset_gap_handling、export_gate、speaker_notes、main_script、sub_script、transition
- 缺少选手视角字段 contestant_intent、audience_takeaway、proof_object、visual_pattern、next_slide_bridge
- proof_object 没有 type/source/must_be_visible/fallback，或 visual_pattern.pattern_id 不在参考 pattern 库内
- 缺少 primary_visual 合同，或 primary_visual 缺少 type、purpose、required_elements、visual_weight、forbidden_layouts
- 技术页、实操页、支撑材料页、成果页仍以纯卡片/纯列表/纯表格作为主视觉
- 缺少现场执行字段 stage_mode、display_target、time_budget_sec、speaker_role、operator_role、operator_action、expected_screen_state、fallback_plan、module_flow、acceptance_signal、command_cue
- 缺少故事线推进字段 story_role，或全稿像项目汇报清单而不是“问题 -> 方案 -> 跑通 -> 验证 -> 价值”的连续故事线
- 第18-24页附近的实施过程仍像前端/后端/模块说明书，没有围绕一次现场事件形成输入、判断、处置、记录、复盘链
- 出现重复页，或两页标题/核心句/正文只是换词但证明对象相同
- 上传图片素材充足却没有形成足够的真实素材页，系统截图、设备图、运行图表、反馈图被降级成纯 SVG
- 出现独立的“现场实操演示准备/演示环境已就绪/操作脚本已就绪/演示准备状态”页面
- 测试、运行数据或稳定性页面之后又回头进入“准备演示/开始演示”页面，导致故事线倒退
- 核心模块缺少“功能价值/代码还原/产品测试/模块小结”链条
- 成果数据、百分比、金额、推广数量缺少来源
- 真实截图、运行效果、测试结果、证书、协议、专利材料缺失却被写成已完成事实
- 声称现场实操但没有故障恢复或复测方案
- 页面结构不满足 page_type 和分隔规则
- 项目背景没有覆盖时事新闻/政策/市场/研发动因，或应用价值没有覆盖企业、学校、团队、知识产权、就业/行业帮助
- PPT 可见正文出现“证据”二字，或出现评分点、采分点、口令、操作角色、字段名、导出门禁、待补充来源、模拟测试数据等后台语言
- PPT 可见正文出现“我们如何证明”“一张图看懂”“路演路线”“支撑材料的总链路”等系统策划语言
"""


PAGE_COUNT_EVIDENCE_TYPES = (
    "system_screenshot",
    "workflow_diagram",
    "code_or_interface",
    "test_record",
    "log_record",
    "device_or_scene",
    "result_claim_source",
    "fault_recovery",
)

PAGE_COUNT_MODULE_MARKERS = (
    "模块一",
    "模块二",
    "模块三",
    "模块四",
    "模块五",
    "核心模块",
    "功能模块",
    "子系统",
)

PAGE_COUNT_TECH_GROUPS = (
    ("前端", "大屏", "小程序", "移动端", "Web", "Vue", "React"),
    ("后端", "接口", "API", "服务", "Spring", "FastAPI"),
    ("数据库", "SQL", "MySQL", "Redis", "数据表"),
    ("算法", "模型", "识别", "预测", "规则引擎", "阈值"),
    ("硬件", "设备", "传感器", "控制器", "网关", "物联网", "IoT"),
    ("测试", "验收", "日志", "运行记录", "复测", "工单"),
)


def _target_page_count(num_pages: int | None) -> int:
    if num_pages and 35 <= num_pages <= 45:
        return num_pages
    if num_pages and num_pages < 35:
        return num_pages
    if num_pages and num_pages > 45:
        return 45
    return 40


def _roadshow_page_count_decision(
    *,
    num_pages: int | None,
    paper: ParsedPaper,
    source_md: str,
    source_profile: dict,
    material_analysis: str = "",
    evidence_report: dict | None = None,
) -> dict:
    """Choose a formal roadshow page count from source richness and complexity."""
    if num_pages:
        return {
            "mode": "explicit",
            "requested_num_pages": num_pages,
            "recommended_pages": _target_page_count(num_pages),
            "reason": "用户或前端显式指定页数，后端只做合法范围处理。",
            "factors": {},
        }

    evidence_report = evidence_report or {}
    available_assets = evidence_report.get("available_assets") or []
    available_types = evidence_report.get("available_types") or []
    missing_types = evidence_report.get("missing_core_types") or []
    text = f"{source_md}\n\n{material_analysis}"
    source_chars = len(source_md)
    uploaded_figure_count = len([asset for asset in available_assets if asset.get("source") == "uploaded_figure"])
    text_asset_count = len([asset for asset in available_assets if asset.get("source") == "uploaded_text"])
    module_marker_hits = sum(1 for marker in PAGE_COUNT_MODULE_MARKERS if marker in text)
    tech_group_hits = sum(1 for group in PAGE_COUNT_TECH_GROUPS if any(token.lower() in text.lower() for token in group))
    value_hits = sum(1 for token in ("成果", "应用", "推广", "企业", "学校", "就业", "知识产权", "专利", "协议") if token in text)
    readiness_bonus = 1 if evidence_report.get("formal_readiness") == "ready" else 0

    score = 35
    factors: dict[str, int | str | bool] = {
        "source_chars": source_chars,
        "available_asset_count": len(available_assets),
        "uploaded_figure_count": uploaded_figure_count,
        "text_asset_count": text_asset_count,
        "available_type_count": len(available_types),
        "missing_core_type_count": len(missing_types),
        "module_marker_hits": module_marker_hits,
        "tech_group_hits": tech_group_hits,
        "value_hits": value_hits,
        "agent_seed_draft": bool(source_profile.get("agent_seed_draft")),
    }

    source_bonus = 2 if source_chars >= 50000 else 1 if source_chars >= 12000 else 0
    figure_bonus = 3 if uploaded_figure_count >= 16 else 2 if uploaded_figure_count >= 8 else 1 if uploaded_figure_count >= 3 else 0
    text_bonus = 1 if text_asset_count >= 5 else 0
    asset_bonus = figure_bonus + text_bonus
    type_bonus = 2 if len(available_types) >= 6 else 1 if len(available_types) >= 3 else 0
    module_bonus = 2 if module_marker_hits >= 5 else 1 if module_marker_hits >= 3 else 0
    tech_bonus = 2 if tech_group_hits >= 6 else 1 if tech_group_hits >= 4 else 0
    value_bonus = 1 if value_hits >= 5 else 0
    missing_penalty = min(3, len(missing_types) // 2)
    if len(available_assets) <= 2 and source_chars < 8000:
        missing_penalty += 1

    score += source_bonus + asset_bonus + type_bonus + module_bonus + tech_bonus + value_bonus + readiness_bonus
    score -= missing_penalty
    recommended = max(35, min(45, score))

    factors.update(
        {
            "source_bonus": source_bonus,
            "figure_bonus": figure_bonus,
            "text_bonus": text_bonus,
            "asset_bonus": asset_bonus,
            "type_bonus": type_bonus,
            "module_bonus": module_bonus,
            "tech_bonus": tech_bonus,
            "value_bonus": value_bonus,
            "readiness_bonus": readiness_bonus,
            "missing_penalty": missing_penalty,
        }
    )
    if recommended <= 36:
        reason = "素材较少或核心支撑类型缺口较多，采用35-36页的紧凑正式稿。"
    elif recommended <= 40:
        reason = "素材与模块复杂度处于常规水平，采用38-40页左右的正式稿。"
    else:
        reason = "素材较丰富且模块/技术/价值链条较多，扩展到42-45页承载完整故事线。"
    return {
        "mode": "adaptive",
        "requested_num_pages": None,
        "recommended_pages": recommended,
        "reason": reason,
        "factors": factors,
    }


def _roadshow_slide_contract(num_pages: int | None) -> str:
    count = _target_page_count(num_pages)
    return (
        f"生成 exactly {count} slides，结构页计入总页数。\n"
        "- 第1页 cover，第2页建议目录 content，最后1页 ending。\n"
        "- 职业赛制正式稿建议35-45页；快速验证可少于35页。\n"
        "- 所有页面必须用独立一行 `---` 分隔，分隔线数量=页数-1。\n"
        "- 每页必须写 `<!-- page_type: cover|chapter|content|ending -->`。\n"
        "- chapter 只用于主要模块切换，实操准备/实操过程/成果材料/团队分工/创新价值均可作为 content 页。"
    )


def _slide_ranges(total_pages: int, chunk_size: int = ROADSHOW_CHUNK_SIZE) -> list[tuple[int, int]]:
    return [
        (start, min(start + chunk_size - 1, total_pages))
        for start in range(1, total_pages + 1, chunk_size)
    ]


def _normalize_roadshow_page_boundaries(manuscript: str) -> str:
    """Repair LLM drift where field sections inside one slide are split by `---`."""
    parts = [part.strip() for part in re.split(r"(?m)^\s*---\s*$", manuscript) if part.strip()]
    pages: list[str] = []
    current: list[str] = []

    for part in parts:
        if PAGE_TYPE_MARKER_RE.search(part):
            if current:
                pages.append("\n\n".join(current).strip())
            current = [part]
        elif current:
            current.append(part)
        else:
            current = [part]

    if current:
        pages.append("\n\n".join(current).strip())

    normalized = "\n\n---\n\n".join(pages)
    return PRIVATE_GROUP_HEADING_RE.sub("", normalized).strip()


def _normalize_roadshow_field_labels(manuscript: str) -> str:
    """Normalize `**field**:` drift to `field:` so private fields stay private."""
    allowed = {
        "page",
        "section",
        "formal_title",
        "title",
        *PRIVATE_FIELD_NAMES,
    }
    allowed_lower = {item.lower() for item in allowed}

    def _replace(match: re.Match) -> str:
        name = match.group(2)
        if name.lower() not in allowed_lower:
            return match.group(0)
        return f"{match.group(1)}{name}:"

    return ROADSHOW_FIELD_LABEL_RE.sub(_replace, manuscript)


def _roadshow_field_value(page: str, name: str) -> str:
    pattern = re.compile(ROADSHOW_FIELD_VALUE_RE_TEMPLATE.format(name=re.escape(name)))
    match = pattern.search(page)
    if not match:
        return ""
    value = match.group(1).strip()
    value = re.sub(r"\n{2,}", "\n", value).strip()
    return value


def _clean_visible_value(value: str, *, max_chars: int = 900) -> str:
    value = value.strip()
    value = re.sub(r"^\{|\}$", "", value).strip()
    value = re.sub(r"(?m)^\s*\*\*\s+", "", value)
    value = value.replace("**", "")
    value = re.sub(r"\s+", " ", value)
    value = value.replace("。 ", "。\n").replace("； ", "；\n")
    return value[:max_chars].strip()


def _clean_formal_title(value: str, *, max_chars: int = 46) -> str:
    value = _clean_visible_value(value, max_chars=160)
    value = value.splitlines()[0] if value else ""
    value = re.sub(r"^\s*#{1,6}\s*", "", value)
    value = re.sub(r"^\s*[-*•\d.、]+\s*", "", value)
    value = re.sub(r"^(?:正式标题|页面标题|标题|formal_title|title)\s*[:：]\s*", "", value, flags=re.I)
    value = value.strip(" `*_#：:，,。；;|")
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) <= max_chars:
        return value
    cut = value[:max_chars]
    for sep in ("。", "；", ";", "：", ":", "，", ","):
        pos = cut.rfind(sep)
        if pos >= 10:
            return cut[:pos].strip()
    return cut.rstrip()


def _title_looks_dirty_or_truncated(title: str) -> bool:
    raw = title.strip()
    clean = _clean_formal_title(raw)
    if not clean:
        return True
    if raw != clean or "**" in raw or raw.startswith("*"):
        return True
    if len(clean) <= 2:
        return True
    if clean in {"因此", "市场调研显示"}:
        return True
    if any(term in clean for term in ("本次汇报将围绕", "为何做", "如何做", "有何价值")):
        return True
    return clean[-1] in {"的", "在", "将", "为", "与", "和", "中", "从", "把"}


def _fallback_formal_title(page: str, index: int) -> str:
    for field in ("formal_title", "title"):
        value = _roadshow_field_value(page, field)
        if value:
            title = _clean_formal_title(value)
            if title:
                return title
    core = _clean_visible_value(_roadshow_field_value(page, "page_core_sentence"), max_chars=90)
    if core:
        return _clean_formal_title(re.split(r"[。；;]", core)[0])
    section = _clean_visible_value(_roadshow_field_value(page, "section"), max_chars=24)
    return section or f"第 {index} 页"


def _split_visible_prefix_and_private_tail(lines: list[str]) -> tuple[list[str], list[str]]:
    field_re = re.compile(
        r"^\s*(?:\*\*)?(?:"
        + "|".join(re.escape(name) for name in ("page", "section", "formal_title", "title", *PRIVATE_FIELD_NAMES))
        + r")(?:\*\*)?\s*:",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        if field_re.match(line):
            return lines[:index], lines[index:]
    return lines, []


def _clean_existing_visible_prefix(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or re.match(r"\s*<!--.*?-->\s*$", stripped):
            continue
        stripped = re.sub(r"^\s*\*\*\s*", "", stripped).replace("**", "").strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


SPEAKER_NOTES_META_RE = re.compile(
    r"本页|这一页|这页|页面|核心观点|核心结论|核心信息|评委视角|"
    r"留下的判断|要回答的是|证明任务|证明对象|它的作用是|讲解时|"
    r"可以自然提示|如果现场|字段|备注|待补充|主视觉|版式|布局|"
    r"项目名称|一句定位语|继续汇报目录|把内容落到|设计思路|页面分析|"
    r"底部任务|副标题|可见内容|标题层级|设计上|画面中|这里要|这一部分重点说明|"
    r"可见正文|speaker_notes|main_script|sub_script|transition|next_slide_bridge",
    re.IGNORECASE,
)


def _clean_speaker_notes_value(value: str, *, title: str, core: str) -> str:
    text = str(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[\[(?:ASSET|FIG):[^\]]+\]\]", "", text, flags=re.IGNORECASE)
    text = re.sub(
        r"(?im)^\s*(?:speaker_notes|speech_script|script|main_script|sub_script|transition)\s*[:：]\s*",
        "",
        text,
    )
    text = re.sub(
        r"接下来继续汇报目录，把内容落到材料和系统能力上[。！？!?]?",
        "接下来，我们先看本次汇报的整体结构。",
        text,
    )
    text = re.sub(r"首先[，,]?\s*项目名称[、，,]\s*一句定位语[^。！？!?]*[。！？!?]?", "", text)
    text = re.sub(r"项目名称[、，,]\s*一句定位语[^。！？!?]*[。！？!?]?", "", text)
    text = re.sub(r"首先[，,]?\s*(?:副标题|底部任务|标题层级|可见内容)[^。！？!?]*[。！？!?]?", "", text)
    text = re.sub(r"接下来[，,]?\s*我们继续汇报[“\"]?目录[”\"]?[^。！？!?]*[。！？!?]?", "接下来，我们先看本次汇报的整体结构。", text)
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[。！？!?])\s*", text)
    cleaned = [
        sentence.strip()
        for sentence in sentences
        if sentence.strip() and not SPEAKER_NOTES_META_RE.search(sentence)
    ]
    result = "".join(cleaned).strip()
    if not result:
        title_text = _clean_formal_title(title, max_chars=40) or "当前内容"
        core_text = _clean_visible_value(core, max_chars=120) or f"围绕{title_text}说明项目事实、系统能力和支撑材料。"
        result = (
            f"各位评委老师，下面进入{title_text}。"
            f"{core_text}"
            "我们会结合真实材料、运行记录和现场演示结果，说明项目如何解决实际问题，并把相关能力落实到可复核的应用价值上。"
        )
    if not re.search(r"[。！？!?]$", result):
        result += "。"
    return result[:1000].strip()


def _sanitize_roadshow_speaker_notes(manuscript: str) -> str:
    """Remove prompt/meta language from speaker_notes after LLM generation."""
    pages = split_manuscript_pages(_normalize_roadshow_field_labels(manuscript))
    normalized_pages: list[str] = []
    field_re = re.compile(
        r"(?ims)^(\s*(?:\*\*)?speaker_notes(?:\*\*)?\s*:\s*)"
        r"(.*?)(?=^\s*(?:\*\*)?[A-Za-z_][A-Za-z0-9_]*(?:\*\*)?\s*:|^\s*<!--|^\s*#|\Z)"
    )
    for index, page in enumerate(pages, start=1):
        title = _fallback_formal_title(page, index)
        core = _roadshow_field_value(page, "page_core_sentence") or _roadshow_field_value(page, "visible_content")

        def _replace(match: re.Match) -> str:
            return f"{match.group(1)}{_clean_speaker_notes_value(match.group(2), title=title, core=core)}\n"

        normalized_pages.append(field_re.sub(_replace, page, count=1))
    return "\n\n---\n\n".join(normalized_pages)


def _ensure_formal_page_content(manuscript: str) -> str:
    """Ensure every slide has a real heading and visible body before private fields."""
    pages = split_manuscript_pages(_normalize_roadshow_field_labels(manuscript))
    normalized_pages: list[str] = []
    for index, page in enumerate(pages, start=1):
        lines = page.strip().splitlines()
        meta: list[str] = []
        rest: list[str] = []
        for line in lines:
            if re.match(r"\s*<!--.*?-->\s*$", line):
                meta.append(line)
            else:
                rest.append(line)
        visible_prefix, private_tail = _split_visible_prefix_and_private_tail(rest)
        body = "\n".join(rest).strip()
        heading_match = re.search(r"(?m)^#{1,3}\s+(.+?)\s*$", body)
        heading = _clean_formal_title(heading_match.group(1)) if heading_match else ""
        visible = _clean_visible_value(_roadshow_field_value(page, "visible_content"))
        core = _clean_visible_value(_roadshow_field_value(page, "page_core_sentence"), max_chars=180)
        title = _fallback_formal_title(page, index) if _title_looks_dirty_or_truncated(heading) else heading
        if index == 2 and any(term in title for term in ("本次汇报", "为何做", "如何做", "有何价值")):
            title = "项目大纲"
        visible_block: list[str] = [f"# {title}"]
        if core:
            core_line = _clean_visible_value(core, max_chars=180)
            if core_line and core_line not in visible:
                visible_block.append(f"**{core_line}**")
        if visible:
            visible_block.append(visible)
        else:
            visible_block.extend(_clean_existing_visible_prefix(visible_prefix)[:8])
        body_parts = ["\n\n".join(item for item in visible_block if item).strip()]
        if private_tail:
            body_parts.append("\n".join(private_tail).strip())
        normalized_pages.append("\n".join([*meta, "\n\n".join(body_parts).strip()]).strip())
    return "\n\n---\n\n".join(normalized_pages)


def _truncate_for_prompt(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[内容已截断，仅保留前部要点供本轮生成使用]"


def _image2_chunk_size(enabled: bool) -> int:
    return ROADSHOW_IMAGE2_CHUNK_SIZE if enabled else ROADSHOW_CHUNK_SIZE


def _normalize_roadshow_chunk_output(
    text: str,
    *,
    paper: ParsedPaper,
    locked_facts: object,
) -> str:
    chunk_manuscript = _normalize_roadshow_field_labels(text)
    chunk_manuscript = _normalize_inline_contract_blocks(chunk_manuscript)
    chunk_manuscript = _normalize_roadshow_pattern_ids(chunk_manuscript)
    chunk_manuscript = _normalize_roadshow_page_boundaries(chunk_manuscript)
    chunk_manuscript = _ensure_formal_page_content(chunk_manuscript)
    chunk_manuscript = _sanitize_roadshow_speaker_notes(chunk_manuscript)
    chunk_manuscript = remove_disallowed_figure_tokens(chunk_manuscript, paper)
    return apply_locked_facts_to_manuscript(chunk_manuscript, locked_facts)


def _image2_light_outline_contract(effective_num_pages: int) -> str:
    return (
        "## Image2 Lightweight Outline Contract\n\n"
        "当前为 image2 完整页面生成模式。这里只生成 banana-slides 风格的干净页纲，不生成完整 manuscript，不做现场执行重型策划。\n"
        f"输出 exactly {effective_num_pages} 行 Markdown 表格，列固定为："
        "page | section | page_type | title | core_message | visible_points | visual_scene | asset_refs | speaker_goal。\n"
        "- 第 1 页 page_type=cover，第 2 页 page_type=content 且作为项目大纲，最后 1 页 page_type=ending，其余为 content 或 chapter。\n"
        "- 第 1 页封面 asset_refs 写“无”，但 visual_scene 必须描述完整封面画面；不要写“不配图”“空白背景”或“只放文字”。\n"
        "- title 是正式页标题；core_message 是本页一句话结论；visible_points 是可直接放上 PPT 的 2-4 条短要点，不能写占位句。\n"
        "- visual_scene 描述完整页面画面和主视觉，不写 SVG 组件、布局字段名或可编辑元素。\n"
        "- asset_refs 只列 0-3 项，使用上传素材时必须写 `[[ASSET:asset_id]]`，没有素材写“无”。\n"
        "- 不输出 asset_status、export_gate、fallback_visual、layout_hint、primary_visual、operator_action 等内部字段。\n"
        "- 不输出解释、清单外字段或完整讲稿。"
    )


def _compact_user_requirement_for_image2(instruction: str, max_chars: int = 1400) -> str:
    """Remove repeated questionnaire/user note blocks before image2 outline planning."""
    text = re.sub(r"\r\n?", "\n", instruction or "").strip()
    if not text:
        return "无额外要求"
    lines: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        normalized = re.sub(r"^[\-*]\s*", "", line)
        if normalized in {"用户补充说明：", "用户问卷信息："}:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        lines.append(line)
    compact = "\n".join(lines)
    # The same long paragraph can be repeated with small prefix changes. Deduplicate by sentence.
    pieces = [item.strip() for item in re.split(r"(?<=[。；;])", compact) if item.strip()]
    deduped: list[str] = []
    sentence_seen: set[str] = set()
    for item in pieces:
        key = re.sub(r"\s+", "", item)
        if len(key) > 18 and key in sentence_seen:
            continue
        sentence_seen.add(key)
        deduped.append(item)
    compact = "".join(deduped) if deduped else compact
    return _truncate_for_prompt(compact, max_chars)


def _asset_keywords_for_image2(asset_type: str, caption: str) -> str:
    text = f"{asset_type} {caption}"
    if asset_type == "policy_source":
        return "政策背景、行业趋势、立项依据、公开来源"
    if asset_type == "system_screenshot":
        return "系统方案、功能界面、数据看板、平台能力"
    if asset_type == "device_or_scene":
        return "现场实操、硬件部署、设备集成、温室场景"
    if asset_type == "data_chart":
        return "测试成果、运行数据、效率提升、应用成效"
    if asset_type == "video_frame":
        return "流程演示、异常预警、联动处置、归档复核"
    if asset_type == "formal_document_image":
        return "成果材料、应用反馈、合作证明、知识产权"
    if any(term in text for term in ("政策", "公开", "官网")):
        return "政策背景、行业趋势"
    if any(term in text for term in ("大屏", "驾驶舱", "界面", "系统")):
        return "系统方案、功能展示"
    if any(term in text for term in ("设备", "节点", "控制箱", "温室")):
        return "现场实操、硬件部署"
    if any(term in text for term in ("图表", "数据", "趋势", "效率")):
        return "测试成果、运行数据"
    return "项目支撑材料"


def _image2_asset_token_inventory_block(project_dir: Path | None, paper: ParsedPaper) -> str:
    """Return image2-specific ASSET inventory, not legacy FIG tokens."""
    registry = load_asset_registry(project_dir) if project_dir is not None else {}
    rows: list[str] = []
    if registry:
        for asset_id, asset in sorted(registry.items()):
            filename = str(asset.get("filename") or asset.get("path") or "")
            suffix = Path(filename).suffix.lower()
            if suffix and suffix not in IMAGE_ASSET_EXTENSIONS:
                continue
            caption = str(asset.get("caption") or asset.get("filename") or asset_id).replace("\n", " ").strip()
            asset_type = str(asset.get("asset_type") or "material_image").strip()
            keywords = _asset_keywords_for_image2(asset_type, caption)
            rows.append(f"| `[[ASSET:{asset_id}]]` | {asset_type} | {caption} | {keywords} |")
    if not rows:
        for fig in paper.all_figures():
            if not getattr(fig, "available", False):
                continue
            asset_id = str(getattr(fig, "fig_id", "") or "").strip()
            if not asset_id:
                continue
            caption = (fig.caption or "项目素材图片").replace("\n", " ").strip()
            keywords = _asset_keywords_for_image2("material_image", caption)
            rows.append(f"| `[[ASSET:{asset_id}]]` | material_image | {caption} | {keywords} |")
    lines = [
        "## Image2 ASSET Inventory",
        "",
        "Only use tokens from this table in `asset_refs`. Use ASSET tokens from the table; never use legacy figure tokens in image2 outline rows.",
        "Bind real assets whenever they directly support the page. If a page needs no uploaded material, write `无`.",
        "",
    ]
    if not rows:
        lines.append("No usable uploaded image assets are available; write `无` in asset_refs and make visual_scene explicit.")
        return "\n".join(lines)
    lines.extend(["| Token | Type | Caption | Best-fit pages |", "| ----- | ---- | ------- | -------------- |"])
    lines.extend(rows[:36])
    return "\n".join(lines)


def _image2_asset_tokens_from_inventory(asset_inventory: str) -> set[str]:
    return set(re.findall(r"\[\[ASSET:([A-Za-z0-9_.:-]+)\]\]", asset_inventory or ""))


def _asset_ref_count(cards: list) -> int:
    return sum(1 for card in cards if any("[[ASSET:" in str(item) for item in getattr(card, "required_assets", []) or []))


def _image2_outline_segments(effective_num_pages: int) -> list[dict[str, object]]:
    specs = [
        ("开场定位", "cover and agenda", 1, 2, 0, "封面和目录，封面不绑定上传素材，目录可不绑定素材。"),
        ("项目背景", "policy, pain points, users", 3, 8, 2, "优先绑定 policy_source；政策、痛点、市场/用户页不能空泛。"),
        ("系统方案", "architecture, modules, UI", 9, 15, 3, "优先绑定 system_screenshot；每页说明系统如何运行。"),
        ("现场实操", "deployment, demo flow, device actions", 16, 24, 4, "优先绑定 device_or_scene、video_frame、system_screenshot；突出可演示闭环。"),
        ("测试成果", "data, metrics, support materials", 25, 31, 3, "优先绑定 data_chart、video_frame；数据页必须写清运行记录或测试结果。"),
        ("创新价值", "innovation and value", 32, 38, 1, "可绑定 data_chart 或 formal_document_image；避免价值口号化。"),
        ("团队规划", "team, roadmap, closing", 39, effective_num_pages, 1, "团队、风险、后续规划和总结；最后一页 ending。"),
    ]
    segments: list[dict[str, object]] = []
    for label, focus, start, end, min_assets, guidance in specs:
        if start > effective_num_pages:
            continue
        end = min(end, effective_num_pages)
        if start > end:
            continue
        segments.append(
            {
                "label": label,
                "focus": focus,
                "start": start,
                "end": end,
                "min_assets": min_assets,
                "guidance": guidance,
            }
        )
    return segments


def _image2_segment_contract(segment: dict[str, object], effective_num_pages: int) -> str:
    start = int(segment["start"])
    end = int(segment["end"])
    count = end - start + 1
    min_assets = int(segment.get("min_assets") or 0)
    return (
        "## Segment Output Contract\n\n"
        f"只输出第 {start}-{end} 页，共 {count} 行 Markdown 表格数据。"
        "必须包含表头和分隔行，列固定为：page | section | page_type | title | core_message | visible_points | visual_scene | asset_refs | speaker_goal。\n"
        f"- page 必须从 {start} 到 {end} 连续，不能少页、重页或改页码。\n"
        f"- 本段主题：{segment.get('label')}；重点：{segment.get('focus')}。\n"
        f"- 本段素材绑定要求：至少 {min_assets} 页使用 `[[ASSET:...]]`，除非素材表完全没有对应素材。\n"
        f"- 选材说明：{segment.get('guidance')}。\n"
        "- 第 1 页若在本段内，page_type 必须是 cover 且 asset_refs=无。\n"
        f"- 第 {effective_num_pages} 页若在本段内，page_type 必须是 ending。\n"
        "- asset_refs 只能写 `[[ASSET:asset_id]]` 或“无”，禁止 legacy figure token、中文文件名、路径和解释。\n"
        "- visible_points 写 2-4 条可见短要点；visual_scene 要描述主视觉和布局画面，不能写内部字段名。\n"
        "- 不输出表格外解释。"
    )


def _set_segment_card_pages(cards: list, start: int) -> list:
    for offset, card in enumerate(cards):
        card.page = start + offset
    return cards


def _validate_image2_segment_cards(
    cards: list,
    *,
    start: int,
    end: int,
    min_assets: int,
    asset_tokens: set[str],
) -> list[str]:
    errors = validate_cards_for_formal_render(cards, expected_pages=end - start + 1)
    expected_pages = list(range(start, end + 1))
    actual_pages = [getattr(card, "page", 0) for card in cards]
    if actual_pages != expected_pages:
        errors.append(f"页码不连续：expected {expected_pages}, got {actual_pages}")
    joined_assets = "\n".join("；".join(getattr(card, "required_assets", []) or []) for card in cards)
    if "[[FIG:" in joined_assets:
        errors.append("asset_refs 使用了 FIG token，image2 页纲只能使用 ASSET token")
    for token in re.findall(r"\[\[ASSET:([A-Za-z0-9_.:-]+)\]\]", joined_assets):
        if asset_tokens and token not in asset_tokens:
            errors.append(f"asset_refs 使用了素材表之外的 ASSET token：{token}")
    if asset_tokens and min_assets > 0 and _asset_ref_count(cards) < min_assets:
        errors.append(f"真实素材绑定不足：expected at least {min_assets}, got {_asset_ref_count(cards)}")
    return errors


def _render_image2_outline_table(cards: list) -> str:
    rows = ["| page | section | page_type | title | core_message | visible_points | visual_scene | asset_refs | speaker_goal |"]
    rows.append("|---|---|---|---|---|---|---|---|---|")
    for card in sorted(cards, key=lambda item: getattr(item, "page", 0)):
        visual_scene = str((getattr(card, "main_visual", {}) or {}).get("visual_scene") or "")
        rows.append(
            "| "
            + " | ".join(
                _table_cell(value)
                for value in (
                    str(getattr(card, "page", "")),
                    getattr(card, "section", ""),
                    getattr(card, "page_type", ""),
                    getattr(card, "formal_title", ""),
                    getattr(card, "core_sentence", ""),
                    getattr(card, "visible_content", ""),
                    visual_scene,
                    "；".join(getattr(card, "required_assets", []) or []) or "无",
                    getattr(card, "speaker_goal", ""),
                )
            )
            + " |"
        )
    return "\n".join(rows)


def _table_cell(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("|", "，")).strip()


def _project_title_from_locked_facts(locked_facts: dict | list | None, fallback: str = "项目") -> str:
    if isinstance(locked_facts, dict):
        for key in ("project_title", "project_name", "title", "name"):
            value = str(locked_facts.get(key) or "").strip()
            if value:
                return value
    return fallback


def _build_deterministic_image2_outline(
    *,
    effective_num_pages: int,
    locked_facts: dict | list | None,
) -> str:
    project_title = _project_title_from_locked_facts(locked_facts, "智慧农业物联网解决方案")
    section_specs = [
        ("开场定位", "cover", f"{project_title}", "用一句话明确项目定位和应用场景", "项目名称；一句定位；智慧农业、数据驱动、温室调控关键词", "科技农业封面，温室、传感器、数据大屏、光效和项目标题形成完整视觉"),
        ("开场定位", "content", "汇报目录", "先建立评委理解路径", "项目背景；总体方案；现场验证；成果价值；团队与推广", "五段式路演路径图，节点之间用数据流和农业场景连接"),
        ("项目背景", "content", "行业趋势与政策机遇", "智慧农业正在从经验管理走向数据化协同", "政策导向；设施农业升级；数字化管理需求", "政策文件、温室场景和趋势箭头组成背景地图"),
        ("项目背景", "content", "传统温室管理痛点", "传统管理依赖人工经验，异常发现和处置不够及时", "人工巡检滞后；环境波动难追踪；调控记录不完整", "温室巡检、告警延迟和数据断点组成问题地图"),
        ("项目背景", "content", "目标用户与使用场景", "项目面向温室种植、教学实训和农业运维场景", "种植管理；学校实训；运维巡检；成果展示", "用户画像和温室/课堂/运维三场景拼接"),
        ("方案总览", "content", "项目定位与核心价值", "系统以实时感知、智能预警和联动调控提升管理效率", "实时采集；阈值预警；远程调控；记录留痕", "中心平台连接传感器、控制箱、移动端和大屏的方案总览"),
        ("方案总览", "content", "总体架构", "系统由感知层、网络层、平台层和应用层协同运行", "环境传感；数据传输；智能分析；应用展示", "四层架构图叠加温室真实场景和数据流线"),
        ("方案总览", "content", "业务闭环", "从采集到处置再到复盘形成完整管理闭环", "数据采集；异常判断；控制执行；结果复核", "闭环流程环形图，突出输入、判断、动作、反馈"),
        ("核心技术", "content", "传感节点设计", "多类传感节点持续采集温室关键环境数据", "温度；湿度；光照；土壤墒情；设备状态", "传感器分布在温室中的点位图和参数面板"),
        ("核心技术", "content", "数据采集与传输", "系统把现场数据稳定送入平台形成实时状态", "采集频率；通信链路；异常过滤；数据入库", "传感器到网关再到云平台的数据流图"),
        ("核心技术", "content", "智能预警规则", "平台根据阈值和趋势变化识别异常风险", "阈值判断；趋势分析；等级提醒；处置建议", "告警规则树和实时曲线仪表盘组合"),
        ("核心技术", "content", "联动调控机制", "系统将预警结果转化为可执行的设备控制动作", "风机；水泵；补光；喷淋；控制反馈", "控制箱、设备联动箭头和状态回传面板"),
        ("核心技术", "content", "平台界面与数据看板", "管理端把复杂环境数据转化为可读的运行视图", "实时曲线；设备状态；告警列表；历史记录", "大屏仪表盘、趋势图和设备状态卡片"),
        ("核心技术", "content", "移动端巡检协同", "移动端让现场人员及时查看状态并完成处置记录", "远程查看；异常确认；巡检拍照；处理备注", "手机界面、温室巡检路线和记录卡片"),
        ("现场验证", "content", "现场验证流程", "通过一次温室异常事件验证系统闭环能力", "输入数据；风险识别；设备联动；结果记录", "现场事件流程图，突出从异常出现到复盘完成"),
        ("现场验证", "content", "设备部署与点位规划", "传感节点和控制设备按温室区域完成部署", "点位分布；设备编号；覆盖范围；维护入口", "温室平面图、点位标记和设备照片式插图"),
        ("现场验证", "content", "控制箱接线与设备集成", "控制箱把平台指令可靠转化为现场设备动作", "接线规范；继电器控制；安全保护；状态反馈", "控制箱特写、接线示意、设备联动和安全标识"),
        ("现场验证", "content", "进入监测大屏", "评委可以通过大屏直接看到当前温室运行状态", "实时温湿度；光照变化；设备状态；告警提示", "监测大屏主界面占据视觉中心，旁边叠加温室现场"),
        ("现场验证", "content", "异常识别演示", "系统在环境数据越界时自动提示风险等级", "异常触发；规则命中；等级标识；处理建议", "告警弹窗、红黄绿状态和趋势曲线变化"),
        ("现场验证", "content", "远程调控演示", "操作端下发控制指令后，现场设备状态同步更新", "选择设备；下发指令；设备响应；状态回传", "操作端界面、设备响应动画感和状态更新面板"),
        ("现场验证", "content", "处置记录留痕", "每次异常处理都会形成可追溯的运行记录", "处理时间；处理人；设备动作；复核结果", "日志列表、时间轴和复核勾选形成记录页"),
        ("现场验证", "content", "故障恢复与备用方案", "现场波动时系统保留人工接管和复测路径", "网络异常；手动控制；预置方案；复测确认", "故障切换流程、备用面板和复测结果卡片"),
        ("测试成果", "content", "测试环境与测试方法", "项目通过多场景测试验证稳定性和可用性", "模拟异常；连续运行；多设备联动；人工复核", "测试台、温室场景和测试方法矩阵"),
        ("测试成果", "content", "运行数据复核", "系统用运行记录说明识别、响应和留痕能力", "响应时间；告警准确性；设备联动；记录完整性", "结果仪表盘、折线图和指标卡片"),
        ("测试成果", "content", "效率提升表现", "数据化管理减少人工巡检压力并提升响应速度", "巡检效率；响应速度；管理视野；决策依据", "效率对比图和人工/系统两种模式对照"),
        ("测试成果", "content", "成果材料展示", "项目形成了系统平台、设备集成和应用材料", "系统界面；设备样机；测试记录；项目文档", "成果墙式布局，放置平台、设备、记录和文档缩略图"),
        ("创新亮点", "content", "创新点一：感知与控制闭环", "项目把环境感知和设备调控连接成可验证闭环", "实时数据；规则判断；联动控制；效果复核", "闭环机制图，强调从数据到动作再到结果"),
        ("创新亮点", "content", "创新点二：低成本可复制部署", "方案适合教学实训和中小型温室快速落地", "通用传感器；模块化控制；低门槛运维；可扩展", "模块化设备、成本标签和复制部署路径"),
        ("创新亮点", "content", "创新点三：教学与生产融合", "项目兼顾真实生产管理和职业技能训练", "岗位任务；实训流程；数据分析；团队协作", "课堂、温室和岗位任务三端融合图"),
        ("应用价值", "content", "企业应用价值", "系统帮助管理方降低巡检压力并提升环境管理精度", "管理效率；风险预警；用工优化；过程留痕", "企业温室运营看板和价值指标组合"),
        ("应用价值", "content", "学校育人价值", "项目把物联网、农业和数据分析转化为真实学习任务", "课程融合；项目实训；竞赛训练；岗位能力", "学生实训、任务卡和能力成长路径"),
        ("应用价值", "content", "行业推广路径", "方案可扩展到不同作物和不同规模的设施农业场景", "标准化部署；场景复制；运维培训；区域推广", "地图扩散、作物图标和部署流程"),
        ("团队能力", "content", "团队分工与协作", "团队围绕硬件、软件、测试和汇报形成协作闭环", "硬件集成；平台开发；测试验证；展示汇报", "团队角色矩阵和任务流转图"),
        ("团队能力", "content", "研发迭代过程", "项目经过需求调研、原型搭建、测试优化和展示打磨", "需求调研；样机搭建；联调测试；版本优化", "研发时间轴和版本迭代节点"),
        ("团队能力", "content", "风险控制与安全规范", "项目在设备接线、数据使用和现场操作中强调规范安全", "用电安全；设备保护；数据留痕；操作规范", "安全规范清单、设备保护和现场操作图"),
        ("价值收束", "content", "商业与社会价值", "项目以数据驱动助力农业生产提质增效", "节水节能；降本增效；绿色生产；智慧管理", "农业价值矩阵和绿色发展视觉"),
        ("价值收束", "content", "知识产权与成果沉淀", "项目持续沉淀软件、硬件和文档化成果", "平台代码；硬件方案；测试报告；推广材料", "成果沉淀金字塔和资料归档视觉"),
        ("价值收束", "content", "后续规划", "后续将继续提升模型能力、设备兼容和规模化部署", "算法优化；多棚联动；移动协同；推广试点", "路线图、未来版本和试点场景"),
        ("总结答辩", "ending", "总结与答辩", "项目用可运行系统证明智慧农业管理可以更及时、更准确、更可追溯", "实时感知；智能预警；联动控制；应用推广", "收束式总结页，项目关键词、温室背景和答辩致谢"),
    ]
    if effective_num_pages <= len(section_specs):
        selected = section_specs[: max(1, effective_num_pages - 1)] + [section_specs[-1]]
    else:
        selected = list(section_specs)
        for index in range(len(section_specs) + 1, effective_num_pages + 1):
            selected.insert(
                -1,
                (
                    "专题补充",
                    "content",
                    f"专题补充 {index - len(section_specs)}",
                    "围绕项目关键能力补充一页正式说明",
                    "应用场景；系统能力；运行记录；价值说明",
                    "智慧农业场景、数据看板和能力标签组合成专题说明页",
                ),
            )
    rows = ["| page | section | page_type | title | core_message | visible_points | visual_scene | asset_refs | speaker_goal |"]
    rows.append("|---|---|---|---|---|---|---|---|---|")
    for page, (section, page_type, title, core, visible, visual_scene) in enumerate(selected[:effective_num_pages], start=1):
        if page == 1:
            page_type = "cover"
            title = project_title
        elif page == effective_num_pages:
            page_type = "ending"
        rows.append(
            "| "
            + " | ".join(
                _table_cell(value)
                for value in (
                    str(page),
                    section,
                    page_type,
                    title,
                    core,
                    visible,
                    visual_scene,
                    "无",
                    f"让评委理解{core}",
                )
            )
            + " |"
        )
    return "\n".join(rows)


async def _generate_valid_image2_outline(
    *,
    llm: LLMProvider,
    model: str,
    base_messages: list[LLMMessage],
    effective_num_pages: int,
    locked_facts: dict | list | None,
    debug_dir: Path | None,
    on_progress: Callable[[str, float], None] | None,
) -> str:
    context_messages = list(base_messages)
    context_text = "\n\n".join(
        str(message.content)
        for message in context_messages
        if message.role == "user" and isinstance(message.content, str)
    )
    asset_tokens = _image2_asset_tokens_from_inventory(context_text)
    segments = _image2_outline_segments(effective_num_pages)
    all_cards: list = []
    all_errors: list[str] = []

    for segment_index, segment in enumerate(segments, start=1):
        start = int(segment["start"])
        end = int(segment["end"])
        min_assets = int(segment.get("min_assets") or 0)
        segment_errors: list[str] = []
        segment_cards: list | None = None
        segment_progress_start = 0.181 + (segment_index - 1) * (0.024 / max(1, len(segments)))
        segment_progress_end = 0.181 + segment_index * (0.024 / max(1, len(segments)))

        for attempt in range(1, ROADSHOW_IMAGE2_OUTLINE_RETRY_ATTEMPTS + 1):
            if on_progress:
                repair_label = "定向修复" if attempt > 1 else "生成"
                on_progress(
                    f"正在{repair_label} image2 页纲：{segment.get('label')}（第 {start}-{end} 页）",
                    min(0.205, segment_progress_start),
                )
            segment_prompt = (
                f"{context_text}\n\n"
                f"{_image2_segment_contract(segment, effective_num_pages)}"
            )
            if attempt > 1:
                segment_prompt += (
                    "\n\n## Previous Segment Errors\n\n"
                    "上一轮只修复本段，不要改其他页。必须重新输出本段完整表格。\n"
                    "- " + "\n- ".join(segment_errors[:12])
                )
            messages = [
                LLMMessage.system(IMAGE2_CLEAN_OUTLINE_SYSTEM_PROMPT),
                LLMMessage.user(segment_prompt),
            ]
            if debug_dir is not None:
                _debug_write_messages(
                    debug_dir,
                    f"roadshow_pass2_image2_segment_{start:02d}_{end:02d}_attempt{attempt}_prompt.md",
                    messages,
                )
            try:
                response = await _await_llm_with_safe_progress(
                    lambda messages=messages, attempt=attempt: llm.chat(
                        messages,
                        model,
                        temperature=0.18 if attempt > 1 else 0.24,
                        max_tokens=max(2400, min(5200, (end - start + 1) * 650)),
                    ),
                    on_progress=on_progress,
                    messages=(
                        f"正在生成 {segment.get('label')} 页纲",
                        f"正在绑定 {segment.get('label')} 相关素材",
                        f"正在校验第 {start}-{end} 页主线",
                    ),
                    start_fraction=segment_progress_start,
                    end_fraction=segment_progress_end,
                    stall_retry_seconds=ROADSHOW_IMAGE2_OUTLINE_SEGMENT_STALL_SECONDS,
                    retry_message=f"{segment.get('label')} 页纲连接波动，准备定向修复",
                    max_attempts=1,
                )
            except Exception as exc:
                segment_errors = [f"第 {start}-{end} 页 LLM 连接或超时失败：{exc}"]
                logger.warning("Image2 outline segment %s-%s attempt %s failed: %s", start, end, attempt, exc)
                continue

            outline = (response.content or "").strip()
            if debug_dir is not None:
                _debug_write_text(
                    debug_dir,
                    f"roadshow_pass2_image2_segment_{start:02d}_{end:02d}_attempt{attempt}.md",
                    outline,
                )
            cards = _set_segment_card_pages(parse_slide_content_plan(outline), start)
            segment_errors = _validate_image2_segment_cards(
                cards,
                start=start,
                end=end,
                min_assets=min_assets,
                asset_tokens=asset_tokens,
            )
            if not segment_errors:
                segment_cards = cards
                break
            logger.info("Image2 outline segment %s-%s validation failed: %s", start, end, segment_errors[:6])

        if segment_cards is None:
            all_errors.extend(segment_errors or [f"第 {start}-{end} 页页纲未生成"])
        else:
            all_cards.extend(segment_cards)

    if all_errors:
        logger.warning("Image2 segmented outline failed before fallback: %s", all_errors[:12])
    else:
        outline = _render_image2_outline_table(all_cards)
        if debug_dir is not None:
            _debug_write_text(debug_dir, "roadshow_pass2_image2_light_outline_segmented.md", outline)
        cards = parse_slide_content_plan(outline)
        final_errors = validate_cards_for_formal_render(cards, expected_pages=effective_num_pages)
        asset_ref_count = _asset_ref_count(cards)
        min_total_assets = min(len(asset_tokens), max(6, round(max(0, effective_num_pages - 3) * 0.35))) if asset_tokens else 0
        if asset_tokens and asset_ref_count < min_total_assets:
            final_errors.append(f"整套页纲真实素材绑定不足：expected at least {min_total_assets}, got {asset_ref_count}")
        if "[[FIG:" in outline:
            final_errors.append("整套页纲仍包含 FIG token，image2 只能使用 ASSET token")
        if not final_errors:
            return outline
        all_errors.extend(final_errors)

    fallback = _build_deterministic_image2_outline(
        effective_num_pages=effective_num_pages,
        locked_facts=locked_facts,
    )
    fallback_cards = parse_slide_content_plan(fallback)
    fallback_errors = validate_cards_for_formal_render(fallback_cards, expected_pages=effective_num_pages)
    if fallback_errors:
        raise ValueError("image2 轻量页纲主链路失败：" + "；".join((all_errors + fallback_errors)[:16]))
    if debug_dir is not None:
        _debug_write_text(
            debug_dir,
            "roadshow_pass2_image2_light_outline_emergency_fallback.md",
            fallback,
        )
        _debug_write_text(
            debug_dir,
            "roadshow_pass2_image2_light_outline_main_path_errors.txt",
            "\n".join(all_errors[:40]),
        )
    if on_progress:
        on_progress("image2 页纲主链路失败，已启用最后异常保护", 0.205)
    return fallback


def _image2_manuscript_chunk_contract(
    *,
    start_page: int,
    end_page: int,
    effective_num_pages: int,
    expected_chunk_pages: int,
) -> str:
    return (
        "## Image2 Chunk Contract\n\n"
        f"只生成第 {start_page}-{end_page} 页，共 {expected_chunk_pages} 页。"
        f"完整 PPT 总页数为 {effective_num_pages} 页，本轮只是一个 5 页以内的连续页段。\n"
        "- 输出必须只有本页段 manuscript，不要输出本页段以外页面，不要解释。\n"
        "- 每页仍用独立一行 `---` 分隔；页面内部禁止使用 `---`。\n"
        "- 每页顶部必须有 `<!-- page_type: cover|chapter|content|ending -->`。\n"
        "- image2 会负责完整页面画面、文字和版式；不要规划 SVG 兜底，不要写“用 SVG 绘制”。\n"
        "- 可见正文要短、准、适合直接放入图片生成页面：标题、核心句、3-5 条短要点即可。\n"
        "- 每页必须包含 page_core_sentence、visible_content、main_visual、visual_asset_plan、required_assets、asset_status、fallback_visual、asset_gap_handling、export_gate、speaker_notes、main_script、sub_script、transition。\n"
        "- 每页必须包含 page_role、judge_focus、visual_strategy、layout_hint、evidence_assets、speaker_goal、primary_visual、stage_mode、display_target、time_budget_sec、speaker_role、operator_role、operator_action、expected_screen_state、fallback_plan、module_flow、acceptance_signal、command_cue。\n"
        "- main_visual.type 优先使用 generated_image；有真实上传素材时可用 real_image、screenshot、product_ui、chart、certificate、material_photo 并引用 `[[ASSET:asset_id]]`。\n"
        "- primary_visual 必须用多行块，包含 type、purpose、required_elements、visual_weight、forbidden_layouts。\n"
        "- speaker_notes 是正式讲稿，控制在 220-420 个中文字符，保留承接、主体说明和自然转场，避免页面设计术语。\n"
        "- 第 1 页封面不绑定上传图片素材；最后一页才允许 ending。"
    )


def _light_plan_rows_for_range(slide_content_plan: str, start_page: int, end_page: int) -> str:
    """Keep only table rows for the current chunk from the lightweight plan."""
    rows: list[str] = []
    header: str | None = None
    separator: str | None = None
    for raw_line in slide_content_plan.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first.lower() == "page":
            header = line
            continue
        if set(first) <= {"-", ":"}:
            separator = line
            continue
        if not first.isdigit():
            continue
        page_num = int(first)
        if start_page <= page_num <= end_page:
            rows.append(line)
    if not rows:
        return _truncate_for_prompt(slide_content_plan, 6000)
    output: list[str] = []
    if header:
        output.append(header)
    if separator:
        output.append(separator)
    output.extend(rows)
    return "\n".join(output)


def _merge_markdown_plan_tables(segments: list[str]) -> str:
    """Merge segmented Markdown tables into one table ordered by page number."""
    header: str | None = None
    separator: str | None = None
    rows_by_page: dict[int, str] = {}
    for segment in segments:
        for raw_line in (segment or "").splitlines():
            line = raw_line.strip()
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells:
                continue
            first = cells[0]
            if first.lower() == "page":
                if header is None:
                    header = line
                continue
            if set(first) <= {"-", ":"}:
                if separator is None:
                    separator = line
                continue
            if not first.isdigit():
                continue
            page_num = int(first)
            # Prefer first successful segment for a page (stable, no overwrite races).
            rows_by_page.setdefault(page_num, line)
    if not rows_by_page:
        return "\n\n".join(seg.strip() for seg in segments if (seg or "").strip())
    if header is None:
        header = (
            "| page | page_type | section | formal_title | page_core_sentence | "
            "visible_content | main_visual_type | required_assets | asset_status | "
            "fallback_visual | export_gate |"
        )
    if separator is None:
        separator = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    ordered = [rows_by_page[page] for page in sorted(rows_by_page)]
    return "\n".join([header, separator, *ordered])


def _roadshow_parallel_segments() -> int:
    try:
        value = int(getattr(settings, "roadshow_parallel_segments", ROADSHOW_PARALLEL_SEGMENTS) or 0)
    except (TypeError, ValueError):
        value = ROADSHOW_PARALLEL_SEGMENTS
    return max(1, min(6, value))


async def _generate_light_slide_plan_parallel(
    *,
    llm: LLMProvider,
    model: str,
    effective_num_pages: int,
    material_analysis: str,
    locked_facts_block: str,
    evidence_block: str,
    pattern_block: str,
    outline_plan: str,
    contestant_plan: str,
    source_profile: dict,
    language: str,
    page_contract: str,
    figure_inventory: str | None,
    debug_dir: Path | None,
    on_progress: Callable[[str, float], None] | None,
) -> str:
    """Generate light SlideContentPlan table by parallel page segments.

    Keeps full 35-45 page targets; each segment is a short table call so one
    silent stall cannot block the entire deck.
    """
    ranges = _slide_ranges(effective_num_pages, ROADSHOW_LIGHT_PLAN_SEGMENT_SIZE)
    if len(ranges) <= 1:
        # Tiny decks: single call is fine.
        ranges = [(1, effective_num_pages)]
    concurrency = min(_roadshow_parallel_segments(), len(ranges))
    sem = asyncio.Semaphore(concurrency)
    done_count = 0
    progress_lock = asyncio.Lock()
    shared_context = [
        f"## Material Analysis\n\n{_truncate_for_prompt(material_analysis, 2800)}",
        f"\n## Locked Facts\n\n{locked_facts_block}",
        f"\n## Support Material Summary\n\n{_truncate_for_prompt(evidence_block, 2400)}",
        f"\n## Competition Outline (compact)\n\n{_truncate_for_prompt(outline_plan, 4500)}",
        f"\n## Contestant / execution notes\n\n{_truncate_for_prompt(contestant_plan, 2000)}",
        f"\n{source_profile_prompt_block(source_profile)}",
        f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
        f"\n## Full Deck Contract\n\n{page_contract}",
        f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
        f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
        f"\n{ROADSHOW_STORYLINE_RULE}",
        f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
        f"\n{pattern_block}" if pattern_block else "",
    ]
    if figure_inventory:
        shared_context.append(f"\n## Asset Inventory\n\n{_truncate_for_prompt(figure_inventory, 3200)}")

    async def _one_segment(start_page: int, end_page: int) -> tuple[int, int, str]:
        nonlocal done_count
        expected = end_page - start_page + 1
        segment_parts = [
            *shared_context,
            "\n## Segment Contract\n\n"
            f"只输出第 {start_page}-{end_page} 页，共 {expected} 行 Markdown 表格。"
            f"完整 PPT 为 {effective_num_pages} 页，本段只是连续页段之一。\n"
            "- 只输出表格，不要解释、不要其他页。\n"
            "- page 列必须使用全局页码（不是从 1 重编号）。\n"
            f"- 若本段包含第 1 页：page_type=cover，required_assets 写“无”，asset_status=not_required。\n"
            f"- 若本段包含第 2 页：正式目录，标题用“目录”或“项目大纲”。\n"
            f"- 若本段包含第 {effective_num_pages} 页：page_type=ending。\n"
            "- 本段内不得出现重复 formal_title / page_core_sentence。\n"
            "- visible_content ≤ 80 中文字符；required_assets ≤ 3 项。\n",
        ]
        messages = [
            LLMMessage.system(LIGHT_SLIDE_CONTENT_PLAN_SYSTEM_PROMPT),
            LLMMessage.user("\n".join(part for part in segment_parts if part)),
        ]
        async with sem:
            _debug_write_messages(
                debug_dir,
                f"roadshow_pass5_light_plan_segment_{start_page:02d}_{end_page:02d}_prompt.md",
                messages,
            )
            response = await _await_llm_with_safe_progress(
                lambda: llm.chat(
                    messages,
                    model,
                    temperature=0.25,
                    max_tokens=min(ROADSHOW_LIGHT_PLAN_MAX_TOKENS, 6000),
                ),
                on_progress=None,
                messages=(
                    f"正在生成第 {start_page}-{end_page} 页内容卡表",
                    f"正在压缩第 {start_page}-{end_page} 页可见文案",
                ),
                start_fraction=0.245,
                end_fraction=0.28,
                stall_retry_seconds=max(90, _roadshow_research_stall_retry_seconds()),
                max_attempts=2,
                retry_message=f"第 {start_page}-{end_page} 页内容卡表连接波动，正在重试",
            )
            content = response.content
            _debug_write_text(
                debug_dir,
                f"roadshow_pass5_light_plan_segment_{start_page:02d}_{end_page:02d}_response.md",
                content,
            )
        async with progress_lock:
            done_count += 1
            if on_progress:
                fraction = 0.245 + (done_count / max(1, len(ranges))) * 0.04
                on_progress(
                    f"页面内容卡片分段并行 {done_count}/{len(ranges)} 完成（第 {start_page}-{end_page} 页）",
                    min(0.29, fraction),
                )
        return start_page, end_page, content

    if on_progress:
        on_progress(
            f"正在分段并行生成页面内容卡片（{len(ranges)} 段 · 并发 {concurrency} · 共 {effective_num_pages} 页）",
            0.245,
        )
    gathered = await asyncio.gather(
        *[_one_segment(start, end) for start, end in ranges],
        return_exceptions=True,
    )
    successes: list[tuple[int, int, str]] = []
    errors: list[str] = []
    for item, (start, end) in zip(gathered, ranges):
        if isinstance(item, Exception):
            errors.append(f"{start}-{end}: {item}")
            logger.warning("Light plan segment %s-%s failed: %s", start, end, item)
            continue
        successes.append(item)
    if not successes:
        raise RuntimeError(
            "页面内容卡片全部分段失败：" + "；".join(errors[:6])
        )
    successes.sort(key=lambda item: item[0])
    merged = _merge_markdown_plan_tables([content for _, _, content in successes])
    if errors:
        logger.warning(
            "Light plan parallel completed with partial segment failures: %s",
            errors[:8],
        )
        _debug_write_text(
            debug_dir,
            "roadshow_pass5_light_plan_segment_errors.txt",
            "\n".join(errors),
        )
    return merged


def _parse_inline_kv(rest: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for part in re.split(r"\s*;\s*", rest.strip()):
        if not part:
            continue
        match = re.match(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*(?:=|:)\s*(?P<value>.+)", part)
        if not match:
            continue
        pairs[match.group("key").strip().lower()] = match.group("value").strip()
    return pairs


INLINE_CONTRACT_FIELDS: dict[str, tuple[str, ...]] = {
    "proof_object": ("type", "source", "must_be_visible", "fallback"),
    "main_visual": ("type", "asset_source", "asset_status", "fallback", "export_rule"),
    "primary_visual": ("type", "purpose", "required_elements", "visual_weight", "forbidden_layouts"),
    "visual_pattern": ("pattern_id", "why"),
}


def _normalize_inline_contract_blocks(manuscript: str) -> str:
    """Convert common `field: key=value; key=value` drift into block fields."""
    output_lines: list[str] = []
    pattern = re.compile(
        r"^(?P<indent>\s*)(?P<field>" + "|".join(re.escape(k) for k in INLINE_CONTRACT_FIELDS) + r")\s*:\s*(?P<rest>.+)$",
        re.IGNORECASE,
    )
    for line in manuscript.splitlines():
        match = pattern.match(line)
        if not match:
            output_lines.append(line)
            continue
        rest = match.group("rest").strip()
        if "\n" in rest or ("=" not in rest and not re.search(r"\btype\s*:", rest)):
            output_lines.append(line)
            continue
        pairs = _parse_inline_kv(rest)
        field = match.group("field").lower()
        if field == "main_visual" and "source" in pairs and "asset_source" not in pairs:
            pairs["asset_source"] = pairs["source"]
        if field == "visual_pattern" and "type" in pairs and "pattern_id" not in pairs:
            pairs["pattern_id"] = pairs["type"]
        if field == "proof_object":
            pairs.setdefault("must_be_visible", "true")
            pairs.setdefault("fallback", "use visible project fact summary if direct asset is unavailable")
        elif field == "main_visual":
            source_value = pairs.get("asset_source", pairs.get("source", "")).lower()
            if "asset_status" not in pairs:
                if any(token in source_value for token in ("upload", "provided", "user", "material", "source")):
                    pairs["asset_status"] = "provided"
                else:
                    pairs["asset_status"] = "derivable"
            pairs.setdefault("fallback", "svg_diagram")
            pairs.setdefault("export_rule", "formal_ok")
        elif field == "primary_visual":
            pairs.setdefault("purpose", "support this slide's core conclusion")
            pairs.setdefault("required_elements", "title, key evidence, visual focus")
            pairs.setdefault("visual_weight", "high")
            pairs.setdefault("forbidden_layouts", "pure card grid without primary visual")
        elif field == "visual_pattern":
            pairs.setdefault("why", "matches slide evidence and page role")
        wanted = INLINE_CONTRACT_FIELDS[field]
        if not pairs:
            output_lines.append(line)
            continue
        output_lines.append(f"{match.group('indent')}{field}:")
        for key in wanted:
            if key in pairs:
                output_lines.append(f"{match.group('indent')}  {key}: {pairs[key]}")
        for key, value in pairs.items():
            if key not in wanted:
                output_lines.append(f"{match.group('indent')}  {key}: {value}")
    return "\n".join(output_lines)


def _normalize_roadshow_pattern_ids(manuscript: str) -> str:
    """Normalize visual_pattern.pattern_id values without asking the LLM to retry."""
    lines = manuscript.splitlines()
    output: list[str] = []
    in_visual_pattern = False
    pattern_id_seen = False
    visual_pattern_indent = 0
    for line in lines:
        stripped = line.strip()
        field_match = re.match(r"^(?P<indent>\s*)(?P<field>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*)$", line)
        if field_match:
            field = field_match.group("field").lower()
            indent = len(field_match.group("indent"))
            if field == "visual_pattern":
                in_visual_pattern = True
                pattern_id_seen = False
                visual_pattern_indent = indent
                output.append(line)
                continue
            if in_visual_pattern and indent <= visual_pattern_indent:
                if not pattern_id_seen:
                    output.append(" " * (visual_pattern_indent + 2) + "pattern_id: support_material_wall")
                in_visual_pattern = False
            if in_visual_pattern and field == "pattern_id":
                normalized = normalize_pattern_id(field_match.group("value"))
                output.append(f"{field_match.group('indent')}pattern_id: {normalized}")
                pattern_id_seen = True
                continue
        if in_visual_pattern and re.match(r"^\s*pattern_id\s*[:：]", stripped, re.I):
            prefix, _, value = line.partition(":")
            normalized = normalize_pattern_id(value)
            output.append(f"{prefix}: {normalized}")
            pattern_id_seen = True
            continue
        output.append(line)
    if in_visual_pattern and not pattern_id_seen:
        output.append(" " * (visual_pattern_indent + 2) + "pattern_id: support_material_wall")
    return "\n".join(output)


def _has_primary_visual_contract(page: str) -> bool:
    lowered = page.lower()
    if "primary_visual:" not in lowered:
        return False
    primary_start = lowered.find("primary_visual:")
    tail = lowered[primary_start:]
    next_field_positions = [
        pos
        for marker in (
            "\nstage_mode:",
            "\ndisplay_target:",
            "\ntime_budget_sec:",
            "\nspeaker_role:",
            "\noperator_role:",
        )
        if (pos := tail.find(marker)) > 0
    ]
    block = tail[: min(next_field_positions)] if next_field_positions else tail
    required = ("type:", "purpose:", "required_elements:", "visual_weight:", "forbidden_layouts:")
    if any(item not in block for item in required):
        return False
    return any(kind in block for kind in PRIMARY_VISUAL_TYPES)


def _has_visual_pattern_contract(page: str) -> bool:
    lowered = page.lower()
    if "visual_pattern:" not in lowered:
        return False
    pattern_start = lowered.find("visual_pattern:")
    tail = lowered[pattern_start:]
    next_field_positions = [
        pos
        for marker in (
            "\nnext_slide_bridge:",
            "\nprimary_visual:",
            "\nstage_mode:",
            "\ndisplay_target:",
        )
        if (pos := tail.find(marker)) > 0
    ]
    block = tail[: min(next_field_positions)] if next_field_positions else tail
    match = re.search(r"pattern_id\s*[:：]\s*([^\n]+)", block, re.I)
    if match:
        normalized = normalize_pattern_id(match.group(1))
        return normalized in {item.lower() for item in allowed_pattern_ids_text().split(", ")}
    return any(pattern_id.lower() in block for pattern_id in allowed_pattern_ids_text().lower().split(", "))


def _has_proof_object_contract(page: str) -> bool:
    lowered = page.lower()
    if "proof_object:" not in lowered:
        return False
    proof_start = lowered.find("proof_object:")
    tail = lowered[proof_start:]
    next_field_positions = [
        pos
        for marker in (
            "\nvisual_pattern:",
            "\nnext_slide_bridge:",
            "\nprimary_visual:",
            "\nstage_mode:",
        )
        if (pos := tail.find(marker)) > 0
    ]
    block = tail[: min(next_field_positions)] if next_field_positions else tail
    return all(item in block for item in ("type:", "source:", "must_be_visible:", "fallback:"))


def _has_slide_content_plan_contract(page: str) -> bool:
    lowered = page.lower()
    required = (
        "page_core_sentence:",
        "visible_content:",
        "main_visual:",
        "visual_asset_plan:",
        "required_assets:",
        "asset_status:",
        "fallback_visual:",
        "asset_gap_handling:",
        "export_gate:",
        "main_script:",
        "sub_script:",
        "transition:",
    )
    if any(field not in lowered for field in required):
        return False
    visual_start = lowered.find("main_visual:")
    tail = lowered[visual_start:]
    next_field_positions = [
        pos
        for marker in (
            "\nvisual_asset_plan:",
            "\nrequired_assets:",
            "\nasset_status:",
            "\nfallback_visual:",
            "\nasset_gap_handling:",
        )
        if (pos := tail.find(marker)) > 0
    ]
    visual_block = tail[: min(next_field_positions)] if next_field_positions else tail[:700]
    if not all(item in visual_block for item in ("type:", "asset_source:", "asset_status:", "fallback:", "export_rule:")):
        return False
    allowed_visuals = (
        "real_image",
        "screenshot",
        "product_ui",
        "chart",
        "certificate",
        "material_photo",
        "generated_image",
        "svg_diagram",
        "none",
    )
    if not any(visual_type in visual_block for visual_type in allowed_visuals):
        return False
    allowed_statuses = ("provided", "derivable", "missing", "not_required", "draft_only", "blocking")
    if not any(status in lowered for status in allowed_statuses):
        return False
    allowed_gates = ("formal_ok", "draft_only", "blocked_until_assets")
    return any(gate in lowered for gate in allowed_gates)


def _is_card_heavy_without_primary_visual(page: str) -> bool:
    lowered = page.lower()
    if any(kind in lowered for kind in PRIMARY_VISUAL_TYPES):
        return False
    return sum(1 for term in CARD_HEAVY_TERMS if term.lower() in lowered) >= 1


def _visible_formal_copy(page: str) -> str:
    visible_lines: list[str] = []
    private_block_indent: int | None = None
    private_field_re = re.compile(
        r"^\s*(?P<name>" + "|".join(re.escape(name) for name in PRIVATE_FIELD_NAMES) + r")\s*:",
        re.IGNORECASE,
    )
    for raw_line in page.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("<!--"):
            continue
        match = private_field_re.match(line)
        indent = len(line) - len(line.lstrip(" "))
        if match:
            private_block_indent = indent
            continue
        if private_block_indent is not None:
            if stripped and indent > private_block_indent and not stripped.startswith("#"):
                continue
            private_block_indent = None
        visible_lines.append(stripped)
    return "\n".join(line for line in visible_lines if line).strip()


def _normalized_page_semantic_key(page: str) -> str:
    visible = _visible_formal_copy(page)
    planned = "\n".join(
        value
        for value in (
            _roadshow_field_value(page, "page_core_sentence"),
            _roadshow_field_value(page, "visible_content"),
        )
        if value
    )
    text = f"{visible}\n{planned}"
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\[\[(?:ASSET|FIG):[A-Za-z0-9_.-]+\]\]", "", text)
    text = re.sub(r"(?im)^\s*(?:page|section|formal_title|title)\s*[:：].*$", "", text)
    text = re.sub(r"\b\d{1,2}\b", "", text)
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", text).lower()
    return text


def _duplicate_visible_pages(manuscript: str) -> list[tuple[int, int]]:
    seen: dict[str, int] = {}
    duplicates: list[tuple[int, int]] = []
    for index, page in enumerate(split_manuscript_pages(manuscript), start=1):
        if index in {1, 2}:
            continue
        key = _normalized_page_semantic_key(page)
        if len(key) < 36:
            continue
        previous = seen.get(key)
        if previous is not None:
            duplicates.append((previous, index))
        else:
            seen[key] = index
    return duplicates


def _asset_token_density_issue(manuscript: str) -> str | None:
    pages = split_manuscript_pages(manuscript)
    if len(pages) < 30:
        return None
    asset_pages = [
        index
        for index, page in enumerate(pages, start=1)
        if re.search(r"\[\[ASSET:[A-Za-z0-9_.-]+\]\]", page)
    ]
    unique_assets = set(re.findall(r"\[\[ASSET:([A-Za-z0-9_.-]+)\]\]", manuscript))
    if len(unique_assets) < 12:
        return None
    min_asset_pages = max(14, round(len(pages) * 0.45))
    if len(asset_pages) < min_asset_pages:
        return (
            f"real material density is too low: {len(asset_pages)}/{len(pages)} slides use uploaded assets; "
            f"expected at least {min_asset_pages} when {len(unique_assets)} assets are available"
        )
    return None


def _visible_meta_language_pages(manuscript: str) -> list[int]:
    offenders: list[int] = []
    for index, page in enumerate(split_manuscript_pages(manuscript), start=1):
        visible = _visible_formal_copy(page)
        if any(term in visible for term in FORMAL_VISIBLE_META_TERMS):
            offenders.append(index)
    return offenders


IMPLEMENTATION_REPORT_STYLE_RE = re.compile(
    r"前端开发|后端开发|测试工程|环境监测模块|设备联动控制模块|告警工单闭环模块|数据分析模块|"
    r"模块实现了|聚焦于|确保数据流|功能模块",
)
EVENT_CHAIN_RE = re.compile(
    r"异常|触发|预警|联动|工单|处置|复盘|运行记录|输入|输出|日志|接口|确认|移动端|大屏",
)
EVENT_TRIGGER_RE = re.compile(r"异常|触发|预警|输入|监测|告警")
EVENT_ACTION_RE = re.compile(r"联动|处置|工单|确认|移动端|大屏|设备|控制")
EVENT_REVIEW_RE = re.compile(r"运行记录|日志|复盘|复测|测试|追溯|记录")


def _implementation_storyline_issue_pages(manuscript: str) -> list[int]:
    """Catch report-style implementation pages that should stay event-driven."""
    pages = split_manuscript_pages(manuscript)
    if len(pages) < 30:
        return []
    offenders: list[int] = []
    for index, page in enumerate(pages, start=1):
        if not 18 <= index <= min(24, len(pages) - 8):
            continue
        visible = _visible_formal_copy(page)
        heading_match = re.search(r"(?m)^#{1,3}\s+(.+)$", visible)
        heading = heading_match.group(1).strip() if heading_match else visible.splitlines()[0] if visible else ""
        if IMPLEMENTATION_REPORT_STYLE_RE.search(heading):
            offenders.append(index)
        elif IMPLEMENTATION_REPORT_STYLE_RE.search(visible) and not EVENT_CHAIN_RE.search(visible):
            offenders.append(index)
    return offenders


def _implementation_event_chain_missing(manuscript: str) -> list[str]:
    pages = split_manuscript_pages(manuscript)
    if len(pages) < 30:
        return []
    middle = "\n".join(pages[17 : min(24, len(pages))])
    missing: list[str] = []
    if not EVENT_TRIGGER_RE.search(middle):
        missing.append("trigger/input")
    if not EVENT_ACTION_RE.search(middle):
        missing.append("action/handling")
    if not EVENT_REVIEW_RE.search(middle):
        missing.append("record/review")
    return missing


def _external_context_block(research_context: "ResearchContext | None") -> str:
    if not research_context or (not research_context.findings and not research_context.errors):
        return ""
    parts = ["## External Research Context"]
    parts.append(
        "这些联网结果优先用于补充项目背景和应用价值：时事新闻、政策背景、行业趋势、市场规模/增长、"
        "目标行业、经济价值、就业岗位、产业链需求、标准或公开来源线索。"
        "不得把未验证内容写成用户项目事实。PPT 可见页可写“公开资料显示/政策导向/行业趋势”，"
        "并保留来源名或年份；不要写“证据”。"
    )
    findings = valid_external_findings(list(research_context.findings))
    if not findings:
        parts.append("No valid external research findings passed source validation. Treat external research as unavailable.")
    for item in findings[:8]:
        title = getattr(item, "title", "") or "Untitled"
        abstract = (getattr(item, "abstract", "") or "").strip()
        if len(abstract) > 360:
            abstract = abstract[:360].rstrip() + "..."
        url = getattr(item, "url", "") or ""
        parts.append(f"- {title}" + (f": {abstract}" if abstract else ""))
        if url:
            parts.append(f"  Source: {url}")
    if research_context.errors:
        parts.append("### Unavailable Sources")
        for err in research_context.errors:
            parts.append(f"- {err}")
    return "\n".join(parts)


def _missing_visual_plan_fields(manuscript: str) -> list[int]:
    required = (
        "page_role:",
        "judge_focus:",
        "visual_strategy:",
        "layout_hint:",
        "evidence_assets:",
        "speaker_goal:",
        "page_core_sentence:",
        "visible_content:",
        "main_visual:",
        "visual_asset_plan:",
        "required_assets:",
        "asset_status:",
        "fallback_visual:",
        "asset_gap_handling:",
        "export_gate:",
        "main_script:",
        "sub_script:",
        "transition:",
        "contestant_intent:",
        "audience_takeaway:",
        "proof_object:",
        "visual_pattern:",
        "next_slide_bridge:",
        "story_role:",
        "primary_visual:",
        "stage_mode:",
        "display_target:",
        "time_budget_sec:",
        "speaker_role:",
        "operator_role:",
        "operator_action:",
        "expected_screen_state:",
        "fallback_plan:",
        "module_flow:",
        "acceptance_signal:",
        "command_cue:",
    )
    missing_pages: list[int] = []
    for index, page in enumerate(split_manuscript_pages(manuscript), start=1):
        lowered = page.lower()
        if (
            any(field not in lowered for field in required)
            or not _has_primary_visual_contract(page)
            or not _has_proof_object_contract(page)
            or not _has_visual_pattern_contract(page)
            or not _has_slide_content_plan_contract(page)
        ):
            missing_pages.append(index)
    return missing_pages


def _visual_plan_validation_error(manuscript: str) -> str | None:
    missing_pages = _missing_visual_plan_fields(manuscript)
    card_heavy_pages = [
        index
        for index, page in enumerate(split_manuscript_pages(manuscript), start=1)
        if _is_card_heavy_without_primary_visual(page)
    ]
    meta_language_pages = _visible_meta_language_pages(manuscript)
    storyline_issue_pages = _implementation_storyline_issue_pages(manuscript)
    event_chain_missing = _implementation_event_chain_missing(manuscript)
    duplicate_pages = _duplicate_visible_pages(manuscript)
    asset_density_issue = _asset_token_density_issue(manuscript)
    messages: list[str] = []
    if missing_pages:
        sample = ", ".join(str(page) for page in missing_pages[:10])
        messages.append(f"missing roadshow visual/execution/primary_visual planning fields on slides {sample}")
    if card_heavy_pages:
        sample = ", ".join(str(page) for page in card_heavy_pages[:10])
        messages.append(f"card-heavy layouts without a strong primary_visual on slides {sample}")
    if meta_language_pages:
        sample = ", ".join(str(page) for page in meta_language_pages[:10])
        messages.append(f"formal visible copy contains planning/meta language on slides {sample}")
    if storyline_issue_pages:
        sample = ", ".join(str(page) for page in storyline_issue_pages[:10])
        messages.append(
            "implementation middle pages read like module reports instead of an event-driven proof chain "
            f"on slides {sample}"
        )
    if event_chain_missing:
        messages.append(
            "implementation middle pages lack required live-event proof chain parts: "
            + ", ".join(event_chain_missing)
        )
    if duplicate_pages:
        sample = ", ".join(f"{left}/{right}" for left, right in duplicate_pages[:8])
        messages.append(f"duplicate or near-identical visible slide content on slide pairs {sample}")
    if asset_density_issue:
        messages.append(asset_density_issue)
    return "; ".join(messages) if messages else None


def _roadshow_candidate_score(manuscript: str, target_pages: int) -> int:
    """Rank fallback manuscripts without letting a shorter retry overwrite a fuller draft."""
    pages = len(split_manuscript_pages(manuscript))
    if 35 <= pages <= 45:
        return 10_000 - abs(pages - target_pages)
    return pages


def _is_pdf_noise_line(stripped: str) -> bool:
    if not stripped:
        return False
    if stripped.startswith("[[FIG:"):
        return True
    if any(marker in stripped for marker in ROADSHOW_PDF_NOISE_MARKERS):
        return True
    if re.fullmatch(r"[—\\-– ]*\\d+[—\\-– ]*", stripped):
        return True
    return False


def _clean_roadshow_source_for_llm(source_md: str) -> str:
    """Remove PDF extraction artifacts before sending roadshow material to LLMs."""
    cleaned: list[str] = []
    skipping_figure_table = False
    previous_blank = False

    for raw_line in source_md.splitlines():
        stripped = raw_line.strip()
        if _is_pdf_noise_line(stripped):
            skipping_figure_table = stripped.startswith("[[FIG:") or "Figure (natural" in stripped
            continue

        if not stripped:
            if cleaned and not previous_blank:
                cleaned.append("")
            previous_blank = True
            continue

        is_heading = stripped.startswith("#")
        is_table_line = stripped.startswith("|") and "|" in stripped[1:]
        if skipping_figure_table and is_table_line:
            continue
        if skipping_figure_table and is_heading:
            skipping_figure_table = False
        elif not is_table_line:
            skipping_figure_table = False

        cleaned.append(raw_line.rstrip())
        previous_blank = False

    return "\n".join(cleaned).strip()


def _looks_like_roadshow_mother_draft(source_md: str) -> bool:
    return bool(classify_roadshow_source(source_md).get("agent_seed_draft"))


def _compact_roadshow_source_for_pass1(source_md: str) -> tuple[str, str]:
    """Keep high-signal roadshow source content under a long-request budget.

    Roadshow uploads can already be "PPT generation mother drafts" with tens of
    thousands of characters and large tables. Sending the full extracted PDF to
    an upstream model route can exceed long-request stability.
    This compactor keeps the parts that matter for competition PPT planning:
    locked facts, module chains, field run-of-show, slide blueprint, support materials,
    risks, and export gates.
    """
    cleaned_source = _clean_roadshow_source_for_llm(source_md)
    is_mother_draft = _looks_like_roadshow_mother_draft(cleaned_source)
    if len(cleaned_source) <= ROADSHOW_PASS1_SOURCE_CHAR_BUDGET:
        note = "source cleaned and kept in full"
        if len(cleaned_source) != len(source_md):
            note += f" after removing PDF extraction noise ({len(source_md)} -> {len(cleaned_source)} chars)"
        return cleaned_source, note

    lines = cleaned_source.splitlines()
    kept: list[str] = []
    section_chars = 0
    keep_section = False
    table_lines_kept = 0

    for line in lines:
        stripped = line.strip()
        is_heading = stripped.startswith("#")
        if is_heading:
            keep_section = any(token in stripped for token in ROADSHOW_SOURCE_KEEP_HEADINGS)
            table_lines_kept = 0
            if keep_section:
                kept.append(line)
                section_chars += len(line) + 1
            continue

        if not keep_section:
            continue
        if section_chars >= ROADSHOW_SECTION_CHAR_BUDGET:
            continue

        # Tables are useful, but extracted PDFs often duplicate table text.
        # Pass 1 only needs enough rows to diagnose support materials and gaps.
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines_kept += 1
            if table_lines_kept > 6:
                continue
        if not stripped:
            if kept and kept[-1].strip():
                kept.append("")
            continue
        kept.append(line)
        section_chars += len(line) + 1

    if is_mother_draft:
        intro = (
            "说明：检测到源材料已经是结构化路演 PPT 生成母稿。第一轮只做短抽取与缺口核验，"
            "不要重新展开全文诊断；后续阶段会继续使用完整工作区材料。"
        )
        snapshot = cleaned_source[:3500]
        closing = cleaned_source[-1200:]
    else:
        intro = "说明：源材料过长，已为第一轮资料诊断保留高信号内容。完整材料仍保留在后续工作区和调试文件中。"
        snapshot = cleaned_source[:4500]
        closing = cleaned_source[-1200:]
    compact = (
        "## Compacted Roadshow Source\n\n"
        f"{intro}\n\n"
        "### Front Matter Snapshot\n\n"
        f"{snapshot}\n\n"
        "### High Signal Sections\n\n"
        f"{chr(10).join(kept)}\n\n"
        "### Closing Snapshot\n\n"
        f"{closing}"
    )
    if len(compact) > ROADSHOW_PASS1_SOURCE_CHAR_BUDGET:
        compact = compact[:ROADSHOW_PASS1_SOURCE_CHAR_BUDGET] + "\n\n[Source compacted: truncated to request budget]"
    note = (
        f"source cleaned from {len(source_md)} to {len(cleaned_source)} chars; "
        f"compacted to {len(compact)} chars for pass1 long-request stability"
    )
    if is_mother_draft:
        note += "; structured mother draft detected"
    return compact, note


async def analyze_materials(
    paper: ParsedPaper,
    llm: LLMProvider,
    model: str,
    *,
    instruction: str = "",
    num_pages: int | None = None,
    language: str = "zh",
    detail_level: str = "normal",
    research_context: "ResearchContext | None" = None,
    debug_dir: Path | None = None,
    on_progress: Callable[[str, float], None] | None = None,
    plan_only: bool = False,
    render_engine: str = "svg",
) -> str:
    """Analyze project/competition materials and produce a roadshow manuscript."""
    is_deepseek = is_deepseek_provider(llm, model)
    image2_mode = render_engine == "image2"
    source_md = paper.to_markdown()
    source_profile = classify_roadshow_source(source_md)
    pass1_source_md, source_compaction_note = _compact_roadshow_source_for_pass1(source_md)
    clean_source_snapshot = _clean_roadshow_source_for_llm(source_md)[:6000]
    external_block = _external_context_block(research_context)
    figure_inventory = roadshow_figure_token_inventory_block(paper)
    _debug_write_text(
        debug_dir,
        "roadshow_source_profile.json",
        json.dumps(source_profile, ensure_ascii=False, indent=2),
    )

    if on_progress:
        on_progress("正在分析资料完整度与关键事实", 0.15)
    pass1_parts = [
        f"## Source Materials\n\n{pass1_source_md}",
        f"\n## Source Compaction Note\n\n{source_compaction_note}",
        f"\n{source_profile_prompt_block(source_profile)}",
        f"\n## User Requirement\n\n{instruction or '无额外要求'}",
        f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
        "\n## Output Budget\n\n"
        "请把第一轮资料分析控制在 2500 个中文字符以内。"
        "只抽取确定事实、支撑链路、现场实操缺口和正式导出风险；"
        "不要复述源材料，不要重写母稿，不要展开长篇说明。",
        f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
        f"\n{ROADSHOW_FULL_LOGIC_FRAME}",
        f"\n{ROADSHOW_STORYLINE_RULE}",
        f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
    ]
    if external_block:
        pass1_parts.append(f"\n{external_block}")
    if is_deepseek:
        pass1_parts.append("\n" + deepseek_research_guidance(detail_level))
    pass1_messages = [
        LLMMessage.system(ANALYSIS_SYSTEM_PROMPT),
        LLMMessage.user("\n".join(pass1_parts)),
    ]
    _debug_write_messages(debug_dir, "roadshow_pass1_material_diagnosis_prompt.md", pass1_messages)
    pass1_response = await llm.chat(
        pass1_messages,
        model,
        temperature=0.35,
        max_tokens=ROADSHOW_PASS1_MAX_TOKENS,
    )
    material_analysis = pass1_response.content
    _debug_write_text(debug_dir, "roadshow_pass1_material_diagnosis_response.md", material_analysis)
    locked_facts = extract_locked_facts(material_analysis, paper)
    locked_facts_block = locked_facts.to_prompt_block()
    _debug_write_text(
        debug_dir,
        "roadshow_locked_facts.json",
        json.dumps(locked_facts.to_dict(), ensure_ascii=False, indent=2),
    )
    evidence_report = build_evidence_asset_report(paper, source_md, material_analysis)
    evidence_block = evidence_asset_prompt_block(evidence_report)
    pattern_block = roadshow_pattern_library_prompt_block()
    page_count_decision = _roadshow_page_count_decision(
        num_pages=num_pages,
        paper=paper,
        source_md=source_md,
        source_profile=source_profile,
        material_analysis=material_analysis,
        evidence_report=evidence_report,
    )
    effective_num_pages = int(page_count_decision["recommended_pages"])
    page_contract = _roadshow_slide_contract(effective_num_pages)
    _debug_write_text(
        debug_dir,
        "roadshow_page_count_decision.json",
        json.dumps(page_count_decision, ensure_ascii=False, indent=2),
    )
    _debug_write_text(
        debug_dir,
        "roadshow_evidence_asset_report.json",
        json.dumps(evidence_report, ensure_ascii=False, indent=2),
    )

    if on_progress:
        on_progress("正在策划比赛大纲与五大板块", 0.18)
        on_progress("正在准备大纲生成约束", 0.181)
    if image2_mode:
        project_dir = project_dir_from_debug_dir(debug_dir)
        image2_user_requirement = _compact_user_requirement_for_image2(instruction)
        image2_asset_inventory = _image2_asset_token_inventory_block(project_dir, paper)
        pass2_parts = [
            f"## Material Analysis\n\n{_truncate_for_prompt(material_analysis, 3200)}",
            f"\n## Locked Facts\n\n{locked_facts_block}",
            f"\n## Support Material Summary\n\n{_truncate_for_prompt(evidence_block, 2600)}",
            f"\n## Source Material Snapshot\n\n{_truncate_for_prompt(clean_source_snapshot, 2600)}",
            f"\n{source_profile_prompt_block(source_profile)}",
            f"\n## User Requirement\n\n{image2_user_requirement}",
            f"\n## Slide Contract\n\n{page_contract}",
            f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
            f"\n{_image2_light_outline_contract(effective_num_pages)}",
            f"\n{image2_asset_inventory}",
        ]
        pass2_messages = [
            LLMMessage.system(IMAGE2_CLEAN_OUTLINE_SYSTEM_PROMPT),
            LLMMessage.user("\n".join(pass2_parts)),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass2_image2_light_outline_prompt.md", pass2_messages)
        outline_plan = await _generate_valid_image2_outline(
            llm=llm,
            model=model,
            base_messages=pass2_messages,
            effective_num_pages=effective_num_pages,
            locked_facts=locked_facts,
            debug_dir=debug_dir,
            on_progress=on_progress,
        )
    elif plan_only:
        # Editable plan_only: skip the multi-minute heavy outline essay.
        # Cards come from the light slide plan (Pass5); outline is only
        # storyline context and can be a compact structure brief.
        if on_progress:
            on_progress("正在生成可编辑大纲（精简模式）", 0.185)
        compact_outline_parts = [
            f"## Material Analysis\n\n{_truncate_for_prompt(material_analysis, 3200)}",
            f"\n## Locked Facts\n\n{locked_facts_block}",
            f"\n## Support Material Summary\n\n{_truncate_for_prompt(evidence_block, 2600)}",
            f"\n## Source Snapshot\n\n{_truncate_for_prompt(clean_source_snapshot, 2200)}",
            f"\n{source_profile_prompt_block(source_profile)}",
            f"\n## User Requirement\n\n{_truncate_for_prompt(instruction or '无额外要求', 1200)}",
            f"\n## Slide Contract\n\n{page_contract}",
            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
            f"\n{ROADSHOW_STORYLINE_RULE}",
            "\n## Output Rule\n\n"
            f"用精简 Markdown 输出 {effective_num_pages} 页路演结构，不要长文。"
            "按五大板块（项目背景、研发历程、实施过程、创新设计、应用价值）列出页序。"
            "每页一行：page | section | formal_title | page_core_sentence | story_role。"
            "story_role 只能从 raise_problem、reveal_solution、prove_flow、unpack_mechanism、"
            "verify_result、extract_innovation、land_value 中选。"
            "禁止输出完整讲稿、禁止输出执行口令、禁止个人/学校信息。",
        ]
        if external_block:
            compact_outline_parts.append(f"\n{_truncate_for_prompt(external_block, 1200)}")
        pass2_messages = [
            LLMMessage.system(
                "你是职业院校技能大赛路演的精简大纲 Agent。"
                "目标是快速给出可编辑页序结构，而不是完整现场执行剧本。"
            ),
            LLMMessage.user("\n".join(compact_outline_parts)),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass2_plan_only_compact_outline_prompt.md", pass2_messages)
        pass2_response = await _await_llm_with_safe_progress(
            lambda: llm.chat(
                pass2_messages,
                model,
                temperature=0.35,
                max_tokens=min(ROADSHOW_LIGHT_PLAN_MAX_TOKENS, 8000),
            ),
            on_progress=on_progress,
            messages=(
                "正在整理五段故事线结构",
                "正在分配页序与板块",
                "正在压缩大纲为可编辑页表",
            ),
            start_fraction=0.181,
            end_fraction=0.205,
            stall_retry_seconds=max(120, _roadshow_research_stall_retry_seconds()),
            max_attempts=2,
            retry_message="精简大纲连接波动，正在重新建立请求",
        )
        outline_plan = pass2_response.content
    else:
        pass2_parts = [
            f"## Material Analysis\n\n{material_analysis}",
            f"\n## Locked Facts\n\n{locked_facts_block}",
            f"\n{evidence_block}",
            f"\n{pattern_block}",
            f"\n## Source Material Snapshot\n\n{clean_source_snapshot}",
            f"\n{source_profile_prompt_block(source_profile)}",
            f"\n## User Requirement\n\n{instruction or '无额外要求'}",
            f"\n## Slide Contract\n\n{page_contract}",
            f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
            f"\n{ROADSHOW_FULL_LOGIC_FRAME}",
            f"\n{ROADSHOW_STORYLINE_RULE}",
            f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
        ]
        if external_block:
            pass2_parts.append(f"\n{external_block}")
        pass2_messages = [
            LLMMessage.system(OUTLINE_SYSTEM_PROMPT),
            LLMMessage.user("\n".join(pass2_parts)),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass2_outline_prompt.md", pass2_messages)
        # Full SVG path needs a richer outline; allow a longer silent window
        # than plan_only so we don't fail a 3–5 minute good request early.
        pass2_response = await _await_llm_with_safe_progress(
            lambda: llm.chat(
                pass2_messages,
                model,
                temperature=0.4,
                max_tokens=ROADSHOW_MAX_TOKENS,
            ),
            on_progress=on_progress,
            messages=ROADSHOW_PASS2_SAFE_PROGRESS_MESSAGES,
            start_fraction=0.181,
            end_fraction=0.205,
            stall_retry_seconds=max(240, _roadshow_research_stall_retry_seconds()),
            max_attempts=2,
            retry_message="大纲策划连接波动，正在重新建立请求并保持原生成要求",
        )
        outline_plan = pass2_response.content
    _debug_write_text(
        debug_dir,
        (
            "roadshow_pass2_image2_light_outline_response.md"
            if image2_mode
            else "roadshow_pass2_plan_only_compact_outline_response.md"
            if plan_only
            else "roadshow_pass2_outline_response.md"
        ),
        outline_plan,
    )

    # Editable plan_only only needs reviewable PageContentCards. Pass3/Pass4 are
    # multi-minute single-shot LLM essays that mostly feed storyline metadata and
    # Pass5 prompt context — not the light-plan table that becomes cards. Skip
    # them for plan_only (same speed path as image2 light outline) so users reach
    # the card editor in minutes instead of hanging on contestant-perspective.
    # Full non-image2 render still runs Pass3/Pass4 for chunk manuscript quality.
    skip_heavy_pass34 = image2_mode or plan_only

    if skip_heavy_pass34:
        if image2_mode:
            run_of_show_plan = (
                "image2 mode: skipped heavy run-of-show planning; "
                "per-page speaker notes are generated in 5-page chunks."
            )
            skip_reason3 = "image2 模式已跳过现场执行重型策划"
        else:
            run_of_show_plan = (
                "plan_only editable path: skipped heavy run-of-show LLM. "
                "Field execution defaults are filled on PageContentCards; "
                "users can refine in the card editor before render."
            )
            skip_reason3 = "可编辑策划已跳过现场执行重型步骤，直接生成页面内容卡片"
        _debug_write_text(debug_dir, "roadshow_pass3_run_of_show_response.md", run_of_show_plan)
        _debug_write_text(debug_dir, "roadshow_run_of_show.md", run_of_show_plan)
        if on_progress:
            on_progress(skip_reason3, 0.21)
    else:
        if on_progress:
            on_progress("正在策划现场执行分镜与口令", 0.21)
        run_of_show_parts = [
            f"## Material Analysis\n\n{material_analysis}",
            f"\n## Locked Facts\n\n{locked_facts_block}",
            f"\n{evidence_block}",
            f"\n{pattern_block}",
            f"\n## Competition Outline\n\n{outline_plan}",
            f"\n## Source Material Snapshot\n\n{source_md[:5000]}",
            f"\n{source_profile_prompt_block(source_profile)}",
            f"\n## User Requirement\n\n{instruction or '无额外要求'}",
            f"\n## Slide Contract\n\n{page_contract}",
            f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
            "\n## Required Competition Narrative\n\n"
            "可见一级结构使用：项目背景、研发历程、实施过程、创新设计、应用价值。\n"
            "技能要点中的每个核心模块必须形成：功能价值说明 -> 关键技术/代码还原 -> 产品效果测试 -> 模块小结。\n"
            "开场必须包含软硬件/安全/应急/环境确认。\n"
            "项目背景必须体现时事新闻、政策背景、市场考察和研发动因；应用价值必须体现企业、学校、团队、知识产权和就业/行业帮助。"
            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}"
            f"\n{ROADSHOW_FULL_LOGIC_FRAME}"
            f"\n{ROADSHOW_STORYLINE_RULE}"
            f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}"
        ]
        if figure_inventory:
            run_of_show_parts.append(f"\n{figure_inventory}")
        if external_block:
            run_of_show_parts.append(f"\n{external_block}")
        run_of_show_messages = [
            LLMMessage.system(RUN_OF_SHOW_SYSTEM_PROMPT),
            LLMMessage.user("\n".join(run_of_show_parts)),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass3_run_of_show_prompt.md", run_of_show_messages)
        run_of_show_response = await _await_llm_with_safe_progress(
            lambda: llm.chat(
                run_of_show_messages,
                model,
                temperature=0.35,
                max_tokens=ROADSHOW_MAX_TOKENS,
            ),
            on_progress=on_progress,
            messages=ROADSHOW_PASS3_SAFE_PROGRESS_MESSAGES,
            start_fraction=0.21,
            end_fraction=0.235,
            stall_retry_seconds=_roadshow_research_stall_retry_seconds(),
            retry_message="现场执行策划连接波动，正在重新建立请求并保持原生成要求",
        )
        run_of_show_plan = run_of_show_response.content
        _debug_write_text(debug_dir, "roadshow_pass3_run_of_show_response.md", run_of_show_plan)
        _debug_write_text(debug_dir, "roadshow_run_of_show.md", run_of_show_plan)

    if skip_heavy_pass34:
        if image2_mode:
            contestant_plan = (
                "image2 mode: skipped heavy contestant-perspective planning; "
                "page goals are generated from the lightweight outline per 5-page chunk."
            )
            skip_reason4 = "image2 模式已跳过选手视角重型策划"
        else:
            contestant_plan = (
                "plan_only editable path: skipped heavy contestant-perspective LLM. "
                "Per-page intent/takeaway/pattern defaults are filled on PageContentCards "
                "from the light slide plan; refine in the editor before formal export."
            )
            skip_reason4 = "可编辑策划已跳过选手视角重型步骤，改为卡片字段默认补齐"
        _debug_write_text(debug_dir, "roadshow_pass4_contestant_perspective_response.md", contestant_plan)
        _debug_write_text(debug_dir, "roadshow_contestant_perspective.md", contestant_plan)
        if on_progress:
            on_progress(skip_reason4, 0.235)
    else:
        if on_progress:
            on_progress("正在策划选手视角与支撑对象", 0.235)
        contestant_parts = [
            f"## Material Analysis\n\n{material_analysis}",
            f"\n## Locked Facts\n\n{locked_facts_block}",
            f"\n{evidence_block}",
            f"\n{pattern_block}",
            f"\n## Competition Outline\n\n{outline_plan}",
            f"\n## Field Run-of-show\n\n{run_of_show_plan}",
            f"\n{PRIMARY_VISUAL_CONTRACT}",
            f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
            f"\n## Slide Contract\n\n{page_contract}",
            f"\n## User Requirement\n\n{instruction or '无额外要求'}",
            "\n## Output Rule\n\n"
            "按目标页数逐页输出选手视角策划。每页都必须先回答：选手这页在现场证明什么、"
            "用什么支撑材料或现场展示支撑、评委应该看懂什么、适合哪一种 reference pattern。",
            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
            f"\n{ROADSHOW_FULL_LOGIC_FRAME}",
            f"\n{ROADSHOW_STORYLINE_RULE}",
            f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
        ]
        contestant_messages = [
            LLMMessage.system(CONTESTANT_PERSPECTIVE_SYSTEM_PROMPT),
            LLMMessage.user("\n".join(contestant_parts)),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass4_contestant_perspective_prompt.md", contestant_messages)
        contestant_response = await _await_llm_with_safe_progress(
            lambda: llm.chat(
                contestant_messages,
                model,
                temperature=0.3,
                max_tokens=ROADSHOW_MAX_TOKENS,
            ),
            on_progress=on_progress,
            messages=ROADSHOW_PASS4_SAFE_PROGRESS_MESSAGES,
            start_fraction=0.235,
            end_fraction=0.245,
            stall_retry_seconds=_roadshow_research_stall_retry_seconds(),
            retry_message="选手视角策划连接波动，正在重新建立请求并保持原生成要求",
        )
        contestant_plan = contestant_response.content
        _debug_write_text(debug_dir, "roadshow_pass4_contestant_perspective_response.md", contestant_plan)
        _debug_write_text(debug_dir, "roadshow_contestant_perspective.md", contestant_plan)

    if on_progress:
        on_progress("正在生成页面内容卡片", 0.245)
    if image2_mode:
        slide_content_plan = outline_plan
        _debug_write_text(debug_dir, "roadshow_pass5_light_slide_plan_response.md", slide_content_plan)
    else:
        # Keep 35-45 pages; generate the light plan table in parallel segments
        # so one long 40-row call cannot stall the whole editable path.
        slide_content_plan = await _generate_light_slide_plan_parallel(
            llm=llm,
            model=model,
            effective_num_pages=effective_num_pages,
            material_analysis=material_analysis,
            locked_facts_block=locked_facts_block,
            evidence_block=evidence_block,
            pattern_block=pattern_block,
            outline_plan=outline_plan,
            contestant_plan=contestant_plan,
            source_profile=source_profile,
            language=language,
            page_contract=page_contract,
            figure_inventory=figure_inventory,
            debug_dir=debug_dir,
            on_progress=on_progress,
        )
        _debug_write_text(debug_dir, "roadshow_pass5_light_slide_plan_response.md", slide_content_plan)
    planning_cards = write_planning_artifacts(
        project_dir_from_debug_dir(debug_dir),
        material_analysis=material_analysis,
        locked_facts=locked_facts,
        page_count_decision=page_count_decision,
        evidence_report=evidence_report,
        source_profile=source_profile,
        outline_plan=outline_plan,
        run_of_show_plan=run_of_show_plan,
        contestant_plan=contestant_plan,
        slide_content_plan=slide_content_plan,
        allow_placeholder_fill=not image2_mode,
    )
    if image2_mode:
        planning_errors = validate_cards_for_formal_render(planning_cards, expected_pages=effective_num_pages)
        if planning_errors:
            _debug_write_text(
                debug_dir,
                "roadshow_image2_page_card_validation_error.txt",
                "\n".join(planning_errors),
            )
            raise ValueError("image2 页面页纲无效，已停止生成：" + "；".join(planning_errors[:10]))
        project_dir = project_dir_from_debug_dir(debug_dir)
        write_image2_page_descriptions(project_dir, planning_cards)
        write_image2_page_briefs(project_dir, planning_cards)
    if plan_only:
        if on_progress:
            on_progress("页面内容卡片已生成，等待确认", 0.30)
        return ""

    if image2_mode:
        manuscript = cards_to_manuscript(planning_cards)
        manuscript = _normalize_roadshow_field_labels(manuscript)
        manuscript = _normalize_roadshow_page_boundaries(manuscript)
        manuscript = remove_disallowed_figure_tokens(manuscript, paper)
        manuscript = apply_locked_facts_to_manuscript(manuscript, locked_facts)
        final_output = ensure_roadshow_manuscript_hard_requirements(
            manuscript,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
        )
        hard_quality_report = evaluate_roadshow_manuscript_quality(
            final_output,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
            require_notes=False,
        )
        _debug_write_text(
            debug_dir,
            "roadshow_hard_quality_report.json",
            json.dumps(hard_quality_report, ensure_ascii=False, indent=2),
        )
        if not hard_quality_report.get("passed"):
            logger.warning(
                "Image2 roadshow clean-outline manuscript has quality warnings; continuing without heavy repair: %s",
                hard_quality_report.get("findings"),
            )
        try:
            script_skill_result = await enhance_roadshow_script(
                llm=llm,
                model=model,
                manuscript=final_output,
                project_dir=project_dir_from_debug_dir(debug_dir),
                debug_dir=debug_dir,
                material_analysis=material_analysis,
                outline_plan=outline_plan,
                run_of_show_plan=run_of_show_plan,
                contestant_plan=contestant_plan,
                target_duration_sec=3600,
                target_chars=8000,
                on_progress=on_progress,
            )
            enhanced_error = _manuscript_validation_error(
                script_skill_result.manuscript,
                paper,
                effective_num_pages,
                detail_level,
            )
            if not enhanced_error:
                final_output = script_skill_result.manuscript
            else:
                logger.warning("Image2 roadshow script skill output kept original manuscript: %s", enhanced_error)
        except Exception as exc:
            logger.warning("Image2 roadshow script skill failed; keeping original speaker notes: %s", exc)
        _debug_write_text(debug_dir, "roadshow_pass5_image2_clean_cards_manuscript.md", final_output)
        _debug_write_text(debug_dir, "roadshow_final_manuscript.md", final_output)
        if on_progress:
            on_progress("image2 干净页纲已完成，准备进入页面生成", 0.30)
        return final_output

    manuscript = ""
    chunk_ranges = _slide_ranges(effective_num_pages, _image2_chunk_size(image2_mode))
    manuscript_parallel = max(1, min(ROADSHOW_MANUSCRIPT_PARALLEL_SEGMENTS, len(chunk_ranges)))
    manuscript_sem = asyncio.Semaphore(manuscript_parallel)
    manuscript_done = 0
    manuscript_progress_lock = asyncio.Lock()

    async def _generate_manuscript_chunk(
        chunk_index: int,
        start_page: int,
        end_page: int,
    ) -> tuple[int, list[str]]:
        nonlocal manuscript_done
        chunk_progress = 0.25 + (chunk_index - 1) / max(1, len(chunk_ranges)) * 0.05
        expected_chunk_pages = end_page - start_page + 1
        pages: list[str] = []
        max_chunk_attempts = ROADSHOW_IMAGE2_CHUNK_RETRY_ATTEMPTS if image2_mode else 2
        compact_light_plan = _light_plan_rows_for_range(slide_content_plan, start_page, end_page)
        last_error: str | None = None

        async with manuscript_sem:
            if on_progress:
                on_progress(
                    f"正在分段并行生成第 {start_page}-{end_page} 页正文（并发 {manuscript_parallel}）",
                    chunk_progress,
                )
            for attempt in range(1, max_chunk_attempts + 1):
                if image2_mode:
                    if on_progress and attempt > 1:
                        on_progress(
                            f"正在重试第 {start_page}-{end_page} 页 image2 内容批次，第 {attempt}/{max_chunk_attempts} 次",
                            chunk_progress + min(0.018, attempt * 0.006),
                        )
                    chunk_parts = [
                        f"## Material Analysis\n\n{_truncate_for_prompt(material_analysis, 2600)}",
                        f"\n## Locked Facts\n\n{locked_facts_block}",
                        f"\n## Support Material Summary\n\n{_truncate_for_prompt(evidence_block, 4200)}",
                        f"\n## Lightweight Outline Rows For This Chunk\n\n{compact_light_plan}",
                        f"\n{source_profile_prompt_block(source_profile)}",
                        f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
                        f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
                        f"\n{PRIMARY_VISUAL_CONTRACT}",
                        f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
                        "\n## Image2 Rendering Note\n\n"
                        "最终页面由 image2 生成完整 PPT 图片。visible_content、visual_strategy、primary_visual 和 speaker_notes "
                        "要服务于一张完整、专业、可读的路演页面图片，不要输出 SVG 组件方案。",
                        _image2_manuscript_chunk_contract(
                            start_page=start_page,
                            end_page=end_page,
                            effective_num_pages=effective_num_pages,
                            expected_chunk_pages=expected_chunk_pages,
                        ),
                    ]
                    if figure_inventory:
                        chunk_parts.append(
                            f"\n## Asset Token Inventory\n\n{_truncate_for_prompt(figure_inventory, 5200)}"
                        )
                    if attempt > 1:
                        chunk_parts.append(
                            "\n## Retry Instruction\n\n"
                            "上一次没有得到完整页数或连接超时。只根据本批次页纲重新输出本批次 manuscript，"
                            "不要补写其他页，不要解释。"
                        )
                else:
                    chunk_parts = [
                        f"## Material Analysis\n\n{_truncate_for_prompt(material_analysis, 5000)}",
                        f"\n## Locked Facts\n\n{locked_facts_block}",
                        f"\n{_truncate_for_prompt(evidence_block, 7000)}",
                        f"\n{pattern_block}",
                        f"\n## Competition Outline\n\n{_truncate_for_prompt(outline_plan, 7000)}",
                        f"\n## Field Run-of-show\n\n{_truncate_for_prompt(run_of_show_plan, 7000)}",
                        f"\n## Contestant Perspective Plan\n\n{_truncate_for_prompt(contestant_plan, 9000)}",
                        f"\n## Light SlideContentPlan\n\n{_truncate_for_prompt(slide_content_plan, 14000)}",
                        f"\n{source_profile_prompt_block(source_profile)}",
                        f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
                        f"\n{PRIMARY_VISUAL_CONTRACT}",
                        f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
                        f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
                        f"\n{ROADSHOW_FULL_LOGIC_FRAME}",
                        f"\n{ROADSHOW_STORYLINE_RULE}",
                        f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
                        f"\n## Detail Level\n\n{detail_level}",
                        "\n## Chunk Contract\n\n"
                        f"只生成第 {start_page}-{end_page} 页，共 {expected_chunk_pages} 页。"
                        f"完整 PPT 总页数为 {effective_num_pages} 页，本轮只是其中一个连续页段。\n"
                        "- 输出必须只有本页段 manuscript，不要输出本页段以外页面，不要解释。\n"
                        "- 每页仍用独立一行 `---` 分隔。\n"
                        "- `---` 只能用于分隔两页，页面内部的内容稿、视觉字段、选手视角、执行字段之间禁止使用 `---`。\n"
                        "- 禁止输出 `Slide Content Plan:`、`Visual Planning Fields:`、`Contestant Perspective Fields:`、`Field Execution Fields:` 这类字段组标题；直接写字段即可。\n"
                        "- 第 1 页必须是 cover；只有全稿最后一页才能是 ending；本页段中间页面不得写 ending。\n"
                        "- 第 1 页封面必须不配图：required_assets 写“无”，asset_status=not_required，main_visual.type 使用 svg_diagram 或 none；禁止绑定上传素材、截图、真实场景图或生成图。\n"
                        "- 第 2 页必须是正式目录或项目大纲，不得写“路演路线”“我们如何证明”。\n"
                        "- 每页先写正式可见内容，再写所有内部字段。\n"
                        "- 同一页段内不得出现重复页；不同页必须有不同证明对象、不同核心句和不同主视觉素材。\n"
                        "- required_assets 中凡是使用上传图片素材，必须引用 `[[ASSET:asset_id]]`，禁止直接写中文路径；provided 的图片素材页必须让后续 SVG 使用真实 `<image>`。\n"
                        "- 系统截图、设备现场图、运行图表、反馈图和正式材料图有 asset_id 时必须优先绑定，不要降级为纯 SVG。\n"
                        "- proof_object、main_visual、primary_visual、visual_pattern 必须使用多行块格式，禁止写成 `type=...; source=...` 行内格式。\n"
                        "- speaker_notes 必须是可直接上台朗读的正式讲稿，包含上页承接、主体说明、项目事实、必要的演示/队友交接话术和自然转场，控制在 320-520 个中文字符；禁止出现“本页核心观点”“评委视角”“证明任务”“证明对象”“它的作用是”“讲解时”“如果现场进入”“主视觉”“版式”“布局”“字段”“项目名称、一句定位语”等页面分析和内部提示。\n"
                        "- 主稿/子稿要简短，main_script/sub_script 每项控制在 120 个中文字符以内。\n"
                        "- display_target、speaker_role、operator_role 等现场执行字段必须填写，但不得出现在可见正文。\n",
                    ]
                    if attempt > 1:
                        chunk_parts = [
                            f"## Locked Facts\n\n{locked_facts_block}",
                            f"\n{_truncate_for_prompt(evidence_block, 5000)}",
                            f"\n## Competition Outline\n\n{_truncate_for_prompt(outline_plan, 5000)}",
                            f"\n## Field Run-of-show\n\n{_truncate_for_prompt(run_of_show_plan, 4000)}",
                            f"\n## Contestant Perspective Plan\n\n{_truncate_for_prompt(contestant_plan, 5000)}",
                            f"\n## Light SlideContentPlan Rows For This Chunk\n\n{compact_light_plan}",
                            f"\n## Target Language\n\n{language}\n\n{_language_guidance(language)}",
                            f"\n{SLIDE_CONTENT_PLAN_CONTRACT}",
                            f"\n{ROADSHOW_VISIBLE_VOCABULARY_RULE}",
                            f"\n{ROADSHOW_STORYLINE_RULE}",
                            f"\n{IMPLEMENTATION_EVENT_CHAIN_RULE}",
                            "\n## Retry Chunk Contract\n\n"
                            f"只生成第 {start_page}-{end_page} 页，共 {expected_chunk_pages} 页。"
                            "输出必须只有 manuscript，不要解释。\n"
                            "- 每页顶部必须有 `<!-- page_type: cover|chapter|content|ending -->`。\n"
                            "- `---` 只能用于分隔两页，页面内部禁止使用 `---`。\n"
                            "- 不要输出字段组标题，直接写 page_core_sentence、visible_content、main_visual、required_assets、"
                            "primary_visual、proof_object、visual_pattern、stage_mode 等字段。\n"
                            "- required_assets 中使用上传图片素材时必须引用 `[[ASSET:asset_id]]`。\n",
                            "- 如果本页段包含第 1 页，第 1 页封面必须不配图：required_assets 写“无”，asset_status=not_required，main_visual.type 使用 svg_diagram 或 none；禁止绑定上传素材、截图、真实场景图、生成图或 pending 图片背景。\n"
                            "- speaker_notes 必须是可直接上台朗读的正式讲稿，控制在 320-520 个中文字符；必须包含承接、主体说明、项目事实、自然转场，演示/测试/代码页要有队友交接话术。\n"
                            "- speaker_notes 禁止出现“本页、这一页、页面、核心观点、证明对象、讲解时、主视觉、版式、布局、字段、项目名称、一句定位语、副标题、底部任务”等元说明或设计提示。\n"
                            "- visible_content 只写可投影正文，优先使用 3-5 条短句或短项目；单页可见正文尽量控制在 180 个中文字符以内，复杂代码、测试和数据页必须拆成步骤/结论/来源，不堆长段落。\n",
                        ]
                if figure_inventory and not image2_mode:
                    chunk_parts.append(
                        f"\n{_truncate_for_prompt(figure_inventory, 5000) if attempt > 1 else figure_inventory}"
                    )

                chunk_messages = [
                    LLMMessage.system(MANUSCRIPT_SYSTEM_PROMPT),
                    LLMMessage.user("\n".join(chunk_parts)),
                ]
                prompt_suffix = "" if attempt == 1 else f"_attempt{attempt}"
                _debug_write_messages(
                    debug_dir,
                    f"roadshow_pass5_manuscript_chunk_{start_page:02d}_{end_page:02d}{prompt_suffix}_prompt.md",
                    chunk_messages,
                )
                try:
                    response = await _await_llm_with_safe_progress(
                        lambda msgs=chunk_messages, att=attempt: llm.chat(
                            msgs,
                            model,
                            temperature=0.28 if image2_mode else (0.25 if att > 1 else 0.35),
                            max_tokens=ROADSHOW_CHUNK_MAX_TOKENS,
                        ),
                        on_progress=on_progress if image2_mode else None,
                        messages=(
                            f"正在生成第 {start_page}-{end_page} 页 image2 内容批次",
                            f"正在压缩第 {start_page}-{end_page} 页素材引用",
                            f"正在校验第 {start_page}-{end_page} 页讲稿与可见文字",
                        ),
                        start_fraction=chunk_progress,
                        end_fraction=min(0.30, chunk_progress + 0.02),
                        stall_retry_seconds=ROADSHOW_IMAGE2_CHUNK_STALL_SECONDS if image2_mode else 0,
                        max_attempts=1,
                    )
                except Exception as exc:
                    last_error = str(exc)
                    if attempt >= max_chunk_attempts:
                        raise
                    logger.warning(
                        "Roadshow manuscript chunk %s-%s attempt %s failed: %s",
                        start_page,
                        end_page,
                        attempt,
                        exc,
                    )
                    continue

                chunk_manuscript = _normalize_roadshow_chunk_output(
                    response.content,
                    paper=paper,
                    locked_facts=locked_facts,
                )
                _debug_write_text(
                    debug_dir,
                    f"roadshow_pass5_manuscript_chunk_{start_page:02d}_{end_page:02d}{prompt_suffix}_response.md",
                    chunk_manuscript,
                )
                pages = split_manuscript_pages(chunk_manuscript)
                if len(pages) >= expected_chunk_pages:
                    break
                last_error = f"expected {expected_chunk_pages} slides, got {len(pages)}"
                logger.warning(
                    "Roadshow manuscript chunk %s-%s returned only %s slides on attempt %s",
                    start_page,
                    end_page,
                    len(pages),
                    attempt,
                )
            if len(pages) != expected_chunk_pages:
                logger.warning(
                    "Roadshow manuscript chunk %s-%s returned %s slides, expected %s",
                    start_page,
                    end_page,
                    len(pages),
                    expected_chunk_pages,
                )
            if len(pages) < expected_chunk_pages:
                raise ValueError(
                    f"比赛版 manuscript 第 {start_page}-{end_page} 页生成不完整："
                    f"expected {expected_chunk_pages} slides, got {len(pages)}; last_error={last_error}"
                )
        async with manuscript_progress_lock:
            manuscript_done += 1
            if on_progress:
                on_progress(
                    f"正文分段并行 {manuscript_done}/{len(chunk_ranges)} 完成（第 {start_page}-{end_page} 页）",
                    min(0.30, 0.25 + manuscript_done / max(1, len(chunk_ranges)) * 0.05),
                )
        return start_page, pages[:expected_chunk_pages]

    if on_progress:
        on_progress(
            f"正在分段并行生成正文（{len(chunk_ranges)} 段 · 并发 {manuscript_parallel} · 共 {effective_num_pages} 页）",
            0.25,
        )
    manuscript_results = await asyncio.gather(
        *[
            _generate_manuscript_chunk(index, start, end)
            for index, (start, end) in enumerate(chunk_ranges, start=1)
        ]
    )
    manuscript_results.sort(key=lambda item: item[0])
    chunk_pages: list[str] = []
    for _, pages in manuscript_results:
        chunk_pages.extend(pages)

    manuscript = "\n\n---\n\n".join(chunk_pages)
    manuscript = _normalize_roadshow_field_labels(manuscript)
    manuscript = _normalize_roadshow_page_boundaries(manuscript)
    manuscript = _normalize_inline_contract_blocks(manuscript)
    manuscript = _normalize_roadshow_pattern_ids(manuscript)
    manuscript = _ensure_formal_page_content(manuscript)
    manuscript = _sanitize_roadshow_speaker_notes(manuscript)
    manuscript, normalization_note = _normalize_competition_manuscript_structure(
        manuscript,
        effective_num_pages,
        detail_level,
    )
    manuscript = remove_disallowed_figure_tokens(manuscript, paper)
    manuscript = apply_locked_facts_to_manuscript(manuscript, locked_facts)
    if normalization_note:
        logger.info("Roadshow manuscript local normalization: %s", normalization_note)
    _debug_write_text(debug_dir, "roadshow_pass3_manuscript_response.md", manuscript)

    structure_error = _manuscript_validation_error(
        manuscript,
        paper,
        effective_num_pages,
        detail_level,
    )
    if structure_error:
        _debug_write_text(debug_dir, "roadshow_pass5_manuscript_validation_error.txt", structure_error)
        raise ValueError(f"比赛版 manuscript 分批生成后结构不完整：{structure_error}")

    visual_error_after_chunks = _visual_plan_validation_error(manuscript)
    if visual_error_after_chunks:
        if on_progress:
            on_progress("正在复核页面内容字段", 0.305)
        manuscript = _normalize_roadshow_field_labels(manuscript)
        manuscript = _normalize_inline_contract_blocks(manuscript)
        manuscript = _normalize_roadshow_pattern_ids(manuscript)
        manuscript = _ensure_formal_page_content(manuscript)
        manuscript = _sanitize_roadshow_speaker_notes(manuscript)
        structure_error = _manuscript_validation_error(
            manuscript,
            paper,
            effective_num_pages,
            detail_level,
        )
        if structure_error:
            _debug_write_text(debug_dir, "roadshow_pass5_manuscript_validation_error.txt", structure_error)
            raise ValueError(f"比赛版 manuscript 本地规范化后结构不完整：{structure_error}")
        visual_error_after_chunks = _visual_plan_validation_error(manuscript)
    if visual_error_after_chunks:
        logger.warning("Roadshow chunked manuscript visual planning warning: %s", visual_error_after_chunks)

    if image2_mode:
        final_output = ensure_roadshow_manuscript_hard_requirements(
            manuscript,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
        )
        hard_quality_report = evaluate_roadshow_manuscript_quality(
            final_output,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
            require_notes=False,
        )
        _debug_write_text(
            debug_dir,
            "roadshow_hard_quality_report.json",
            json.dumps(hard_quality_report, ensure_ascii=False, indent=2),
        )
        if not hard_quality_report.get("passed"):
            logger.warning(
                "Image2 roadshow lightweight manuscript has quality warnings; continuing without heavy repair: %s",
                hard_quality_report.get("findings"),
            )
        _debug_write_text(debug_dir, "roadshow_final_manuscript.md", final_output)
        if on_progress:
            on_progress("image2 轻量内容稿已完成，准备进入页面生成", 0.29)
        return final_output

    if on_progress:
        on_progress("正在校验页面结构与素材引用", 0.31)

    visual_error = _visual_plan_validation_error(manuscript)
    structure_error_before_visual = _manuscript_validation_error(
        manuscript,
        paper,
        effective_num_pages,
        detail_level,
    )
    if visual_error and not structure_error_before_visual:
        if on_progress:
            on_progress("正在补齐页面视觉与现场执行信息", 0.32)
        original_manuscript = manuscript
        original_page_count = len(split_manuscript_pages(original_manuscript))
        visual_messages = [
            LLMMessage.system(VISUAL_PLAN_SYSTEM_PROMPT),
            LLMMessage.user(
                "## Manuscript Missing Visual Planning Fields\n\n"
                f"{visual_error}\n\n"
                "## Competition Outline and Run-of-show\n\n"
                f"{outline_plan[:3000]}\n\n"
                "## Field Run-of-show\n\n"
                f"{run_of_show_plan[:5000]}\n\n"
                "## Contestant Perspective Plan\n\n"
                f"{contestant_plan[:5000]}\n\n"
                f"{evidence_block}\n\n"
                f"{pattern_block}\n\n"
                f"{PRIMARY_VISUAL_CONTRACT}\n\n"
                f"{SLIDE_CONTENT_PLAN_CONTRACT}\n\n"
                f"{ROADSHOW_VISIBLE_VOCABULARY_RULE}\n\n"
                f"{ROADSHOW_FULL_LOGIC_FRAME}\n\n"
                f"{ROADSHOW_STORYLINE_RULE}\n\n"
                f"{IMPLEMENTATION_EVENT_CHAIN_RULE}\n\n"
                "## Material Analysis\n\n"
                f"{material_analysis[:3000]}\n\n"
                "## Locked Facts\n\n"
                f"{locked_facts_block}\n\n"
                "## Manuscript to Enrich\n\n"
                f"{manuscript}\n\n"
                "请输出补齐页面视觉策划字段后的完整 manuscript。"
            ),
        ]
        _debug_write_messages(debug_dir, "roadshow_pass4_visual_plan_prompt.md", visual_messages)
        visual_response = await llm.chat(
            visual_messages,
            model,
            temperature=0.3,
            max_tokens=ROADSHOW_MAX_TOKENS,
        )
        enriched_manuscript = _normalize_roadshow_field_labels(visual_response.content)
        enriched_manuscript = _normalize_inline_contract_blocks(enriched_manuscript)
        enriched_manuscript = _normalize_roadshow_pattern_ids(enriched_manuscript)
        enriched_manuscript = _ensure_formal_page_content(enriched_manuscript)
        enriched_manuscript, normalization_note = _normalize_competition_manuscript_structure(
            enriched_manuscript,
            effective_num_pages,
            detail_level,
        )
        enriched_manuscript = remove_disallowed_figure_tokens(enriched_manuscript, paper)
        enriched_manuscript = apply_locked_facts_to_manuscript(enriched_manuscript, locked_facts)
        if normalization_note:
            logger.info("Roadshow visual plan local normalization: %s", normalization_note)
        _debug_write_text(debug_dir, "roadshow_pass4_visual_plan_response.md", enriched_manuscript)
        enriched_error = _manuscript_validation_error(
            enriched_manuscript,
            paper,
            effective_num_pages,
            detail_level,
        )
        enriched_page_count = len(split_manuscript_pages(enriched_manuscript))
        if enriched_error or enriched_page_count != original_page_count:
            logger.warning(
                "Roadshow visual planner changed manuscript structure; keeping previous manuscript "
                "(before=%s slides, after=%s slides, error=%s)",
                original_page_count,
                enriched_page_count,
                enriched_error,
            )
            manuscript = original_manuscript
        else:
            manuscript = enriched_manuscript
    elif visual_error and structure_error_before_visual:
        logger.warning(
            "Skipping visual planner because manuscript structure is already invalid: %s",
            structure_error_before_visual,
        )

    if on_progress:
        on_progress("正在复核评分关注点、现场执行与合规表达", 0.28)
    pass4_messages = [
        LLMMessage.system(REVIEW_SYSTEM_PROMPT),
        LLMMessage.user(
            "## Manuscript to Review\n\n"
            f"{manuscript}\n\n"
            "## Original Material Analysis\n\n"
            f"{material_analysis[:3500]}\n\n"
            "## Locked Facts\n\n"
            f"{locked_facts_block}\n\n"
            "## Outline and Run-of-show\n\n"
            f"{outline_plan[:2500]}\n\n"
                "## Field Run-of-show\n\n"
                f"{run_of_show_plan[:5000]}\n\n"
                "## Contestant Perspective Plan\n\n"
                f"{contestant_plan[:4000]}\n\n"
                f"{evidence_block}\n\n"
                f"{pattern_block}\n\n"
                f"{PRIMARY_VISUAL_CONTRACT}\n\n"
                f"{SLIDE_CONTENT_PLAN_CONTRACT}\n\n"
                f"{ROADSHOW_VISIBLE_VOCABULARY_RULE}\n\n"
                f"{ROADSHOW_FULL_LOGIC_FRAME}\n\n"
                f"{ROADSHOW_STORYLINE_RULE}\n\n"
                f"{IMPLEMENTATION_EVENT_CHAIN_RULE}\n\n"
                "如果需要修订，输出完整 manuscript；否则输出 QUALITY_CHECK_PASSED。"
            ),
    ]
    _debug_write_messages(debug_dir, "roadshow_pass4_review_prompt.md", pass4_messages)
    pass4_response = await llm.chat(
        pass4_messages,
        model,
        temperature=0.25,
        max_tokens=ROADSHOW_MAX_TOKENS,
    )
    _debug_write_text(debug_dir, "roadshow_pass4_review_response.md", pass4_response.content)
    final_output = _extract_manuscript_from_review(pass4_response.content, manuscript)
    final_output = _normalize_roadshow_field_labels(final_output)
    final_output = _normalize_inline_contract_blocks(final_output)
    final_output = _normalize_roadshow_pattern_ids(final_output)
    final_output = _ensure_formal_page_content(final_output)
    final_output, normalization_note = _normalize_competition_manuscript_structure(
        final_output,
        effective_num_pages,
        detail_level,
    )
    final_output = remove_disallowed_figure_tokens(final_output, paper)
    final_output = apply_locked_facts_to_manuscript(final_output, locked_facts)
    if normalization_note:
        logger.info("Roadshow review local normalization: %s", normalization_note)
    final_error = _manuscript_validation_error(final_output, paper, effective_num_pages, detail_level)
    if not final_error:
        final_error = _visual_plan_validation_error(final_output)
    manuscript_error = _manuscript_validation_error(manuscript, paper, effective_num_pages, detail_level)
    if not manuscript_error:
        manuscript_error = _visual_plan_validation_error(manuscript)
    if final_error and not manuscript_error:
        logger.warning("Roadshow review changed manuscript structure; keeping Pass 3: %s", final_error)
        final_output = manuscript

    final_output = ensure_roadshow_manuscript_hard_requirements(
        final_output,
        expected_pages=effective_num_pages,
        allow_cover_images=image2_mode,
    )
    hard_quality_report = evaluate_roadshow_manuscript_quality(
        final_output,
        expected_pages=effective_num_pages,
        allow_cover_images=image2_mode,
        require_notes=False,
    )
    _debug_write_text(
        debug_dir,
        "roadshow_hard_quality_report.json",
        json.dumps(hard_quality_report, ensure_ascii=False, indent=2),
    )
    if hard_quality_report.get("needs_repair"):
        if on_progress:
            on_progress("正在按质量规则复核讲稿、首页和证据口径", 0.285)
        repair_instruction = build_roadshow_quality_repair_instruction(hard_quality_report)
        repair_messages = [
            LLMMessage.system(MANUSCRIPT_SYSTEM_PROMPT),
            LLMMessage.user(
                f"{repair_instruction}\n\n"
                "## Current manuscript\n\n"
                f"{final_output}\n\n"
                "只输出修订后的完整 manuscript。"
            ),
        ]
        _debug_write_messages(debug_dir, "roadshow_hard_quality_repair_prompt.md", repair_messages)
        repair_response = await llm.chat(
            repair_messages,
            model,
            temperature=0.18,
            max_tokens=ROADSHOW_MAX_TOKENS,
        )
        _debug_write_text(debug_dir, "roadshow_hard_quality_repair_response.md", repair_response.content)
        repaired_output = _extract_manuscript_from_review(repair_response.content, final_output)
        repaired_output = _normalize_roadshow_field_labels(repaired_output)
        repaired_output = _normalize_inline_contract_blocks(repaired_output)
        repaired_output = _normalize_roadshow_pattern_ids(repaired_output)
        repaired_output = _ensure_formal_page_content(repaired_output)
        repaired_output, _ = _normalize_competition_manuscript_structure(
            repaired_output,
            effective_num_pages,
            detail_level,
        )
        repaired_output = remove_disallowed_figure_tokens(repaired_output, paper)
        repaired_output = apply_locked_facts_to_manuscript(repaired_output, locked_facts)
        repaired_output = ensure_roadshow_manuscript_hard_requirements(
            repaired_output,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
        )
        repaired_structure_error = _manuscript_validation_error(
            repaired_output,
            paper,
            effective_num_pages,
            detail_level,
        )
        if not repaired_structure_error:
            repaired_structure_error = _visual_plan_validation_error(repaired_output)
        repaired_quality_report = evaluate_roadshow_manuscript_quality(
            repaired_output,
            expected_pages=effective_num_pages,
            allow_cover_images=image2_mode,
            require_notes=False,
        )
        _debug_write_text(
            debug_dir,
            "roadshow_hard_quality_repaired_report.json",
            json.dumps(repaired_quality_report, ensure_ascii=False, indent=2),
        )
        if not repaired_structure_error and repaired_quality_report.get("passed"):
            final_output = repaired_output
            hard_quality_report = repaired_quality_report
        else:
            logger.warning(
                "Roadshow hard quality repair kept original: structure=%s quality=%s",
                repaired_structure_error,
                repaired_quality_report.get("findings"),
            )

    if not hard_quality_report.get("passed"):
        messages = [
            str(item.get("message") or item.get("rule"))
            for item in hard_quality_report.get("findings", [])
            if item.get("severity") == "error"
        ]
        raise ValueError("路演内容质量校验未通过：" + "；".join(messages[:3]))

    try:
        script_skill_result = await enhance_roadshow_script(
            llm=llm,
            model=model,
            manuscript=final_output,
            project_dir=project_dir_from_debug_dir(debug_dir),
            debug_dir=debug_dir,
            material_analysis=material_analysis,
            outline_plan=outline_plan,
            run_of_show_plan=run_of_show_plan,
            contestant_plan=contestant_plan,
            target_duration_sec=3600,
            target_chars=8000,
            on_progress=on_progress,
        )
        enhanced_error = _manuscript_validation_error(
            script_skill_result.manuscript,
            paper,
            effective_num_pages,
            detail_level,
        )
        if not enhanced_error:
            final_output = script_skill_result.manuscript
            _debug_write_text(
                debug_dir,
                "roadshow_script_skill_quality_report.json",
                json.dumps(script_skill_result.quality_report, ensure_ascii=False, indent=2),
            )
        else:
            logger.warning("Roadshow script skill output kept original manuscript: %s", enhanced_error)
    except Exception as exc:
        logger.warning("Roadshow script skill failed; keeping original speaker notes: %s", exc)

    _debug_write_text(debug_dir, "roadshow_final_manuscript.md", final_output)
    if on_progress:
        on_progress("路演内容稿已完成", 0.29)
    return final_output
