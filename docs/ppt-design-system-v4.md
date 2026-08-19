# OREP PPT 设计系统 v4.0

> 所有组件模板必须遵循此规范。目标风格：**竞赛级 PPT 演示文稿**，不是网页应用。

---

## 一、设计哲学

**三个词：克制、层次、呼吸。**

- **克制**：能用颜色区分的，不用容器。能用一条线分隔的，不用卡片。能用留白表达的，不用装饰。
- **层次**：通过字号对比（140px vs 30px）、透明度对比（4% vs 100%）、色彩饱和度对比建立视觉层次，不是通过阴影和边框。
- **呼吸**：内容区与页面边缘保持 ≥60px 间距，步骤之间用极细分隔线或空白，不要满。

**反模式（禁止出现）：**
- ❌ 半透明毛玻璃卡片（`backdrop-filter: blur`）
- ❌ 圆角输入框/按钮风格的容器（border-radius > 8px 的卡片）
- ❌ 多层 box-shadow 模拟立体感
- ❌ 所有内容挤在一个容器里
- ❌ Emoji 做装饰（可做功能性标注，不做装饰）

---

## 二、背景系统

### 2.1 通用背景层

所有页面共享的底层结构：

```css
body {
    background: #0f1923;  /* 深蓝黑，全局底色 */
}

/* 细网格暗纹，全页面覆盖 */
.bg-grid {
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
    background-size: 48px 48px;
    z-index: 0;
}
```

### 2.2 斜切色块（核心设计语言）

不同语义类型使用不同颜色的斜切色块，**统一在右侧 55% 宽度，斜切角度 18%**：

| 语义类型 | 色块渐变 | 用途 |
|----------|---------|------|
| `SKILL_STEPS` | `#1a3a5c → #0d2640`（深蓝） | 技能操作页 |
| `BACKGROUND_DATA` | `#1a3d2e → #0d2a1c`（深绿） | 背景数据页 |
| `PAIN_POINTS` | `#3d1a1a → #2a0d0d`（深红） | 痛点分析页 |
| `SOLUTION_ARCH` | `#2a1a3d → #1a0d2a`（深紫） | 方案架构页 |
| `ACHIEVEMENT` | `#3d3a1a → #2a270d`（深金） | 成果展示页 |
| `DATA_COMPARE` | `#1a2d3d → #0d1f2a`（青蓝） | 数据对比页 |
| `TEAM_INTRO` | `#2d1a3d → #1f0d2a`（粉紫） | 团队介绍页 |

斜切色块标准代码：

```css
.bg-clip {
    position: absolute;
    right: 0; top: 0; bottom: 0;
    width: 55%;
    background: linear-gradient(135deg, <浅色> 0%, <深色> 100%);
    clip-path: polygon(18% 0, 100% 0, 100% 100%, 0% 100%);
    z-index: 0;
}
```

### 2.3 装饰光晕

页面左下角或右上角加一个柔和光晕，增强纵深感：

```css
.bg-glow {
    position: absolute;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(主色调, 0.1) 0%, transparent 70%);
    border-radius: 50%;
    z-index: 0;
}
/* 位置根据页面布局调整，通常 left:-100px; bottom:-100px */
```

---

## 三、排版系统

### 3.1 字号层级

| 元素 | 字号 | 字重 | 颜色 | 用途 |
|------|------|------|------|------|
| 装饰数字 | 140px | 900 | rgba(255,255,255,0.04) | 大号背景数字 |
| 页面标题 | 28-32px | 800 | #ffffff | 页面主标题 |
| 卡片标题 | 16-18px | 700 | #ffffff | 步骤名/卡片名 |
| 正文 | 12.5-14px | 400 | rgba(255,255,255,0.45-0.55) | 描述文字 |
| 强调标注 | 12-13px | 600 | 彩色（见色彩系统） | 关键点/结果标签 |
| 页码 | 11px | 500 | rgba(255,255,255,0.15) | 页脚 |

