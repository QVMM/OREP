# 竞赛大脑用户端高保真 Figma 原型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Figma 文件 `N3tbAR4UMBd4nhcVfL2Tap` 中建立覆盖 `https://localhost:5174` 用户端全部页面、子界面、弹窗和主要交互的高保真桌面原型。

**Architecture:** 以 Vue 路由和源码建立范围清单，以 Chrome 运行页面作为视觉事实来源；先构建设计基础和公共组件，再按业务模块分 Figma Page 增量创建画板与 Overlay，最后连接原型并逐屏截图验收。网页捕获只作为像素和图片参考，可编辑画板使用 Figma 组件、变量、样式和实例构建。

**Tech Stack:** Vue 3/Vite 源码、Chrome Browser 控制、Figma Design、Figma Plugin API、`generate_figma_design`、Figma Prototype reactions。

---

### Task 1: 建立页面、状态与触发入口清单

**Files:**
- Read: `frontend/user/src/router/index.js`
- Read: `frontend/user/src/views/**/*.vue`
- Read: `frontend/user/src/components/**/*.vue`
- Create: `docs/superpowers/plans/2026-07-14-zhdn-screen-inventory.md`

- [x] **Step 1:** 从路由文件提取路径、组件、鉴权和重定向，写入清单。
- [x] **Step 2:** 搜索 `el-dialog`、`el-drawer`、`el-popover`、`el-dropdown`、`v-if`、`visible`、`open` 和 `show`，补充弹窗、抽屉与条件状态。
- [x] **Step 3:** 将页面按 `首页/在线路演/内容制作/学习/考试/评分/任务/账户与全局` 分组，并为每项记录浏览器触发入口。
- [x] **Step 4:** 对照 `https://localhost:5174` 主导航，确认不存在遗漏的主模块。
- [x] **Step 5:** 检查清单中每个路由都有页面名、默认态和交互状态；根目录非 Git 仓库，因此记录“commit N/A”。

### Task 2: 采集视觉基准与产品字体

**Files:**
- Read: `frontend/user/src/**/*.css`
- Read: `frontend/user/src/**/*.vue`
- Create: `.superpowers/brainstorm/zhdn-capture-manifest.json`

- [ ] **Step 1:** 从 CSS 变量、全局样式和布局组件确认字体族、主色、背景、边框、圆角、阴影和布局尺寸。
- [ ] **Step 2:** 在 Chrome 中按清单访问每个路由，记录最终 URL、页面标题、视口、可见主区域和滚动高度。
- [ ] **Step 3:** 捕获每个主页面默认态，并对含图片页面启动 `generate_figma_design` 参考捕获。
- [ ] **Step 4:** 逐个触发菜单、抽屉、标签、弹窗和表单校验，记录状态名称与触发控件。
- [ ] **Step 5:** 验证清单中的每项都有浏览器证据或明确标记为源码可达但当前数据不可达。

### Task 3: 检查 Figma 文件并建立模块 Pages

**Target:** Figma file `N3tbAR4UMBd4nhcVfL2Tap`

- [x] **Step 1:** 只读检查现有 Pages、顶层节点、变量、样式和组件；当前已知 `Page 1` 为空。
- [x] **Step 2:** 检查 Code Connect 文件；若无匹配，记录 `N/A`，再检查现有画板实例；空文件则记录 `N/A`。
- [x] **Step 3:** 检查可用 Figma libraries，再决定复用库资产或创建本地基础组件。
- [x] **Step 4:** 创建 `00 Foundations` 至 `09 Prototype Flow` Pages，并移除或重命名空白 `Page 1`。
- [x] **Step 5:** 重新读取 Pages，确认名称、顺序和数量正确。

### Task 4: 建立 Foundations、变量、样式与公共组件

**Target:** Figma page `00 Foundations`

- [x] **Step 1:** 创建颜色、间距、圆角和阴影变量；Free/Starter 模式限制下使用单一默认模式。
- [x] **Step 2:** 创建并验证产品字体文本样式，显式检查实际字体族而非默认 Inter。
- [x] **Step 3:** 创建侧栏、顶栏、AI 助手栏、按钮、输入框、标签、徽标、卡片和表单控件组件。
- [x] **Step 4:** 创建菜单、Dialog、Drawer、Toast、空状态、加载态和错误态组件。
- [x] **Step 5:** 截图检查组件变体，确认无裁切、重叠、错误字体和占位文本。

