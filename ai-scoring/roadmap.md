# OREP PPT生成系统优化路线图

> 基于 Agent Team 专项研究汇总
> 研究时间：2026-04-14
> 团队成员：Prompt Engineer | Architecture Auditor | Quality Benchmark | Integration Tester

---

## 执行摘要

| 指标 | 任务54基准 | 目标 | 改进幅度 |
|------|-----------|------|----------|
| 有效页数 | 29 | ≥35 | +6页 |
| 空壳页 | 11 | ≤3 | -8页 |
| 空壳率 | 23% | ≤8% | -15pp |
| SVG图表 | 13 | ≥10 | 维持 |
| 每页内容密度 | ~10块 | ~18-20块 | +80% |

---

## 一、立即可实施的改进（1-2天内完成）

### 1.1 修复bg_generator方法名Bug（Agent 2发现）

**问题**：`bg_generator.py` 方法名不匹配导致AI背景图生成完全失效

**位置**：`ppt_service.py` 第267行

```python
# 错误调用
bg_images = await bg_gen.batch_generate(processed_pages, theme)

# 正确调用
bg_images = await bg_gen.generate_batch(processed_pages, theme)
```

**预期效果**：COVER/SECTION_DIVIDER/ENDING页面将获得AI生成的背景图

**实施难度**：低（1行代码）

**依赖关系**：无

---

### 1.2 增强用户提示词内容填充原则（Agent 1设计）

**问题**：用户提示词没有强化系统提示词中的内容填充原则，导致AI生成空壳凑数

**方案**：在 `_build_user_prompt_v4` 末尾添加强化指令：

```
## 关键指令（必须遵守！）

### 1. 内容优先，页数其次
**你的首要目标是生成有内容的页面，不是满足页数要求。**
- 如果数据只能支撑25页有效内容，生成25页，不要为凑40页而稀释数据
- 每页key_points必须满足最小数据量要求
- **空壳页是最低等级的失败** -宁可少页，不要空壳

### 2. 数据打散分配规则
将总数据量均匀分配到各页面，每页分配 = max(4, floor(D/S))

### 3. 页面合并策略
当某类型数据不足时，合并相关内容到同一页，不要把1个数据点撑成1页。
```

**预期效果**：
- 有效页从29页→≥35页
- 空壳页从11页→0-2页

**实施难度**：低（修改提示词模板）

**依赖关系**：无

---

### 1.3 消除章节分隔空壳页（Agent 3建议）

**问题**：11个章节分隔页（5-11, 14, 15, 20, 30, 40）只有大号数字，无实质内容

**方案**：在 `layout_rules.py` 中修改章节分隔页生成逻辑，为每页添加3-5个章节要点

```python
# 在 _assign_layouts_and_components() 中为 SECTION_DIVIDER 添加内容填充
if page.get('layout_id') == 'section_divider':
    # 从下一节内容中提取3个关键词作为要点
    next_section_keypoints = _extract_next_section_keypoints(page, all_pages)
    page['key_points'] = next_section_keypoints[:3]  # 最多3个
```

**预期效果**：47页→36页左右，每页都有实质内容

**实施难度**：中（需修改layout_rules逻辑）

**依赖关系**：无

---

### 1.4 增加数据来源标注（Agent 3建议）

**问题**：竞品有"艾瑞咨询2024"等数据来源标注，我们没有

**方案**：在 `outline_generator.py` 的系统提示词中添加数据来源标注要求

```
## 数据来源标注规则
每条量化数据必须标注来源，格式：[来源名称+年份]
示例：
- "市场规模5000亿元 [艾瑞咨询2024]"
- "响应时间<10s [内部测试数据]"
如无明确来源，标注"基于行业常识推断"
```

**预期效果**：提升PPT专业性和说服力

**实施难度**：低

**依赖关系**：无

---

## 二、中期优化（1-2周）

### 2.1 建立组件数据Schema统一规范（Agent 2设计）

**问题**：各组件期望的字段不统一（metrics/items/segments/values等）

**方案**：建立 `COMPONENT_DATA_SCHEMAS` 统一规范

