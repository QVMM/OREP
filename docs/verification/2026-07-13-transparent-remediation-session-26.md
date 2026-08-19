# 会话 26：全量公开、分轮执行、重新验证灰度验收记录

验收日期：2026-07-13（Asia/Shanghai）  
验收对象：新一代信息技术赛道，会话 26，报告 40  
验收结论：通过

## 1. 本次交付边界

- 使用会话 26 已保存的分析结果重建并重放 v3 完成回调，没有重跑视频、ASR 或视觉分析。
- Python 负责产生唯一评分事实、完整失分账本、整改任务和组合预测。
- Java 负责二次对账、报告快照、任务状态、失分关联和跨轮验证记录。
- 用户端继续只展示一个 AI 分数；任务勾选、提交或进入待复评状态均不直接改变该分数。
- 新一轮路演使用同一评分规则完成后，才按稳定失分键重新验证任务，并产生 `verified`、`partial`、`failed`、`regressed` 或 `not_observable` 结果。

## 2. 契约与评分身份

| 项目 | 验收值 |
|---|---|
| 契约版本 | `ai-score-report-v3` |
| 待办组合状态 | `complete` |
| 规则哈希 | `sha256:cad28518702e251c307d0c0473e2fe51f92d37ee95c54693245235d5124e7920` |
| 评分指纹 | `4488efa9024f348cde03dd55be86c70baf57388a764da2ea350f75961de70b59` |
| 覆盖计算版本 | `remediation-coverage-v1` |
| 提分计算版本 | `score-impact-v2` |

## 3. API 与数据库对账

| 事实 | 验收值 |
|---|---:|
| 当前 AI 分数 | 49.5 |
| 距离 100 分的完整差距 | 50.5 |
| 失分账目 | 19 条 |
| 失分账目合计 | 50.5 分 |
| 涉及观测点 | 15 个 |
| 去重后整改任务 | 23 项 |
| 正式计分任务 | 18 项 |
| 诊断性整改任务 | 5 项 |
| 已覆盖失分账目 | 19 条 |
| 已覆盖差距 | 50.5 分 |
| 差距覆盖率 | 100% |
| 未覆盖账目 | 0 条 |
| 重复预算冲突 | 0 项 |
| 全部最低验收通过后的预测 | 81.0～96.5 分 |
| 保守预计提升 | +31.5～+47.0 分 |

恒等式核对：

```text
49.5 + 50.5 = 100.0
sum(lossLedger.points) = 50.5
coveredLossItemCount / lossItemCount = 19 / 19 = 1.0
```

数据库已保存报告 v3 四个快照字段，以及标准化任务、任务—失分关联和跨轮验证三张表。会话 26 当前 23 项任务均处于初始执行状态；没有伪造本轮之外的验证结果。

## 4. 用户端验收

### 结果页

- 展示唯一 AI 分数 49.5 和固定满分目标 100。
- 展示完整差距 50.5，而不是“下一档定位线”或阶段目标。
- 展示全部整改通过后的预测区间 81.0～96.5，并明确最终以重新路演评分为准。
- 顶部待办数为完整去重队列 23；首页恰好展示前三项，并说明这是执行顺序、不是最终目标。
- 展示“19 条失分账目、23 项整改任务、覆盖全部 50.5 分差距”。

### 全部待办页

- 展示 API 返回的完整 23 项队列，不把任务数写死为 6、7、19 或 23。
- 正式计分任务展示保守提分区间；5 项诊断性任务只展示验收要求，不承诺分数。
- 显示 15 个观测点、19 条失分账目、23 项整改任务和 100% 差距覆盖率。
- 明确提示多个任务可能共同覆盖同一失分，各任务分值不能简单相加。

### 评分依据页

- 标题为“为什么不是 100 分”。
- 完整公开 19 条失分账目，合计 50.5 分。
- 分为表现差距 41.0 分、证据上限 7.5 分、规则惩罚 2.0 分。
- 每条账目展示观测点、原因、分值和关联整改入口。

验收截图：

- [结果页](screenshots/session-26-result.png)
- [全部待办页](screenshots/session-26-todos.png)
- [评分依据页](screenshots/session-26-why.png)

## 5. 自动化验证结果

```text
Python:
.venv/bin/python -m pytest \
  tests/test_authoritative_rule_executor.py \
  tests/test_loss_ledger_service.py \
  tests/test_remediation_planner.py \
  tests/test_coverage_validator.py \
  tests/test_score_impact_service.py \
  tests/test_session_authoritative_callback.py \
  tests/test_backend_callback_client.py -q
结果：40 passed

Java:
mvn test
结果：220 tests，0 failures，0 errors，BUILD SUCCESS

用户端单测:
node --test src/utils/*.test.js
结果：56 passed

用户端生产构建:
npm run build
结果：成功，3710 modules transformed

用户端端到端:
OREP_E2E_CAPTURE=1 npm run test:e2e:ai-score
结果：3 passed
```

端到端用例通过正式登录接口建立隔离登录态；本地证书存在时，Playwright 与 Vite 使用同一 HTTPS 判定，并接受本地自签名证书。会话验收用例从真实报告 API 动态读取任务总数，再核对结果、待办和依据三页。

## 6. 兼容与发布说明

- v3 只有在分数对账和失分覆盖同时完整时，才允许使用“完整待办”文案。
- v2 历史报告继续走兼容解析，不会被伪装为 v3 完整队列。
- Java 可先部署；新列允许为空。Python 随后开始发送 v3，前端最后启用 v3 展示。
- 回滚任一应用层时不得删除已经写入的 v3 列、任务、关联或验证记录。
- 构建仅保留既有的大分块警告，不影响本次功能与验收结果；后续可独立做前端代码分包优化。

本记录不包含视频路径、完整转录、用户密钥或登录令牌。
