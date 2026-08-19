# OpenPencil ↔ V9 组件双向同步工作流

## 概述

这个工作流实现了 OpenPencil（可视化设计工具）和 V9 组件系统（代码渲染引擎）之间的双向同步：

```
┌─────────────────┐         ┌─────────────────┐
│   OpenPencil    │ ◄─────► │   V9 Components │
│   (.op 文件)    │         │   (Python 代码) │
└─────────────────┘         └─────────────────┘
        │                           │
        ▼                           ▼
   可视化设计                    代码渲染
   所见即所得                    主题系统
```

## 第一步：安装和配置（已完成）

### 1.1 OpenPencil MCP 服务器

已配置在 `~/.claude/mcp.json`：
```json
{
  "mcpServers": {
    "openpencil": {
      "command": "node",
      "args": ["/Applications/OpenPencil.app/Contents/Resources/mcp-server.cjs"],
      "env": {
        "OPENPENCIL_HOST": "localhost",
        "OPENPENCIL_PORT": "53943"
      }
    }
  }
}
```

### 1.2 验证安装

```bash
# 检查 OpenPencil 是否运行
ps aux | grep OpenPencil

# 检查端口
cat ~/.openpencil/.port
```

## 第二步：使用 OpenPencil 设计组件

### 2.1 创建新设计

1. 打开 OpenPencil 应用
2. 创建新项目，设置画布尺寸为 1280x720（PPT 标准尺寸）
3. 使用可视化工具设计组件

### 2.2 .op 文件格式

OpenPencil 使用 `.op` 文件存储设计，格式如下：

```json
{
  "version": "0.7.0",
  "name": "组件名称",
  "pages": [
    {
      "id": "page-1",
      "name": "Page Name",
      "width": 1280,
      "height": 720,
      "nodes": [
        {
          "id": "bg",
          "type": "RECT",
          "x": 0,
          "y": 0,
          "width": 1280,
          "height": 720,
          "fill": {
            "type": "GRADIENT_LINEAR",
            "stops": [
              {"offset": 0, "color": "#0a0a1a"},
              {"offset": 1, "color": "#0a1b3d"}
            ]
          }
        },
        {
          "id": "title",
          "type": "TEXT",
          "x": 100,
          "y": 200,
          "width": 650,
          "text": "标题文本",
          "fontSize": 56,
          "fontWeight": 900,
          "fill": "#FFFFFF",
          "fontFamily": "Noto Sans SC"
        }
      ]
    }
  ],
  "variables": [
    {"name": "bg-primary", "type": "color", "value": "#0a0a1a"},
    {"name": "accent", "type": "color", "value": "#0056d3"}
  ]
}
```

### 2.3 支持的节点类型

- `RECT`: 矩形（支持圆角、渐变）
- `ELLIPSE`: 椭圆/圆形
- `TEXT`: 文本
- `LINE`: 线条
- `IMAGE`: 图片

## 第三步：导出为 V9 组件

### 3.1 转换流程

```
OpenPencil 设计 → .op 文件 → 转换脚本 → V9 Python 组件
```

### 3.2 使用转换工具

```bash
# 从 .op 文件生成 V9 组件
python tools/op_to_v9.py input.op --output app/services/ppt/components/my_component.py

# 预览转换结果
python tools/op_to_v9.py input.op --preview
```

### 3.3 转换规则

| OpenPencil | V9 组件 |
|------------|---------|
| RECT + fill | `<div style="background: ...">` |
| ELLIPSE | `<div style="border-radius: 50%">` |
| TEXT | `<h1>`, `<p>`, `<span>` |
| GRADIENT_LINEAR | `linear-gradient()` |
| GRADIENT_RADIAL | `radial-gradient()` |
| variables | ThemeContext 属性 |

## 第四步：V9 组件结构

### 4.1 组件基类