### 3.2 字体

- 主字体：`'Noto Sans SC', 'PingFang SC', sans-serif`
- 装饰数字：`'Inter', 'SF Pro Display', sans-serif`（纯数字用等宽感更强的西文字体）

### 3.3 标题区结构

每个内容页的标题区统一结构：

```html
<!-- 标题区 -->
<div style="position:absolute;left:72px;top:40px;z-index:10;">
    <h2 style="font-size:30px;font-weight:800;color:#fff;
               letter-spacing:-0.01em;line-height:1.35;">
        页面标题
    </h2>
    <div style="width:40px;height:3px;background:#3b82f6;
                border-radius:2px;margin-top:12px;"></div>
</div>
```

装饰数字放在标题背后，巨大、半透明：

```html
<div style="position:absolute;left:72px;top:30px;z-index:1;
            font-size:140px;font-weight:900;
            color:rgba(255,255,255,0.04);line-height:0.85;
            letter-spacing:-0.04em;font-family:'Inter',sans-serif;
            user-select:none;">
    04
</div>
```

---

## 四、色彩系统

### 4.1 主色

- **主强调色**：`#3b82f6`（蓝）—— 分隔线、编号边框、装饰元素
- **全局底色**：`#0f1923`（深蓝黑）

### 4.2 功能色

| 颜色 | 色值 | 用途 |
|------|------|------|
| 黄/橙 | `#f59e0b` | 关键点（key_point）强调 |
| 绿 | `#34d399` | 结果（result）强调 |
| 灰 | `rgba(255,255,255,0.35)` | 工具/辅助信息 |
| 白 | `#ffffff` | 标题 |
| 淡白 | `rgba(255,255,255,0.45-0.55)` | 正文 |

### 4.3 用法规则

- **颜色只用来区分语义**，不用来做装饰或填充大面积色块
- 正文中用颜色文字内联标注，不用标签框/标签块：
  ```html
  <!-- ✅ 正确 -->
  <span style="color:#f59e0b;font-weight:600;">关键点：</span>具体描述
  
  <!-- ❌ 错误 -->
  <span style="background:rgba(255,165,0,0.12);padding:2px 8px;border-radius:4px;">关键点</span>
  ```
- 装饰数字和分隔线是**唯一的非内容视觉元素**

---

## 五、布局系统

### 5.1 通用布局原则

- **左右分栏**：标题 + 装饰在左侧约 40-45%，内容在右侧 55-60%
- **或者上下分栏**：标题在上方，内容在下方
- **绝对不要居中堆叠**（除了封面、章节分隔、结尾这三类特殊页面）

### 5.2 内容间距

- 页面边缘安全区：≥ 60px
- 标题到内容：≥ 30px
- 步骤/卡片之间：极细分隔线 `rgba(255,255,255,0.06)` + 0px 间距，或 16-20px 空白
- 内部行间距：8-12px

### 5.3 分隔线样式

```css
/* 横向分隔 */
border-top: 1px solid rgba(255,255,255,0.06);

/* 标题下装饰线 */
width: 40px; height: 3px;
background: #3b82f6;
border-radius: 2px;
```

---

## 六、各组件模板规范

### 6.1 kpi_metrics（KPI 数据展示）

**布局**：左右分栏。左侧标题 + 装饰数字，右侧 KPI 列表纵向排列。

```html
<!-- 左侧 -->
<div class="left" style="position:absolute;left:0;top:0;bottom:0;width:45%;...">
    <div class="big-num">08</div>
    <h1>市场规模与增长</h1>
    <div class="sep"></div>
    <p class="desc">行业核心数据一览</p>
</div>

<!-- 右侧 KPI 列表 -->
<div class="right" style="position:absolute;right:0;top:0;bottom:0;width:55%;...display:flex;flex-direction:column;justify-content:center;">
    <!-- 每个 KPI 项 -->
    <div style="padding:20px 0;border-bottom:1px solid rgba(255,255,255,0.06);">
        <div style="font-size:12px;color:rgba(255,255,255,0.35);margin-bottom:4px;">整体市场规模</div>
        <div style="font-size:36px;font-weight:800;color:#3b82f6;line-height:1.2;">8000亿</div>
        <div style="font-size:12px;color:rgba(255,255,255,0.45);margin-top:4px;">年增长率达18%，市场潜力巨大</div>
    </div>
</div>
```

