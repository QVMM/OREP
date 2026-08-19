# OREP PPT生成系统 - 集成测试执行指南

## 测试执行流程文档
## Integration Test Execution Guide

---

## 1. 测试概述

### 1.1 测试目标
- 验证PPT生成系统的功能完整性和稳定性
- 确保不同行业、边界条件下的生成质量满足基线要求
- 建立质量指标基线，实现自动化质量检测

### 1.2 测试范围
- **行业测试**: Healthcare、Education、Manufacturing、Finance、Tech、AIoT
- **边界测试**: 极少数据、极多数据、缺失字段、特殊字符
- **回归测试**: 确保修复不破坏已有功能
- **稳定性测试**: 多次生成的重复性验证
- **竞品对比**: 行业质量标准对比

### 1.3 质量指标基线

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 有效页数 | ≥ 35 | 非空壳页的数量 |
| 空壳页 | ≤ 3 | 内容不足的页面 |
| SVG图表 | ≥ 10 | 嵌入的SVG图形数量 |
| 技能操作页 | ≥ 10 | 包含技能操作内容的页面 |
| 乱码字符 | = 0 | 检测到的乱码字符数 |
| KPI页面 | ≥ 8 | 关键指标展示页面 |
| 时间线页面 | ≥ 3 | 时间轴/规划类页面 |
| 内容页 | ≥ 5 | 文本内容丰富的页面 |
| 团队页 | ≥ 1 | 团队介绍页面 |
| 封面/目录/结束 | 3页 | 基础页面结构 |

---

## 2. 测试用例矩阵

### 2.1 测试用例列表

| Case ID | 名称 | 行业 | 优先级 | 预期页数 | 标签 |
|---------|------|------|--------|----------|------|
| P0-001 | 基线测试-任务54 | Healthcare | P0_Critical | ≥40 | baseline, healthcare |
| P0-002 | 多行业回归-HealthCare | Healthcare | P0_Critical | ≥35 | regression |
| P0-003 | 多行业回归-AIIoT | AIoT | P0_Critical | ≥35 | regression |
| P1-001 | Healthcare完整测试 | Healthcare | P1_High | ≥35 | healthcare |
| P1-002 | Education行业测试 | Education | P1_High | ≥30 | education |
| P1-003 | Manufacturing行业测试 | Manufacturing | P1_High | ≥30 | manufacturing |
| P1-004 | Finance行业测试 | Finance | P1_High | ≥30 | finance |
| P1-005 | Tech行业测试 | Tech | P1_High | ≥30 | tech |
| P2-001 | 极少数据测试 | Tech | P2_Medium | ≥20 | boundary, minimal |
| P2-002 | 极多数据测试 | Tech | P2_Medium | ≥45 | boundary, max |
| P2-003 | 缺失可选字段 | Tech | P2_Medium | ≥30 | boundary, missing |
| P2-004 | 缺失必填字段 | Tech | P2_Medium | 错误处理 | boundary, error |
| P2-005 | 特殊字符测试 | Tech | P2_Medium | ≥30 | boundary, special |
| P3-001 | 稳定性-多次生成 | Healthcare | P3_Low | - | stability |
| P3-002 | 并发测试 | Healthcare | P3_Low | - | concurrency |
| P3-003 | 性能测试 | Healthcare | P3_Low | - | performance |

### 2.2 测试用例分类统计

```
按行业:
  healthcare:  4 cases
  ai_iot:      2 cases
  education:   1 case
  manufacturing: 1 case
  finance:    1 case
  tech:       7 cases

按优先级:
  P0_Critical: 3 cases
  P1_High:    5 cases
  P2_Medium:  5 cases
  P3_Low:      3 cases
```

---

## 3. 测试执行流程

### 3.1 完整测试流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                      测试启动                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  1. 环境检查                                                     │
│     - 检查服务状态: curl http://localhost:8090/docs             │
│     - 检查数据库连接: mysql -h localhost -u root -p              │
│     - 检查Python环境: .venv/bin/python --version                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. 选择测试用例                                                 │
│     - 单个测试: --case P0-001                                   │
│     - 所有测试: --all                                           │
│     - 稳定性测试: --stability                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. 创建PPT生成任务                                              │
│     POST /api/ppt/v2/task/create                                 │
│     {                                                           │
│       "questionnaire_id": 28,                                   │
│       "user_id": 1,                                             │
│       "tenant_id": 1,                                           │
│       "industry": "healthcare"                                  │
│     }                                                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. 轮询任务状态 (最多600秒)                                      │
│     GET /api/ppt/task/{task_id}/status                          │
│                                                                  │
│     状态流转:                                                    │
│     pending -> generating -> generating -> ... -> completed      │
│                  or                                              │
│               failed                                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. 获取任务详情                                                 │
│     GET /api/ppt/task/{task_id}                                  │
│     - 检查 pptx_path                                             │
│     - 检查 status                                                │
│     - 获取 outline_json                                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. 分析PPT文件                                                   │
│     - 解析PPTX (python-pptx)                                     │
│     - 统计页面类型和数量                                          │
│     - 检测SVG图表                                                 │
│     - 检测乱码字符                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. 质量基线检查                                                  │
│     - 有效页数 >= 35                                             │
│     - 空壳页 <= 3                                                │
│     - SVG图表 >= 10                                              │
│     - 技能操作页 >= 10                                           │
│     - 乱码字符 = 0                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  8. 生成测试报告                                                  │
│     - 保存JSON结果到 tests/integration/results/                 │
│     - 打印摘要信息                                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 详细执行步骤

