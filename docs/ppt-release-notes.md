# PPT 生成服务发布规范

## 禁止

- 在生产容器内 `docker exec` 热改 `.py` 后 `restart` 作为常规发布手段  
  （曾导致 `ModuleNotFoundError` / 502 / 进行中任务 orphan）
- 将 `ai-scoring` 的 uvicorn `--workers` 设为大于 1（session/job 进程内状态会跨 worker 丢失）

## 正确发布

1. 改代码进仓库：`ai-scoring/` 与同步到 `deploy/ai-service/`
2. 构建镜像：`docker compose ... build ai-scoring`
3. 滚动重建：`up -d --no-deps --force-recreate ai-scoring`
4. 若容器 IP 变更导致 502：`force-recreate nginx`
5. 验证：`GET /api/ppt/health` → 200

## 运行约束

- `command: uvicorn ... --workers 1`
- PDF 解析在子进程（轻量文本路径），不得在 API 进程内直接跑完整 fitz 抽图
- Job/Session 元数据：`runtime/sessions/*.json`、`runtime/jobs/*.json` + 精简 `session_state.json`
- MySQL 表：`ppt_agent_session` / `ppt_agent_job`（`sql/upgrade_ppt_agent_job_queue.sql`）
- `PPT_EXECUTION_MODE=queue` + 服务 `ppt-worker`（`python ppt_worker.py`）认领队列
- 回退：`PPT_EXECUTION_MODE=inline` 时 API 进程内跑流水线（仍双写 DB）

## 队列模式发布清单

1. 执行 SQL：`upgrade_ppt_agent_job_queue.sql` 到 orep 库  
2. 构建并启动 `ai-scoring`（带 MYSQL_* + PPT_EXECUTION_MODE=queue）  
3. 构建并启动 `ppt-worker`（同一镜像、`ppt_worker.py`）  
4. 检查 `GET /api/ppt/health` → `db_ok: true`, `queue_mode: true`  
5. 生成任务后查：`SELECT id,status,worker_id FROM ppt_agent_job ORDER BY created_at DESC LIMIT 5`
