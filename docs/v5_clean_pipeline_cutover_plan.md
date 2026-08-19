# V5 Clean Pipeline Cutover Plan

## 目标

不再在旧 `V4 + fallback + repair + 模板壳` 上继续补洞，而是新建一条完全隔离的 clean pipeline：

`输入语义 -> narrative graph -> layout decisions -> render contracts -> final HTML`

这条链的目标不是“比 V4 多几个修复规则”，而是：

- 页面先被理解为 `叙事职责`
- 再被决策为 `family / variant / focus / density / scan`
- 最后被渲染为 `可验收的结构化 HTML`
- reviewer 和 gate 只看最终 HTML 与 contract，不再依赖旧模板修补链

## 明确舍弃

以下能力在 V5 中不再作为主路径复用：

- V4 的本地模板 fallback 壳
- 旧的 “生成坏了再 repair” 作为常态机制
- family 注册很多但 renderer 不完整的做法
- 先把内容塞进 HTML 再靠 sanitizer/gate 兜底
- 依赖读路径补 metadata 才能让页面看起来正确

## V5 最小模块

代码位置：

- [v5/__init__.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/__init__.py)
- [v5/schemas.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/schemas.py)
- [v5/narrative_graph.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/narrative_graph.py)
- [v5/layout_engine.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/layout_engine.py)
- [v5/render_contracts.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/render_contracts.py)
- [v5/clean_pipeline.py](/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/v5/clean_pipeline.py)

模块职责：

- `narrative_graph.py`
  - 把页面先识别成 `opening / definition / solution / proof_value / closing`
  - 并细分为 `handoff_chain / retrospective_improvement / value_proof` 等职责
- `layout_engine.py`
  - 直接按职责映射到 `family_id / variant_id / skeleton / focus / density / scan`
  - 不再通过旧 V4 fallback 链兜底
- `render_contracts.py`
  - 为每个 skeleton 明确 `slot_roles / structure_markers / motion_scope`
  - 以后 renderer 和 reviewer 都只认 contract
- `clean_pipeline.py`
  - 组合产出 `deck_intent / narrative_graph / layout_decisions / render_contracts`

## 切换原则

V5 切换不是今天就删掉旧代码，而是：

1. 新功能只往 V5 写，不再给旧 V4 主链加新设计能力。
2. V5 先跑定向任务、回归任务、再跑真实用户任务。
3. 当 V5 的命中率、稳定性、视觉验收都站住后，再逐步切主入口。
4. 旧 V4 在切换完成前只保留“兼容读取”和“应急回退”角色，不再承担未来设计演进。

## 当前已落地

- 已建立 V5 clean pipeline 骨架
- 已明确 V5 与旧 V4 repair/fallback 逻辑隔离
- 已支持基于 narrative role 直接产出 family / variant / skeleton / contract

## 下一步

1. 给 V5 增加正式 renderer，不再复用 V4 formal renderer。
2. 给 V5 增加独立 reviewer，只看 V5 contract 和最终 HTML。
3. 先迁移 `cover / agenda / journey_timeline / collaboration_matrix / value_matrix`。
4. 跑定向任务和真实任务双回归，确认 V5 不再出现“半新半旧”的问题。
