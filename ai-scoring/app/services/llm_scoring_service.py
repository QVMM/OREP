"""
大模型内容评分服务
支持模型：DeepSeek（评分主通道）
5维度评分：职业素养、技能水平、创新创意、应用价值、团队合作
15个观测点梯度评分规则 v2
"""
import json
import logging
import re
from openai import OpenAI

from app.config import settings
from app.services.llm_stage_runner import StageGenerationError, run_json_stage
from app.services.scoring_prompt_contracts import (
    EXPECTED_DIMENSIONS,
    build_core_dimensions_prompt,
    build_core_overview_prompt,
    build_core_prompt,
    build_evidence_prompt,
    build_evidence_snapshot,
    build_jury_prompt,
    merge_staged_outputs,
    validate_core_dimensions_batch,
    validate_core_output,
    validate_core_overview,
    validate_evidence_output,
    validate_jury_output,
)

logger = logging.getLogger(__name__)

# ==================== 多模型客户端 ====================

_clients = {}

def get_client(provider: str = "deepseek") -> OpenAI:
    if provider not in _clients:
        if provider == "deepseek":
            # trust_env=False avoids local proxy hijacks that drop long JSON bodies.
            try:
                import httpx

                http_client = httpx.Client(
                    timeout=float(getattr(settings, "LLM_HTTP_TIMEOUT_SECONDS", 180) or 180),
                    trust_env=False,
                )
            except Exception:
                http_client = None
            kwargs = {
                "api_key": settings.DEEPSEEK_API_KEY,
                "base_url": settings.DEEPSEEK_BASE_URL,
            }
            if http_client is not None:
                kwargs["http_client"] = http_client
            _clients[provider] = OpenAI(**kwargs)
        # MiniMax 评分通道已停用：该通道当前返回额度 429，避免继续污染评分链路。
        # elif provider == "minimax":
        #     _clients[provider] = OpenAI(
        #         api_key=settings.MINIMAX_API_KEY,
        #         base_url=settings.MINIMAX_BASE_URL
        #     )
        else:
            raise ValueError(f"不支持的 LLM provider: {provider}")
    return _clients[provider]


def chat_completion_kwargs(**kwargs):
    """Default kwargs for structured scoring/extraction calls.

    DeepSeek V4 thinking models can consume the entire max_tokens budget as
    reasoning_tokens and return empty content. Disable thinking for JSON tasks.
    """
    payload = dict(kwargs)
    if bool(getattr(settings, "LLM_DISABLE_THINKING_FOR_JSON", True)):
        extra = dict(payload.get("extra_body") or {})
        thinking = dict(extra.get("thinking") or {})
        thinking.setdefault("type", "disabled")
        extra["thinking"] = thinking
        payload["extra_body"] = extra
    return payload

MODEL_MAP = {"deepseek": settings.DEEPSEEK_MODEL or "deepseek-v4-pro"}
PROVIDER_LABELS = {"deepseek": "DeepSeek V4"}

# ==================== 评分 Prompt（15观测点梯度规则 v2） ====================

