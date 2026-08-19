# Sprint Plan · 路演评议席硬规格

- 日期：2026-08-15
- 规范：`docs/路演评议席-四件硬规格.md`
- 计划书（唯一状态源）：`docs/路演评议席-开发计划书.md`
- Tech Lead：本编排会话
- Git：不 commit、不建 worktree

## 本 sprint 目标

打通步骤 1：`docketId` 纯函数 → 表 → bind → 完成回调写 run。  
不改结论首页，不点亮席位，不宣称「评议席已上」。

## 分工（同时只改互不重叠的文件）

| 角色 | 本 sprint | 状态 |
|------|-----------|------|
| Tech Lead | 计划书、仲裁、门禁措辞 | 进行中 |
| Backend Engineer | Task 1–4（docket / 表 / bind / run） | **启动 Task 1** |
| Prompt Engineer | 待命（步骤 4 才开工） | 待命 |
| Frontend Engineer | 待命（步骤 7 才开工） | 待命 |
| QA Reviewer | Task 1 交卷后对照计划书第 8 节复检 | 待命 |
| Standards Keeper | 契约已写入计划书第 6 节 | 本轮无新代码 |

## 完成定义

`mvn -q -Dtest=DocketIdServiceTest test` 通过，且计划书 Task 1 勾选。