#### 步骤1: 环境检查

```bash
# 检查服务状态
curl -s http://localhost:8090/docs | head -5

# 检查PPT API健康
curl -s http://localhost:8090/api/ppt/health

# 检查数据库连接
mysql -h localhost -P 3306 -u root -p12345678 -e "SELECT 1" 2>/dev/null

# 检查Python环境
/Users/liuyixing/项目/OREP/ai-scoring/.venv/bin/python --version
```

#### 步骤2: 运行单个测试

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring

# 运行基线测试 P0-001
./.venv/bin/python tests/integration/ppt_integration_tester.py \
    --case P0-001 \
    --questionnaire-id 28 \
    --user-id 1 \
    --tenant-id 1 \
    --industry healthcare
```

#### 步骤3: 运行所有测试

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring

# 运行所有测试
./.venv/bin/python tests/integration/ppt_integration_tester.py --all
```

#### 步骤4: 运行稳定性测试

```bash
cd /Users/liuyixing/项目/OREP/ai-scoring

# 连续3次生成测试
./.venv/bin/python tests/integration/ppt_integration_tester.py \
    --stability \
    --case P3-001 \
    --questionnaire-id 28 \
    --user-id 1 \
    --tenant-id 1 \
    --industry healthcare \
    --runs 3
```

---

## 4. 测试结果解读

### 4.1 测试状态

| 状态 | 说明 |
|------|------|
| passed | 测试通过，质量指标满足基线 |
| failed | 测试失败，质量指标未达标 |
| error | 执行错误，可能是API调用失败 |
| timeout | 任务超时（默认600秒） |
| running | 测试进行中 |

### 4.2 质量指标解读

#### 有效页数 (effective_pages)
- **定义**: 非空壳页的数量
- **计算**: 总页数 - 空壳页数
- **基线**: ≥ 35
- **低于基线原因**:
  - 数据不足导致填充内容不够
  - 某些章节被合并或省略
  - 生成算法问题

#### 空壳页 (empty_pages)
- **定义**: 文字少于20字，形状少于3个的页面
- **基线**: ≤ 3
- **超过基线原因**:
  - 章节内容未正确填充
  - 模板渲染失败
  - 数据字段缺失

#### SVG图表 (svg_charts)
- **定义**: PPT中嵌入的SVG图形数量
- **基线**: ≥ 10
- **低于基线原因**:
  - KPI图表未正确生成
  - 某些页面类型不支持图表
  - 渲染引擎问题

#### 技能操作页 (skill_pages)
- **定义**: 包含"技能"、"操作"、"岗位职责"等关键词的页面
- **基线**: ≥ 10
- **低于基线原因**:
  - 评分规则未正确应用
  - 数据中缺少技能相关内容
  - 页面生成逻辑问题

### 4.3 竞品对比评级

| 评级 | 分数范围 | 说明 |
|------|----------|------|
| A+ | 90-100 | 远超行业标准 |
| A | 80-89 | 达到行业标准 |
| B | 70-79 | 基本达标 |
| C | 60-69 | 低于标准 |
| D | 50-59 | 明显不足 |
| F | <50 | 严重不足 |

---

## 5. 稳定性测试分析

### 5.1 稳定性指标

| 指标 | 稳定性等级 | 变异系数(CV) |
|------|-----------|-------------|
| 完全稳定 | - | 0 |
| 非常稳定 | 优秀 | < 5% |
| 稳定 | 良好 | 5-10% |
| 轻微波动 | 可接受 | 10-20% |
| 波动较大 | 需改进 | > 20% |

### 5.2 稳定性测试输出示例