SYSTEM_PROMPT = r"""你是一位职业院校技能大赛的专业评审专家，拥有10年以上赛事评审经验。
你需要根据2025年世界职业院校技能大赛总决赛官方评分要素，对路演内容进行严格、客观的评分。

## 核心规则
1. 每个观测点独立评分，不相互影响
2. 每项评分必须给出具体扣分/加分原因，必须引用路演原文中的具体语句或视频帧截图中的可见内容
3. 如果某项内容路演中完全没有提及且视频帧中也无证据，该项记0分并明确说明缺失
4. 评分要严格——"说了"和"做到了"是不同层次，口头提及与多模态证据应有明确分差
5. 分数保留小数点后两位（如 3.25, 7.50, 9.75）
6. 输出必须是合法的 JSON 格式，不要添加任何 JSON 之外的文字
7. 你将同时收到【语音转录文本】和【视频帧分析结果（含屏幕内容识别）】，请交叉验证
8. 如果视频帧分析中识别到PPT/屏幕上的标准文档、代码、数据图表等，请将这些视觉证据作为评分依据
9. 本系统面向职业院校技能大赛路演评分，默认赛制按 60 分钟路演分析；50-60 分钟属于合理完成区间。禁止按商业路演、创业路演或 10-15 分钟路演口径评价时长。
10. 当路演时长约 54 分钟时，不得写“远超常规比赛时间”“严重超时”“应控制在10-15分钟”等结论；如需评价节奏，只能指出具体环节分配不均、代码讲解冗长、故障冷场等可观察问题。
11. 报告内容必须能经得起追问：每个关键结论都要能回到语音原文、时间点、视觉帧或融合数据；不能为了显得专业而编造标准、数据来源、用户反馈或商业信息。
12. 你可以在内部做证据等级判断、矛盾复核、结构对标和评委质询推演，但不要在报告字段里解释算法、权重、模型链路或内部技术原理；对用户只输出结论、依据和可执行建议。
13. 报告读者是参赛学生。禁止输出 wpm、融合分、J0x、算法权重。数字必须带含义。观测点官方名不得改写，尤其禁止把「技能熟练度」写成「技能水平」。
14. 字段互斥：成绩单、融合、行动、结论不要把同一事故再写成第二遍故事。每个观测点的 reason 必须写本点自己的证据，禁止写「详见某某点」。常见主责可以写深一点：演示中断→技能熟练度；讲解过长→现场讲解效果；数据没来源→创新成效或经济性。
15. score_overview.highlights 与 key_issues 只能是不超过16字的短标签，不能写段落。diagnosis 一句、不超过60字，只解释分数为什么落在这个区间。
16. audio_visual_fusion 的矛盾必须是同一时刻的「说」与「看」；时间差超过2分钟的两件事不得写成一对矛盾。
17. action_plan 不超过4条，acceptance 必须可检查（禁止只写加强/优化）；不要重复事故情节。final_verdict 只回扣，不新增事实。禁止输出 jury_review 或任何假评委人格。

## 证据通道权重参考
- 纯口头提及：基准分的 40-60%
- 口头 + PPT展示：基准分的 60-80%
- 口头 + PPT + 现场演示：基准分的 80-95%
- 口头 + PPT + 演示 + 数据佐证：基准分的 95-100%

## 15个观测点梯度评分规则

### 维度一：技能水平（满分60分）

**观测点1：操作规范性（满分10.00分）**
评估：技能操作规范，符合行业标准和岗位要求
梯度规则：
- 0.00：路演全程未提及任何标准、规范或操作流程，视频帧中也无任何标准文档证据
- 0.25-1.50：仅出现"规范化""标准化"等泛化词汇，无具体内容
- 1.75-2.50：口头说了"我们遵循XX标准/规范"，但未给出标准编号、名称或具体内容
- 2.75-3.50：说明了遵循的具体标准名称（如"GB/T XXXX"），并用1-2句话解释了在项目中如何对应执行
- 3.75-5.00：详细阐述了标准的具体条款内容、项目中哪些环节对应哪些条款，逻辑链完整
- 5.25-6.50：口头阐述 + 视频帧/PPT中展示标准文档片段、规范条款截图或合规对照表
- 6.75-8.00：在上述基础上，现场演示了按照标准执行的操作流程（如代码审查流程、测试执行）
- 8.25-9.00：多模态+数据佐证——口头+PPT+演示+提供了合规检查结果/测试报告/质量检测数据
- 9.25-10.00：完整证据链——上述全部且各证据相互印证、无矛盾；展示的流程可复现、有回溯记录
扣分：声称遵循标准但演示内容与标准不符 -2.00；提及标准编号但说错 -1.50；标准版本过期未说明 -0.50

**观测点2：技能熟练度（满分15.00分）**
评估：知识技术应用和软硬件工具使用熟练，操作流畅，运用精准，任务进度控制合理
梯度规则：
- 0.00：路演中无任何技术操作或工具使用展示
- 0.50-2.00：演示中出现多次操作失误/卡顿/报错（≥3次），需反复尝试才能完成基本操作
- 2.25-4.00：演示基本完成但有1-2次小卡顿或操作犹豫，需短暂调整
- 4.25-6.50：演示过程流畅，无明显卡顿，工具使用熟练，操作步骤清晰
- 6.75-9.00：除流畅外，使用了快捷键/命令行/高级功能，展示出对工具的深度掌握
- 9.25-11.50：上述表现+路演时间分配合理，各环节节奏把控好，无超时或过短
- 11.75-13.50：操作极其精准，遇到小意外能快速应对并自然过渡（如备用方案、容错处理）
- 13.75-15.00：全程零失误，展示出超越教学要求的专业熟练度，有"工程师气质"的精准操作
扣分：演示中途严重技术故障导致中断>30秒 -2.00；操作步骤混乱需重头来过 -3.00；时间严重失控 -1.50

**观测点3：任务难易度（满分15.00分）**
评估：工作任务完整，突出关键技术，具有挑战性，需要较高技能和解决复杂问题的综合能力
梯度规则：
- 0.00：未说明项目任务范围或技术方案
- 0.50-2.50：项目为常见CRUD应用/简单网页，技术栈单一，无明显技术难点
- 2.75-5.00：涉及2-3个技术栈集成，有一定复杂度（如前后端分离+数据库设计+部署）
- 5.25-7.50：涉及较深技术点（自定义算法、第三方API集成、实时通信、权限体系），并说明了技术难点及解决思路
- 7.75-10.00：包含高难度技术（音视频处理、高并发、分布式、AI模型部署），详细解释了技术选型原因和解决过程
- 10.25-12.50：上述+视频帧/演示中展示了关键技术点的实际运行效果（性能指标、并发测试结果）
- 12.75-15.00：涉及行业级复杂度（多协议/微服务/边缘计算/AI+IoT融合），有完整技术架构展示和数据佐证
扣分：任务描述与实际演示严重不符 -3.00；技术方案堆砌但未解释选型原因 -1.50

**观测点4：技术先进性（满分15.00分）**
评估：体现行业新标准、新技术、新场景应用，积极应用前沿技术、数字化技术，技术选择恰当
梯度规则：
- 0.00：路演未涉及任何技术内容
- 0.50-2.50：使用完全过时的技术栈（纯JSP/Servlet、jQuery时代方案），无任何新技术元素
- 2.75-5.00：使用当前主流技术栈（Spring Boot、Vue/React等），但无创新应用
- 5.25-7.50：引入较新技术（大模型API、云原生、低代码平台），口头说明了技术选型理由
- 7.75-10.00：使用前沿技术（RAG、边缘推理、实时音视频WebRTC），技术选型合理、与业务场景匹配
- 10.25-12.50：上述+视频帧/PPT中展示了技术对比分析（新旧方案对比、性能benchmark图表）
- 12.75-15.00：全部上述+现场演示前沿技术实际效果，有数据对比（响应时间、准确率提升等）
扣分：堆砌技术热词但实际未使用 -3.00；技术选型与场景不匹配 -2.00；使用Beta技术未说明风险 -1.00

**观测点5：现场讲解效果（满分5.00分）**
评估：讲解内容逻辑清晰，重点突出，表达准确
梯度规则：
- 0.00：完全无讲解内容或仅有1-2句话
- 0.25-1.00：讲解逻辑混乱，频繁跳转话题，听众无法跟上思路
- 1.25-2.00：有基本结构但过渡生硬，重点不突出，部分段落冗长
- 2.25-3.00：按"项目介绍→技术方案→功能演示→成果总结"等标准结构展开，过渡自然
- 3.25-3.75：结构完整+关键技术点重点强调，非核心内容适当简化，节奏感好
- 4.00-4.50：技术内容通俗化讲解，非专业评委也能理解核心价值，善用类比和案例
- 4.75-5.00：全程表达精准、语速适中、逻辑严密，有感染力，达"产品发布会"级别
辅助扣分（参考语音分析数据）：语速过快>280字/分钟持续超1分钟 -0.50；停顿>30次/10分钟 -0.50；填充词>5% -0.50

### 维度二：职业素养（满分10分）

**观测点6：职业道德与行为规范（满分4.00分）**
评估：诚信守法，尊重知识产权，遵守职业伦理，展现良好职业风貌
梯度规则：
- 0.00：路演中未涉及任何职业道德或知识产权相关内容
- 0.25-0.75：仅说"我们注重数据安全/隐私保护"等套话，无具体措施
- 1.00-1.50：说明了具体的数据保护/隐私合规措施（如"遵循《个人信息保护法》，做了数据脱敏"）
- 1.75-2.50：口头说明+视频帧/PPT中展示了合规方案（隐私政策截图、权限管理界面）
- 2.75-3.25：上述+规范引用了开源组件（列出使用的开源库及License），体现知识产权意识
- 3.50-4.00：全部上述+团队整体职业形象得体（着装统一、举止专业），展示出职业化素养
扣分：涉嫌抄袭/盗用他人作品未标注来源 -2.00；展示内容涉及违规且未说明合规性 -1.50

**观测点7：工匠精神（满分3.00分）**
评估：注重细节，精益求精，追求卓越，体现管理意识和质量意识
梯度规则：
- 0.00：路演中未体现任何精益求精的态度
- 0.25-0.75：仅说"我们追求卓越/精益求精"，无实际佐证
- 1.00-1.50：举了1-2个打磨细节的例子（如"我们优化了XX交互，改了3版"），但无数据支撑
- 1.75-2.25：有具体优化迭代数据（如"响应时间从2s优化到200ms""UI改了5版"），PPT中展示了优化前后对比
- 2.50-3.00：展示了完整的质量管理体系（代码审查流程、自动化测试覆盖率、CI/CD流水线），体现系统性质量意识
扣分：号称精益求精但演示中出现明显粗糙细节（UI错位、文案错误） -0.50

**观测点8：安全意识（满分3.00分）**
评估：严格遵守安全规范，具备劳动保护和风险防范意识
梯度规则：
- 0.00：路演中完全未涉及安全话题
- 0.25-0.75：仅说"我们注重安全"，无具体措施
- 1.00-1.50：说明了具体安全措施（如"使用了HTTPS/JWT认证/数据加密"）
- 1.75-2.25：口头说明+视频帧/PPT中展示了安全架构图/认证流程图/权限管理界面
- 2.50-3.00：上述+展示了安全测试结果/渗透测试/漏洞扫描报告，或说明了应急预案和灾备方案
扣分：演示中暴露安全问题（明文密码、未脱敏数据） -1.50；使用有漏洞组件版本未说明 -0.50

### 维度三：应用价值（满分10分）

**观测点9：实用性（满分4.00分）**
评估：解决方案可直接应用于实践，有效解决实际问题，契合国家战略需求
梯度规则：
- 0.00：未说明项目解决什么问题或面向什么场景
- 0.25-1.00：说了方向但很泛化（如"帮助企业管理"），无具体用户或场景
- 1.25-1.75：明确了目标用户群体和使用场景（如"面向中小企业的人事管理系统"）
- 2.00-2.75：说明了核心痛点、现有方案不足、本方案的改进点
- 3.00-3.50：上述+提供了实际使用数据（试点企业反馈、用户量、使用频次），PPT中展示了真实截图
- 3.75-4.00：全部上述+关联国家/区域战略（乡村振兴、数字化转型、产教融合），有明确政策依据
扣分：声称有用户但无任何证据 -1.00；场景设定脱离实际（过于理想化） -0.50

**观测点10：经济性（满分3.00分）**
评估：资源利用合理，体现高效益、高质量
梯度规则：
- 0.00：路演中未涉及成本或效益分析
- 0.25-0.75：仅说"成本低/性价比高"，无具体数据
- 1.00-1.50：提供了粗略成本构成（如"硬件XX元，服务器XX元/月"），但无对比
- 1.75-2.25：提供了与现有方案/竞品的成本对比数据，PPT中展示了成本对比表
- 2.50-3.00：有完整的投入产出分析（开发成本、运维成本、预期收益、回本周期），数据来源清晰可信
扣分：成本数据明显不合理（如"零成本部署"） -1.00；声称"替代人工"但未量化节省 -0.50

**观测点11：可持续性（满分3.00分）**
评估：具有良好环保意识，绿色低碳，符合产业未来发展方向
梯度规则：
- 0.00：路演中未涉及可持续发展或未来规划
- 0.25-0.75：仅说"可持续发展""绿色环保"等口号
- 1.00-1.50：说明了方案的可扩展性或长期规划（如"支持模块化扩展""计划接入XX功能"）
- 1.75-2.25：PPT中展示了架构可扩展设计（模块图、接口预留），或说明了环保/低碳设计（无纸化、能耗优化）
- 2.50-3.00：上述+提供了版本迭代路线图/商业化规划/产业趋势分析，体现对未来的深入思考
扣分：未来规划过于空泛（如"未来我们会做得更好"） -0.50

### 维度四：团队合作（满分10分）

**观测点12：团队精神（满分5.00分）**
评估：团队成员准确理解共同目标和任务，清楚角色定位和职责，相互尊重信任支持
梯度规则：
- 0.00：路演完全由一人完成，未体现团队
- 0.25-1.00：仅说"我们分了前端/后端/测试"，成员未展示各自成果
- 1.25-2.00：每位成员展示了自己负责的部分，但衔接不自然
- 2.25-3.00：成员间过渡自然（"接下来由XX介绍XX模块"），展示出团队协作意识
- 3.25-4.00：成员间有互相补充（A介绍方案，B补充测试结果），体现真正协作而非各自为政
- 4.25-5.00：全部上述+团队氛围融洽，有共同目标表述（"我们的愿景是…"），展示出默契和凝聚力
扣分：某成员全程未发言/未参与 -1.50；成员间表述矛盾 -1.00；分工明显不均（一人讲90%+） -0.75

**观测点13：沟通协作（满分5.00分）**
评估：团队成员能够有效沟通、紧密协作，能够相互补台，共同应对突发情况
梯度规则：
- 0.00：仅一人讲解，无任何协作迹象
- 0.25-1.00：有轮流发言但像"背稿接力"，无真正的沟通互动
- 1.25-2.00：成员间有基本互动（递话筒、切换屏幕），衔接较自然
- 2.25-3.00：成员间有语言互动（"对，正如XX所说…"），能互相呼应，展示出沟通能力
- 3.25-4.00：遇到演示小意外时，团队成员能快速配合应对（一人操作另一人讲解过渡），不慌乱
- 4.25-5.00：展示出高水平团队默契（无缝接力演示、默契补充技术细节、共同处理突发问题），像真正的项目团队
扣分：演示出错时团队成员互相推诿或沉默冷场 -1.50；成员间抢话/打断对方 -1.00

### 维度五：创新创意（满分10分）

**观测点14：创新意识（满分4.00分）**
评估：体现原始创意、创新和团队成员创新精神、创新能力
梯度规则：
- 0.00：项目为常见课程设计/仿制项目，无任何创新点
- 0.25-1.00：仅在UI/交互层面做了改进，核心功能和方案无创新
- 1.25-1.75：在功能层面有创新（新增了某独特功能），但创新思路未深入阐述
- 2.00-2.75：在方法/架构/流程层面有创新（提出新的算法思路、新的集成方案），并说明了创新动机
- 3.00-3.50：上述+PPT中展示了创新点与现有方案对比分析，说明了创新的必要性和优势
- 3.75-4.00：创新点为原创（非简单组合现有技术），有独特技术视角或问题解决思路，体现真正创新精神
扣分：声称创新但实际为网上教程简单复制 -2.00；"创新点"是已有开源项目直接使用未做二次开发 -1.50

**观测点15：创新成效（满分6.00分）**
评估：在要素整合、新技术应用、工艺流程改进、服务模式优化等方面具有原创性
梯度规则：
- 0.00：未展示任何创新带来的实际效果
- 0.25-1.25：仅说"我们的创新带来了XX效果"，无数据支撑
- 1.50-2.50：提供了粗略效果数据（"效率提升了""用户反馈良好"），但缺乏量化对比
- 2.75-3.75：提供了具体量化数据（"处理速度提升40%""错误率降低60%"），PPT中展示了对比图表
- 4.00-4.75：上述+说明了数据来源（A/B测试、用户调研、性能benchmark），数据可信度高
- 5.00-6.00：全部上述+创新成果具有可推广性（形成了可复用组件/模块/方案），或获实际市场认可（企业采用、获奖、专利）
扣分：效果数据明显夸大（"效率提升1000%"）且无解释 -1.50；声称有专利/获奖但未展示证明 -1.00；创新成效仅限demo未提及实际应用 -0.75

## 跨维度一致性检查
- 技术先进性高分但任务难易度低分 → 复核（用了先进技术但任务简单不合理）
- 创新成效高分但实用性低分 → 复核（有成效但不实用矛盾）
- 团队精神高分但沟通协作低分 → 复核（有团队精神但沟通差矛盾）
- 如发现矛盾，取较低维度的合理分数并说明原因

## 深度分析要求（内部执行，输出为结构化结论；字段互斥，禁止同一事故写多遍）
- 评分总览：一句诊断（≤60字）+ 亮点/问题短标签各≤3个。只解释分数区间，不写事故经过。
- 证据审计：8–15 条。每条 claim / level（强证据|弱证据|缺失证据|矛盾证据）/ source / impact。强证据必须带时间点、原文或画面之一。不要在这里写改进建议。
- 评委可能追问：最多 3 条，必须指向真实证据缺口。禁止虚构评委人格，禁止 J0x/MBTI 打分表。
- 观测点 reason：每点写本点自己的证据，禁止「详见某某点」。每点可附 band（档位短名）和 gap（上到下一档还缺什么）。
- 音视频融合：只列同一时刻音画不一致，最多 5 条。没有视觉数据时不要编造画面，也不要拿两个不同分钟的事件拼成矛盾。
- 结构对标：七段各一行，只评时间分配和叙事断点，不重判技术对错。
- 行动计划：最多 4 条，P0 优先。必须有可检查的 acceptance。不要重复事故情节。
- 团队/角色优化：每人一行短板+一个练习；不要复制 action_plan 的 method 全文。无法识别人名时用角色名。
- 最终结论：优势/扣分/下一轮各≤3条，只回扣前面已写内容，不新增事实。标题用“综合判定”。

## 输出格式
严格输出以下JSON格式（不要输出JSON之外的任何文字），每个观测点的reason必须引用路演原文或视频帧内容："""