```python
# component_schemas.py
COMPONENT_DATA_SCHEMAS = {
    "kpi_metrics": {"required": ["metrics"], "metrics_item": {...}},
    "bar_chart_svg": {"required": ["items"], "items_item": {...}},
    "pie_chart_svg": {"required": ["segments"], "segments_item": {...}},
    "line_chart_svg": {"required": ["values", "years"], ...}
}

# 在 assembly_engine 之前进行数据标准化
def normalize_component_data(data: Dict, component: str) -> Dict:
    """根据组件Schema标准化数据格式"""
```

**预期效果**：消除数据格式导致的渲染异常

**实施难度**：中

**依赖关系**：需要同步修改各组件的字段读取逻辑

---

### 2.2 提取_fix_empty_data_pages到独立模块（Agent 2建议）

**问题**：`_fix_empty_data_pages` 混合在 layout_rules 中，职责不清

**方案**：提取到 `data_validator.py`

```
Phase 1: Outline Generation
└─ _validate_and_normalize_pages() ★ 新增：统一数据格式 + 空壳修复

Phase 2: Data Validation (原layout_rules的Step 6)
└─ validate_metrics_integrity() ★ 提取到这里
```

**预期效果**：架构更清晰，职责边界更明确

**实施难度**：中

**依赖关系**：无

---

### 2.3 增加技能操作页和Before/After对比页（Agent 3建议）

**问题**：0页技能操作展示，缺乏对比页

**方案**：
1. 在 `outline_generator.py` 中增加技能操作页生成规则
2. 添加Before/After对比页模板

```python
# 系统提示词增加：
## 技能操作页要求
每个核心技能操作生成1页，包含：
- 操作步骤（3-5步）
- 每步的工具输入/输出
- 关键参数说明

## Before/After对比页
针对每个痛点，生成1页对比：
- 左：现状问题（红色调）
- 右：解决方案效果（绿色调）
```

**预期效果**：
- 技能操作页≥2页
- Before/After对比页≥1页

**实施难度**：中

**依赖关系**：需要AI理解技能操作数据

---

### 2.4 语义驱动的组件选择（Agent 2设计）

**问题**：`data_layout` 路由仅基于字段存在性，不考虑语义

**方案**：改为语义驱动的组件选择

```python
SEMANTIC_TO_COMPONENT = {
    "BACKGROUND_DATA": {
        "default": "kpi_metrics",
        "chart_types": {
            "market_share": "pie_chart_svg",
            "trend": "line_chart_svg",
            "comparison": "bar_chart_svg"
        }
    },
    "DATA_COMPARE": {"default": "comparison_table"},
    "SKILL_STEPS": {"default": "timeline_vertical"}
}

def select_component(semantic: str, data: Dict) -> str:
    """语义驱动的组件选择"""
    # 1. 语义类型默认映射
    # 2. 数据特征分析后选择图表类型
    # 3. 回退到默认组件
```

**预期效果**：更准确的组件匹配，减少错误降级

**实施难度**：中

**依赖关系**：需要同步更新组件数据Schema

---

### 2.5 运行回归测试验证优化效果（Agent 4交付）

**已交付测试脚本**：
```bash
# 运行基线测试
.venv/bin/python tests/integration/ppt_integration_tester.py --case P0-001

# 运行所有测试
.venv/bin/python tests/integration/ppt_integration_tester.py --all

# 运行稳定性测试
.venv/bin/python tests/integration/ppt_integration_tester.py --stability --case P3-001 --runs 3
```

**预期效果**：量化验证优化效果，建立质量基线

---

## 三、长期架构升级（1个月+）

### 3.1 Pipeline重构（Agent 2设计）

**目标**：建立清晰的Phase划分

```
Phase 1: Outline Generation (AI调用)
└─ outline_generator.py
   ├─ generate()
   ├─ _parse_semantic_sequence()
   └─ _normalize_page_data() ★ 新增：统一数据格式

Phase 2: Data Validation & Enhancement (0次AI)
└─ data_validator.py ★ 新增模块
   ├─ validate_and_fix_empty_pages()
   └─ validate_metrics_integrity()

Phase 3: Layout & Structure (0次AI)
└─ layout_rules.py（精简，只保留布局相关）

Phase 4: Background Generation (AI调用 - 可选)
└─ bg_generator.py（修复方法名）

Phase 5: Assembly & Render (0次AI)
└─ assembly_engine.py（简化路由逻辑）
```