### 6.2 three_column_cards（三列卡片/痛点/方案）

**布局**：上下分栏。标题在上，三列在下。

三列不用卡片容器，用**分隔线**区分：

```html
<!-- 三列区域 -->
<div style="position:absolute;left:72px;right:72px;top:130px;bottom:72px;
            display:flex;z-index:10;">
    <!-- 每列 -->
    <div style="flex:1;padding:0 24px;
                border-right:1px solid rgba(255,255,255,0.06);">
        <div style="font-size:14px;font-weight:700;color:#fff;margin-bottom:12px;">
            诊疗量占比低
        </div>
        <div style="font-size:12.5px;color:rgba(255,255,255,0.45);line-height:1.7;">
            基层机构诊疗量不足30%，导致大医院超负荷，患者等待时间超2小时
        </div>
    </div>
    <!-- 最后一列不加右分隔线 -->
</div>
```

可选：每列顶部加一个大号序号（如 01、02、03），字号 48px，颜色 `rgba(59,130,246,0.12)`。

### 6.3 timeline_vertical（技能操作步骤）

**布局**：左右分栏。左侧标题 + 装饰数字，右侧步骤列表。

步骤列表用**圆圈编号 + 极细分隔线**：

```html
<div class="step">
    <div style="width:36px;height:36px;border:2px solid rgba(59,130,246,0.35);
                border-radius:50%;display:flex;align-items:center;justify-content:center;
                font-size:14px;font-weight:800;color:rgba(59,130,246,0.7);
                font-family:'Inter',sans-serif;flex-shrink:0;margin-top:2px;">
        1
    </div>
    <div style="flex:1;">
        <div style="font-size:16px;font-weight:700;color:#fff;margin-bottom:6px;">
            步骤名称
        </div>
        <div style="font-size:12.5px;color:rgba(255,255,255,0.45);line-height:1.65;">
            <span style="color:#f59e0b;font-weight:600;">关键点：</span>内容&emsp;
            <span style="color:#34d399;font-weight:600;">结果：</span>内容&emsp;
            工具：内容
        </div>
    </div>
</div>
```

### 6.4 comparison_table（数据对比）

**布局**：左右分栏。左侧标题，右侧对比表。

对比表不用 `<table>` 标签式的网格，用**横线分隔 + 左右对齐**：

```html
<div style="display:flex;justify-content:space-between;padding:16px 0;
            border-bottom:1px solid rgba(255,255,255,0.06);">
    <span style="font-size:13px;color:rgba(255,255,255,0.45);">对比维度</span>
    <div style="text-align:right;">
        <span style="font-size:13px;color:#3b82f6;font-weight:600;">我方值</span>
        <span style="font-size:13px;color:rgba(255,255,255,0.2);margin:0 8px;">vs</span>
        <span style="font-size:13px;color:rgba(255,255,255,0.25);">基准值</span>
    </div>
</div>
```

### 6.5 flow_diagram（流程图）

**布局**：上下分栏。标题在上，横向流程在下。

流程用**箭头连接的节点**，不用卡片：

```html
<div style="display:flex;align-items:center;gap:0;">
    <div style="padding:12px 20px;background:rgba(59,130,246,0.08);
                border:1px solid rgba(59,130,246,0.15);border-radius:6px;
                font-size:13px;color:#fff;font-weight:600;">
        采集
    </div>
    <div style="width:40px;text-align:center;color:rgba(255,255,255,0.15);font-size:16px;">→</div>
    <div style="padding:12px 20px;background:rgba(59,130,246,0.08);
                border:1px solid rgba(59,130,246,0.15);border-radius:6px;
                font-size:13px;color:#fff;font-weight:600;">
        分析
    </div>
</div>
```

