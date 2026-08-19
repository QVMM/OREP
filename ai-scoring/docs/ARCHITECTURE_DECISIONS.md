# 架构决策记录

> 项目代号：PitchForge
> 版本：1.0.0
> 维护者：Tech Lead

---

## 一、技术选型决策

### 1.1 后端框架

**决策**：采用 FastAPI 作为后端框架

**依据**：
- 原项目已使用 FastAPI，保持一致性
- 异步支持优秀，适合 IO 密集型任务
- 自动生成 OpenAPI 文档，开发效率高
- 类型提示支持良好，利于维护

**替代方案考虑**：
- Flask：过于轻量，异步支持不足
- Django：过于重型，不适合此场景
- Starlette：FastAPI 基于此构建，直接使用 FastAPI 更方便

### 1.2 PPT 生成策略

**决策**：采用多阶段 Pipeline 架构，AI 调用与规则引擎分离

**依据**：
- AI 调用成本高、延迟大，应尽量减少调用次数
- 布局规则相对稳定，适合用规则引擎处理
- 分离关注点，便于调试和优化

**阶段划分**：
```
Phase 1: Outline Generation     -> AI 调用 (1 次)
Phase 2: Data Validation        -> 规则引擎 (0 次 AI)
Phase 3: Layout & Structure    -> 规则引擎 (0 次 AI)
Phase 4: Background Generation -> AI 调用 (可选)
Phase 5: Assembly & Render     -> 规则引擎 (0 次 AI)
```

### 1.3 组件渲染

**决策**：采用 HTML/CSS/SVG 渲染方案

**依据**：
- SVG 适合数据可视化，缩放无损
- HTML/CSS 布局灵活，支持复杂样式
- 便于后续扩展动画效果
- 输出格式可转换为 PPTX

### 1.4 数据存储

**决策**：文件系统的 output/ 目录作为临时存储

**依据**：
- PPT 生成为一次性任务，不需要持久化
- 简化架构，降低复杂度
- 便于清理和维护

**注意**：生产环境可能需要对接对象存储（如 S3）

---

## 二、架构原则

### 2.1 单一职责原则

每个模块只负责一件事：
- `outline_generator.py`：AI 大纲生成
- `layout_rules.py`：布局规则
- `assembly_engine.py`：组件装配
- `bg_generator.py`：背景图生成
- `data_validator.py`：数据验证

### 2.2 依赖方向

```
用户请求
    │
    ▼
┌─────────────────┐
│ outline_generator │  <- AI 依赖
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ data_validator  │  <- 规则引擎，无 AI
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ layout_rules    │  <- 规则引擎，无 AI
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ assembly_engine │  <- 规则引擎，无 AI
└─────────────────┘
    │
    ▼
   PPT
```

**原则**：依赖方向必须单向，禁止反向依赖

### 2.3 接口抽象

关键接口定义：

```python
# Outline Generator 接口
class OutlineGeneratorProtocol:
    async def generate(self, user_data: dict, theme: str) -> List[Page]:
        """生成 PPT 大纲"""
        pass

# Layout Rules 接口
class LayoutRulesProtocol:
    def assign_layouts(self, pages: List[Page], theme: str) -> List[Page]:
        """为每页分配布局"""
        pass

# Assembly Engine 接口
class AssemblyEngineProtocol:
    def assemble(self, pages: List[Page]) -> List[Dict]:
        """将大纲组装为最终渲染数据"""
        pass
```

### 2.4 错误处理

**原则**：每个 Phase 独立错误处理，失败后尝试降级

```python
# 错误处理策略
try:
    result = await phase_n()
except AIError:
    # AI 调用失败，尝试规则引擎降级
    result = fallback_rule_engine()
except DataValidationError:
    # 数据验证失败，尝试修复
    result = await fix_and_retry()
except LayoutError:
    # 布局错误，使用默认布局
    result = use_default_layout()
```

---

## 三、已知问题与应对

### 3.1 循环依赖

**问题**：`outline_generator.py` <-> `layout_rules.py` 存在循环调用

**原因**：
- outline_generator 需要调用 layout_rules 获取布局建议
- layout_rules 需要调用 outline_generator 获取语义信息

**解决方案**：
提取共同接口到 `page_semantics.py`

```
outline_generator.py
    ├─> page_semantics.py (提取接口)
    └─> layout_rules.py (单向调用)

layout_rules.py
    └─> page_semantics.py (单向调用)
```

**状态**：待实施（Sprint 3）

### 3.2 data 字段丢失

**问题**：`rule_engine.process()` 重复调用导致 `data` 字段丢失

**现象**：BACKGROUND_DATA 页面渲染时无法获取 metrics 数据

**原因**：Pipeline 中某些步骤覆盖了 data 字段

**解决方案**：
1. 在 Phase 2 增加数据保留检查
2. 修复覆盖问题

**状态**：待修复（Sprint 1）

### 3.3 空壳页问题

**问题**：某些页面（如章节分隔页）内容空洞

**根本原因**：
1. AI 生成时内容填充不足
2. 规则引擎未检测和修复空壳页

**解决方案**：
1. 增强 prompt 中的内容填充原则
2. 在 Phase 2 增加空壳页检测和修复
3. 章节分隔页添加 3-5 个章节要点

**状态**：部分解决（Sprint 1-2）

---

## 四、扩展性设计

### 4.1 新增组件类型

新增组件只需：
1. 在 `components/` 目录创建组件文件
2. 在 `COMPONENT_REGISTRY` 中注册
3. 定义组件的 Schema 和渲染模板

```python
# components/__init__.py
COMPONENT_REGISTRY = {
    "kpi_metrics": KPI_metricsComponent(),
    "bar_chart_svg": BarChartSVGComponent(),
    # 新增组件
    "new_component": NewComponent(),
}
```

### 4.2 新增主题

新增主题只需：
1. 在 `themes/` 目录创建主题配置
2. 定义颜色、字体、背景等样式

### 4.3 新增行业模板

新增行业模板只需：
1. 在 `prompts/` 目录创建行业 prompt
2. 定义该行业的特定布局和组件偏好

---

## 五、性能考虑

### 5.1 AI 调用优化

- Phase 1 只调用 1 次 AI 生成大纲
- Phase 4 背景图生成为可选，降低成本
- 批量生成而非逐页生成

### 5.2 缓存策略

- 相同主题的布局规则可缓存
- 常用组件渲染结果可缓存

### 5.3 并发处理

- 多个 PPT 生成任务可并发处理
- 单个 PPT 内部 Phase 串行（保证依赖顺序）

---

## 六、安全考虑

### 6.1 输入验证

- 用户输入必须经过验证
- 防止恶意构造的数据导致系统异常

### 6.2 资源限制

- 单次生成任务有页数上限
- 单页内容有长度限制
- 防止恶意消耗系统资源

### 6.3 敏感信息

- API Key 等敏感信息通过环境变量配置
- 日志中不记录敏感信息

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|--------|
| 1.0.0 | 2026-04-15 | 初始版本 | Tech Lead |
