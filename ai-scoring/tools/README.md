# OpenPencil ↔ V9 双向同步工具

这些工具实现了 OpenPencil 设计工具和 V9 组件系统之间的双向转换。

## 工具列表

| 工具 | 用途 | 示例 |
|------|------|------|
| `op_to_v9.py` | 将 .op 设计文件转换为 V9 Python 组件 | `python op_to_v9.py cover.op -o cover.py` |
| `v9_to_op.py` | 将 V9 组件转换为 .op 文件用于预览 | `python v9_to_op.py cover -o preview.op` |
| `sync_watch.py` | 实时监听文件变化并自动同步 | `python sync_watch.py --op-dir ./designs` |

## 快速开始

### 1. 从 OpenPencil 设计导出为 V9 组件

```bash
# 基本用法
python tools/op_to_v9.py ~/项目/OREP/ai-scoring/test_cover.op \
    --output app/services/ppt/components/cover_from_op.py

# 生成预览 HTML
python tools/op_to_v9.py test_cover.op --preview -o preview.html

# 自定义组件名称
python tools/op_to_v9.py test_cover.op \
    --component-id my_cover \
    --component-name "我的封面" \
    -o my_cover.py
```

### 2. 从 V9 组件生成 .op 预览文件

```bash
# 基本用法（使用预设模板）
python tools/v9_to_op.py cover -o cover_preview.op

# 使用指定主题
python tools/v9_to_op.py cover --theme black-gold -o cover_black_gold.op

# 自定义内容
python tools/v9_to_op.py cover \
    --title "我的项目" \
    --subtitle "创新解决方案" \
    --team "我的团队" \
    -o custom_cover.op
```

### 3. 实时同步监听

```bash
# 启动双向同步监听
python tools/sync_watch.py \
    --op-dir ./designs \
    --v9-dir ./app/services/ppt/components \
    --preview-dir ./preview \
    --theme deep-blue-tech

# 只监听 .op → V9
python tools/sync_watch.py --direction op-to-v9

# 只监听 V9 → .op
python tools/sync_watch.py --direction v9-to-op
```

## 支持的主题

- `deep-blue-tech` - 深蓝科技（默认）
- `black-gold` - 黑金奢华
- `fresh-green` - 清新绿意
- `sky-blue-tech` - 天蓝科技

## 工作流程示例

### 场景 1：设计新组件

```bash
# 1. 在 OpenPencil 中设计，保存为 my_component.op
# 2. 转换为 V9 组件
python tools/op_to_v9.py my_component.op \
    -o app/services/ppt/components/my_component.py

# 3. 在代码中使用
# from app.services.ppt.components.my_component import MyComponentComponent
```

### 场景 2：迭代现有组件

```bash
# 1. 从 V9 组件生成预览 .op
python tools/v9_to_op.py my_component -o preview.op

# 2. 在 OpenPencil 中打开 preview.op 进行修改
# 3. 保存后重新转换
python tools/op_to_v9.py preview.op \
    -o app/services/ppt/components/my_component.py --update
```

### 场景 3：使用 Claude Code MCP

在 Claude Code 对话中，可以直接：

```
# 读取设计文件
读取 test_cover.op 的内容

# 修改设计
将 test_cover.op 中的标题改为 "新的标题"

# 生成 V9 代码
基于 test_cover.op 生成 V9 组件代码
```

## 文件格式

### .op 文件结构

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
      "nodes": [...]
    }
  ],
  "variables": [...]
}
```

### V9 组件结构

```python
from .base import BaseComponent, ThemeContext

class MyComponent(BaseComponent):
    component_id = "my_component"
    component_name = "我的组件"

    def render(self, data: Dict, theme: ThemeContext,
               page_index: int = 1, total_pages: int = 1) -> str:
        # 渲染逻辑
        return self._wrap_full_page(body, theme)
```

## 依赖

- Python 3.8+
- watchdog（仅 sync_watch.py 需要）

```bash
pip install watchdog
```

## 故障排除

### 问题：转换后的组件样式不对

- 检查 .op 文件中的 variables 是否正确
- 确认主题颜色映射是否匹配

### 问题：中文显示乱码

- 确保所有文件使用 UTF-8 编码
- 检查 fontFamily 是否支持中文（如 "Noto Sans SC"）

### 问题：sync_watch.py 无法启动

```bash
pip install watchdog
```