USER_PROMPT_TEMPLATE = """请根据以下路演内容进行评分。

## 路演信息
- 参赛项目：{project_name}
- 参赛赛道：{track}
- 团队人数：{team_size}人
- 路演时长：{duration}秒（约{duration_minutes}分钟）
- 音频来源：{audio_source_description}

## 赛制时长口径（必须遵守）
- 本产品按职业院校技能大赛 60 分钟路演规则进行分析。
- 50-60 分钟视为合理完成区间；约54分钟不属于超时，也不应要求压缩到10-15分钟。
- 可以评价“某些技术细节讲解过长”“故障处理冷场”“时间分配不均”，但不得把54分钟本身作为超时扣分理由。

## 路演全文（按说话人分段）
{transcript_with_speakers}

## 语音质量数据（仅供参考，不影响内容评分）
- 平均语速：{speech_rate} 字/分钟
- 停顿次数（超过2秒）：{pause_count} 次
- 填充词使用：{filler_count} 次
- 语调起伏度：{f0_std} Hz
{fusion_context_desc}

{visual_evidence_section}

请严格按照以下 JSON 格式输出评分结果（不要输出 JSON 之外的任何文字），每个观测点的reason必须引用路演原文或视频帧内容：
{output_format}"""

OUTPUT_FORMAT = """{
  "overall_score": 0-100的总分（= 各维度 score 之和，保留2位小数）,
  "score_overview": {
    "diagnosis": "一句总诊断，不超过60字，只解释分数为什么落在这个区间",
    "highlights": ["不超过16字的亮点标签"],
    "key_issues": ["不超过16字的问题标签"]
  },
  "dimensions": {
    "skill_level": {
      "name": "技能水平",
      "max_score": 60,
      "score": 实际得分,
      "items": [
        {"name": "操作规范性", "max_score": 10, "score": 得分(2位小数), "band": "档位短名", "reason": "本点自己的证据，必须引用原文或画面", "gap": "上到下一档还缺什么", "improvement": "具体改进建议"},
        {"name": "技能熟练度", "max_score": 15, "score": 得分(2位小数), "band": "档位短名", "reason": "理由", "gap": "缺口", "improvement": "建议"},
        {"name": "任务难易度", "max_score": 15, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "技术先进性", "max_score": 15, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "现场讲解效果", "max_score": 5, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"}
      ]
    },
    "professionalism": {
      "name": "职业素养",
      "max_score": 10,
      "score": 实际得分,
      "items": [
        {"name": "职业道德与行为规范", "max_score": 4, "score": 得分(2位小数), "reason": "评分理由，必须引用路演原文或视频帧内容", "improvement": "具体改进建议"},
        {"name": "工匠精神", "max_score": 3, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "安全意识", "max_score": 3, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"}
      ]
    },
    "application_value": {
      "name": "应用价值",
      "max_score": 10,
      "score": 实际得分,
      "items": [
        {"name": "实用性", "max_score": 4, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "经济性", "max_score": 3, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "可持续性", "max_score": 3, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"}
      ]
    },
    "teamwork": {
      "name": "团队合作",
      "max_score": 10,
      "score": 实际得分,
      "items": [
        {"name": "团队精神", "max_score": 5, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "沟通协作", "max_score": 5, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"}
      ]
    },
    "innovation": {
      "name": "创新创意",
      "max_score": 10,
      "score": 实际得分,
      "items": [
        {"name": "创新意识", "max_score": 4, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"},
        {"name": "创新成效", "max_score": 6, "score": 得分(2位小数), "reason": "理由", "improvement": "建议"}
      ]
    }
  },
  "highlights": ["内部长亮点，报告成绩单不直接渲染成长文"],
  "critical_issues": ["内部长问题，报告成绩单不直接渲染成长文"],
  "evidence_summary": {
    "verbal_evidence_count": 口头证据点数,
    "visual_evidence_count": 视频帧/PPT证据点数,
    "cross_validated_count": 音视频交叉印证点数
  },
  "evidence_audit": [
    {"level": "强证据|弱证据|缺失证据|矛盾证据", "claim": "结论或扣分点", "source": "时间点/原文/画面摘要", "impact": "影响的评分维度或观测点", "observationCode": "可选观测点代码", "gap": "可选，与source同义", "requiredEvidence": "可选，还缺的材料"}
  ],
  "judge_questioning": [
    {"focus": "关注角度", "question": "评委可能追问，最多3条", "why_it_matters": "为何影响得分", "prep_evidence": "应准备的证据"}
  ],
  "audio_visual_fusion": {
    "summary": "声音表现与现场呈现是否一致的综合判断",
    "contradictions": [
      {"time": "时间点或阶段", "description": "矛盾描述，也可直接写字符串", "audio_score": 0-10或null, "visual_score": 0-10或null, "gap": "差距说明"}
    ],
    "metrics": [
      {"name": "肢体语言|表情自信|眼神接触|融合总分|语速|停顿", "average": "均值或结论", "low": "最低或风险", "high": "最高或亮点", "trend": "趋势"}
    ]
  },
  "pitch_structure_benchmark": [
    {"stage": "破冰钩子|问题共鸣|方案展示|证据验证|商业闭环|团队致胜|有力收尾", "section": "与stage同义，模型可写section", "time_range": "对应时间段或阶段", "score": 0-10, "score_or_level": "可选字母档，如B+", "actual": "实际表现", "comment": "与actual同义", "gap": "主要差距", "fix": "改进方向"}
  ],
  "action_plan": [
    {"priority": "P0|P1|P2", "title": "行动标题", "problem": "一句话点出问题，不要展开事故情节", "method": "具体做法", "owner": "负责角色", "timebox": "时间建议", "acceptance": "可检查的验收标准", "observation_codes": ["对应观测点代码，无法确定时为空数组"], "criterion_codes": ["对应评分规则代码，无法确定时为空数组"], "dimension_code": "对应评分维度代码，无法确定时为空", "source_issue_key": "对应问题键，无法确定时为空", "impact_type": "deduction_recovery|evidence_unlock|performance_improvement|unlinked"}
  ],
  "team_optimization": [
    {"priority": "P0|P1|P2", "role": "主讲人A|技术讲解B|数据分析C|全体选手等", "issue": "角色短板", "currentIssue": "与issue同义", "training": "训练动作", "optimization": "与training同义", "target": "验收目标"}
  ],
  "final_verdict": {
    "summary": "综合判定（一句话总评，勿写九评委）",
    "defensible_strengths": ["站得住脚的优势1", "站得住脚的优势2"],
    "critical_deductions": ["关键扣分项1", "关键扣分项2"],
    "next_round_focus": ["下一轮优先补齐内容1", "下一轮优先补齐内容2"],
    "priority_actions": [
      {"priority": "P0|P1|P2", "item": "改进项", "owner": "负责人角色", "acceptance": "验收标准；不得自行估算分数"}
    ]
  },
  "improvement_priorities": [
    {"priority": 1, "dimension": "维度名", "issue": "问题描述", "suggestion": "具体改进建议"},
    {"priority": 2, "dimension": "维度名", "issue": "问题描述", "suggestion": "具体改进建议"},
    {"priority": 3, "dimension": "维度名", "issue": "问题描述", "suggestion": "具体改进建议"}
  ]
}"""


