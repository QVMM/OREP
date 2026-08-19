# Backend Engineer Work Log

## 当前状态
**角色**: Backend Engineer（后端工程师）
**Sprint**: Sprint 0 - 项目骨架搭建

---

## 进展记录

### 2026-04-15
- [x] **T007: 搭建项目骨架、CI/CD**

  **已完成的工作：**

  1. **创建 FastAPI 应用骨架**
     - 创建 `backend/` 目录结构
     - 创建所有 `__init__.py` 模块文件

  2. **创建 `backend/main.py`**
     - FastAPI 应用入口
     - 健康检查端点 `/health`
     - PPT 生成端点 `/api/v1/ppt/generate`
     - 状态查询端点 `/api/v1/ppt/status/{task_id}`

  3. **创建 `backend/config.py`**
     - API 密钥配置（DashScope、DeepSeek）
     - 超时配置
     - 重试配置
     - 主题配置（dark_tech、light_professional、corporate_blue）

  4. **创建 `backend/routers/ppt_router.py`**
     - PPT 生成路由（空实现）
     - 任务状态查询路由（空实现）
     - 任务结果获取路由（空实现）

  5. **创建服务层**
     - `backend/services/round1_service.py` - 大纲生成服务
     - `backend/services/round2_service.py` - 内容生成服务
     - `backend/services/round3_service.py` - HTML预览服务
     - `backend/services/html_batch_service.py` - 批量生成服务

  6. **创建数据模型**
     - `backend/models/request.py` - 请求模型（Pydantic）
     - `backend/models/response.py` - 响应模型（Pydantic）

  7. **创建工具模块**
     - `backend/utils/prompt_loader.py` - Prompt加载器
     - `backend/utils/ai_client.py` - AI客户端
     - `backend/utils/validators.py` - 数据验证器

  8. **创建测试文件**
     - `backend/tests/test_round1.py` - 大纲生成测试
     - `backend/tests/test_round2.py` - 内容生成测试
     - `backend/tests/test_round3.py` - HTML预览测试

  9. **设置 CI/CD**
     - 创建 `.github/workflows/ci.yml`
     - 包含 lint、test、build、security 四个 job

### 2026-04-15 - Pipeline 直接切换
- [x] **直接切换到新 Pipeline（Round 1/2/3/4 AI Pipeline）**

  **决策**：不使用渐进式切换（ConfigSwitch），直接替换 `_generate_v2_async()` 方法的实现

  **修改的文件**：`app/services/ppt/ppt_service.py`

  **修改内容**：
  - 将 `_generate_v2_async()` 方法的实现从旧的"装配引擎路径"切换到新的 `PipelineCoordinator`
  - 旧实现：调用 `outline_generator.generate()` + `LayoutRuleEngine.process()` + `BackgroundGenerator.generate_batch()` + `AssemblyEngine.assemble_page()` + `PPTXRendererHTML.render()`
  - 新实现：调用 `PipelineCoordinator.execute()` 一次性完成 Round 1/2/3/4 + Self-Check，然后渲染PPTX

  **关键代码变更**：
  ```python
  # 直接调用新 Pipeline
  from .adapter_code.pipeline_coordinator import PipelineCoordinator
  coordinator = PipelineCoordinator(timeout=600)
  result = await coordinator.execute(
      task_id=task_id,
      questionnaire_data=responses,
      progress_callback=progress_callback
  )
  outline_json = result.get("outline_json", {})
  html_pages = result.get("html_pages", [])  # AI生成的HTML页面列表
  ```

  **新 Pipeline 返回格式**：
  - `outline_json`: 通过 OutputAdapter 转换的大纲JSON
  - `enriched_pages`: 丰富后的页面内容
  - `html_pages`: AI生成的HTML字符串列表（核心创新）
  - `check_report`: 质量审计报告
  - `meta`: 元数据

  **后续处理（保持不变）**：
  1. 保存HTML预览到 `preview_{task_id}/` 目录
  2. 调用 `PPTXRendererHTML.render()` 将HTML渲染为PPTX
  3. 更新任务状态为 completed

  **验证的依赖文件**：
  - `app/services/ppt/adapter_code/pipeline_coordinator.py` - PipelineCoordinator 类
  - `app/services/ppt/adapter_code/input_adapter.py` - 输入格式转换
  - `app/services/ppt/adapter_code/output_adapter.py` - 输出格式转换

---

## 产出物清单

### API & Pipeline
- [x] backend/routers/ppt_router.py
- [x] backend/services/round1_service.py
- [x] backend/services/round2_service.py
- [x] backend/services/round3_service.py
- [x] backend/services/html_batch_service.py

### Models
- [x] backend/models/request.py
- [x] backend/models/response.py

### Utils
- [x] backend/utils/prompt_loader.py
- [x] backend/utils/ai_client.py
- [x] backend/utils/validators.py

### Tests
- [x] backend/tests/test_round1.py
- [x] backend/tests/test_round2.py
- [x] backend/tests/test_round3.py

### Infrastructure
- [x] .github/workflows/ci.yml

## 备注
- 所有代码遵循 `standards/CODING_STANDARDS.md` 规范
- 服务层方法均为空实现（NotImplementedError），等待后续 Sprint 实现
- CI/CD 流水线包含：代码质量检查、单元测试、构建验证、安全扫描
