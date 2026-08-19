# Coding Standards

> 项目代号：PitchForge
> 版本：1.0.0
> 创建日期：2026-04-15
> 维护者：Standards Keeper

---

## 变更历史

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|---------|-------|
| 1.0.0 | 2026-04-15 | 初始版本 | Standards Keeper |

---

## 一、Python 代码规范

### 1.1 PEP 8 遵循

所有 Python 代码必须遵循 [PEP 8](https://peps.python.org/pep-0008/) 规范，关键点：

- **缩进**：使用 4 个空格（不使用 Tab）
- **行长度**：最大 120 字符（项目自定义，比 PEP 8 的 79 更宽松）
- **空行**：
  - 模块级函数/类之间空 2 行
  - 类方法之间空 1 行
  - 函数内部避免多余空行
- **import 顺序**：
  1. 标准库
  2. 第三方库
  3. 本地应用/自定义模块
  - 每组之间空 1 行
  - 使用 `isort` 自动排序

### 1.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | 小写下划线 | `ppt_service.py`, `bg_generator.py` |
| 类名 | CapWords（大驼峰） | `PPTService`, `OutlineGenerator` |
| 函数名 | 小写下划线 | `get_task()`, `submit_questionnaire()` |
| 变量名 | 小写下划线或小写 | `task_id`, `user_id`, `page_index` |
| 常量 | 全大写下划线 | `MAX_RETRY_COUNT`, `PAGE_WIDTH` |
| 私有属性 | 前缀下划线 | `_db_config`, `_theme_cache` |
| 类型变量 | CapWords 或小写 | `T = TypeVar('T')`, `DictStrAny` |

**禁止使用的命名**：
- 单字符名称（循环变量除外：`i`, `j`, `k`）
- 拼音命名
- 与内置函数同名（如 `list`, `dict`, `str`）

### 1.3 文档字符串 (Docstring)

所有公共模块、类、方法必须包含 docstring。

#### Google 风格 docstring 示例

```python
def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """获取PPT任务详情。

    Args:
        task_id: 任务ID

    Returns:
        任务详情字典，包含以下字段：
        - task_id: 任务ID
        - status: 任务状态
        - created_at: 创建时间
        - questionnaire_id: 问卷ID

    Raises:
        HTTPException: 任务不存在时抛出 404 错误

    Example:
        >>> task = await get_task(123)
        >>> print(task['status'])
        'completed'
    """
    pass
```

#### 模块级 docstring

```python
"""
PPT智能生成服务 - 主服务

提供PPT生成、问卷提交、任务管理等核心功能。
依赖 MySQL 数据库存储任务状态。

作者：Backend Team
版本：v2.0
"""
```

### 1.4 类型注解

**必须使用类型注解的场景**：
- 所有公共函数和方法的参数、返回值
- 类实例属性（`__init__` 中声明的）

**类型注解规范**：

```python
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# 基础类型
def get_user_name(user_id: int) -> str:
    pass

# Optional 类型（有默认值）
def get_task(task_id: int, include_details: bool = True) -> Optional[Dict[str, Any]]:
    pass

# List 类型
def get_user_tasks(user_id: int) -> List[Dict[str, Any]]:
    pass

# Union 类型
def parse_value(value: Union[str, int, float]) -> str:
    pass

# 无返回值
def log_error(message: str) -> None:
    pass
```

**禁止使用类型别名降低可读性**：

```python
# 不推荐
MyDict = Dict[str, Any]  # 除非非常复杂的类型

# 推荐：直接使用
def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    pass
```

---

## 二、Git 工作流

### 2.1 分支命名规范

```
<类型>/<任务ID>-<简短描述>

类型前缀：
- feature/     - 新功能
- bugfix/      - Bug修复
- hotfix/      - 紧急修复
- refactor/    - 代码重构
- docs/        - 文档更新
- test/        - 测试相关
- standards/   - 规范相关

示例：
- feature/T123-ppt-generation
- bugfix/T456-fix-empty-page-issue
- hotfix/T789-critical-security-patch
- refactor/T101-extract-rule-engine
```

### 2.2 Commit Message 规范

**格式**：

```
<类型>(<范围>): <简短描述>

[可选的正文]

[可选的脚注]
```

**类型**：
| 类型 | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug修复 |
| docs | 文档更新 |
| style | 代码格式（不影响功能） |
| refactor | 重构（不影响功能） |
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具相关 |

**示例**：

```
feat(ppt): 添加背景图AI生成功能

- 修复bg_generator方法名不匹配问题
- 支持可选的背景图生成

Closes #T123
```

### 2.3 Pull Request 合并规范

**PR 创建前**：
1. 代码必须通过本地测试 `pytest`
2. 无 Pylint/Flake8 错误
3. 更新了相关文档（如有必要）

**PR 描述必须包含**：
- 变更目的和范围
- 关键技术决策
- 测试结果
- 相关的任务/Issue 链接

**合并条件**：
- 至少 1 人 Review 通过（重大变更需 2 人）
- CI/CD 流水线全部通过
- 无 P0/P1 级 Bug

---

## 三、API 设计规范

### 3.1 RESTful 规范

| 操作 | HTTP 方法 | URL 模式 | 示例 |
|------|----------|----------|------|
| 获取资源列表 | GET | `/resource` | `GET /api/ppt/tasks` |
| 获取单个资源 | GET | `/resource/{id}` | `GET /api/ppt/task/123` |
| 创建资源 | POST | `/resource` | `POST /api/ppt/task/create` |
| 更新资源 | PUT | `/resource/{id}` | `PUT /api/ppt/task/123` |
| 删除资源 | DELETE | `/resource/{id}` | `DELETE /api/ppt/task/123` |
| 执行操作 | POST | `/resource/{id}/action` | `POST /api/ppt/task/123/confirm` |

### 3.2 请求/响应格式

**请求格式**：
- 使用 FastAPI 的 Pydantic 模型验证
- Content-Type: `application/json`
- 字符编码: UTF-8

**成功响应格式**：

```json
{
    "success": true,
    "data": {
        "task_id": 123,
        "status": "completed",
        "created_at": "2026-04-15T10:30:00Z"
    }
}
```

**分页响应格式**：

```json
{
    "success": true,
    "data": {
        "items": [...],
        "total": 100,
        "page": 1,
        "page_size": 20,
        "total_pages": 5
    }
}
```

### 3.3 错误码规范

**HTTP 状态码使用**：

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 | OK | 成功获取/更新资源 |
| 201 | Created | 成功创建资源 |
| 400 | Bad Request | 请求参数错误 |
| 401 | Unauthorized | 未认证 |
| 403 | Forbidden | 无权限 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |

**错误响应格式**：

```json
{
    "success": false,
    "error": {
        "code": "TASK_NOT_FOUND",
        "message": "任务不存在",
        "details": {
            "task_id": 123
        }
    }
}
```

**业务错误码命名**：
- 使用大写下划线格式
- 前缀表示模块：`TASK_*`, `QUESTIONNAIRE_*`, `PPT_*`

---

## 四、安全规范

### 4.1 敏感信息管理

**硬编码禁止**：
- API 密钥、数据库密码、Token 等敏感信息禁止硬编码
- 必须使用环境变量或配置文件

**环境变量命名**：
```
<服务>_<类型>_<名称>

示例：
- MYSQL_HOST
- MYSQL_PORT
- MYSQL_USER
- MYSQL_PASSWORD
- DEEPSEEK_API_KEY
- DASHSCOPE_API_KEY
```

**敏感信息日志禁止**：
- 禁止在日志中输出密码、Token、密钥
- 脱敏处理：`password: ****`, `token: ab***cd`

### 4.2 输入验证

**所有外部输入必须验证**：

```python
# 使用 Pydantic 进行请求体验证
class TaskCreateRequest(BaseModel):
    questionnaire_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    tenant_id: int = Field(..., gt=0)
    theme: str = Field(default="dark_tech", max_length=50)

# 路径参数验证
@router.get("/task/{task_id}")
async def get_task(task_id: int = Path(..., gt=0)):
    pass
```

**SQL 注入防护**：
- 必须使用参数化查询
- 禁止字符串拼接 SQL

```python
# 正确
cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))

# 错误
cursor.execute(f"SELECT * FROM tasks WHERE id = {task_id}")
```

### 4.3 API 认证

**认证方式**：
- Header 认证：`Authorization: Bearer <token>`
- API Key 认证：`X-API-Key: <key>`

**认证检查**：
- 所有敏感 API 必须验证身份
- Token 过期时间不超过 24 小时

---

## 五、代码审查清单

### 5.1 功能性
- [ ] 代码实现了需求的功能
- [ ] 边界条件和异常情况已处理
- [ ] 无运行时错误或异常

### 5.2 代码质量
- [ ] 遵循 PEP 8 规范
- [ ] 命名清晰、可读性强
- [ ] 包含必要的 docstring
- [ ] 使用了类型注解

### 5.3 安全性
- [ ] 无敏感信息硬编码
- [ ] 用户输入已验证
- [ ] SQL 使用参数化查询
- [ ] 敏感操作有权限检查

### 5.4 测试
- [ ] 核心逻辑有单元测试
- [ ] 测试覆盖关键路径
- [ ] 本地测试通过

---

## 六、附录

### A. 参考资源

- [PEP 8 - Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [RESTful API 设计最佳实践](https://restfulapi.net/)

### B. 工具推荐

| 工具 | 用途 |
|------|------|
| `black` | 代码格式化 |
| `isort` | import 排序 |
| `pylint` | 代码检查 |
| `mypy` | 类型检查 |
| `pytest` | 单元测试 |