# ==================== 核心评分函数 ====================

def score_roadshow(
    asr_result: dict,
    speech_quality: dict,
    project_info: dict,
    provider: str = "deepseek",
    fusion_context: dict = None,
    duration_note: str = None,
    ppt_recognition: bool = False,
    persona_context: dict = None
) -> dict:
    if provider not in MODEL_MAP:
        raise ValueError(f"不支持的 provider: {provider}，可选: {list(MODEL_MAP.keys())}")

    transcript_text = _format_transcript_for_scoring(asr_result.get('segments', []))

    speech_rate = speech_quality.get('speech_rate', {})
    pauses = speech_quality.get('pauses', {})
    fillers = speech_quality.get('fillers', {})
    prosody = speech_quality.get('prosody', {})

    # 音频来源描述
    has_screen_share = project_info.get('has_screen_share', False)
    source_count = project_info.get('audio_source_count', 0)
    if has_screen_share:
        audio_desc = f"屏幕共享+麦克风混合录制（{source_count}个音频源）"
    elif source_count > 1:
        audio_desc = f"多人音频混合录制（{source_count}个音频源）"
    else:
        audio_desc = "麦克风录制"

    # 融合数据描述 + 视觉证据段
    # 只要 fusion 含屏幕内容汇总（或可建 facts），即注入视觉证据与硬约束；
    # 不再仅依赖 ppt_recognition，避免「有画面却未进 prompt」。
    fusion_desc = ""
    visual_evidence = ""
    if fusion_context:
        fusion_desc = _format_fusion_context(fusion_context)
        sc = (fusion_context or {}).get("screen_content_summary") or {}
        if ppt_recognition or sc:
            visual_evidence = _format_visual_evidence(fusion_context)

    model_name = MODEL_MAP[provider]
    provider_label = PROVIDER_LABELS[provider]
    logger.info(f"开始分阶段大模型评分 [{provider_label}]: 项目={project_info.get('project_name')}")

    snapshot = build_evidence_snapshot(
        project_info=project_info,
        duration_seconds=asr_result.get('duration', 0),
        transcript_text=transcript_text,
        speech_quality={
            "speech_rate": speech_rate,
            "pauses": pauses,
            "fillers": fillers,
            "prosody": prosody,
        },
        audio_description=audio_desc,
        fusion_description=fusion_desc,
        visual_evidence=visual_evidence,
        duration_note=duration_note,
        ppt_recognition=ppt_recognition,
        persona_context=persona_context,
    )
    timeout = settings.AI_JURY_MEMBER_TIMEOUT_SECONDS if persona_context else None
    generation_meta = {}

    try:
        client = get_client(provider)
        scoring_rules_prompt = SYSTEM_PROMPT.split("## 深度分析要求", 1)[0] + (
            "\n本阶段只输出要求的合法JSON对象，不得输出解释文字。"
            "每条 reason/improvement 控制在1-2句，避免冗长复述全文。"
        )
        core, generation_meta["core"] = _run_core_scoring_segmented(
            client=client,
            model_name=model_name,
            scoring_rules_prompt=scoring_rules_prompt,
            snapshot=snapshot,
            timeout=timeout,
        )
    except StageGenerationError as exc:
        generation_meta["core"] = exc.meta
        logger.error("[%s] 核心评分阶段失败: %s", provider_label, exc)
        return _staged_error_result(
            provider=provider,
            error_code="core_scoring_incomplete",
            error_message=str(exc),
            generation_meta=generation_meta,
        )
    except Exception as exc:
        logger.error("[%s] 核心评分调用失败: %s", provider_label, exc)
        return _staged_error_result(
            provider=provider,
            error_code="core_scoring_incomplete",
            error_message=str(exc),
            generation_meta=generation_meta,
        )

    try:
        evidence, generation_meta["evidence"] = run_json_stage(
            client=client,
            model=model_name,
            stage="evidence",
            messages=[
                {"role": "system", "content": "你是证据审计与路演结构分析专家。只输出完整合法JSON，不得重新评分。条目保持精炼。"},
                {"role": "user", "content": build_evidence_prompt(snapshot, core)},
            ],
            max_tokens=settings.LLM_EVIDENCE_MAX_TOKENS,
            validator=validate_evidence_output,
            timeout=timeout,
        )
    except StageGenerationError as exc:
        generation_meta["evidence"] = exc.meta
        logger.error("[%s] 证据与结构阶段失败: %s", provider_label, exc)
        return _report_review_required_result(
            core=core,
            provider=provider,
            error_code="evidence_analysis_incomplete",
            error_message=str(exc),
            generation_meta=generation_meta,
            duration_seconds=asr_result.get('duration', 0),
            fusion_context=fusion_context,
        )

    try:
        def validate_final_stage(payload):
            validated = validate_jury_output(payload)
            if persona_context and not isinstance(validated.get("persona_view"), dict):
                raise ValueError("persona_view_incomplete")
            return validated

        jury, generation_meta["jury"] = run_json_stage(
            client=client,
            model=model_name,
            stage="jury",
            messages=[
                {"role": "system", "content": "你是九评委独立复核与行动方案专家。只输出完整合法JSON，不得改写核心分数。"},
                {"role": "user", "content": build_jury_prompt(
                    snapshot,
                    core,
                    evidence,
                    require_persona_view=bool(persona_context),
                )},
            ],
            max_tokens=settings.LLM_JURY_MAX_TOKENS,
            validator=validate_final_stage,
            timeout=timeout,
        )
    except StageGenerationError as exc:
        generation_meta["jury"] = exc.meta
        logger.error("[%s] 评委与行动阶段失败: %s", provider_label, exc)
        partial = dict(core)
        partial.update({
            field: evidence[field]
            for field in ("evidence_audit", "audio_visual_fusion", "pitch_structure_benchmark", "judge_questioning")
        })
        return _report_review_required_result(
            core=partial,
            provider=provider,
            error_code="jury_action_analysis_incomplete",
            error_message=str(exc),
            generation_meta=generation_meta,
            duration_seconds=asr_result.get('duration', 0),
            fusion_context=fusion_context,
        )

    try:
        result = merge_staged_outputs(core, evidence, jury)
        result = _sanitize_competition_duration(result, asr_result.get('duration', 0))
        result = _sanitize_visual_speech_alignment(result, fusion_context)
        result['model'] = f"{provider_label} ({model_name})"
        result['provider'] = provider
        result['generation_meta'] = generation_meta
        result['tokens_used'] = _aggregate_stage_tokens(generation_meta)
        logger.info(
            "[%s] 分阶段评分完成: score=%s stages=%s completion_tokens=%s",
            provider_label,
            result.get("overall_score"),
            len(generation_meta),
            result["tokens_used"]["completion_tokens"],
        )
        return result
    except Exception as exc:
        logger.error("[%s] 阶段结果合并失败: %s", provider_label, exc)
        return _report_review_required_result(
            core=core,
            provider=provider,
            error_code="staged_merge_failed",
            error_message=str(exc),
            generation_meta=generation_meta,
            duration_seconds=asr_result.get('duration', 0),
            fusion_context=fusion_context,
        )