### 6.6 呼吸页（breath page）

呼吸页是数据快照，**极简风格**：

```html
<!-- 不用斜切色块，全局深色底 -->
<body style="background:#0f1923;">
    <div class="big-num">—</div>
    <h1 style="position:absolute;left:72px;top:280px;font-size:28px;
               font-weight:800;color:#fff;z-index:10;">
        核心数据一览
    </h1>
    <!-- 2-3个大号数字横向排列 -->
    <div style="position:absolute;left:72px;right:72px;top:360px;
                display:flex;gap:80px;z-index:10;">
        <div style="text-align:center;">
            <div style="font-size:48px;font-weight:900;color:#3b82f6;">95.6%</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.35);margin-top:8px;">诊断准确率</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:48px;font-weight:900;color:#34d399;">＜3秒</div>
            <div style="font-size:12px;color:rgba(255,255,255,0.35);margin-top:8px;">响应时间</div>
        </div>
    </div>
</body>
```

### 6.7 skill_stairs（技能阶梯/递进展示）

如果需要展示能力递进或等级提升，用**阶梯式布局**：

```html
<!-- 3-4级阶梯，每级向右偏移 -->
<div style="display:flex;flex-direction:column;gap:12px;">
    <div style="margin-left:0;padding:16px 24px;
                background:rgba(59,130,246,0.06);border-left:3px solid #3b82f6;
                font-size:14px;color:#fff;font-weight:600;">
        初级：基础诊疗能力
    </div>
    <div style="margin-left:60px;padding:16px 24px;
                background:rgba(59,130,246,0.08);border-left:3px solid #3b82f6;
                font-size:14px;color:#fff;font-weight:600;">
        中级：AI辅助诊断
    </div>
    <div style="margin-left:120px;padding:16px 24px;
                background:rgba(59,130,246,0.10);border-left:3px solid #3b82f6;
                font-size:14px;color:#fff;font-weight:600;">
        高级：全科智能诊疗
    </div>
</div>
```

---

## 七、特殊页面

### 7.1 封面（cover）

- 使用 AI 生成背景图
- 标题居中，大号，加投影
- 保持现有设计，不改

### 7.2 目录（toc）

左右分栏，左侧标题，右侧章节列表：

```html
<!-- 右侧章节列表 -->
<div style="...display:flex;flex-direction:column;gap:24px;">
    <div style="display:flex;align-items:baseline;gap:16px;">
        <span style="font-size:36px;font-weight:900;color:rgba(59,130,246,0.15);
                     font-family:'Inter',sans-serif;line-height:1;">01</span>
        <span style="font-size:18px;font-weight:600;color:rgba(255,255,255,0.85);">
            项目背景
        </span>
    </div>
</div>
```

### 7.3 章节分隔页（section_divider）

- 使用 AI 生成背景图
- 居中标题
- 保持现有设计，不改

### 7.4 结尾页（ending）

- 使用 AI 生成背景图（与封面呼应）
- 保持现有设计，不改

---

## 八、实现 Checklist

改每个组件时，逐项检查：

- [ ] 用了斜切色块做背景？（或特殊页面用了 AI 背景）
- [ ] 左右分栏还是上下分栏？没有居中堆叠？
- [ ] 装饰数字（大号半透明）放在标题后面了？
- [ ] 标题下有 40px 蓝色分隔线？
- [ ] 内容区没有毛玻璃卡片/圆角容器？
- [ ] 关键点用黄色文字、结果用绿色文字内联标注？
- [ ] 分隔线是 `rgba(255,255,255,0.06)` 的极细线？
- [ ] 页面边缘安全区 ≥ 60px？
- [ ] 页码在左下角，小标签在右下角？
