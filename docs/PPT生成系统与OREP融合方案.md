# AI智能PPT生成系统与OREP融合方案

> 分析日期：2026-04-07
> 基于：AI智能PPT生成系统技术方案 + OREP在线路演评审平台

---

## 一、技术可行性分析

### 1.1 PPT生成方案技术可行性评估

| 技术模块 | 可行性 | 评估依据 |
|---------|--------|---------|
| **LLM理解需求** | ✅ 高 | DeepSeek/MiniMax已集成于OREP，可直接复用 |
| **TTS语音合成** | ✅ 高 | 有成熟的阿里云DashScope API，与OREP的ASR同一体系 |
| **PPT结构生成** | ⚠️ 中 | 垂类场景结构固定，prompt工程可解决 |
| **PPT美化排版** | ⚠️ 中-低 | python-pptx排版能力有限，需大量模板支撑 |
| **图片生成/匹配** | ⚠️ 中 | 通用图库+垂类图库成本可控，质量需人工审核 |
| **实时演讲对应** | ✅ 高 | 音频切分+时间戳对齐技术成熟 |

### 1.2 关键技术瓶颈

1. **中文排版问题**：python-pptx对中文字体、排版控制能力有限
2. **设计感不足**：纯AI生成的PPT缺乏视觉设计专业性
3. **图片版权**：通用AI生成图片与职业教育场景贴合度低
4. **风格一致性**：多页之间的视觉连贯性难以保证

---

## 二、与OREP项目的技术重合度分析

### 2.1 现有技术资产重合矩阵

| PPT生成模块 | OREP对应资产 | 重合度 | 复用方式 |
|------------|-------------|--------|---------|
| **LLM文案生成** | `llm_scoring_service.py` (DeepSeek/MiniMax) | **95%** | 复用客户端+改造prompt |
| **语音质量分析** | `speech_analysis_service.py` | **90%** | 直接复用 |
| **ASR语音识别** | `asr_service.py` (FunASR) | **85%** | 直接复用 |
| **五维评分体系** | `llm_scoring_service.py` 15观测点 | **100%** | 直接复用评分标准 |
| **AI微服务架构** | FastAPI + Python | **100%** | 直接复用基础设施 |
| **后端API网关** | Spring Boot | **100%** | 直接复用 |
| **前端UI框架** | Vue 3 + Element Plus | **100%** | 直接复用 |
| **文件存储** | MinIO + 本地存储 | **100%** | 直接复用 |
| **PPT模板管理** | `PptTemplateController.java` | **80%** | 扩展为动态模板系统 |
| **讲稿管理** | `ScriptController.java` | **100%** | 直接复用 |

**综合技术重合度：约85%**

### 2.2 OREP已解决但PPT生成需要的关键能力

```
OREP已有 → PPT生成可直接复用
├── 多模型LLM调用（DeepSeek + MiniMax双模型对比评分）
├── 15观测点梯度评分规则（职业院校技能大赛官方标准）
├── 五维评分体系（技能水平60分 + 职业素养10分 + 应用价值10分 + 团队合作10分 + 创新创意10分）
├── 能力画像生成（定性分析 + 关键洞察 + 改进建议）
├── 复盘问答系统（AI评委对话）
├── ASR转录 + 语音质量分析
├── 视频帧分析（Qwen3-VL-Flash）
├── 多模态融合分析
└── 完整的前后端+微服务架构
```

---

## 三、融合架构设计

