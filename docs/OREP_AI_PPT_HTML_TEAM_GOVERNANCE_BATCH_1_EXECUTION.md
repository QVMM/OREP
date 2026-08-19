# OREP AI 生成 PPT 式 HTML

## Team 治理规范 · 第一批执行清单

更新时间：2026-04-27

配套文档：

- [OREP_AI_PPT_HTML_TEAM_PROBLEM_GOVERNANCE_SPEC.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_TEAM_PROBLEM_GOVERNANCE_SPEC.md)
- [OREP_AI_PPT_HTML_TEAM_PROBLEM_REGISTER_AND_REMEDIATION_PLAN.md](/Users/liuyixing/项目/OREP/docs/OREP_AI_PPT_HTML_TEAM_PROBLEM_REGISTER_AND_REMEDIATION_PLAN.md)

---

## 1. 本批次目标

第一批不追求把全部问题一次做完，而是先解决 3 条最会把系统带偏的主干问题：

1. **A 组：最终成品仍有 HTML 味，关键页不够像比赛页**
2. **B 组：评分底座仍残留商业 BP 语义，补分路径不稳定**
3. **C 组：后端当前真相源和校验链不够硬，导致做了不一定生效**

这一批的总目标是：

- 让关键页真正开始按页面契约和页系样张生成
- 让评分覆盖开始围绕技能大赛评分点而不是市场/融资语义
- 让当前页、质量卡、下载条件、总审读的是同一种“当前真相”

---

## 2. 批次划分

## Batch 1A：页面契约与页系骨架落地

### 对应问题 ID

- A1 页面仍有明显 HTML 味
- A2 技术页、实操页、价值页最容易模板化
- A3 证据页不是证据主导页
- A5 页系样张体系不完整

### 本批目标

把页面契约和页系样张从文档层推进到：

- Round 2
- Round 3
- Round 4
- html_generator
- rebuild / fallback
- visual judge
- repair accept/reject

### 关键任务

1. 建立页面契约注册表
2. Round 2 输出 `contract_id / page_series_type / page_visual_role`
3. Round 3 输出 `page_template_contract / layout_slots`
4. 主生成器按 `page_series_type + layout_slots` 选骨架
5. rebuild / fallback 按同一套块位语言长页
6. 视觉审查新增：
   - `contract_mismatch`
   - `series_language_missing`
   - `visual_role_not_realized`
7. 候选页采用前执行页系契约验收

### 涉及文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/page_contracts.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round4_html_generation_optimized.md`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/vision_judge_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`

### 验收标准

- 抽样页系回归脚本 `regressed = 0`
- `evidence_board / practice_evidence / architecture_system / value_matrix / closing_board` 五类页系均能在真实任务中跑通
- 候选页若仍是普通卡片页，会被契约门拒绝

---

## Batch 1B：比赛原生评分底座替换

### 对应问题 ID

- B1 底层评分覆盖仍残留商业 BP 语义
- B2 节奏控制不够比赛原生
- B3 实操页不够像操作能力展示页
- B6 当前可下载不等于比赛终稿
- C4 评分覆盖过度依赖文本启发式

### 本批目标

让评分覆盖优先读：

- `served_scoring_dimensions`
- `score_evidence_blocks`

并把主补强方向收回到技能大赛评分点，而不是市场规模/融资需求等 BP 语义。

### 关键任务

1. 用职业院校技能大赛评分点替换旧 `scoring_checker` 必备章节底座
2. Round 2 / Round 3 增加 `score_evidence_blocks`
3. 默认化老任务页的 `score_evidence_blocks`
4. repair prompt 支持比赛评分点直达约束：
   - 操作规范性
   - 技能熟练度
   - 任务难易度
   - 技术先进性
   - 现场讲解效果
   - 职业道德与行为规范
   - 工匠精神
   - 安全意识
   - 实用性
   - 经济性
   - 可持续性
   - 团队合作
   - 创新创意
5. 下载条件和评分覆盖 UI 优先展示比赛评分点

### 涉及文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/scoring_checker.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/page_contracts.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round2_narrative.md`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts/round3_enrich.md`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptDownloadReadiness.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/components/ppt/PptScoringCoveragePanel.vue`

### 验收标准

- 一键补评分点后，覆盖率变化稳定
- 系统优先补的评分点不再长期出现“市场规模 / 融资需求”这类商业 BP 主项
- 评分覆盖说明中，优先缺失点以比赛评分点为主

---

## Batch 1C：当前真相源与校验链收口

### 对应问题 ID

- C1 当前真相源过多
- C2 读接口带写副作用
- C3 HTML 真值与交付页面不一致
- C6 页面契约 deterministic validator 不完整

### 本批目标

把“当前页面真值”和“页面是否达到比赛页标准”的判断收口到后端唯一链路。

### 关键任务

1. 明确 `html_page` 为当前页面真值
2. snapshot 退回审计/回放角色
3. repair 预览与 apply 共用同一套契约验收
4. 读接口优先只读，重算和刷新显式触发
5. 对页系契约 validator 增加确定性校验：
   - 预期块位
   - 内部词泄露
   - 主视觉职责

### 涉及文件

- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/ppt_service.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/html_generator.py`
- `/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/adapter_code/pipeline_coordinator.py`
- `/Users/liuyixing/项目/OREP/frontend/user/src/views/PptHistoryDetail.vue`
- `/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptDownloadReadiness.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptCurrentPageWorkspace.js`
- `/Users/liuyixing/项目/OREP/frontend/user/src/composables/usePptRepairWorkspace.js`

### 验收标准

- 同一任务在当前页、质量页、下载条件、总审里读到的是同一当前页版本
- 候选页没过契约门时，拒绝原因能在当前页、质量卡、总审、下载条件里一致回显
- 刷新详情页不会无提示改变交付结论

---

## 3. 实施顺序

建议执行顺序固定为：

1. `Batch 1A` 页面契约与页系骨架
2. `Batch 1B` 比赛原生评分底座
3. `Batch 1C` 当前真相源与校验链收口

原因：

- 没有 1A，就不知道“好页面长什么样”
- 没有 1B，系统会继续推荐错的补强方向
- 没有 1C，用户即使做对了事，也可能看不到一致结果

---

## 4. 特殊变故处理

### 4.1 老任务缺结构化字段

处理原则：

- 允许回退到默认化补齐
- 不允许因此跳过页面契约和评分证据字段

### 4.2 缺真实素材

处理原则：

- 测试阶段允许临时演示素材
- 正式比赛版必须回补真实素材

### 4.3 repair 连续失败

处理原则：

- 连续 2 轮仍未通过契约门时，禁止继续普通修页
- 强制切到契约骨架重建

### 4.4 新旧链路并存

处理原则：

- 旧链路只做兼容和迁移
- 新功能只挂在新链路

---

## 5. 本批完成标志

当满足以下条件时，第一批可判定为“主干完成”：

1. 五类核心页系回归稳定
2. 评分覆盖主语义完成比赛化切换
3. 当前页 / 质量卡 / 下载条件 / 总审读到同一种当前真相
4. 一键补评分点与一键重做契约页在真实任务中都可稳定生效