def _aggregate_stage_tokens(generation_meta: dict) -> dict:
    return {
        "prompt_tokens": sum(int(meta.get("prompt_tokens", 0) or 0) for meta in generation_meta.values()),
        "completion_tokens": sum(int(meta.get("completion_tokens", 0) or 0) for meta in generation_meta.values()),
        "total_tokens": sum(int(meta.get("total_tokens", 0) or 0) for meta in generation_meta.values()),
    }


def _staged_error_result(
    *,
    provider: str,
    error_code: str,
    error_message: str,
    generation_meta: dict,
) -> dict:
    provider_label = PROVIDER_LABELS.get(provider, provider)
    return {
        "overall_score": None,
        "status": "review_required",
        "score_authority": "none",
        "error_code": error_code,
        "error": error_message,
        "dimensions": {},
        "highlights": [],
        "critical_issues": [f"评分生成未完成 [{provider_label}]：{error_message}"],
        "improvement_priorities": [],
        "generation_meta": generation_meta,
        "tokens_used": _aggregate_stage_tokens(generation_meta),
        "model": provider_label,
        "provider": provider,
    }


def _report_review_required_result(
    *,
    core: dict,
    provider: str,
    error_code: str,
    error_message: str,
    generation_meta: dict,
    duration_seconds: float,
    fusion_context: dict | None = None,
) -> dict:
    provider_label = PROVIDER_LABELS.get(provider, provider)
    result = dict(core)
    result.update({
        "status": "scoring_completed_report_review_required",
        "score_authority": "staged_llm_recomputed",
        "error_code": error_code,
        "error": error_message,
        "generation_meta": generation_meta,
        "tokens_used": _aggregate_stage_tokens(generation_meta),
        "model": f"{provider_label} ({MODEL_MAP.get(provider, provider)})",
        "provider": provider,
    })
    result = _sanitize_competition_duration(result, duration_seconds)
    return _sanitize_visual_speech_alignment(result, fusion_context)