### 3.1 系统融合后的完整架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        OREP + PPT生成融合平台                      │
├─────────────────────────────────────────────────────────────────┤
│  前端 (Vue 3)                                                    │
│  ├── 会议室 (MeetingRoom.vue) ✅ 已有                            │
│  ├── 评分结果 (ScoreResult.vue) ✅ 已有                          │
│  ├── AI复盘问答 (RoadshowChat.vue) ✅ 已有                       │
│  ├── PPT生成器 (PptGenerator.vue) 🆕 新增                       │
│  ├── 讲稿编辑器 (ScriptEditor.vue) 🔄 扩展                       │
│  └── PPT模板库 (PptTemplate.vue) 🔄 扩展                        │
├─────────────────────────────────────────────────────────────────┤
│  后端 (Spring Boot) ✅ 已有                                      │
│  ├── 新增 PptGeneratorController.java 🆕                        │
│  ├── 新增 PptScriptController.java 🆕 (讲稿→PPT联动)            │
│  └── 扩展 PptTemplateController.java 🔄                         │
├─────────────────────────────────────────────────────────────────┤
│  AI微服务 (Python FastAPI) ✅ 已有                               │
│  ├── llm_scoring_service.py ✅ 复用评分prompt + 扩展生成prompt   │
│  ├── speech_analysis_service.py ✅ 直接复用                      │
│  ├── asr_service.py ✅ 直接复用                                  │
│  ├── video_analysis_service.py ✅ 直接复用                       │
│  ├── character_profile_service.py ✅ 复用画像→PPT内容            │
│  ├── ppt_script_service.py 🆕 新增 (讲稿生成/优化)               │
│  ├── ppt_content_service.py 🆕 新增 (PPT内容规划)                │
│  ├── ppt_slide_service.py 🆕 新增 (幻灯片生成)                   │
│  └── tts_service.py 🆕 新增 (语音合成)                          │
├─────────────────────────────────────────────────────────────────┤
│  数据库 (MySQL) ✅ 已有                                          │
│  ├── 新增 ppt_project 表 🆕                                     │
│  ├── 新增 ppt_slide 表 🆕                                       │
│  ├── 新增 ppt_script 表 🆕                                      │
│  └── 新增 ppt_asset 表 🆕 (图片/图标素材)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流融合设计

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           路演全生命周期闭环                              │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  【准备阶段】                        【路演阶段】                         │
│  ┌─────────┐     ┌─────────┐       ┌─────────┐     ┌─────────┐        │
│  │ 项目文档 │────▶│ AI分析  │       │ 实时路演 │────▶│ 多模态  │        │
│  │ 上传    │     │ 内容理解 │       │ MeetingRoom│    │ 录制    │        │
│  └─────────┘     └────┬────┘       └─────────┘     └────┬────┘        │
│                       │                                  │              │
│                       ▼                                  ▼              │
│               ┌───────────────┐                  ┌───────────────┐     │
│               │ AI讲稿生成    │                  │ ASR+视频分析  │     │
│               │ (OREP评分体系)│                  │ (OREP已有)    │     │
│               └───────┬───────┘                  └───────┬───────┘     │
│                       │                                  │              │
│                       ▼                                  ▼              │
│               ┌───────────────┐                  ┌───────────────┐     │
│               │ AI PPT生成    │                  │ 五维评分+画像 │     │
│               │ (按讲稿生成)  │                  │ (OREP已有)    │     │
│               └───────┬───────┘                  └───────┬───────┘     │
│                       │                                  │              │
│                       ▼                                  ▼              │
│               ┌───────────────┐                  ┌───────────────┐     │
│               │ TTS音频生成   │                  │ AI复盘问答    │     │
│               │ (可选)        │                  │ (OREP已有)    │     │
│               └───────┬───────┘                  └───────┬───────┘     │
│                       │                                  │              │
│                       └──────────┐    ┌──────────────────┘              │
│                                  ▼    ▼                                 │
│                          ┌────────────────┐                            │
│                          │  改进建议生成   │                            │
│                          │ (评分→PPT优化) │                            │
│                          └────────┬───────┘                            │
│                                   │                                    │
│                                   ▼                                    │
│                          ┌────────────────┐                            │
│                          │ PPT迭代优化    │                            │
│                          │ (闭环改进)     │                            │
│                          └────────────────┘                            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 四、融合后的技术路线（与OREP高度重合）

### 4.1 开发阶段调整

| 阶段 | 原PPT方案 | 融合后方案 | OREP资产复用率 |
|------|----------|-----------|--------------|
| **阶段一** | AI理解需求 | **复用OREP评分体系 + 扩展讲稿生成** | 90% |
| **阶段二** | AI生成文案+大纲 | **复用LLM服务 + 新增PPT内容规划** | 85% |
| **阶段三** | PPT美化排版 | **复用PPT模板系统 + 新增动态生成** | 70% |
| **阶段四** | 图片生成/匹配 | **新增垂类图库 + AI图片** | 30% |
| **阶段五** | TTS+演讲对齐 | **复用语音分析 + 新增TTS** | 60% |
| **阶段六** | 测试+部署 | **复用Docker部署** | 95% |

### 4.2 详细开发计划

