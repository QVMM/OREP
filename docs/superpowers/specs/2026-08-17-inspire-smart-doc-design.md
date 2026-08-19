# 启发 Office · 智能文档设计

> 日期：2026-08-17  
> 状态：待评审后进入实现  
> 标准产品：金山文档「智能文档」（Block 文档，`.otl` 一类）  
> 引擎：TipTap（ProseMirror）+ Vue 3  
> 视觉：布局对标金山；颜色、字号、控件尺寸遵守 `frontend/user/DESIGN.md`

---

## 1. 要做成什么

在启发 Office 里新增一种文档：**智能文档**。用户打开后是一篇可连续书写的文档，用 `/` 或工具栏插入块：段落、标题、表格、图片、文件、分栏、高亮块、日期、代码、引用、音视频、表情、超链接、分隔线、内容保护区、思维导图、流程图。

它不是：

- Collabora 里的 Word / Excel（继续保留，管标准 Office 文件）
- 金山「智能表格」（工作表 + 数据表，另立项）
- 小启聊天窗口本身（小启是侧栏大脑，往文档里读写）

**小启 / AI 本期不做。** 先把文档编辑器做到接近参考图，AI 总结、帮我写、侧栏小启全部后置。

成功标准（文档做好即可演示）：

1. 列表里能「新建智能文档」，进入独立编辑器，不进 Collabora iframe。
2. 版式对齐参考图：顶栏 + 一条格式条 + 左侧目录 + 大标题 + 元信息 + `/` 写正文。
3. 输入会自动保存；刷新不丢。

---

## 2. 和现有系统的边界

```text
启发 Office 列表  /inspire-office
├── Word / Excel / PPT     → 现有 InspireOfficeWorkbench + Collabora/WOPI
└── 智能文档 (sdoc)        → 新 SmartDocEditor（TipTap）
                              └── 画布（AI 侧栏后置）
```

| 沿用 | 新建 |
|---|---|
| 列表、范围（个人/项目/团队）、权限、重命名、复制、删除、资源中心同步 | 文档 JSON 存取、TipTap schema、块组件 |
| `inspire_office_document` 元数据（title/scope/team） | `ext = sdoc`，内容不走 WOPI |
| 版本表思路（快照） | JSON 快照，不是二进制 Office |
| `DESIGN.md` + `--ds-*` | 按参考图做金山式布局的专用 CSS |

编辑路由：`/inspire-office/sdoc/:id`  
工作台分屏里若打开 sdoc，该窗格渲染 TipTap，不渲染 Collabora。

---

## 3. 信息架构

### 3.1 页面结构（以用户提供的金山截图为准）

参考图结构，从上看：

1. **应用顶栏**：返回列表、文档标题（可改）、收藏位预留、保存态。分享等后置。
2. **一条格式条**（不是 Office 多行 Ribbon）：撤销/重做、段落样式、字号、B/I/U、高亮、颜色、代码、列表、缩进、插入。颜色用竞赛大脑橙，不用金山紫。
3. **左栏「目录 / 要点」**：无标题时显示「在文中使用标题样式即可生成目录」。
4. **主区白纸通栏**（参考图是满宽白底，不是灰底小纸卡）：
   - 大标题占位「输入标题」
   - 元信息：创建者、更新时间（评论数可先占位 0）
   - 正文占位：输入正文或 `/` 插入内容
   - 空文档快捷入口：导入、模板（**「AI 帮我写 / AI 总结」先不做**）
5. **底栏**：字数、缩放（P1）。

```text
┌──────────────────────────────────────────────────────────┐
│ ←  标题          已保存                                  │
├──────────────────────────────────────────────────────────┤
│ ↩ ↪ │ 正文 ▾ 16 │ B I U │ 高亮 色 │ 列表 │ + 插入        │
├──────────┬───────────────────────────────────────────────┤
│ 目录 要点│  输入标题                                     │
│          │  创建者 · 今天更新                            │
│ 使用标题 │  | 输入正文或 / 插入                          │
│ 即可生成 │    导入    模板                               │
└──────────┴───────────────────────────────────────────────┘
```

- 主区纯白，无卡片投影。
- 正文 `--ds-ink`，16px / 1.75。
- 主按钮、焦点：`#c43a12`。
- 不要 WPS 紫、不要 Collabora 工具带、不要右下角 AI 伴侣。

块交互（金山交互，我们的视觉）：

- 悬停块左侧出现六点手柄：上移/下移/删除/转成…
- 空段输入 `/` 弹出插入菜单（分类：基础 / 媒体 / 竞赛 / 小启）
- 选中文字：浮层（粗斜链、高亮、问小启）
- 不默认铺满一条 Office 式功能 Ribbon

### 3.2 文档数据

TipTap JSON（ProseMirror doc）：

```json
{
  "type": "doc",
  "content": [
    { "type": "heading", "attrs": { "level": 1 }, "content": [{ "type": "text", "text": "路演提纲" }] },
    { "type": "paragraph", "content": [{ "type": "text", "text": "…" }] }
  ]
}
```