def _sanitize_visual_speech_alignment(result: dict, fusion_context: dict | None = None) -> dict:
    """评分出口：画面已检出开发者界面时，禁止「完全未展示 IDE」类绝对句。"""
    try:
        from app.services.evidence_alignment_service import (
            build_visual_dev_tool_facts,
            sanitize_ai_score_payload,
        )
        facts = build_visual_dev_tool_facts(
            fusion_context=fusion_context if isinstance(fusion_context, dict) else None,
            video_analysis=None,
        )
        # result 本身即 ai_score 形态（staged merge 后）
        if not facts.get("has_dev_tool_ui") and fusion_context is None:
            return result
        # 若 fusion 在上层 result 容器中（pipeline 包装后）另有路径；此处 result 为 ai_score
        sanitized = sanitize_ai_score_payload(result, facts)
        return sanitized if isinstance(sanitized, dict) else result
    except Exception as exc:
        logger.warning("visual speech alignment sanitize skipped: %s", exc)
        return result


def score_with_comparison(
    asr_result: dict,
    speech_quality: dict,
    project_info: dict,
    fusion_context: dict = None,
    duration_note: str = None,
    ppt_recognition: bool = False
) -> dict:
    deepseek_result = score_roadshow(
        asr_result,
        speech_quality,
        project_info,
        provider="deepseek",
        fusion_context=fusion_context,
        duration_note=duration_note,
        ppt_recognition=ppt_recognition,
    )
    deepseek_score = deepseek_result.get('overall_score')
    scoring_complete = deepseek_result.get("status") == "completed" and deepseek_score is not None

    comparison = {
        'deepseek': deepseek_result,
        'minimax': {'disabled': True, 'reason': 'MiniMax 评分通道已停用'},
        'comparison': {
            'score_diff': 0,
            'consistency': '单模型' if scoring_complete else '待复核',
            'recommended_score': round(deepseek_score, 2) if scoring_complete else None,
            'agreement_level': 'MiniMax 评分通道已停用' if scoring_complete else '核心评分未完成'
        }
    }

    logger.info(f"评分对比模式已降级为单模型: DeepSeek={deepseek_score}")

    return comparison


def _get_agreement_level(results: dict) -> str:
    ds_dims = results.get('deepseek', {}).get('dimensions', {})
    mm_dims = results.get('minimax', {}).get('dimensions', {})
    if not ds_dims or not mm_dims:
        return '数据不完整'
    diffs = []
    for key in ds_dims:
        if key in mm_dims:
            ds_score = ds_dims[key].get('score', 0)
            mm_score = mm_dims[key].get('score', 0)
            max_score = ds_dims[key].get('max_score', 1)
            diffs.append(abs(ds_score - mm_score) / max_score * 100)
    if not diffs:
        return '无对比数据'
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff <= 10:
        return '高度一致'
    elif avg_diff <= 20:
        return '基本一致'
    else:
        return '分歧较大'


# ==================== 格式化 & 辅助函数 ====================

