# zhdn 用户端页面与状态清单

## 范围规则

- 产品范围：`https://localhost:5174` 用户端。
- 视觉主源：运行中的 Chrome 页面。
- 结构补充：`frontend/user/src/router/index.js`、`views` 与 `components`。
- 不包含：`https://localhost:5173` 管理后台、不可达且未注册路由的旧 View。
- 兼容重定向保留在清单中，但不为与目标页完全相同的重定向单独绘制画板。
- 鉴权：`/intro`、`/login` 为 `requiresAuth:false, publicShell:true`；已登录访问时重定向 `/`。`/` 无 token 重定向 `/intro`。其余业务路由均为 `requiresAuth:true`，无 token 重定向 `/intro`。
- 版本记录：工作区根目录不是 Git 仓库，Task 1 commit 记为 `N/A`。

## 公共壳层

- Desktop：64px 顶栏；216–260px 左侧栏；主内容最大 1280px；340px AI rail。
- 标准桌面 Frame：`1680 × 889`（当前 Chrome CSS viewport）；侧栏在该宽度采用 218px（`13vw`），AI rail 展开时 340px 覆盖右侧内容。
- 主导航：首页、在线路演、PPT 制作、讲稿制作、文件中心、学习中心、考试中心、评分总结、任务管理、选题策划。
- 全局状态：搜索、日历、消息、帮助 Popover；账户菜单；升级权益 Dialog；退出确认；AI rail 收起/展开；Toast 四种语义状态。
- 视觉主源：`workspace-tokens.css` 的浅色暖橙体系；旧 Apple、深色 `orep-*` 仅在实际页面使用时按屏保留。

## 00 公共与认证

| 路由/组件 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/intro` | 产品介绍默认态；publicShell；已登录重定向 `/` | 未登录默认入口或账户菜单“产品介绍”；独立画板，不包含 Workspace 账户菜单 |
| `/login` | 登录默认、校验错误、提交中、登录失败；已登录重定向 `/` | Intro“开始使用”；画板 + 状态 |
| `/register` | 重定向 `/login` | 兼容直达；不单独绘制 |
| `/profile` | 个人资料默认、保存成功；需鉴权 | 账户菜单；画板 + Toast |
| WorkspaceTopbar | 搜索、日历、消息、帮助 | 4 个 Overlay |
| WorkspaceSidebar | 账户菜单、升级权益、退出确认 | Menu + Dialog + MessageBox |
| WorkspaceAiRail | 收起、展开、输入状态 | 组件状态 |

## 01 首页

| 路由 | 页面/状态 | 入口 |
|---|---|---|
| `/` | 首页默认态：最新点评、五维评分、本场得分、备赛脉搏、上场缺项、最近事项、训练路径、AI rail；无 token 重定向 `/intro` | 主导航/品牌 |
| `/track-match` | 重定向首页 | 旧兼容，不单独绘制 |

## 02 在线路演

| 路由/组件 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/online-meeting` | 路演大厅/列表默认态 | 画板 |
| OnlineMeeting | 创建本场 | Dialog |
| `/meeting/:id` | 会议室默认、问题清单、聊天、评分、屏幕侧栏、次视频区、质量菜单 | 会议列表/报告返回；画板 + Drawer/Panel/Menu |
| AudioRecorder | 开始评分；录制中 recording/scoring/completed/failed；终止/重开确认 | Dialog 集合 |
| `/meeting-history/:id` | 历史详情默认态 | 画板 |
| `/my-recordings` | 我的录制、删除确认 | 画板 + MessageBox |
| `/roadshow-chat/:meetingId` | 路演问答、帮助 | 画板 + Dialog |

## 03 内容制作