### Task 5: 构建首页、在线路演与任务管理

**Target Pages:** `01 首页`, `02 在线路演`, `07 任务管理`

- [ ] **Step 1:** 创建每个页面的 1440px 桌面 wrapper，并置于不重叠的画布位置。
- [ ] **Step 2:** 使用公共侧栏、顶栏和 AI 助手实例构建页面骨架。
- [ ] **Step 3:** 按浏览器基准填充首页、路演大厅/列表/会议室/历史/录制和任务团队内容。
- [ ] **Step 4:** 为创建会议、加入会议、录制、成员和任务操作创建 Overlay 状态。
- [ ] **Step 5:** 分区截图并与浏览器基准比较，修复布局、字体、图片和层级差异。

### Task 6: 构建内容制作全流程

**Target Page:** `03 内容制作`

- [ ] **Step 1:** 创建 PPT、讲稿、文件中心和选题策划默认态画板。
- [ ] **Step 2:** 创建 PPT 模板、生成、编辑、预览、历史详情和下载状态。
- [ ] **Step 3:** 创建讲稿列表/编辑、材料上传/预览/文件操作和选题策划状态。
- [ ] **Step 4:** 创建生成中、成功、失败、未保存确认、上传和删除确认 Overlay。
- [ ] **Step 5:** 对含图片和 PPT 预览的区域传递捕获图像资源，并检查可编辑层结构。

### Task 7: 构建学习与考试全流程

**Target Pages:** `04 学习中心`, `05 考试中心`

- [ ] **Step 1:** 创建课程列表、课程详情和课程播放器画板。
- [ ] **Step 2:** 创建考试首页、练习、答题、结果、错题本和收藏画板。
- [ ] **Step 3:** 创建题目导航、答案选择、收藏、提交确认、计时与结果详情状态。
- [ ] **Step 4:** 补充空列表、加载、无权限和网络错误状态。
- [ ] **Step 5:** 测试从课程/考试入口到详情再返回的完整点击路径。

### Task 8: 构建评分总结与报告详情

**Target Page:** `06 评分总结`

- [ ] **Step 1:** 创建评分报告列表及“我参加/我队伍”标签状态。
- [ ] **Step 2:** 创建发起路演评分和上传视频评分的输入、处理中、完成和失败状态。
- [ ] **Step 3:** 创建评分结果及当前真实可达的 Result、Why、Jury、Compare 和 Todos 子界面；记录 Overview/Dimensions/Evidence/Voice/Presentation/Actions 到现行页面的重定向复用关系。
- [ ] **Step 4:** 使用报告导航、证据卡、维度卡、风险徽标和建议卡组件实例。
- [ ] **Step 5:** 对照当前已打开的 `/statistics` 与 `/ai-score/report/23/result` 页面逐屏验收。

### Task 9: 构建账户与全局界面

**Target Page:** `08 账户与全局状态`

- [ ] **Step 1:** 创建登录、个人资料和账户菜单画板。
- [ ] **Step 2:** 创建全局搜索、通知、帮助、升级权益和快捷键状态。
- [ ] **Step 3:** 创建全局确认框、Toast、权限错误、加载和空状态；由于路由无 catch-all，不创建虚构 404 页面。
- [ ] **Step 4:** 将全局 Overlay 组件实例应用到对应业务画板。
- [ ] **Step 5:** 检查遮罩层级、关闭区域、焦点顺序和返回路径。

### Task 10: 连接原型并完成验收

**Target Page:** `09 Prototype Flow`
- Modify: `docs/superpowers/plans/2026-07-14-zhdn-screen-inventory.md`

- [ ] **Step 1:** 建立主导航、返回、卡片详情、CTA、标签、菜单、抽屉和弹窗 reactions。
- [ ] **Step 2:** 建立首页→内容制作→预览、在线路演→会议→报告、学习→课程、考试→答题→结果四条核心流程。
- [ ] **Step 3:** 在 `09 Prototype Flow` 创建流程入口和说明，确保每条路径可重置。
- [ ] **Step 4:** 逐屏截图检查字体、颜色、间距、图片、裁切、重叠和占位文本。
- [ ] **Step 5:** 逐项勾选页面清单，确认所有路由、子界面和弹窗均有对应节点。
- [ ] **Step 6:** 打开 Figma 原型演示并测试所有主要路径无死路。