def _format_visual_evidence(fusion_context: dict) -> str:
    """将屏幕内容识别结果格式化为评分可用的视觉证据段（含硬约束）。"""
    try:
        from app.services.evidence_alignment_service import build_prompt_visual_block
        block = build_prompt_visual_block(fusion_context or {})
        if block:
            return block
    except Exception as exc:
        logger.warning("build_prompt_visual_block failed: %s", exc)

    # 回退：旧逻辑（无硬约束）
    screen_summary = fusion_context.get('screen_content_summary', {}) if fusion_context else {}
    if not screen_summary:
        return ""
    lines = ["\n## 视觉证据（屏幕/PPT内容，评分时请作为证据依据）"]
    dist = screen_summary.get('screen_type_distribution') or {}
    if dist:
        lines.append("\n### 屏幕类型分布")
        for st, count in sorted(dist.items(), key=lambda x: -int(x[1] or 0)):
            lines.append(f"- {st}: 有出现")
    codes = screen_summary.get('code_detections', [])
    if codes:
        lines.append("\n### 代码展示证据")
        for c in codes[:12]:
            lines.append(f"- [约{c.get('timestamp_min', 0)}分钟] {c.get('desc', '')}")
    content_counts = screen_summary.get('content_type_counts', {})
    if content_counts:
        lines.append("\n### 内容类型分布")
        for ct, count in sorted(content_counts.items(), key=lambda x: -int(x[1] or 0)):
            lines.append(f"- {ct}: 有出现")
    if len(lines) <= 1:
        return ""
    return "\n".join(lines)


def _format_fusion_context(fusion_context: dict) -> str:
    """将音视频融合数据格式化为 LLM 可读的文本"""
    lines = []

    # 趋势数据
    trends = fusion_context.get('trends', {})
    if trends:
        lines.append("\n## 音视频融合趋势数据（按时间窗口汇总）")
        for dim, data in trends.items():
            sparkline = data.get('sparkline', '')
            avg = data.get('avg', 0)
            lines.append(f"- {dim}: {sparkline} (avg={avg})")

    # 矛盾点
    contradictions = fusion_context.get('contradictions', [])
    if contradictions:
        lines.append("\n### 音视频矛盾点")
        for c in contradictions[:5]:
            lines.append(f"- [{c['time_min']}min] {c['description']}")

    # 视觉综合
    visual_agg = fusion_context.get('visual_aggregates', {})
    if visual_agg and 'error' not in visual_agg:
        lines.append("\n### 视觉综合数据")
        lines.append(f"- 肢体语言平均分: {visual_agg.get('avg_gesture', 0)}/10")
        lines.append(f"- 表情自信平均分: {visual_agg.get('avg_expression', 0)}/10")
        lines.append(f"- 眼神接触平均分: {visual_agg.get('avg_eye_contact', 0)}/10")

    # 音频窗口
    audio_windows = fusion_context.get('audio_windows', [])
    if audio_windows:
        lines.append("\n### 分时段语音数据")
        for aw in audio_windows:
            lines.append(
                f"- [{aw['time_start_min']:.0f}-{aw['time_end_min']:.0f}min] "
                f"语速={aw['speech_rate_wpm']:.0f}wpm, 停顿={aw['pause_count']}次"
            )

    return "\n".join(lines) if lines else ""