#### 阶段一：讲稿智能生成（2-3天）

**目标**：基于项目文档和五维评分体系，自动生成路演讲稿

**复用OREP资产**：
- `llm_scoring_service.py` 的15观测点评分规则作为内容生成的反向约束
- `character_profile_service.py` 的能力画像结构作为讲稿组织参考
- `ScriptController.java` 讲稿存储接口

**新增模块**：
```python
# ai-scoring/app/services/ppt_script_service.py

class PptScriptService:
    """讲稿生成服务 - 基于OREP评分体系"""

    # 复用评分prompt中的15观测点，反向构建讲稿prompt
    SCRIPT_SYSTEM_PROMPT = """
    你是一位职业院校技能大赛路演讲稿撰写专家。
    你需要根据项目文档，生成符合2025年世界职业院校技能大赛评分标准的路演讲稿。

    ## 讲稿要求
    1. 内容必须覆盖五维评分体系的所有观测点：
       - 技能水平（60分）：操作规范性、技能熟练度、任务难易度、技术先进性、现场讲解效果
       - 职业素养（10分）：职业道德、工匠精神、安全意识
       - 应用价值（10分）：实用性、经济性、可持续性
       - 团队合作（10分）：团队精神、沟通协作
       - 创新创意（10分）：创新意识、创新成效

    2. 讲稿结构要求：
       - 开场（30秒）：项目概述 + 团队介绍
       - 问题背景（1分钟）：行业痛点 + 需求分析
       - 技术方案（3分钟）：架构设计 + 核心技术 + 创新点
       - 实现演示（3分钟）：操作规范 + 现场演示 + 效果展示
       - 应用价值（1分钟）：实用性 + 经济性 + 可持续性
       - 团队协作（30秒）：分工 + 协作方式
       - 总结（30秒）：核心亮点 + 未来展望

    3. 语言风格：
       - 口语化但专业
       - 每段标注[预计时长]
       - 标注[演示要点]（需要配合PPT/操作的部分）
       - 标注[评分覆盖]（对应评分观测点编号）
    """

    async def generate_script(
        self,
        project_doc: str,           # 项目文档内容
        team_info: dict,            # 团队信息
        duration_sec: int = 600,    # 路演时长（默认10分钟）
        provider: str = "deepseek"  # LLM选择
    ) -> dict:
        """生成路演讲稿"""
        pass

    async def optimize_script(
        self,
        script: str,
        score_result: dict,         # OREP评分结果
        profile: dict               # OREP能力画像
    ) -> dict:
        """基于评分结果优化讲稿（闭环改进）"""
        pass
```

#### 阶段二：PPT内容规划（2-3天）

**目标**：基于讲稿，规划PPT每页的内容结构

**复用OREP资产**：
- `llm_scoring_service.py` 的双模型对比评分机制 → 用于内容质量验证
- `video_analysis_service.py` 的PPT内容识别 → 用于现有PPT分析

**新增模块**：
```python
# ai-scoring/app/services/ppt_content_service.py

class PptContentService:
    """PPT内容规划服务"""

    CONTENT_SYSTEM_PROMPT = """
    你是一位PPT内容规划专家，专精职业院校技能大赛路演PPT。

    ## 输入
    - 路演讲稿（已按评分体系优化）
    - 团队信息
    - 评分标准（五维15观测点）

    ## 输出要求
    为每页PPT规划：
    1. 页码 + 标题
    2. 核心信息（1-2句）
    3. 内容类型：标题页/内容页/图表页/图片页/演示页/总结页
    4. 文案内容：
       - 标题文案
       - 要点文案（3-5条，每条≤20字）
       - 补充说明（可选）
    5. 视觉元素建议：
       - 图片描述（用于AI生成或图库匹配）
       - 图表类型（柱状图/折线图/饼图/流程图/架构图）
       - 图标建议
    6. 评分覆盖：该页对应哪些评分观测点
    7. 演示要点：该页的讲解重点
    """

    async def plan_slides(
        self,
        script: dict,
        template_style: str = "tech",
        slide_count: int = 15
    ) -> list[dict]:
        """规划PPT幻灯片结构"""
        pass
```

#### 阶段三：PPT幻灯片生成（3-4天）

**目标**：基于内容规划，生成PPT文件

