# PPT 生成三期改造规划

> 原则：只许更好，不许更差。每期有验收门禁，通过后再进入下一期。

## 总目标

1. 服务不被 PDF/渲染拖死  
2. 上传后生成不再 Session not found  
3. 历史只认 job_id，点得进去  
4. 中断可重跑/可续  
5. 用户主入口收敛到 `/ppt-editor`

---

## P0 止血与统一体验（本迭代优先）

### 改动范围

| 项 | 内容 |
|----|------|
| P0-1 | Session/Job 磁盘 sidecar + 紧凑 events（已有则加固） |
| P0-2 | PDF 子进程轻量解析固化进源码与 deploy 树 |
| P0-3 | workers=1 写死 + 发布说明禁止热补丁 |
| P0-4 | 历史/打开路径统一 job_id；旧 task 兼容跳转 |
| P0-5 | 中文错误与 orphan 文案；失败一键重跑 |
| P0-6 | 状态同步 502 降噪 |

### 验收门禁 P0

- [x] `python3 -m py_compile` 相关 py 通过  
- [x] pdf_parser 含 `_parse_via_subprocess` + lightweight  
- [x] manager 含 hydrate + compact events + 中文 orphan  
- [x] compose workers=1  
- [x] PptGenerator 打开历史优先 job  
- [x] PptEditor 失败可重跑文案  
- [x] 发布规范文档 `docs/ppt-release-notes.md`  
- [x] 生产 health 200 + PDF 子进程解析 ALIVE  

---

## P1 状态外置 + 可恢复

### 改动范围

| 项 | 内容 |
|----|------|
| P1-1 | Job/Session 元数据权威落盘目录结构（jobs/{id}.json） |
| P1-2 | get_job 跨重启 hydrate（与 session 对称） |
| P1-3 | 状态 API 返回 `can_resume` / `can_retry` / `session_alive` |
| P1-4 | 前端 canResume / 重新生成 绑定上述字段 |
| P1-5 | 健康检查与 job 隔离说明 |

### 验收门禁 P1

- [x] job sidecar 读写闭环（单元测试 UNIT_OK）  
- [x] get_job hydrate + list_jobs 扫 sidecar  
- [x] status 响应含恢复提示字段  
- [x] 前端 `jobRecovery` / `canRetryGenerate` 绑定  

---

## P2 入口收敛

### 改动范围

| 项 | 内容 |
|----|------|
| P2-1 | `/ppt-generator` → 重定向到 `/ppt-editor` |
| P2-2 | `/ppt-history/:id` 保留；详情内 job 回退编辑器 |
| P2-3 | AI 应用中心已指向 `/ppt-editor` |
| P2-4 | 旧详情只读兼容不挡主路径 |

### 验收门禁 P2

- [x] 路由 redirect 已合入并构建  
- [x] 历史 job 优先打开编辑器  
- [x] 前端镜像已部署 `PptEditor-DjpYK0wb.js`  

---

## 全局验收

- [x] 代码编译/语法  
- [x] 关键字符串与符号存在  
- [x] 生产 `/api/ppt/health` = 200  
- [x] workers=1  
- [x] PDF 解析不杀主进程  

---

## P3 API/Worker + MySQL 表（已落地）

| 项 | 内容 |
|----|------|
| SQL | `ppt_agent_session` / `ppt_agent_job`（现有 orep 库） |
| 双写 | SessionManager → 磁盘 sidecar + MySQL |
| 模式 | `PPT_EXECUTION_MODE=queue` API 只入队 |
| Worker | 容器 `orep-ppt-worker`，`python ppt_worker.py` 认领执行 |

### 验收

- [x] 表已创建  
- [x] health: `db_ok=true`, `queue_mode=true`  
- [x] worker log: `PPT worker starting ... db=True`  
