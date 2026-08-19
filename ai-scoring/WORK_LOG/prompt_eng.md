# Prompt Engineer Work Log

## 当前状态
**角色**: Prompt Engineer（提示词工程师）
**Sprint**: Sprint 0
**任务**: T006 - 梳理 Prompt 需求，输出需求清单
**状态**: 已完成

---

## 进展记录

### 2026-04-15 - T006 任务完成

#### 任务概述
分析了现有的 5 个 Prompt 文件（round1_structurize.md、round2_narrative.md、round3_enrich.md、round4_html_generation.md、self_check.md），梳理了每个 Round 的需求，输出了完整的 Prompt 需求清单。

#### 完成工作

1. **分析了现有 Prompt 结构**
   - Round 1: 信息收集与结构化（542行）
   - Round 2: 叙事框架生成（606行）
   - Round 3: 内容充实（628行）
   - Round 4: HTML 生成（604行）
   - Self-Check: 内容质量自检（446行）

2. **创建了 PROMPT_REQUIREMENTS.md**
   - A 节: Round 1 Prompt 需求（系统提示词、用户提示词模板、Few-shot、输出格式）
   - B 节: Round 2 Prompt 需求（内容填充原则、口播稿生成、数据打散、空壳页惩罚）
   - C 节: Round 3 Prompt 需求（HTML 结构、样式规则、图表渲染规范）
   - D 节: Round 4 Prompt 需求（批量生成指令、文件命名规则）
   - E 节: Self-Check Prompt 需求（质量检查维度、违规检测）

3. **创建了 CHANGE_LOG_TEMPLATE.md**
   - 变更记录表模板
   - 详细变更记录模板
   - 各 Round 独立变更日志
   - 变更通知模板
   - 变更控制流程

4. **创建了 EVALUATION_CRITERIA.md**
   - 核心指标：有效页数、空壳页率、SVG 图表数量、内容密度
   - 辅助指标：confidence_score、口播稿达标率、图表完整率
   - 评估流程与报告模板
   - 指标异常处理机制

#### 产出文件清单

| 文件路径 | 说明 | 行数 |
|----------|------|------|
| `/Users/liuyixing/项目/OREP/ai-scoring/prompts/PROMPT_REQUIREMENTS.md` | Prompt 需求清单 | ~650 |
| `/Users/liuyixing/项目/OREP/ai-scoring/prompts/CHANGE_LOG_TEMPLATE.md` | 版本变更记录模板 | ~350 |
| `/Users/liuyixing/项目/OREP/ai-scoring/prompts/EVALUATION_CRITERIA.md` | Prompt 效果评估标准 | ~500 |

---

## 产出物清单

### Sprint 0 产出（T006）

- [x] prompts/PROMPT_REQUIREMENTS.md
- [x] prompts/CHANGE_LOG_TEMPLATE.md
- [x] prompts/EVALUATION_CRITERIA.md
- [x] WORK_LOG/prompt_eng.md（已更新）

### Round 1（规划中）
- [ ] prompts/round1/system_prompt.md
- [ ] prompts/round1/user_prompt_template.md
- [ ] prompts/round1/few_shot_examples.json
- [ ] prompts/round1/CHANGELOG.md

### Round 2（规划中）
- [ ] prompts/round2/system_prompt.md
- [ ] prompts/round2/user_prompt_template.md
- [ ] prompts/round2/few_shot_examples.json
- [ ] prompts/round2/CHANGELOG.md

### Round 3（规划中）
- [ ] prompts/round3/system_prompt.md
- [ ] prompts/round3/user_prompt_template.md
- [ ] prompts/round3/few_shot_examples.json
- [ ] prompts/round3/CHANGELOG.md

### Phase 2 HTML（规划中）
- [ ] prompts/phase2_html/batch_prompt_template.md
- [ ] prompts/phase2_html/style_anchor.md
- [ ] prompts/phase2_html/chart_rendering_spec.md

### Evaluation（规划中）
- [ ] prompts/evaluation/prompt_eval_criteria.md
- [ ] prompts/evaluation/eval_results/

---

## 备注

T006 任务已完成。产出了三个核心文档：
1. PROMPT_REQUIREMENTS.md - 完整的 Prompt 需求清单
2. CHANGE_LOG_TEMPLATE.md - 变更记录模板
3. EVALUATION_CRITERIA.md - 效果评估标准

这些文档为后续的 Prompt 开发提供了清晰的需求规范和评估标准。