**复用OREP资产**：
- `PptTemplateController.java` → 扩展为动态模板系统
- MinIO存储 → PPT文件存储

**新增模块**：
```python
# ai-scoring/app/services/ppt_slide_service.py

class PptSlideService:
    """PPT幻灯片生成服务"""

    def __init__(self):
        self.template_dir = "templates/ppt"
        self.asset_dir = "assets/ppt"

    async def generate_ppt(
        self,
        slide_plan: list[dict],
        template_id: str,
        team_info: dict
    ) -> bytes:
        """生成PPT文件"""
        # 1. 加载模板
        template = self.load_template(template_id)

        # 2. 逐页填充
        prs = Presentation(template)
        for i, slide_data in enumerate(slide_plan):
            slide = prs.slides[i]
            await self.fill_slide(slide, slide_data)

        # 3. 保存
        return self.save_ppt(prs)

    async def fill_slide(self, slide, data: dict):
        """填充单页内容"""
        # 文本替换
        for shape in slide.shapes:
            if shape.has_text_frame:
                self.replace_text(shape, data)

        # 插入图片
        if data.get("image_url"):
            await self.insert_image(slide, data["image_url"], data["image_position"])

        # 插入图表
        if data.get("chart_type"):
            self.insert_chart(slide, data["chart_type"], data["chart_data"])

    async def generate_image(self, description: str) -> str:
        """AI生成图片（调用DashScope）"""
        # 调用通义万相API
        pass

    def get_builtin_assets(self, category: str) -> list[str]:
        """获取内置职业教育图库"""
        # 标准图标、流程图、架构图等
        pass
```

#### 阶段四：TTS语音合成（1-2天）

**目标**：为讲稿生成演讲音频

**复用OREP资产**：
- `speech_analysis_service.py` → 语音质量评估基准
- `asr_service.py` → DashScope API体系

**新增模块**：
```python
# ai-scoring/app/services/tts_service.py

class TtsService:
    """语音合成服务 - DashScope CosyVoice"""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY

    async def synthesize(
        self,
        text: str,
        voice: str = "longcheng",    # 龙城（男声，专业）
        speed: float = 1.0,          # 语速
        emotion: str = "neutral"     # 情感
    ) -> bytes:
        """合成单段语音"""
        # DashScope CosyVoice API
        pass

    async def synthesize_script(
        self,
        script_sections: list[dict],
        voice_mapping: dict = None   # 角色→声音映射
    ) -> list[dict]:
        """为整个讲稿生成语音，返回每段音频+时间戳"""
        results = []
        for section in script_sections:
            audio = await self.synthesize(
                section["text"],
                voice=voice_mapping.get(section["role"], "longcheng")
            )
            results.append({
                "section_id": section["id"],
                "audio_bytes": audio,
                "duration_ms": self.get_duration(audio),
                "text": section["text"]
            })
        return results
```

#### 阶段五：讲稿-PPT对齐（1-2天）

**目标**：将TTS音频与PPT页面精确对齐

**新增模块**：
```python
# ai-scoring/app/services/ppt_alignment_service.py

class PptAlignmentService:
    """讲稿-PPT对齐服务"""

    async def align_script_to_slides(
        self,
        script_sections: list[dict],
        slide_plan: list[dict],
        audio_segments: list[dict]
    ) -> dict:
        """
        对齐讲稿段落与PPT页面

        返回：
        {
            "total_duration_ms": 600000,
            "slides": [
                {
                    "slide_index": 0,
                    "slide_title": "项目概述",
                    "script_text": "...",
                    "audio_url": "...",
                    "start_ms": 0,
                    "end_ms": 30000,
                    "highlight_points": ["评分覆盖：观测点1,2"]
                },
                ...
            ]
        }
        """
        pass

    async def generate_timed_ppt(
        self,
        ppt_bytes: bytes,
        alignment: dict
    ) -> bytes:
        """生成带时间轴的PPT（在备注区添加时间信息）"""
        pass
```

#### 阶段六：闭环优化（2-3天）

**目标**：基于路演评分结果，自动优化PPT和讲稿

**复用OREP资产**：
- `llm_scoring_service.py` 的15观测点评分 → 精确定位改进点
- `character_profile_service.py` 的能力画像 → 定性改进建议
- `chat_service.py` 的AI复盘问答 → 交互式改进指导

