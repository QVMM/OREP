# OREP AI 生成 PPT 式 HTML

## 问题关闭清单

更新时间：2026-04-28

配套文档：

- [OREP_AI_PPT_HTML_TEAM_PROBLEM_GOVERNANCE_SPEC.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_TEAM_PROBLEM_GOVERNANCE_SPEC.md)
- [OREP_AI_PPT_HTML_TEAM_PROBLEM_REGISTER_AND_REMEDIATION_PLAN.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_TEAM_PROBLEM_REGISTER_AND_REMEDIATION_PLAN.md)
- [OREP_AI_PPT_HTML_TEAM_GOVERNANCE_BATCH_1_EXECUTION.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_TEAM_GOVERNANCE_BATCH_1_EXECUTION.md)

---

## 1. 使用说明

这份清单只做一件事：明确当前所有问题的状态，避免继续凭感觉判断“是不是做完了”。

状态定义：

- `已关闭`
  现阶段已达到治理规范中的主验收口径，可从主任务板移出，仅保留回归验证。
- `半关闭，需继续验证`
  主干方案已落地，但仍需真实任务回归、更多页型覆盖或用户链路压测。
- `未关闭，下一阶段必须继续做`
  还没有真正进入“稳定可用”状态，或只做了方案、局部补丁，尚未达到主验收口径。

---

## 2. 已关闭

### C2 读接口带写副作用

- 当前状态：已关闭
- 关闭依据：
  - `GET /history-detail` 已改成缓存优先、只读口径
  - `POST /workspace-refresh` 已成为动作后显式刷新入口
  - `material_evidence_plan / scoring_dashboard / roadshow_health / optimization_queue` 等核心工作台结果不再在普通详情读取时顺手重算