存储：

- 表 `inspire_smart_doc`：`document_id`（FK 到 `inspire_office_document`）、`content_json`（MEDIUMTEXT）、`schema_version`、`updated_at`
- `inspire_office_document.ext = sdoc`
- 自动保存：debounce 800–1200ms，`PUT /api/inspire-office/sdoc/{id}`
- 版本：沿用 `inspire_office_version`，`storage_path` 指向 json 文件或把 json 放进现有 blob 策略
- 冲突：P0 后写覆盖 + `updated_at` 乐观锁；P2 再上 Yjs 协同

---

## 4. 块清单（以金山为标准，分期交付）

| 块 | 对标 | 阶段 | 实现要点 |
|---|---|---|---|
| 段落 / 标题 1–3 / 列表 / 待办 | 基础书写 | P0 | TipTap starter |
| 粗斜删、行内代码、链接 | 选区 | P0 | mark |
| 分隔线 | `/` | P0 | horizontalRule |
| 引用 | `/` | P0 | blockquote |
| 代码块 | `/` | P0 | 语言标签，等宽 |
| 高亮块 | 金山高亮块 | P0 | 自定义 Node + 表情/色 |
| 图片 | 本地上传 | P0 | 走现有 `/api/upload` |
| 表格 | 金山文档表（排版表，非智能表） | P1 | `@tiptap/extension-table` |
| 分栏 | 2/3 栏 | P1 | 自定义 columns 节点 |
| 本地文件 / 云文档卡片 | 插入附件、链到启发 Office / 资源中心 | P1 | 自定义 fileCard / cloudDoc |
| 日期、表情、音视频 | 插入 | P1 | 节点或 mark |
| 内容保护区 | 金山同名能力 | P2 | 自定义节点 + 角色可读/可编 |
| 思维导图 | 文档内嵌 | P3 | 块内嵌独立图编辑器 |
| 流程图 | 文档内嵌 | P3 | 同上 |
| 智能表格块 | 嵌 ksheet 一类 | **不做本期** | 另立项 |

P0 不包含协同光标、评论、目录、导出 Word。

---

## 5. 小启联动（后置，文档做好再做）

本期不接小启。参考图里的 WPS AI、AI 总结、AI 帮我写、双击唤起 AI、底栏 AI 伴写全部不做。

文档稳定后另开阶段：选区问小启、`/` 技能、写回确认。到时小启仍是唯一对话入口。文档编辑器只提供**选区、文档摘要、写回命令**。

| 入口 | 行为 |
|---|---|
| 选区浮层「问小启」 | 把纯文本 + 块 JSON 片段带进当前/新会话，`context.type = inspire_sdoc` |
| `/` → 小启技能 | 复用 `GET /api/assistant/skills`，执行后 `insertContent` |
| 右侧小启 | 复用 `assistant-core`，会话绑定 `documentId` |
| 小启工具 | `sdoc.get` / `sdoc.replaceSelection` / `sdoc.insertBlocks`，写操作必须现有「确认后再写」 |

竞赛向技能（P1）：

- 把选中段变成训练日任务书结构
- 提炼路演三点
- 按当前训练营补一节课大纲
- 把材料改成学生能交的清单

不接 TipTap 官方付费 AI。

---

## 6. 权限与范围

与启发 Office 一致：

- 个人：仅所有者
- 项目 / 团队：团队成员可看可编（P0 不细分批注权限）
- 内容保护区（P2）：块级覆盖，未授权只见占位
- 教师端：P1 只读或同编辑器打开（先学生端做完）

---

## 7. 非目标（写死，避免做成第二个金山全站）

- 不替换 Collabora
- 不做智能表格 / 多维表
- P0 不做多人实时协同
- 不做完整 Word 往返保真
- 不在编辑器里做第二个小启产品

---

## 8. 风险

| 风险 | 处理 |
|---|---|
| 金山块太多，P0 铺太大 | 严格按上表分期，P0 必须能写能存能问小启 |
| TipTap table 与金山手感差 | P1 单独打磨，不在 P0 承诺 |
| 导图/流程自研过大 | P3 嵌现成开源图编辑，当块 iframe/canvas |
| JSON 变大 | 图和文件只存 URL |
| 与 Collabora 工作台抢路由 | `ext===sdoc` 分支，列表用新类型图标 |

---

## 9. 文件落点（实现时）

```text
frontend/user/src/views/inspire-office/smart-doc/
  SmartDocEditor.vue          页壳（顶栏+纸+侧栏）
  SmartDocCanvas.vue          TipTap 挂载
  slash/SlashMenu.vue
  bubble/SelectionToolbar.vue
  nodes/HighlightBlock.vue
  nodes/FileCard.vue
  ...
  schema/smartDocExtensions.js
  persist/useSmartDocSave.js
  xiaoqi/useSmartDocAssistant.js

frontend/user/src/styles/smart-doc.css     纸张布局，只用 --ds-*

backend/.../inspire/sdoc/
  SmartDocService.java
  SmartDocController 挂在 /api/inspire-office/sdoc
```