**预期效果**：架构清晰，职责明确，易于维护和扩展

**实施难度**：高

**依赖关系**：需要全面重构，影响范围大

---

### 3.2 视觉元素增强（Agent 3建议）

**目标**：缩小与竞品的视觉差距

| 元素 | 当前状态 | 目标 | 实施难度 |
|------|---------|------|----------|
| 粒子动画 | 无 | 每页20个 | 高 |
| 环形旋转动画 | 无 | 封面+结束页 | 高 |
| 渐入动画组合 | 无 | 每页1-2种 | 中 |
| 玻璃态卡片 | 无 | 内容页卡片 | 中 |
| 进度条/达成率 | 无 | 痛点页 | 中 |

**方案**：
1. 在 `base.py` 中添加动画CSS类
2. 在各组件中引用动画类
3. 添加粒子效果到全局背景

---

### 3.3 图表类型扩展（Agent 3建议）

**当前**：只有KPI卡片 + SVG圆环

**目标**：增加柱状图/折线图/架构图/仪表盘

**方案**：
1. 扩展 `bar_chart_svg.py` 支持更多数据格式
2. 新增 `architecture_diagram.py` 组件
3. 新增 `dashboard_svg.py` 仪表盘组件

---

### 3.4 消除循环依赖（Agent 2发现）

**问题**：`outline_generator.py` ↔ `layout_rules.py` 循环调用

**方案**：提取共同接口到 `page_semantics.py`

```
outline_generator.py
    ├─→ page_semantics.py (提取接口)
    └─→ layout_rules.py (单向调用)

layout_rules.py
    └─→ page_semantics.py (单向调用)
```

**预期效果**：消除循环依赖，编译更安全

**实施难度**：中

---

## 四、质量指标基线（Agent 4定义）

| 指标 | 目标 | 描述 |
|------|------|------|
| 有效页数 | ≥35 | 非空壳页 |
| 空壳页 | ≤3 | 少于20字且少于3个图形元素 |
| SVG图表 | ≥10 | 嵌入式SVG图形 |
| 技能操作页 | ≥10 | 含技能/操作关键词的页面 |
| 乱码字符 | =0 | 无编码错误 |
| KPI页面 | ≥8 | KPI指标页面 |
| 时间线页面 | ≥3 | 时间轴/路线图页面 |
| 内容页 | ≥5 | 文本内容丰富的页面 |
| 团队页 | ≥1 | 团队介绍页面 |

---

## 五、测试用例矩阵（Agent 4交付）

| Case ID | 名称 | 行业 | 优先级 | 预期页数 |
|---------|------|------|--------|----------|
| P0-001 | Baseline-Test Task 54 | Healthcare | P0_Critical | ≥40 |
| P0-002 | Multi-industry Regression-Healthcare | Healthcare | P0_Critical | ≥35 |
| P0-003 | Multi-industry Regression-AIIoT | AIoT | P0_Critical | ≥35 |
| P1-001 | Healthcare Full Test | Healthcare | P1_High | ≥35 |
| P1-002 | Education Industry Test | Education | P1_High | ≥30 |
| P1-003 | Manufacturing Industry Test | Manufacturing | P1_High | ≥30 |
| P1-004 | Finance Industry Test | Finance | P1_High | ≥30 |
| P1-005 | Tech Industry Test | Tech | P1_High | ≥30 |
| P2-001 | Minimal Data Test | Tech | P2_Medium | ≥20 |
| P2-002 | Max Data Test | Tech | P2_Medium | ≥45 |
| P2-003 | Missing Optional Fields | Tech | P2_Medium | ≥30 |
| P2-004 | Missing Required Fields | Tech | P2_Medium | Error handling |
| P2-005 | Special Characters Test | Tech | P2_Medium | ≥30 |
| P3-001 | Stability-Multiple Runs | Healthcare | P3_Low | - |
| P3-002 | Concurrency Test | Healthcare | P3_Low | - |
| P3-003 | Performance Test | Healthcare | P3_Low | - |

**测试脚本位置**：`tests/integration/ppt_integration_tester.py`

---

## 六、实施优先级总结