| 路由/状态 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/script-editor?tab=topic` | 选题策划默认、方向/证据/侧栏折叠 | 画板 + 状态 |
| `/script-editor?tab=ppt` | PPT 制作列表/工作台 | 画板 |
| `/script-editor?tab=script` | 讲稿制作列表/工作台 | 画板 |
| `/script-editor?tab=materials` | 文件中心默认、文件预览/下载 | 画板 + Dialog |
| ScriptList | 模板新建、另存模板、文档预览、团队切换、删除确认 | Dialog/Menu/MessageBox |
| `/script-editor/detail/:scriptId` | 讲稿编辑默认；添加角色、添加章节、另存模板 | 画板 + 3 Dialog |
| `/script-editor/template/:templateId` | 模板编辑兼容 | 与讲稿编辑共用 |
| `/ppt-generator` | PPT 生成默认、任务记录 | 画板 |
| `/ppt-editor` | PPT 编辑；历史记录、问卷资料、内容卡片规划、清空/切换确认 | 画板 + 2 Drawer + Panel + 2 MessageBox |
| `/ppt-history/:id` | PPT 历史详情；修复预览、同步小结、修复历史、破坏性确认 | 画板 + 3 Dialog + 4 MessageBox |
| `/resources` | PPT 资源模板默认态；源码可达、浏览器证据待采集 | 旧资源入口；画板 |

## 04 学习中心

| 路由 | 页面/状态 | 入口 |
|---|---|---|
| `/course-learning` | 课程列表默认、空、加载、错误 | 主导航 |
| `/course-learning/:courseId` | 课程详情默认 | 课程卡片 |
| `/course-learning/:courseId/lesson/:lessonId` | 课程播放器默认、完成/失败反馈 | 课时入口 |

## 05 考试中心

| 路由/状态 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/exam-system` | training/exam/wrong 三视图 | 3 状态画板 |
| `/exam-system/practice/:source` | chapter/wrong/random；加载、空、练习中、完成结果 | 训练集/错题本；画板变体 |
| `/exam-system/take/:paperId` | 正式答题、题目导航、选择、计时、交卷确认、自动交卷提示；提交结果（通过/未通过、人工评阅、错题） | 试卷列表；画板 + 结果状态 + MessageBox/Toast |
| `/exam-system/wrong-book` | 错题本默认/空 | 画板 |
| `/exam-system/favorites` | 收藏默认/空 | 画板 |

## 06 评分总结