```
稳定性测试摘要 (3次运行)
============================================================

total_pages:
  数值: [47, 46, 47]
  方差: 0.22
  稳定性: 非常稳定

effective_pages:
  数值: [40, 41, 40]
  方差: 0.22
  稳定性: 非常稳定

svg_charts:
  数值: [13, 13, 14]
  方差: 0.22
  稳定性: 非常稳定

skill_pages:
  数值: [11, 12, 11]
  方差: 0.22
  稳定性: 非常稳定
```

---

## 6. 测试结果文件

### 6.1 结果保存位置

```
/Users/liuyixing/项目/OREP/ai-scoring/tests/integration/results/
├── P0-001_20260414_120000.json    # 单次测试结果
├── P0-002_20260414_121000.json
├── stability_P3-001_20260414_130000.json  # 稳定性测试报告
└── ...
```

### 6.2 结果JSON格式

```json
{
  "case_id": "P0-001",
  "task_id": 55,
  "status": "passed",
  "start_time": "2026-04-14T12:00:00",
  "end_time": "2026-04-14T12:05:30",
  "duration_seconds": 330.0,
  "baseline_passed": true,
  "metrics": {
    "total_pages": 47,
    "effective_pages": 40,
    "empty_pages": 2,
    "svg_charts": 13,
    "skill_pages": 11,
    "garbled_chars": 0,
    "kpi_pages": 8,
    "timeline_pages": 5,
    "content_pages": 12,
    "team_pages": 1,
    "cover_pages": 1,
    "toc_pages": 1,
    "ending_pages": 1
  },
  "issues": [],
  "error_message": null
}
```

---

## 7. 常见问题排查

### 7.1 服务无响应

```bash
# 检查服务是否运行
ps aux | grep "python.*main.py" | grep -v grep

# 检查端口占用
lsof -i :8090

# 查看服务日志
tail -f /Users/liuyixing/项目/OREP/ai-scoring/logs/*.log
```

### 7.2 数据库连接失败

```bash
# 测试数据库连接
mysql -h localhost -P 3306 -u root -p12345678 -e "SELECT 1" 2>&1

# 检查数据库配置
grep -r "MYSQL" /Users/liuyixing/项目/OREP/ai-scoring/.env
```

### 7.3 PPT生成超时

- 检查问卷数据是否完整
- 检查AI服务(DeeSeek/Qwen)是否可用
- 增加超时时间: `--timeout 1200`

### 7.4 分析脚本错误

```bash
# 测试python-pptx
.venv/bin/python -c "from pptx import Presentation; print('OK')"

# 检查PPTX文件是否损坏
file /Users/liuyixing/项目/OREP/ai-scoring/uploads/ppt/ppt_54.pptx
```

---

## 8. 测试脚本API参考

### 8.1 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --case | string | - | 测试用例ID |
| --all | flag | false | 运行所有测试 |
| --stability | flag | false | 运行稳定性测试 |
| --questionnaire-id | int | 28 | 问卷ID |
| --user-id | int | 1 | 用户ID |
| --tenant-id | int | 1 | 租户ID |
| --industry | string | healthcare | 行业类型 |
| --runs | int | 3 | 稳定性测试次数 |
| --timeout | int | 600 | 超时时间(秒) |

### 8.2 API端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/ppt/v2/task/create | 创建PPT生成任务 |
| GET | /api/ppt/task/{id}/status | 获取任务状态 |
| GET | /api/ppt/task/{id} | 获取任务详情 |
| GET | /api/ppt/task/{id}/download | 下载PPT文件 |
| GET | /api/ppt/forms/{domain} | 获取表单配置 |
| GET | /api/ppt/health | 健康检查 |

---

## 9. 维护与更新

### 9.1 更新测试用例

编辑 `/Users/liuyixing/项目/OREP/ai-scoring/tests/integration/test_case_matrix.py`

```python
# 添加新测试用例
TestCase(
    case_id="NEW-001",
    name="新测试用例",
    industry=Industry.TECH,
    priority=TestPriority.P1_HIGH,
    questionnaire_id=99,
    user_id=1,
    tenant_id=1,
    description="描述",
    tags=["new"]
)
```

### 9.2 更新质量基线

编辑 `ppt_integration_tester.py`

```python
QUALITY_BASELINES = {
    "min_effective_pages": 40,  # 调整基线
    "max_empty_pages": 2,
    ...
}
```

### 9.3 更新竞品基线

编辑 `CompetitiveAnalyzer.COMPETITIVE_BASELINES`

```python
COMPETITIVE_BASELINES = {
    "healthcare": {
        "min_pages": 35,
        ...
    }
}
```

---

## 10. 联系与支持

如有测试相关问题，请联系:
- 测试负责人: Integration Team
- 文档版本: v1.0
- 最后更新: 2026-04-14