### Week 1（立即）
1. [x] 修复bg_generator方法名Bug
2. [x] 增强用户提示词内容填充原则
3. [x] 增加数据来源标注规则
4. [ ] 消除章节分隔空壳页（部分修改）

### Week 2
5. [ ] 建立组件数据Schema统一规范
6. [ ] 提取_fix_empty_data_pages到独立模块
7. [ ] 增加技能操作页和Before/After对比页
8. [ ] 语义驱动的组件选择
9. [ ] 运行P0回归测试验证

### Month 2-4
10. [ ] Pipeline重构
11. [ ] 视觉元素增强（动画、粒子、玻璃态）
12. [ ] 图表类型扩展
13. [ ] 消除循环依赖

---

## 七、关键文件位置索引

| 功能 | 文件路径 | 关键行号 |
|------|----------|----------|
| AI大纲生成 | `app/services/ppt/outline_generator.py` | 249-300 |
| 布局规则引擎 | `app/services/ppt/layout_rules.py` | 50-127 |
| 空壳页修复 | `app/services/ppt/layout_rules.py` | 361-478 |
| 组件装配引擎 | `app/services/ppt/assembly_engine.py` | 42-263 |
| 组件选择路由 | `app/services/ppt/assembly_engine.py` | 61-116 |
| 背景图生成器 | `app/services/ppt/bg_generator.py` | 116-311 |
| **Bug: 方法名** | `app/services/ppt/bg_generator.py` | **198** |
| 组件注册表 | `app/services/ppt/components/__init__.py` | 28-47 |
| 语义类型定义 | `app/services/ppt/page_semantics.py` | 1-241 |
| PPT主服务 | `app/services/ppt/ppt_service.py` | 209-340 |
| 测试脚本 | `tests/integration/ppt_integration_tester.py` | - |
| 测试用例矩阵 | `tests/integration/test_case_matrix.py` | - |
| 质量基线 | `tests/integration/QUALITY_BASELINES.md` | - |

---

## 八、Agent Team 研究报告链接

- [Agent 1: Prompt Engineer 分析报告](/private/tmp/claude/-Users-liuyixing/tasks/ac9e673.output)
- [Agent 2: Architecture Auditor 审查报告](/private/tmp/claude/-Users-liuyixing/tasks/a4d1d81.output)
- [Agent 3: Quality Benchmark 竞品分析报告](/private/tmp/claude/-Users-liuyixing/tasks/a42b544.output)
- [Agent 4: Integration Tester 测试设计报告](/private/tmp/claude/-Users-liuyixing/tasks/a87cc3f.output)

---

## 更新记录（2026-04-14 19:50）

### 已完成的改进

#### Action 1: 修复bg_generator方法名Bug ✅
- **文件**: `app/services/ppt/ppt_service.py` 第267行
- **修改**: `batch_generate` → `generate_batch`
- **验证**: bg_generator被成功调用，但API下载图片失败（网络问题）

#### Action 2: 增强用户提示词 ✅
- **文件**: `app/services/ppt/outline_generator.py`
- **修改**: 在`_build_user_prompt_v4`末尾添加：
  - 内容优先原则
  - 数据打散分配规则
  - 空页面惩罚机制
  - 3个few-shot示例（扁平化格式避免f-string转义问题）

### Task 61测试结果

| 指标 | Task 54 | Task 61 | 变化 |
|------|---------|---------|------|
| 总页数 | 40 | 39 | -1 |
| 空壳页(auto=true无数据) | 14 | 14 | 无变化 |
| SVG图表 | 13 | 12 | -1 |

**结论**: 单纯prompt优化效果有限。根本原因可能是Agent 2发现的架构问题：
- `rule_engine.process()` 重复调用导致 `data` 字段丢失
- BACKGROUND_DATA页面渲染时无法获取metrics数据

### 待解决问题

1. **架构问题**: data字段在pipeline中丢失（需重构rule_engine流程）
2. **bg_generator API问题**: 下载图片失败（外部API网络问题）
3. **空壳页问题**: 纯prompt优化不足以消除空壳页

### 下一步建议

1. 修复架构问题（data字段丢失）
2. 增加_fix_empty_data_pages的检查频率
3. 考虑在AI生成后增加后置验证步骤