| 路由/状态 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/statistics` | 我参加/我队伍；报告列表 | 2 状态画板 |
| `/ai-score-upload` | 上传输入、校验、处理中、完成、失败 | 画板状态集 |
| `/score-result/:meetingId` | 旧评分结果；源码可达、当前 UI 入口未发现 | 鉴权直达；兼容画板 |
| `/ai-score/report/:sessionId/result` | 新报告结果 | 画板 |
| `.../todos` | 待办/行动建议 | 画板 |
| `.../why` | 证据与扣分原因 | 画板 |
| `.../jury` | 多维评委；评委详情 sheet | 画板 + Sheet |
| `.../compare` | 对比 | 画板 |
| 报告结果 | 处方 accordion；团队同步 select/success | 状态 + Dialog |
| `/ai-score/report-id/:reportId/*` | reportId 同构入口 | 复用上述画板 |
| `/ai-score/:meetingId/*` | meetingId 兼容入口 | 复用上述画板 |
| `overview/dimensions/evidence/voice/presentation/actions` | 重定向 result/why/todos | 不单独绘制 |
| `/ai-score/report-prototype` | 报告原型默认态 | 鉴权直达；画板 |

## 07 任务管理

| 路由/状态 | 页面/状态 | 画板或 Overlay |
|---|---|---|
| `/project-team` | 团队/任务默认；stage/team/quick 折叠 | 画板状态 |
| ProjectTeam | 分配任务、编辑阶段、创建项目/成员分工 | 3 Modal |
| ProjectTeam | 任务详情、提交成果 | 2 Drawer |
| ProjectTeam | 交付查看、审核交付、证据详情 | Inspector + 2 Dialog |

## 08 全局组件与反馈

- Button：primary/secondary/text/danger；small/medium/large；default/hover/active/disabled/loading。
- Input：label/required/prefix/suffix/hint/error/focus/disabled/readonly。
- Card：default/elevated/hoverable。
- Chip、Badge、Status LED、Empty State、Toast、Dialog、Drawer、Popover、Dropdown、MessageBox。
- App Shell：Desktop；移动端仅作为响应式组件参考，本轮原型以桌面为主。

## 触发入口矩阵

| 页面/状态 | 浏览器触发入口 |
|---|---|
| 首页 | 左侧主导航“首页”或品牌按钮 |
| 在线路演 | 左侧主导航“在线路演”或首页“在线会议室/路演训练” |
| 创建本场 | 在线路演页“创建本场” |
| 会议室 | 在线路演会议列表的进入/加入按钮；报告返回会议入口 |
| 问题清单/聊天/评分/质量菜单 | 会议室工具栏对应按钮 |
| 评分录音开始/运行/终止 | 会议室“开始评分”及录音状态卡 |
| 会议历史详情 | 在线路演历史列表卡片 |
| 我的录制/删除确认 | 在线路演“我的录制”；录制项删除按钮 |
| 路演问答/帮助 | 旧评分结果“路演问答”；页面帮助按钮 |
| PPT 制作 | 左侧主导航“PPT制作” |
| 讲稿制作 | 左侧主导航“讲稿制作” |
| 文件中心 | 左侧主导航“文件中心” |
| 选题策划 | 左侧主导航“选题策划” |
| 模板新建/另存模板/文档预览/删除 | ScriptList 模板、更多、策划书和删除入口 |
| 讲稿编辑 | 讲稿列表卡片 |
| 添加角色/章节/另存模板 | 讲稿编辑工具栏对应按钮 |
| PPT 生成 | PPT 工作台生成入口或旧首页 QuickEntry |
| PPT 编辑 | PPT 工作台编辑入口或旧 AppHeader 入口 |
| PPT 历史详情 | PPT 生成任务记录卡片 |
| PPT 历史/问卷 Drawer | PPT 编辑器历史与问卷按钮 |
| 修复预览/同步小结/修复历史 | PPT 历史详情的单页修复、采用候选、修复历史入口 |
| 资源模板 | `/resources` 鉴权直达或旧资源入口 |
| 学习中心 | 左侧主导航“学习中心”或首页课程入口 |
| 课程详情 | 课程列表卡片 |
| 课程播放器 | 课程详情课时项 |
| 考试中心 | 左侧主导航“考试中心”或首页考试入口 |
| 专项练习 | 考试训练集、错题复习、随机练习入口 |
| 正式答题 | 考试试卷列表 |
| 错题本/收藏 | 考试首页对应入口 |
| 交卷确认/结果 | 答题页“交卷”；提交完成自动进入结果 |
| 评分总结 | 左侧主导航“评分总结”或首页“打开评分总结” |
| 上传视频评分 | 评分总结/在线路演“上传视频评分” |
| 旧评分结果 | `/score-result/:meetingId` 鉴权直达；当前 UI 入口未发现，待运行态确认 |
| 新报告 Result | 评分列表卡片、上传完成或会议评分完成 |
| 新报告 Why/Todos/Jury/Compare | 报告左侧/顶部子导航及 Result CTA |
| 处方 Accordion | Result 处方卡标题 |
| 团队同步 | Result 同步建议、单条处方或待办草稿入口 |
| 报告原型 | `/ai-score/report-prototype` 鉴权直达 |
| 任务管理 | 左侧主导航“任务管理”或首页任务入口 |
| 分配任务 | 任务页页头、空态或工作区“新建任务” |
| 编辑阶段 | 阶段标题编辑入口 |
| 创建项目/成员分工 | 创建项目、成员分工或邀请成员入口 |
| 任务详情 | 任务卡详情入口 |
| 提交成果 | 任务详情“提交成果”或任务操作入口 |
| 交付查看/审核/证据详情 | 交付项“查看”、审核按钮、证据锚点 |
| 搜索/日历/消息/帮助 | 顶栏搜索框、日历、铃铛、帮助按钮；搜索另支持 ⌘K |
| 账户菜单 | 左侧栏底部账户按钮 |
| 升级权益 | 侧栏版本区“查看升级权益 →” |
| 退出确认 | 账户菜单“退出登录” |
| AI rail | 右侧“展开 AI 助手”FAB 与 Rail“收起”按钮 |

## Figma 命名与交付类型

- 页面 Frame：`模块编号 / 路由语义 / 状态`，例如 `06 / Statistics / Default`。
- 动态路由 Frame：用语义占位符命名，不把测试数据 ID 写入 Frame 名；例如 `02 / Meeting Room / Default`。
- Overlay：`OV / 所属页面 / 类型 / 状态`，例如 `OV / Project Team / Dialog / Create Task`。
- Component：`C / 类别 / 名称 / 变体`，例如 `C / Button / Primary / Default`。
- `Dialog`：居中模态；`Drawer`：边缘滑出；`Popover`：锚点浮层；`MessageBox`：短确认框；`Sheet`：页面内详情面板；`Inspector`：交付物检查层；`Panel`：不遮罩的互斥区域。
- “画板 + 状态”不作为最终命名；下方原子交付矩阵中的每一行必须对应独立 Frame、组件 Variant 或 Overlay。
- `INT /` 表示仅需 Prototype reaction 的交互，不要求独立视觉 Frame；其结果视觉必须指向已列出的 Component Variant 或页面状态。

## 原子状态与 Overlay 交付矩阵

| Figma 名称 | 类型 | 触发入口 |
|---|---|---|
| `00 / Login / Default` | Frame | Intro“开始使用” |
| `00 / Login / Validation Error` | Frame state | 提交空表单 |
| `00 / Login / Submitting` | Frame state | 提交有效表单 |
| `00 / Login / Failed` | Frame state | 登录接口失败 |
| `OV / Global / Popover / Search` | Popover | 搜索框或 ⌘K |
| `OV / Global / Popover / Calendar` | Popover | 日历按钮 |
| `OV / Global / Popover / Messages` | Popover | 消息按钮 |
| `OV / Global / Popover / Help` | Popover | 帮助按钮 |
| `OV / Global / Menu / Account` | Menu | 账户按钮 |
| `OV / Global / Dialog / Upgrade` | Dialog | 查看升级权益 |
| `OV / Global / MessageBox / Logout` | MessageBox | 退出登录 |
| `OV / Meeting Room / Drawer / Issues` | Drawer | 问题清单 |
| `02 / Meeting Room / Chat` | Panel | 聊天按钮 |
| `02 / Meeting Room / Score` | Panel | 评分按钮 |
| `OV / Meeting / Dialog / Start Score` | Dialog | 开始评分 |
| `OV / Meeting / Dialog / Recording` | Dialog state | 录音状态卡 |
| `OV / Meeting / Dialog / Scoring` | Dialog state | 结束采集 |
| `OV / Meeting / Dialog / Completed` | Dialog state | 评分完成 |
| `OV / Meeting / Dialog / Failed` | Dialog state | 评分失败 |
| `OV / Meeting / MessageBox / Abort` | MessageBox | 终止评分 |
| `OV / Meeting / MessageBox / Restart` | MessageBox | 重新开始 |
| `OV / Script List / Dialog / From Template` | Dialog | 模板新建 |
| `OV / Script List / Dialog / Save Template` | Dialog | 另存模板 |
| `OV / Script List / Dialog / Document Preview` | Dialog | 策划书草稿 |
| `OV / Script List / MessageBox / Delete Script` | MessageBox | 删除讲稿 |
| `OV / Script Editor / Dialog / Add Role` | Dialog | 添加角色 |
| `OV / Script Editor / Dialog / Add Chapter` | Dialog | 添加章节 |
| `OV / Script Editor / Dialog / Save Template` | Dialog | 另存模板 |
| `OV / PPT Editor / Drawer / History` | Drawer | 历史记录 |
| `OV / PPT Editor / Drawer / Questionnaire` | Drawer | 问卷资料 |
| `OV / PPT Editor / MessageBox / Clear Current` | MessageBox | 新建并清空当前内容 |
| `OV / PPT Editor / MessageBox / Switch Task` | MessageBox | 进入设计渲染/切换任务 |
| `OV / PPT History / Dialog / Repair Preview` | Dialog | 单页修复 |
| `OV / PPT History / Dialog / Repair Summary` | Dialog | 采用候选或批量修复完成 |
| `OV / PPT History / Dialog / Repair History` | Dialog | 修复历史 |
| `OV / PPT History / MessageBox / New Material` | MessageBox | 新素材动作 |
| `OV / PPT History / MessageBox / Batch Repair` | MessageBox | 批量修复 |
| `OV / PPT History / MessageBox / Rollback` | MessageBox | 回滚版本 |
| `OV / PPT History / MessageBox / High Cost Action` | MessageBox | 高成本动作 |
| `05 / Exam Practice / Loading` | Frame state | 进入专项练习 |
| `05 / Exam Practice / Empty` | Frame state | 无题目数据 |
| `05 / Exam Practice / Taking` | Frame | 题目加载完成 |
| `05 / Exam Practice / Result` | Frame | 练习完成 |
| `05 / Exam Taking / Taking` | Frame | 试卷列表进入 |
| `OV / Exam Taking / MessageBox / Submit` | MessageBox | 手动交卷 |
| `05 / Exam Taking / Result Passed` | Frame state | 交卷后通过 |
| `05 / Exam Taking / Result Failed` | Frame state | 交卷后未通过 |
| `05 / Exam Taking / Result Manual Review` | Frame state | 主观题待人工评阅 |
| `OV / Report Result / Dialog / Team Sync Select` | Dialog state | 同步建议/处方/待办 |
| `OV / Report Result / Dialog / Team Sync Success` | Dialog state | 确认生成完成 |
| `OV / Report Jury / Sheet / Member` | Sheet | 点击评委席 |
| `OV / Project Team / Dialog / Create Task` | Dialog | 新建任务 |
| `OV / Project Team / Dialog / Edit Stage` | Dialog | 编辑阶段 |
| `OV / Project Team / Dialog / Create Project` | Dialog | 创建项目/成员分工 |
| `OV / Project Team / Drawer / Task Detail` | Drawer | 任务卡详情 |
| `OV / Project Team / Drawer / Submit Delivery` | Drawer | 提交成果 |
| `OV / Project Team / Inspector / Delivery` | Inspector | 查看交付 |
| `OV / Project Team / Dialog / Review Delivery` | Dialog | 审核交付 |
| `OV / Project Team / Dialog / Evidence` | Dialog | 证据锚点 |
| `C / AI Rail / Collapsed` | Component variant | Rail“收起” |
| `C / AI Rail / Expanded` | Component variant | 右侧展开 FAB |
| `C / AI Rail / Input Active` | Component variant | AI 输入框 focus |
| `C / Toast / Success` | Component variant | 保存/提交成功 |
| `C / Toast / Warning` | Component variant | 自动交卷/业务警告 |
| `C / Toast / Error` | Component variant | 接口或操作失败 |
| `C / Toast / Info` | Component variant | 普通提示 |
| `02 / Meeting Room / Screen Sidebar Expanded` | Frame state | 屏幕共享侧栏展开 |
| `02 / Meeting Room / Screen Sidebar Collapsed` | Frame state | 屏幕共享侧栏折叠 |
| `02 / Meeting Room / Secondary Videos Expanded` | Frame state | 次视频区展开 |
| `02 / Meeting Room / Secondary Videos Collapsed` | Frame state | 次视频区折叠 |
| `OV / Meeting Room / Menu / Quality` | Menu | 质量按钮 |
| `03 / Topic / Direction Expanded` | Frame state | 方向分组标题 |
| `03 / Topic / Evidence Expanded` | Frame state | 证据分组标题 |
| `03 / Topic / Rail Collapsed` | Frame state | 收起侧栏 |
| `OV / Script List / Menu / Team Switcher` | Menu | 团队切换 |
| `OV / Materials / Dialog / File Preview` | Dialog | 文件项“预览” |
| `INT / Materials / Download` | Prototype interaction，无独立视觉 Frame | 文件预览“下载”；点击后停留在预览并显示 Success Toast |
| `OV / Online Meeting / Dialog / Create Meeting` | Dialog | 在线路演“创建本场” |
| `OV / Recordings / MessageBox / Delete` | MessageBox | 录制项删除按钮 |
| `OV / Roadshow Chat / Dialog / Help` | Dialog | 路演问答帮助按钮 |
| `04 / Course List / Empty` | Frame state | 无课程数据 |
| `04 / Course List / Loading` | Frame state | 课程加载中 |
| `04 / Course List / Error` | Frame state | 课程接口失败 |
| `04 / Lesson Player / Completed` | Frame state | 完成课程 |
| `04 / Lesson Player / Failed` | Frame state | 播放/提交失败 |
| `05 / Exam Practice / Chapter` | Frame variant | chapter 练习入口 |
| `05 / Exam Practice / Wrong` | Frame variant | wrong 练习入口 |
| `05 / Exam Practice / Random` | Frame variant | random 练习入口 |
| `OV / Exam Taking / Toast / Auto Submit` | Toast | 计时结束自动交卷 |
| `05 / Exam Taking / Result Wrong Answers` | Frame state | 结果页错题区域 |
| `05 / Wrong Book / Empty` | Frame state | 错题本无数据 |
| `05 / Favorites / Empty` | Frame state | 收藏无数据 |
| `06 / Statistics / Participated` | Frame state | “我参加的会议”标签 |
| `06 / Statistics / Team` | Frame state | “我队伍的会议”标签 |
| `06 / Score Upload / Input` | Frame state | 上传视频评分入口 |
| `06 / Score Upload / Validation` | Frame state | 无效输入 |
| `06 / Score Upload / Processing` | Frame state | 提交有效视频 |
| `06 / Score Upload / Completed` | Frame state | 评分完成 |
| `06 / Score Upload / Failed` | Frame state | 评分失败 |
| `06 / Report Result / Prescription Expanded` | Frame state | 处方卡标题 |
| `07 / Project Team / Stage Collapsed` | Frame state | stage 分组标题 |
| `07 / Project Team / Team Collapsed` | Frame state | team 分组标题 |
| `07 / Project Team / Quick Collapsed` | Frame state | quick 分组标题 |
| `03 / PPT Editor / Card Planning` | Panel | 内容卡片规划入口 |

## 报告完整路由映射

- 主画板 `06 / Report Result / Default`：`/ai-score/report/:sessionId/result`、`/ai-score/report-id/:reportId/result`、`/ai-score/:meetingId/result`。
- 主画板 `06 / Report Todos / Default`：三个父路径各自的 `/todos`；`voice`、`presentation`、`actions` 重定向并复用此画板。
- 主画板 `06 / Report Why / Default`：三个父路径各自的 `/why`；`dimensions`、`evidence` 重定向并复用此画板。
- 主画板 `06 / Report Jury / Default`：三个父路径各自的 `/jury`。
- 主画板 `06 / Report Compare / Default`：三个父路径各自的 `/compare`。
- 三个父路径的空子路径均重定向 `/result`；`overview` 重定向并复用 Result 画板。

## 浏览器验收夹具

- 当前账号：已登录的 `admin` 用户；不得在原型采集时执行真实上传、创建会议或删除操作。
- 已知稳定样例：`/ai-score/report/23/result`；`/statistics`；`/`。
- 动态路由取值从现有列表的可见链接提取，不猜测 ID；首次采集后将实际 URL 回填到捕获 manifest。
- `script-editor` 必须分别采集 `tab=topic`、`tab=ppt`、`tab=script`、`tab=materials`。
- “每个主路由”指每个实际渲染不同 View 或不同 tab 的路由；同构 `reportId/sessionId/meetingId` 父路径与纯重定向不重复截图，但必须验证重定向目标。
- 数据前置不足时，保留源码可达画板并在 manifest 标记 `source-only`，不得编造浏览器截图证据。

## 需要补充运行态证据的已纳入项

- `/resources`、`/ppt-generator`、`/ppt-editor`、`/score-result/:meetingId` 均为已注册鉴权路由，必须绘制；需补充当前浏览器视觉证据。
- `MeetingList.vue`、`AiScoreResult.vue` 未直接挂路由，确认是否作为嵌套组件出现。
- `/privacy`、`/terms`、`/contact` 仅在旧 Footer 中存在且路由缺失，不纳入当前可进入页面。
- 未知 URL 无 catch-all；不制作虚构 404 页面，只保留通用错误组件。
- 会议室“移动更多”和移动底栏只进入响应式参考组件，不作为本轮桌面核心 Overlay 验收项。

## 完成判定

- 每个“画板”条目在 Figma 中存在对应 Frame。
- 每个 Overlay/状态条目存在独立 Frame、组件变体或 Prototype Overlay；`INT /` 条目只验收 reaction 与目标状态，不计独立 Frame。
- 每个主路由至少有一个 Chrome 运行态证据。
- 重定向和同构兼容入口不重复绘制，但在 Prototype Flow 说明复用关系。