**新增模块**：
```python
# ai-scoring/app/services/ppt_optimization_service.py

class PptOptimizationService:
    """PPT闭环优化服务"""

    OPTIMIZATION_PROMPT = """
    你是一位PPT优化专家。基于路演评分结果和能力画像，给出PPT改进建议。

    ## 输入
    - 当前PPT内容规划
    - 五维评分结果（含各观测点得分和扣分原因）
    - 能力画像（含关键洞察和改进建议）
    - AI复盘问答记录

    ## 输出
    为每页PPT给出：
    1. 当前问题（对应扣分观测点）
    2. 具体改进建议
    3. 修改后的文案/内容
    4. 预期提升效果
    """

    async def analyze_improvements(
        self,
        current_slides: list[dict],
        score_result: dict,
        profile: dict,
        qa_records: list[dict]
    ) -> list[dict]:
        """分析PPT改进点"""
        pass

    async def generate_optimized_ppt(
        self,
        current_ppt: bytes,
        improvements: list[dict]
    ) -> bytes:
        """生成优化后的PPT"""
        pass
```

---

## 五、新增数据库表设计

```sql
-- PPT项目表
CREATE TABLE ppt_project (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meeting_id BIGINT COMMENT '关联会议ID',
    user_id BIGINT NOT NULL COMMENT '创建用户',
    name VARCHAR(200) NOT NULL COMMENT '项目名称',
    project_doc_url VARCHAR(500) COMMENT '项目文档URL',
    template_id VARCHAR(50) COMMENT '模板ID',
    status ENUM('draft','script_generated','ppt_generated','optimized') DEFAULT 'draft',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_meeting (meeting_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PPT幻灯片表
CREATE TABLE ppt_slide (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    slide_index INT NOT NULL COMMENT '页码',
    title VARCHAR(200) COMMENT '标题',
    content_type ENUM('title','content','chart','image','demo','summary') DEFAULT 'content',
    content_json JSON COMMENT '内容结构（文案、图表数据等）',
    image_url VARCHAR(500) COMMENT '主图URL',
    chart_config JSON COMMENT '图表配置',
    script_text TEXT COMMENT '对应讲稿文本',
    audio_url VARCHAR(500) COMMENT '对应音频URL',
    duration_ms INT COMMENT '预计展示时长(ms)',
    score_coverage JSON COMMENT '覆盖的评分观测点',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PPT讲稿表
CREATE TABLE ppt_script (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    script_id BIGINT COMMENT '关联OREP讲稿ID',
    content LONGTEXT NOT NULL COMMENT '讲稿全文',
    sections_json JSON COMMENT '分段结构（含时间标注）',
    ai_generated TINYINT DEFAULT 0,
    optimized_by_score TINYINT DEFAULT 0,
    version INT DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PPT素材表
CREATE TABLE ppt_asset (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category ENUM('icon','shape','background','chart_template') NOT NULL,
    industry VARCHAR(50) COMMENT '适用行业（tech/education/industry/medical）',
    name VARCHAR(100) NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    tags JSON COMMENT '标签（用于检索）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (category, industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PPT生成记录表
CREATE TABLE ppt_generation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    project_id BIGINT NOT NULL,
    action ENUM('script_generate','content_plan','slide_generate','tts','optimize') NOT NULL,
    provider VARCHAR(50) COMMENT '使用的LLM/TTS provider',
    model VARCHAR(50) COMMENT '使用的模型',
    prompt_tokens INT COMMENT '输入token数',
    completion_tokens INT COMMENT '输出token数',
    duration_ms INT COMMENT '耗时(ms)',
    status ENUM('success','failed') NOT NULL,
    error_msg TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 六、技术重合度总结

| 模块 | 原PPT方案独立实现 | 融合后复用OREP | 节省工作量 |
|------|-----------------|---------------|-----------|
| **LLM调用** | 需新建API封装 | 直接复用`get_client()` | 80% |
| **评分体系** | 需重新定义规则 | 直接复用15观测点prompt | 100% |
| **ASR语音** | 需新建服务 | 直接复用`asr_service.py` | 90% |
| **语音分析** | 需新建服务 | 直接复用`speech_analysis_service.py` | 90% |
| **视频分析** | 需新建服务 | 直接复用`video_analysis_service.py` | 85% |
| **后端API** | 需新建Spring Boot项目 | 直接复用现有项目 | 95% |
| **前端UI** | 需新建Vue项目 | 直接复用现有项目 | 95% |
| **数据库** | 需新建Schema | 在现有Schema上扩展 | 80% |
| **部署** | 需新建Docker配置 | 直接复用`docker-compose.yml` | 90% |
| **存储** | 需新建存储服务 | 直接复用MinIO | 95% |

**总体复用率：约85%**

**新增开发工作量估算**：
- 原PPT方案独立实现：约20-25天
- 融合后新增开发：约10-12天（节省50%+）

---

## 七、融合优势

### 7.1 数据闭环

```
路演准备（PPT+讲稿） → 路演实况 → 评分分析 → 改进建议 → PPT优化 → 再路演
         ↑                                                          │
         └──────────────────────────────────────────────────────────┘
