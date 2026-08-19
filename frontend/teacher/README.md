# 竞赛大脑 · 教师端

以**方便老师日常带队**为第一原则：工作台驱动，配置沉二级。

## 启动

```bash
cd frontend/teacher
npm install
npm run dev
```

默认：http://localhost:5175  

- 登录页：`/login`（`POST /api/auth/login`，token 与学生端共用 `orep_user_token`）  
- 未登录可直接进工作台，使用 **演示 mock**  
- 后端默认代理：`localhost:8080`  
- 学生端联调预览：会议/报告链到 `localhost:5174`

## 结构

```
src/
  components/TeacherShell.vue   # 壳：轨 + 二级 + 顶栏上下文
  config/nav.js                 # 一级/二级导航
  mock/workbench.js             # 演示数据（后续换 API）
  stores/context.js             # 当前项目/营/队
  views/                        # 业务页
```

## 一级导航

| 模块 | 老师用来 |
|---|---|
| 工作台 | 今天先批谁、开哪场会、审哪些待办 |
| 集训营 | 计划、批改、进度；课/题/考在二级 |
| 路演 | 场次优先；录制/PPT/讲稿二级 |
| 复盘 | 待审、报告、AI 待办（原版备份） |
| 团队 | 项目 + 成员组队 + 协作任务 |
| 资源 | 文件版本与可见范围 |
| 数据 | 只读趋势 |

## 当前主路径

```text
工作台（左队列 / 右处理台）
  → 连续批改、催交、审核 AI 待办

备赛团队
  → /team/create 三步组建向导
  → /team/:teamId 一站式团队工作台
```

旧入口 `/team/members`、`/team/tasks` 已重定向到团队列表；成员、任务和文件改在团队工作台内处理。

设计 token 复用 `frontend/user/src/styles`。