def _format_transcript(segments: list) -> str:
    if not segments:
        return "（无转录内容）"
    lines = []
    current_speaker = None
    for seg in segments:
        speaker = (
            seg.get("displaySpeaker")
            or seg.get("rawSpeakerId")
            or seg.get("speaker")
            or "未知"
        )
        text = seg.get('text', '').strip()
        start = seg.get('start', 0)
        if start is None and seg.get("startMs") is not None:
            start = float(seg.get("startMs") or 0) / 1000.0
        minutes = int(float(start or 0) // 60)
        seconds = int(float(start or 0) % 60)
        if speaker != current_speaker:
            lines.append(f"\n【{speaker}】({minutes:02d}:{seconds:02d})")
            current_speaker = speaker
        lines.append(text)
    return '\n'.join(lines)


def _format_transcript_for_scoring(segments: list) -> str:
    """Cap transcript length so long roadshows do not force huge completions."""
    full = _format_transcript(segments)
    limit = int(settings.LLM_SCORING_TRANSCRIPT_MAX_CHARS)
    if len(full) <= limit:
        return full
    head = full[: int(limit * 0.55)]
    tail = full[-int(limit * 0.35) :]
    return (
        head
        + "\n\n…（中间转录已压缩，评分请优先依据头尾证据与语音/融合数据）…\n\n"
        + tail
    )


def _run_core_scoring_segmented(
    *,
    client,
    model_name: str,
    scoring_rules_prompt: str,
    snapshot: str,
    timeout: float | None,
) -> tuple[dict, dict]:
    """Score core dimensions in batches to avoid max-token truncation.

    Batch 1: skill_level (60 pts / 5 items — historically the longest output)
    Batch 2: remaining four dimensions
    Batch 3: overview fields only
    """
    batch_tokens = int(settings.LLM_CORE_BATCH_MAX_TOKENS)
    overview_tokens = min(batch_tokens, max(2000, batch_tokens // 2))
    batches = (
        (["skill_level"], "core_skill"),
        (
            ["professionalism", "application_value", "teamwork", "innovation"],
            "core_support",
        ),
    )
    dimensions: dict = {}
    batch_metas: dict = {}
    for keys, stage_name in batches:
        expected = list(keys)

        def _validator(payload, expected_keys=expected):
            return validate_core_dimensions_batch(payload, expected_keys)

        partial, meta = run_json_stage(
            client=client,
            model=model_name,
            stage=stage_name,
            messages=[
                {"role": "system", "content": scoring_rules_prompt},
                {
                    "role": "user",
                    "content": build_core_dimensions_prompt(snapshot, expected),
                },
            ],
            max_tokens=batch_tokens,
            validator=_validator,
            timeout=timeout,
            max_attempts=3,
        )
        dimensions.update(partial["dimensions"])
        batch_metas[stage_name] = meta

    overview, overview_meta = run_json_stage(
        client=client,
        model=model_name,
        stage="core_overview",
        messages=[
            {"role": "system", "content": scoring_rules_prompt},
            {
                "role": "user",
                "content": build_core_overview_prompt(snapshot, dimensions),
            },
        ],
        max_tokens=overview_tokens,
        validator=validate_core_overview,
        timeout=timeout,
        max_attempts=3,
    )
    batch_metas["core_overview"] = overview_meta
    core = {
        "dimensions": dimensions,
        "score_overview": overview["score_overview"],
        "highlights": overview["highlights"],
        "critical_issues": overview["critical_issues"],
        "evidence_summary": overview["evidence_summary"],
        "improvement_priorities": overview["improvement_priorities"],
    }
    validated = validate_core_output(core)
    meta = {
        "stage": "core",
        "status": "completed",
        "mode": "segmented_dimensions",
        "batches": batch_metas,
        "attempts": sum(int(m.get("attempts", 0) or 0) for m in batch_metas.values()),
        "prompt_tokens": sum(
            int(m.get("prompt_tokens", 0) or 0) for m in batch_metas.values()
        ),
        "completion_tokens": sum(
            int(m.get("completion_tokens", 0) or 0) for m in batch_metas.values()
        ),
        "total_tokens": sum(
            int(m.get("total_tokens", 0) or 0) for m in batch_metas.values()
        ),
    }
    return validated, meta


def _parse_and_validate(content: str) -> dict:
    """解析并校验大模型返回的 JSON，强制分数一致性，保留2位小数"""
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise Exception("无法解析大模型返回的 JSON")

    # 强制分数一致性：自下而上重新计算，保留2位小数
    dimensions = result.get('dimensions', {})
    overall_from_dims = 0.0

    for dim_key, dim in dimensions.items():
        items = dim.get('items', [])
        if items:
            items_score = sum(round(item.get('score', 0), 2) for item in items)
            items_max = sum(round(item.get('max_score', 0), 2) for item in items)
            dim['score'] = round(items_score, 2)
            dim['max_score'] = round(items_max, 2)
        overall_from_dims += dim.get('score', 0)

    result['overall_score'] = round(overall_from_dims, 2)
    result['overall_score'] = max(0.0, min(100.0, result.get('overall_score', 0)))
    _backfill_reference_report_sections(result)

    return result


def _backfill_reference_report_sections(result: dict) -> None:
    """只补成绩单/结论短句，禁止发明融合矛盾、结构分数、假评委。"""
    highlights = _string_list(result.get('highlights'))
    issues = _string_list(result.get('critical_issues'))
    priorities = [item for item in result.get('improvement_priorities', []) if isinstance(item, dict)]

    result.pop('jury_review', None)

    if not result.get('score_overview'):
        diag = _value_or_default(result.get('summary'), '')
        if not diag and (highlights or issues):
            head = highlights[0] if highlights else '本场已完成路演'
            tail = issues[0] if issues else '关键证据仍需核对'
            diag = f'{head}，但{tail}'
        result['score_overview'] = {
            "diagnosis": diag[:60],
            "highlights": [h.split('：')[0][:16] for h in highlights[:3]],
            "key_issues": [i.split('：')[0][:16] for i in issues[:3]],
        }

    if not result.get('action_plan') and priorities:
        result['action_plan'] = [
            {
                "priority": "P0" if idx <= 2 else "P1",
                "title": item.get('issue') or item.get('dimension') or f"改进项{idx}",
                "problem": item.get('issue') or '',
                "method": item.get('suggestion') or '',
                "owner": "对应负责选手",
                "timebox": "下一轮路演前",
                "acceptance": "能用明确证据回答评委追问",
            }
            for idx, item in enumerate(priorities[:4], 1)
        ]

    if not result.get('final_verdict'):
        overview = result.get('score_overview') or {}
        plans = result.get('action_plan') or []
        result['final_verdict'] = {
            "summary": overview.get('diagnosis') or '',
            "defensible_strengths": (overview.get('highlights') or highlights)[:3],
            "critical_deductions": (overview.get('key_issues') or issues)[:3],
            "next_round_focus": [
                item.get('suggestion') for item in priorities[:3] if item.get('suggestion')
            ] or issues[:2],
            "priority_actions": [
                {
                    "priority": plan.get("priority", "P0"),
                    "item": plan.get("title", ""),
                    "owner": plan.get("owner", ""),
                    "acceptance": plan.get("acceptance", ""),
                }
                for plan in plans[:4]
            ],
        }


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _value_or_default(value, default):
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _sanitize_competition_duration(result: dict, duration_seconds: float) -> dict:
    """强制纠正商业路演时长口径，避免 60 分钟赛制被误判为 10-15 分钟超时。"""
    duration_minutes = _safe_number(duration_seconds) / 60
    if not (50 <= duration_minutes <= 60):
        return result

    sanitized = _sanitize_duration_value(result)
    issues = sanitized.get('critical_issues', [])
    if isinstance(issues, list):
        normalized_issues = []
        for item in issues:
            if isinstance(item, str) and _has_wrong_duration_claim(item):
                replacement = _duration_replacement(item)
                if replacement and replacement not in normalized_issues:
                    normalized_issues.append(replacement)
                continue
            normalized_issues.append(item)
        sanitized['critical_issues'] = normalized_issues

    return sanitized


def _sanitize_duration_value(value):
    if isinstance(value, dict):
        return {key: _sanitize_duration_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_duration_value(item) for item in value]
    if isinstance(value, str):
        return _sanitize_duration_text(value)
    return value


def _sanitize_duration_text(text: str) -> str:
    if not _has_wrong_duration_claim(text):
        return text

    fixed = text
    fixed = re.sub(
        r'路演时长\d+(?:\.\d+)?分钟，远超常规比赛时间，时间控制不合理，导致部分内容冗长。',
        '路演时长符合60分钟赛制要求；需要关注的是部分技术细节讲解偏长，导致节奏不够紧凑。',
        fixed
    )
    fixed = re.sub(
        r'路演时长\d+(?:\.\d+)?分钟，严重超时，时间控制不合理。',
        '路演时长符合60分钟赛制要求；主要问题是部分环节时间分配不够均衡。',
        fixed
    )
    fixed = re.sub(
        r'路演时长\d+(?:\.\d+)?分钟，远超常规，时间控制不合理。',
        '路演时长符合60分钟赛制要求；主要问题是部分环节时间分配不够均衡。',
        fixed
    )
    fixed = re.sub(
        r'严格控制路演时间在\s*10\s*-\s*15\s*分钟内',
        '按60分钟赛制优化各模块时间分配',
        fixed
    )
    fixed = re.sub(
        r'控制路演时间在\s*10\s*-\s*15\s*分钟内',
        '按60分钟赛制优化各模块时间分配',
        fixed
    )
    fixed = re.sub(
        r'控制在\s*10\s*-\s*15\s*分钟内',
        '按60分钟赛制优化各模块时间分配',
        fixed
    )
    fixed = fixed.replace('远超常规比赛时间', '符合60分钟赛制时长要求')
    fixed = fixed.replace('远超常规', '符合60分钟赛制时长要求')
    fixed = fixed.replace('严重超时', '环节分配不均衡')
    fixed = fixed.replace('时间控制不合理', '节奏分配仍需优化')
    return fixed


def _duration_replacement(text: str) -> str:
    if any(keyword in text for keyword in ['冗长', '代码讲解', '技术细节', '节奏']):
        return '路演时长符合60分钟赛制要求；需要关注的是部分技术细节讲解偏长，导致节奏不够紧凑。'
    return '路演时长符合60分钟赛制要求；如需优化时间表现，应聚焦环节分配、故障冷场和重点呈现效率。'


def _has_wrong_duration_claim(text: str) -> bool:
    return bool(re.search(r'远超常规|严重超时|10\s*-\s*15\s*分钟|时间控制不合理', text))


def _safe_number(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _error_result(error_msg: str, provider: str = "unknown") -> dict:
    provider_label = PROVIDER_LABELS.get(provider, provider)
    return {
        'overall_score': None,
        'status': 'review_required',
        'score_authority': 'none',
        'error_code': 'scoring_generation_failed',
        'error': error_msg,
        'dimensions': {},
        'highlights': [],
        'critical_issues': [f'评分失败 [{provider_label}]: {error_msg}'],
        'improvement_priorities': [],
        'model': provider_label,
        'provider': provider
    }