```

OREP的评分结果可以直接驱动PPT的迭代优化，形成完整的**"准备→路演→评估→改进"**闭环。

### 7.2 评分一致性

PPT生成时就内置了15观测点的评分标准，确保：
- 讲稿内容覆盖所有评分维度
- PPT页面结构服务于评分展示
- 改进建议精准对应扣分观测点

### 7.3 技术栈统一

- 后端：统一的Spring Boot API网关
- AI服务：统一的FastAPI微服务
- 前端：统一的Vue 3 + Element Plus UI
- 部署：统一的Docker Compose编排

---

## 八、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| python-pptx中文排版问题 | PPT美观度不足 | 1. 预设高质量模板；2. 限制字体为思源系列；3. 关键页面提供手动调整入口 |
| AI生成图片质量不稳定 | 视觉效果差 | 1. 优先使用垂类图库；2. AI生成仅用于特定场景；3. 提供图片替换功能 |
| 幻觉导致内容错误 | 专业性受损 | 1. 双模型对比验证；2. 关键数据人工审核；3. 提供编辑修改功能 |
| 生成速度慢 | 用户体验差 | 1. 流式输出+实时预览；2. 缓存常见模板；3. 异步生成+通知 |

---

## 九、文件变更清单

| 阶段 | 文件路径 | 操作 | 说明 |
|------|---------|------|------|
| 一 | `ai-scoring/app/services/ppt_script_service.py` | 🆕 新增 | 讲稿生成服务 |
| 一 | `ai-scoring/app/routers/ppt_router.py` | 🆕 新增 | PPT相关API路由 |
| 一 | `backend/src/main/java/com/orep/backend/controller/PptScriptController.java` | 🆕 新增 | 讲稿-PPT联动接口 |
| 二 | `ai-scoring/app/services/ppt_content_service.py` | 🆕 新增 | PPT内容规划服务 |
| 三 | `ai-scoring/app/services/ppt_slide_service.py` | 🆕 新增 | 幻灯片生成服务 |
| 三 | `ai-scoring/app/services/ppt_alignment_service.py` | 🆕 新增 | 讲稿-PPT对齐服务 |
| 四 | `ai-scoring/app/services/tts_service.py` | 🆕 新增 | TTS语音合成服务 |
| 五 | `ai-scoring/app/services/ppt_optimization_service.py` | 🆕 新增 | PPT闭环优化服务 |
| 五 | `frontend/user/src/views/PptGenerator.vue` | 🆕 新增 | PPT生成器页面 |
| 五 | `frontend/user/src/views/PptEditor.vue` | 🆕 新增 | PPT编辑器页面 |
| 六 | `sql/init.sql` | 🔄 扩展 | 新增5张PPT相关表 |
| 六 | `deploy/docker-compose.yml` | 🔄 扩展 | 新增PPT生成服务配置 |

---

## 十、结论

**AI智能PPT生成系统与OREP项目的技术融合是高度可行的**，主要基于以下判断：

1. **技术重合度高（85%）**：OREP已具备PPT生成所需的绝大部分技术基础设施
2. **业务场景一致**：两者都服务于职业院校技能大赛的路演场景
3. **数据闭环完整**：评分结果可驱动PPT迭代优化，形成完整闭环
4. **开发成本可控**：融合后新增开发量约为独立实现的50%

**建议采用融合方案**，将PPT生成功能作为OREP平台的"路演准备"模块，与现有的"路演评估"模块形成完整的路演全生命周期闭环。