```python
from .base import BaseComponent, ThemeContext

class MyComponent(BaseComponent):
    component_id = "my_component"
    component_name = "我的组件"

    def render(self, data: Dict, theme: ThemeContext,
               page_index: int = 1, total_pages: int = 1) -> str:
        title = data.get("title", "默认标题")

        body = f'''
<div style="position:absolute;left:100px;top:180px;z-index:20;">
    <h1 style="font-size:56px;font-weight:900;color:{theme.text_primary};">
        {title}
    </h1>
</div>
{self._get_page_number(theme, page_index, total_pages)}'''

        return self._wrap_full_page(body, theme)
```

### 4.2 主题变量

可用的主题变量（通过 ThemeContext）：

```python
theme.bg_primary      # 主背景色
theme.bg_secondary    # 次背景色
theme.accent          # 强调色
theme.glow_color      # 发光色
theme.text_primary    # 主文本色
theme.text_body       # 正文文本色
theme.shadow_glow     # 发光阴影
```

## 第五步：双向同步

### 5.1 V9 → OpenPencil（预览）

```bash
# 从 V9 组件生成 .op 文件用于预览
python tools/v9_to_op.py my_component --output preview.op

# 在 OpenPencil 中打开预览
open preview.op
```

### 5.2 OpenPencil → V9（更新）

```bash
# 修改设计后，重新生成组件
python tools/op_to_v9.py modified.op --output app/services/ppt/components/my_component.py --update
```

### 5.3 实时同步（使用 MCP）

在 Claude Code 对话中，可以直接使用 MCP 工具：

```
# 读取 .op 文件
读取 /path/to/design.op 文件内容

# 修改 .op 文件
更新 design.op 中的 title 节点文本为 "新标题"

# 生成 V9 代码
基于 design.op 生成 V9 组件代码
```

## 第六步：实际工作流程示例

### 场景：设计一个新的封面组件

1. **在 OpenPencil 中设计**
   ```
   打开 OpenPencil → 新建项目 → 设计封面 → 保存为 cover.op
   ```

2. **转换为 V9 组件**
   ```bash
   python tools/op_to_v9.py cover.op --output app/services/ppt/components/cover_v2.py
   ```

3. **注册组件**
   ```python
   # 在 app/services/ppt/components/__init__.py 中添加
   from .cover_v2 import CoverV2Component
   ```

4. **测试渲染**
   ```bash
   python test_v9_components.py
   ```

5. **如需调整，同步回 OpenPencil**
   ```bash
   python tools/v9_to_op.py cover_v2 --output cover_updated.op
   # 在 OpenPencil 中打开 cover_updated.op 继续编辑
   ```

## 工具清单

| 工具 | 用途 | 命令 |
|------|------|------|
| `op_to_v9.py` | .op → V9 组件 | `python tools/op_to_v9.py input.op` |
| `v9_to_op.py` | V9 组件 → .op | `python tools/v9_to_op.py component_name` |
| `sync_watch.py` | 实时同步监听 | `python tools/sync_watch.py` |
| MCP 服务器 | Claude Code 集成 | 自动配置 |

## 最佳实践

1. **命名规范**
   - .op 文件：使用小写 + 下划线，如 `cover_page.op`
   - V9 组件：使用 PascalCase，如 `CoverPageComponent`

2. **版本控制**
   - .op 文件和 V9 组件代码都应提交到 Git
   - 使用有意义的提交信息说明设计变更

3. **主题一致性**
   - 在 .op 文件中使用 variables 定义颜色
   - 在 V9 组件中使用 theme 变量，避免硬编码颜色

4. **测试驱动**
   - 每次转换后运行 `test_v9_components.py`
   - 验证渲染结果是否符合预期

## 故障排除

### 问题：MCP 连接失败

```bash
# 检查 OpenPencil 是否运行
ps aux | grep OpenPencil

# 重启 OpenPencil
killall OpenPencil
open -a OpenPencil

# 验证端口
cat ~/.openpencil/.port
```

### 问题：转换后的组件样式不对

- 检查 .op 文件中的 variables 是否正确
- 确认 theme 变量映射是否完整
- 对比原始设计和渲染结果

### 问题：中文显示异常

- 确保 fontFamily 设置为 "Noto Sans SC" 或其他中文字体
- 检查 Python 文件编码为 UTF-8

## 下一步

- 创建更多预置组件模板
- 开发实时预览功能
- 集成到自动化构建流程