- 已落地文件：
  - [/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
  - [/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py](/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py)
  - [/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue](/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue)
- 后续要求：
  - 仅做回归验证，不再作为当前主整改项

### C7 素材绑定缺硬关系层

- 当前状态：已关闭
- 关闭依据：
  - `confirmed binding` 已进入后端真值层
  - `/history-detail` 与 `/materials/evidence-plan` 的素材准备度口径已统一
  - `HTML 预览` 右侧工作台和 `素材证据（高级）` 都能直接确认/移除硬绑定
  - 真实任务 `107` 的 `26/27` 页已经验证“传了图还提示缺图”主痛点被收住
- 已落地文件：
  - [/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py)
  - [/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py](/Users/liuyixing/项目/OREP/ai-scoring/app/routers/ppt_router.py)
  - [/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptMaterialsAdvancedPanel.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptMaterialsAdvancedPanel.vue)
  - [/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptHtmlWorkbench.vue](/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptHtmlWorkbench.vue)
  - [/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue](/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue)
- 后续要求：
  - 仅做新增页型/新增素材类型回归，不再作为当前主整改项

---

## 3. 半关闭，需继续验证

### A1 页面仍有明显 HTML 味，像网页模块拼装

- 当前状态：半关闭
- 已完成：
  - 页面契约、页系样张、单页重设计协议已进入系统
  - `main generator / rebuild / fallback` 已开始按 `page_series_type + layout_slots` 长页
  - 候选页已按页系契约 `accept/reject`
- 仍待验证：
  - 全部关键页型是否都稳定摆脱“普通卡片页”味道
  - 非抽样页是否仍会回落到普通 HTML 风格

### A2 技术页、实操页、价值页、创新页模板化

- 当前状态：半关闭
- 已完成：
  - `architecture_system / practice_evidence / value_matrix / evidence_board / closing_board` 已做真实任务回归
- 仍待验证：
  - 创新页、章节页、团队页、产教页等长尾页型仍需补抽样

### A3 证据页不是证据主导页

- 当前状态：半关闭
- 已完成：
  - `evidence_board` 已进入主生成、rebuild、fallback
  - 政策页/实操证据页已有证据主导骨架
- 仍待验证：
  - 所有证据页都是否真正把证据放到视觉主区，而非说明附属区

### A4 主视觉焦点不稳定

- 当前状态：半关闭
- 已完成：
  - 视觉审查已支持 `visual_role_not_realized`
  - repair 已能按主视觉职责做重建
- 仍待验证：
  - 多页连续生成任务中，主视觉焦点是否足够稳定

### B1 底层评分覆盖仍残留商业 BP 语义

- 当前状态：半关闭
- 已完成：
  - 评分标准、输入层、Round 1/2/3/4 显性商业 BP 语义已大幅清理
  - 真实新任务 `125 / 128 / 130+` 已验证前半段明显不再自然长出“市场规模/融资需求/财务预测”页
- 仍待验证：
  - 后半段章节和少量 fallback 文案是否还会残留隐性商业语气

### B2 节奏控制不够比赛原生

- 当前状态：半关闭
- 已完成：
  - `agenda / opening / problem_solution / closing` 已开始比赛原生化
  - 下载前/总审前的流程语境更清晰
- 仍待验证：
  - 整套 60 分钟节奏是否对所有任务都稳定成立

### B3 实操页不够像操作能力展示页

- 当前状态：半关闭
- 已完成：
  - `practice_evidence` 已明确要求输入-操作-输出-证据闭环
  - 真实任务回归已显示明显改善
- 仍待验证：
  - 老任务 repair 和长尾实操页是否都能稳定满足“操作能力展示页”标准

### B6 当前可下载不等于比赛终稿

- 当前状态：半关闭
- 已完成：
  - `blocked / warning / ready` 已明显分层
  - 下载流程从“只会拦”变成“拦住后继续带着处理”
- 仍待验证：
  - `warning` 态下全局卡片、顶部状态条、当前页反馈三处是否始终一致

### C1 当前真相源过多

- 当前状态：半关闭
- 已完成：
  - `history-detail` 主链路开始读同一套持久化当前态
  - `workspace-refresh` 已成为显式刷新入口
- 仍待验证：
  - 是否还存在别的边角入口直接写局部状态

### C3 HTML 真值与交付页面不一致

- 当前状态：半关闭
- 已完成：
  - 候选页采用前已走统一契约验收
  - 当前页 / 质量卡 / 下载条件 / 总审开始理解“候选页没过契约门”
- 仍待验证：
  - 全链路是否都始终读同一个“当前页真值”

### C4 评分覆盖过度依赖文本启发式

- 当前状态：半关闭
- 已完成：
  - `score_evidence_blocks` 已成为主证据结构
  - 判定已改成“结构化证据优先，文本兜底”
- 仍待验证：
  - 历史任务和所有角色页的过渡是否完全稳住

### C6 页面契约 deterministic validator 不完整

- 当前状态：半关闭
- 已完成：
  - 已有：
    - 预期块位
    - 内部词泄露
    - 主视觉职责
  三类确定性校验
- 仍待验证：
  - 更多页型是否还需要补专门 validator

### D1 生成完成后用户还要做很多事

- 当前状态：半关闭
- 已完成：
  - 当前页补图、补评分点、重做契约页、下载链引导已压缩很多
- 仍待验证：
  - 普通用户是否仍然觉得“系统太重”

### D2 预览页仍偏重

- 当前状态：半关闭
- 已完成：
  - `HTML 预览` 已成为主工作台
  - `素材证据（高级）` 已明显降级
- 仍待验证：
  - 当前页右侧是否还承载了过多分析信息

### D4 下载链路还不够“系统替我过关”

- 当前状态：半关闭
- 已完成：
  - 下载条件卡、顶部状态条、当前页反馈卡已基本串起来
- 仍待验证：
  - `warning` 态下三处反馈是否对所有真实任务始终一致

### D5 等待过程仍非零焦虑

- 当前状态：半关闭
- 已完成：
  - 大纲阶段状态查询不再容易被拖死
  - `compact-retry` 已具备更持久的 `repair_substep`
- 仍待验证：
  - 所有慢任务都能稳定把“最近一次恢复动作”显示给用户

### D6 主路径还未彻底当前页化

- 当前状态：半关闭
- 已完成：
  - 当前页补图、当前页契约重做、当前页反馈都已打通
- 仍待验证：
  - 是否还存在高频动作必须跨多个 tab 才能完成

---

## 4. 未关闭，下一阶段必须继续做

### A5 页系样张体系不完整

- 当前状态：半关闭，需继续验证
- 当前缺口：
  - 主生成器 / rebuild / fallback 已补齐并回归通过：
    - `protocol_board`
    - `collaboration_matrix`
    - `journey_timeline`
    - `bridge_story`
    - `innovation_compare`
  - 结合之前已稳定的：
    - `evidence_board`
    - `practice_evidence`
    - `architecture_system`
    - `value_matrix`
    - `closing_board`
    当前关键比赛页系已经形成第一批完整样张族
  - opening 家族这一轮已补进三条生成链：
    - `cover_keynote`
    - `agenda_navigation`
    - `definition_canvas`
    - `mapping_bridge`
  - opening 家族已接入固定回归并完成第一轮真实任务抽样：
    - `cover_keynote`：`keynote_anchor` 已在主生成与 rebuild 同时出现
    - `agenda_navigation`：`navigation_board` 回归通过
    - `definition_canvas`：`definition_canvas` 回归通过
    - `mapping_bridge`：`flow_mapping` 回归通过
  - 当前固定页系回归最新结果已清零 `regressed`：
    - `improved: 16`
    - `stable_pass: 14`
    - `regressed: 0`
  - 新一轮固定回归（`20260428_164423`）继续保持：
    - `improved: 13`
    - `stable_pass: 17`
    - `regressed: 0`
    - `needs_attention: 0`
  - 章节页、突破页和其他长尾页系还没有全部补齐
- 下一阶段动作：
  - 继续扩章节页 / 幕次过渡页 / 导航页的页系样张族
  - 继续扩对应页型回归抽样，尤其验证长尾页型不会退回普通 HTML

### A6 章节页/突破页/收束页镜头感不足

- 当前状态：半关闭，需继续验证
- 当前缺口：
  - opening 家族与 closing 家族的结构骨架已经开始带出镜头感：
    - `cover_keynote`
    - `agenda_navigation`
    - `mapping_bridge`
    - `closing_board`
  - opening 家族已完成第一轮真实任务截图级抽样，不再明显退回普通 HTML 说明页
  - 第二轮截图级验收已进一步收掉：
    - 英文眉标
    - `内容块 1/2/3`
    - 明显的“围绕页面契约补足...”内部说明文
  - 第三轮截图级验收已确认：
    - `main.png / rebuild.png` 中 opening / definition / bridge 家族不再暴露英文眉标、内部块位词和明显模板提示语
    - `cover_keynote / agenda_navigation / definition_canvas / mapping_bridge` 的主视觉与分区关系已经明显更接近比赛终稿页
  - 当前 remaining gap 已缩小到：
    - opening / bridge 家族的支撑卡正文仍偏“说明性描述”，虽然不再像内部模板，但离最终答辩稿式表达还差一层内容感
    - `current.png` 仍会受真实任务历史页面内容影响，不能单独作为新骨架效果判断依据
  - opening 家族已进入固定回归，并且当前无回归退化项
  - 新一轮固定回归继续确认 opening / closing / bridge / definition 相关页无新的结构退化
  - 但“章节推进感 / 突破感 / 收束感”仍主要依赖页系骨架，缺少跨任务、跨行业的截图级验收
  - 大幕次过渡页与章节锚点页还没有形成完整镜头族
- 下一阶段动作：
  - 专门扩章节页/收束页契约
  - 增加导演式视觉审查规则
  - 继续扩 opening/closing 家族的跨任务截图级回归，专门检查“镜头感是否足够”

### B4 团队协作/安全规范/职业素养页变成态度表达页

- 当前状态：接近关闭，持续抽检
- 当前缺口：
  - 契约、默认评分证据块、Round 3/4 提示词和评分兜底已收紧
  - 第一轮真实任务抽查已通过：
    - `team_collaboration` 页已稳定落到 `collaboration_matrix`
    - `safety_norms` 页已稳定落到 `protocol_board`
    - `rd_journey` 页已稳定落到 `journey_timeline`
    - `industry_education` 页已稳定落到 `bridge_story`
  - 真实任务 `107 / 128 / 102` 抽查中，这些页型已不再单靠态度词通过；老任务 `102` 上残留的问题更多是历史内容质量与证据缺口，不是页型判定失真
  - 新一轮固定回归继续确认：
    - `collaboration_matrix`
    - `protocol_board`
    - `journey_timeline`
    - `bridge_story`
    当前没有新的结构回归
  - 跨任务内容层复核表明：
    - 新生成链的 `main/rebuild` 已基本摆脱“共同目标/产业需求驱动/业务指标”这类旧路演语境
    - 老任务 `106` 的 `current.html` 仍残留历史表达，但问题主要在旧任务存量内容，不是新骨架再次回退
  - 本轮已把稳定下来的团队页 / 安全页 / 研发历程页 / 产教融合页回正规则继续外抽到独立 `normalization_rules`
    - 团队页：
      - `团队风采 / 核心成员 / 跨学科的实干者`
      - -> `团队协作：岗位分工与补位机制`
    - 安全页：
      - `安全与规范 / 风险控制措施`
      - -> `安全与规范：流程、数据与应急机制`
    - 研发页：
      - `研发历程 / 研发过程 / 研发历程与迭代`
      - -> `研发历程：问题驱动与迭代验证`
    - 产教页：
      - `产教融合 / 产教融合与合作探究`
      - -> `产教融合：能力来源与任务桥接`
    - 对应 `speech_script / core_argument` 也已同步回正，不再停留在成员介绍、态度表达或泛口号层
  - 真实页回归继续确认：
    - `134 page 34 / 36 / 38 / 39`
    - `102 page 35 / 36 / 37`
    已经稳定落到：
      - `team_collaboration -> collaboration_matrix`
      - `safety_norms -> protocol_board`
      - `rd_journey -> journey_timeline`
      - `industry_education -> bridge_story`
    并且讲稿与核心论点已经回到：
      - 岗位职责、交接补位、协同结果
      - 开发规范、数据安全、异常处置
      - 问题驱动、测试验证、迭代复盘
      - 课程能力、行业任务、合作探究、反馈闭环
  - 另外已修正一处 B4 相关误判：
    - `132 page 6`
    - 不再因为标题里含“粮食安全”被误判成 `safety_norms`
    - 当前已回到 `industry_context`
  - 最新扩大抽查继续确认：
    - `102 / 106 / 107 / 128 / 132 / 133 / 134`
    - 团队页、规范页、研发页、产教页的角色、页系、标题、讲稿、核心论点已基本稳定
    - 当前剩余更多是老任务存量内容细节偏弱，不再是结构性回退为“态度词页”
  - 本轮继续对残留错位页做本地规则重算验证：
    - `134 page 17 / 23`
    - 旧状态仍挂在 `innovation_compare`
    - 现在已稳定回正到：
      - `team_collaboration -> collaboration_matrix`
      - 标题：`团队协作：岗位分工与补位机制`
      - `speech_script / core_argument` 也同步回到岗位职责、交接补位、协同结果语境
- 仍需要继续验证：
    - 后续新行业任务里，是否仍能稳定长出机制、动作和闭环证据
- 下一阶段动作：
  - 保持抽检 `team_collaboration / safety_norms / rd_journey / industry_education`
  - 若新任务再次退回态度表达页，再补页系骨架与 validator

### B5 创新与应用价值页泛化

- 当前状态：接近关闭，持续抽检
- 当前缺口：
  - 契约、默认评分证据块、Round 3/4 提示词和评分兜底已强化
  - 第一轮真实任务抽查已通过：
    - `innovation` 页已稳定落到 `innovation_compare`
    - `application_value` 页已稳定落到 `value_matrix`
  - 真实任务 `107 / 128 / 102` 抽查中，这两类页已不再只靠“创新/亮点/价值”口号式表达判定通过
  - 新一轮固定回归继续确认：
    - `innovation_compare`
    - `value_matrix`
    当前没有新的结构回归
  - 跨任务内容层复核表明：
    - 老任务 `106` 的 `current.html` 仍可见 `模式与社会效益 / 模式创新 / SaaS` 等历史商业表达
    - 但最新 `main/rebuild` 链已经基本不再回退到这类文案，本轮已继续补强比赛原生化替换：
      - `可持续性：模式与社会效益` -> `可持续性：综合效益与推广基础`
      - `技术突破与模式创新` -> `技术突破与机制创新`
      - `政策支持与产业需求` -> `政策支持与场景需求`
      - `SaaS模式 / 商业闭环 / 商业可持续` -> `平台化服务路径 / 推广闭环 / 长期可持续`
    - 老任务 `106 / 107` 的部分价值页还存在历史 `slide_role` 错位：
      - 例如价值页仍残留 `innovation_points`
      - 本轮已补 `title/section` 强语义优先覆盖旧 `slide_role`，并在默认化阶段把页系身份回正到 `application_value -> value_matrix`
      - 同时把明显错位的标题回正为：
        - `应用价值：综合效益与推广基础`
        - `应用推广与持续发展`
      - 本地重算确认：
        - `106 page 31 / 32`
        - `107 page 31 / 32`
        已全部稳定回正到 `application_value -> value_matrix`
        - 原本看起来像 `innovation_compare` 的旧页，不再残留错误页系身份
    - 最新回归报告仍显示：
      - `innovation_compare / collaboration_matrix / bridge_story / protocol_board` 在新生成链中未重新冒出旧商业 BP 词
      - `value_matrix` 在老任务 `106/107` 上的剩余问题开始转向“主价值块是否真正站住”，而不是再次退回 `亮点词 / 商业模式` 文案
      - 本轮已继续补价值页 / 创新页专用正文生成：
        - `服务对象与场景`
        - `实用性`
        - `经济性`
        - `可持续性`
        - `改良前问题`
        - `改良后做法`
        - `创新机制`
        - `量化结果`
        不再回落成“把 xx 做成可比较、可感知的价值表达 / 补充支撑本页结论”的泛提示句
  - 仍需要继续验证：
    - 应用价值页是否在更多任务里都能稳定呈现场景对象、量化成效和推广路径
    - 创新页是否在更多任务里都能稳定体现机制、对照与量化结果
  - 本轮继续对真实仍保留 `innovation_compare` 的任务页做了内容层复核：
    - `132 page 36 / 38`
    - `133 page 31 / 32`
    - `134 page 19 / 28`
    - `main / rebuild` 两条链都已不再回到“技术亮点 / 创新点与技术优势 / 亮点词”式泛描述，正文已经稳定落到：
      - 改良前问题
      - 改良后做法
      - 创新机制
      - 量化结果
    - 剩余小尾巴主要变成标题语义过泛，例如 `技术亮点`；本轮已继续补标题回正：
      - `技术亮点 / 创新点与技术优势 / 五大创新突破 / 五大技术创新点`
      - -> `创新对照：关键机制与成效验证`
    - 真实页面级复验也已通过：
      - `134 page 19 / 28`
      - 页面顶部可见标题不再残留旧的 `技术亮点`
      - 已与逻辑层标题同步为 `创新对照：关键机制与成效验证`
  - 本轮继续做了页面级叙事对齐验证：
    - `106 page 31`
  - 本轮扩大抽查继续确认：
    - `101 / 102 / 106 / 107 / 128 / 134`
    - 价值页当前已经稳定回到：
      - `application_value -> value_matrix`
      - 标题统一收敛到：
        - `应用价值：综合效益与推广基础`
        - `应用推广与持续发展`
    - 其中历史错位页：
      - `128 page 29 / 32`
      - 也已能在本地规则重算中稳定从 `innovation_compare` 回正到 `value_matrix`
  - 本轮同时继续确认真实创新页：
    - `132 / 133 / 134`
    - `innovation_compare` 的标题、讲稿和核心论点都保持“改良前问题 / 改良后做法 / 创新机制 / 量化结果”语境，没有再退回亮点词页面
      - `107 page 31`
      - `134 page 32`
      当前都已经稳定为：
      - `role = application_value`
      - `series = value_matrix`
      - `speech_script` 不再从“我们的创新/技术创新”角度讲价值页，而是统一回到：
        - 服务对象与场景
        - 综合效益
        - 持续推广与复制基础
      - `core_argument` 也已同步收口为：
        - `平台化服务路径可复制，能够支撑持续推广、长期运维和更大范围应用落地。`
    - 本轮也继续对真实创新页做了叙事对齐验证：
      - `132 page 36`
      - `133 page 31`
      - `134 page 19`
      当前都已经稳定为：
      - `role = innovation`
      - `series = innovation_compare`
      - `speech_script / core_argument` 不再是通用兜底句，而是明确要求讲清：
        - 改良前问题
        - 改良后做法
        - 创新机制
        - 量化结果
  - 最新扩大抽查继续确认：
    - `101 / 102 / 106 / 107 / 128 / 132 / 133 / 134`
    - 价值页与创新页在角色、页系、标题、讲稿、核心论点五层上已基本稳定
    - 旧商业 BP 语气的主问题已从“结构性回退”收敛为“少量老任务存量内容细节仍可继续优化”
  - 本轮继续做页面级 HTML 抽查：
    - `101 / 102 / 106 / 107 / 132 / 133 / 134`
    - `value_matrix / innovation_compare` 的重建页里，英文眉标、`必须块 / 视觉规则 / xx页要求`、泛提示句已清空
    - 价值页里原本仍残留的泛标题：
      - `绿色生态与可持续发展`
      - `绿色生态，赋能农业可持续发展`
      - `可持续性：绿色农业与长期可持续`
      已统一回正为：
      - `应用价值：综合效益与推广基础`
- 下一阶段动作：
  - 保持抽检 `innovation / application_value`
  - 若新任务再次退回亮点词/商业化语气，再补对应页系骨架与 validator

### C5 repair / fallback / rebuild / deliverability 并行环路

- 当前状态：半关闭，需继续验证
- 当前缺口：
  - 页动作成功路径已开始统一返回 canonical `workspace_state`：
    - `repair`
    - `apply`
    - `batch repair`
  - 候选页被契约门拒绝时，也已开始返回最新 `workspace_state`，不再只回局部拒绝原因
  - 前端当前页工作台与下载条件内联动作，已优先吃后端返回的 `workspace_state`，并且不再把 `accepted=false` 的候选页误算成“修复成功”
  - 真实任务 `107` 双路径验证已通过：
    - `page 1` 候选页被拒绝：动作返回的 `workspace_state` 与重新读取的 `history-detail` 在 `deliverability / quality / p0 / page_failed_checks` 上一致
    - `page 10` 候选页被采用：动作返回的 `workspace_state` 与重新读取的 `history-detail` 在同一批关键字段上保持一致
  - 真实任务 `102` 轻量旧任务验证已通过：
    - `page 1` 候选页被拒绝：动作返回的 `workspace_state` 与重新读取的 `history-detail` 在 `deliverability / average_score / p0 / blocker types / page_failed_checks` 上保持一致
  - 真实任务 `106` 当前主要暴露的是老任务页动作耗时偏长，不是 `history-detail` 或全局状态回写再次失真；服务健康与只读详情读取仍保持正常
  - 仍需要继续验证：
    - `warning` 状态下，当前页反馈 / 下载条件卡 / 总审 / 顶部下载流程条是否在更多真实任务里持续一致
    - 其他页型与批量动作是否都不再残留“局部成功、全局没跟上”的分叉
- 下一阶段动作：
  - 继续用真实任务压：
    - 当前页修复
    - 下载条件刷新
    - 总审刷新
    - 当前页右侧反馈
    是否完全同口径
  - 若仍出现分叉，优先继续把返回链收口到后端 canonical state，而不是在前端追加局部补丁

### C8 history-detail 过重

- 当前状态：未关闭
- 当前缺口：
  - 组件拆分和 composable 已做很多
  - 但 `history-detail` 作为聚合工作台仍然偏重
- 下一阶段动作：
  - 继续压缩默认视图
  - 把更多高级信息收进折叠/高级入口

### C9 `ppt_service.py` 超级单体

- 当前状态：未关闭
- 当前缺口：
  - 虽然功能在推进，但超大单体文件仍然是持续维护风险
- 下一阶段动作：
  - 分离：
    - deliverability
    - materials
    - repair
    - scoring
    - roadshow health

### C10 旧链路与新链路并存

- 当前状态：未关闭
- 当前缺口：
  - 已有新链路，但老兼容逻辑仍很多
- 下一阶段动作：
  - 列迁移清单
  - 明确哪些旧链路可以下线

### D3 内部概念暴露偏多

- 当前状态：未关闭
- 当前缺口：
  - 用户仍会接触到较多“系统内部视角”的解释
  - 比如某些检查项、模块名、设计约束词
- 下一阶段动作：
  - 继续做人话化
  - 把系统术语下沉为高级说明，不作为主表达

---

## 5. 下一阶段实施顺序

按优先级，建议接下来这样做：

1. `B4 团队协作/安全规范/职业素养页变成态度表达页`
2. `B5 创新与应用价值页泛化`
3. `A5 页系样张体系不完整`
4. `A6 章节页/突破页/收束页镜头感不足`
5. `D4 / D6 / D2` 继续真实任务验收
6. `C5 / C8 / C9 / C10` 做系统收口
7. `D3` 做最后一轮用户可见术语减法

---

## 6. 当前执行约束

后续每一轮开发必须先回答：

1. 当前在解决哪个问题 ID  
2. 该问题属于：已关闭 / 半关闭 / 未关闭  
3. 本轮是：
   - 推进到半关闭
   - 还是从半关闭推进到已关闭  
4. 做完后用什么验收标准判定它是否真的推进了

如果这 4 个问题答不清，就不应继续“凭感觉修系统”。
