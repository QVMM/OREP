# V5 Slide Playbook Library

这份库解决“整页怎么设计”的问题，和 `v5_diagram_prompt_library` 分工不同：

- `slide_playbook_library`：决定本页采用什么表达打法、构图策略、信息密度、文字预算和失败样式。
- `diagram_prompt_library`：决定具体图示如何抽取节点、连线、布局和禁止事项。

## 使用方式

V5 流程中每页先生成 `page_expression_plan`，再根据 `page_role` 选择 `slide_playbook`，最后才生成 `diagram_spec` 和 MiMo 主体区 HTML。

推荐链路：

```text
page
  -> page_expression_plan
  -> slide_playbook
  -> diagram_spec
  -> MiMo body prompt
```

## 首批 Playbook

库文件：

- `docs/v5_slide_playbook_library.json`

首批覆盖：

- `cover_key_visual`
- `agenda_story_map`
- `policy_evidence_board`
- `problem_pressure_wall`
- `solution_big_picture`
- `architecture_system_map`
- `data_pipeline_trace`
- `algorithm_proof_panel`
- `practice_demo_stage`
- `evidence_chain_proof`
- `metric_dashboard_focus`
- `risk_response_matrix`
- `innovation_comparison`
- `team_execution_map`
- `roadmap_growth_path`
- `closing_memory_point`
- `content_support_focus`

## 核心原则

1. 每页先有主结论，再有布局。
2. 每页只允许一个第一视觉焦点。
3. 页面细节进入讲稿，不塞满主体区。
4. 图示优先使用对称、稳定、HTML/SVG 容易实现的结构。
5. 缺少真实证据时明确缺口，不伪造政策、日志、截图、团队照片。
6. 失败页优先回到表达计划或打法层重做，不直接降级成普通安全页。

