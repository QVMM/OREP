# OREP AI 生成 PPT 式 HTML 多模型配置说明

## 目标

PPT 生成链路不再把所有任务都硬绑到同一个 Qwen 模型，而是拆成三个角色：

| 角色 | 配置前缀 | 推荐用途 |
| --- | --- | --- |
| 文本推理模型 | `PPT_TEXT_*` | 问卷结构化、大纲、故事线、评分点、内容增强 |
| HTML 生成/修复模型 | `PPT_HTML_*` | Round4 HTML 初稿、单页 HTML 定向修复 |
| 视觉检察官模型 | `PPT_VISION_*` | 渲染截图后识别错位、拥挤、无焦点、流程漂移等视觉问题 |

## 推荐配置

不要把真实 key 写进代码或文档。请只写入本地 `.env` 或服务器环境变量。

```env
# 文本/大纲/故事线：MiMo-V2-Pro（小米接口模型 ID 为小写）
PPT_TEXT_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
PPT_TEXT_API_KEY=替换为你的本地环境变量
PPT_TEXT_MODEL=mimo-v2-pro

# HTML 初稿/单页修复：先用 MiMo-V2-Pro 做 A/B，若 CSS 稳定性不如 coder 模型再切回
PPT_HTML_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
PPT_HTML_API_KEY=替换为你的本地环境变量
PPT_HTML_MODEL=mimo-v2-pro

# 视觉检察官：Qwen 多模态或 MiMo-V2-Omni 二选一测试
PPT_VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
PPT_VISION_API_KEY=替换为你的本地环境变量
PPT_VISION_MODEL=qwen3.6-plus

# 如果测试 MiMo 全模态，可改为：
# PPT_VISION_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
# PPT_VISION_MODEL=mimo-v2-omni

# 默认不在生成链路里全量跑视觉审查，避免耗时失控。
PPT_VISION_REVIEW_ENABLED=false
PPT_VISION_REVIEW_MAX_PAGES=8
```

## 视觉审查接口

视觉审查会把 HTML 渲染成 `1920x1080` 截图，再调用 `PPT_VISION_*` 模型，返回严格 JSON。

```http
POST /api/ppt/task/{task_id}/visual-review
Content-Type: application/json

{
  "page_indices": [1, 2, 8, 31],
  "max_pages": 4,
  "auto_repair": true,
  "use_ai_repair": true,
  "recheck_after_repair": true
}
```

如果不传 `page_indices`，系统会优先选择关键页和本地质量报告中有风险的页面，最多审查 `PPT_VISION_REVIEW_MAX_PAGES` 页。

当 `auto_repair=true` 时，系统会执行闭环：

1. 视觉模型审查截图并输出 JSON。
2. 系统把 `problems`、`repair_brief`、`screenshot_path` 转成单页修复的 `repair_context`。
3. HTML 修复模型根据视觉 JSON 重写该页。
4. 修复后重新渲染截图并复检一次。
5. 报告中会包含 `repairs` 和 `recheck_pages`。

## 视觉检察官输出方向

视觉模型只负责判断，不直接修改 HTML。它应该输出：

- 页面视觉分数。
- 是否需要修复。
- 问题类型，如 `layout_overlap`、`layout_crowded`、`no_visual_focus`、`diagram_drift`。
- 给 HTML 修复模型的明确修复指令。

后续修复模型再根据这个 JSON 执行单页重写。

## 安全注意

任何发到聊天、文档、Git 记录里的 API key 都应视为泄露，需要在平台后台轮换。
