# 在线会议与会议回放栏目标签移除设计

## 目标

移除在线会议页和会议回放列表页主标题上方重复的“现场讲解”栏目标签，让页头直接从页面主标题开始。

## 设计

- 从 `OnlineMeeting.vue` 删除 `<span class="page-kicker">现场讲解</span>`。
- 从 `MyRecordings.vue` 删除 `<span class="page-kicker">现场讲解</span>`。
- 删除两个文件中各自不再使用的 `.page-kicker` 样式规则。
- 保留主标题、说明文字、状态信息和页头操作按钮。
- 不修改 `MeetingReplay.vue` 单场回放详情页及导航栏中的“现场讲解”模块名称。

## 验收标准

- `/online-meeting` 页头不再显示“现场讲解”，仍显示“在线会议”及原有操作区。
- `/my-recordings` 页头不再显示“现场讲解”，仍显示“会议回放”及原有操作区。
- 两个组件中不再存在无用的 `.page-kicker` 规则。
- 页面无布局溢出，前端生产构建通过。
