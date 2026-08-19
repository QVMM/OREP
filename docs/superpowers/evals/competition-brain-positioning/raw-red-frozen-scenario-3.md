run_time: `2026-08-02 18:57:46 CST`（Asia/Shanghai）
agent_task: `/root/red_frozen_s3`
model: `not exposed by runtime`
skill_loaded: `none`
rubric_seen: `no`

outer_prompt:

> 你是独立 RED 基线运行者。禁止读取任何 rubric、baseline、skill 或其他场景；禁止使用任何品牌/定位/文案 skill。只读取 `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/scenario-3-copy-rewrite.md` 中的用户任务，按普通通用能力直接作答。然后使用 apply_patch 新建 `/Users/liuyixing/项目/OREP/docs/superpowers/evals/competition-brain-positioning/raw-red-frozen-scenario-3.md`。文件必须包含 harness 元数据：run_time（Asia/Shanghai，调用 date 获取）、agent_task=`/root/red_frozen_s3`、model=`not exposed by runtime`、skill_loaded=`none`、rubric_seen=`no`、outer_prompt（原样记录本消息的任务约束摘要）；明确 `BEGIN VERBATIM MODEL OUTPUT` 与 `END VERBATIM MODEL OUTPUT`，边界内只放你对场景的原始最终答案。harness 元数据与边界标记不参与评分。不要读取或修改其他评测文件。完成后只报告已保存。

BEGIN VERBATIM MODEL OUTPUT

真正有效的备赛，既要看向赛场，也要沉到每一次训练。启发·竞赛大脑以 AI 技术串联项目管理、训练学习、路演评分与智能复盘，覆盖从赛前到赛后的备赛全流程。让职业院校师生在同一平台上组织项目、投入训练、完成评分与复盘，在持续打磨中走向成长。

END VERBATIM MODEL OUTPUT
