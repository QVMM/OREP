"""
PPT生成器 API 路由 - 基于模板的可配置PPT生成系统
Phase 1: 后端模板系统
"""
import logging
import os
import uuid
import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.ppt_generator.config_schema import (
    PPTConfig, GenerateRequest, GenerateResponse,
    ThemeListResponse, TemplateListResponse, ThemeName, LayoutType
)
from app.services.ppt_generator.renderer import PPTXRenderer, ThemeManager, TemplateManager
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ppt-generator", tags=["PPT生成器"])

# 初始化管理器
renderer = PPTXRenderer()
theme_manager = ThemeManager()
template_manager = TemplateManager()

# 输出目录
OUTPUT_DIR = os.path.join(settings.UPLOAD_DIR, 'ppt_generator')
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==================== 任务存储（简单内存版本，后续可迁移至Redis/DB）====================

_tasks: dict = {}


class GeneratePPTRequest(BaseModel):
    """生成PPT请求体"""
    config: PPTConfig


class GeneratePPTResponse(BaseModel):
    """生成PPT响应"""
    success: bool
    task_id: str = ""
    download_url: str = ""
    message: str = ""


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "service": "PPT Generator"}


@router.get("/themes", response_model=ThemeListResponse)
async def get_themes():
    """获取所有可用主题"""
    try:
        themes = theme_manager.list_themes()
        return ThemeListResponse(success=True, themes=themes)
    except Exception as e:
        logger.error(f"获取主题列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def get_templates(layout: Optional[str] = None):
    """获取模板列表"""
    try:
        templates = template_manager.list_templates(layout)
        return {"success": True, "templates": templates}
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{layout}")
async def get_templates_by_layout(layout: str):
    """获取指定布局类型的模板"""
    try:
        templates = template_manager.list_templates(layout)
        return {"success": True, "layout": layout, "templates": templates}
    except Exception as e:
        logger.error(f"获取模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/layouts")
async def get_layouts():
    """获取所有可用布局类型"""
    layouts = [
        {"value": lt.value, "label": _get_layout_label(lt.value)}
        for lt in LayoutType
    ]
    return {"success": True, "layouts": layouts}


def _get_layout_label(layout: str) -> str:
    """获取布局类型的中文标签"""
    labels = {
        "cover": "封面",
        "toc": "目录",
        "section": "章节过渡",
        "two_column": "双栏对比",
        "three_cards": "三卡片",
        "kpi_dashboard": "KPI仪表盘",
        "team_cards": "团队展示",
        "timeline": "时间线",
        "full_text": "全文页",
        "ending": "结束页"
    }
    return labels.get(layout, layout)


@router.post("/generate", response_model=GeneratePPTResponse)
async def generate_ppt(req: GeneratePPTRequest, background_tasks: BackgroundTasks):
    """
    生成PPT

    接收PPT配置，异步生成PPTX文件
    """
    try:
        task_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(OUTPUT_DIR, f"ppt_{task_id}.pptx")

        # 初始化任务状态
        _tasks[task_id] = {
            "status": "generating",
            "progress": 0,
            "output_path": output_path,
            "message": "正在生成PPT..."
        }

        # 异步执行生成
        background_tasks.add_task(
            _generate_ppt_task,
            task_id,
            req.config,
            output_path
        )

        return GeneratePPTResponse(
            success=True,
            task_id=task_id,
            message="PPT生成任务已创建，请稍后查询状态"
        )
    except Exception as e:
        logger.error(f"创建PPT生成任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_ppt_task(task_id: str, config: PPTConfig, output_path: str):
    """异步生成PPT任务"""
    try:
        _tasks[task_id]["status"] = "generating"
        _tasks[task_id]["progress"] = 10
        _tasks[task_id]["message"] = "正在渲染PPT..."

        # 渲染PPT
        await renderer.render(config, output_path)

        _tasks[task_id]["status"] = "completed"
        _tasks[task_id]["progress"] = 100
        _tasks[task_id]["message"] = "PPT生成完成"
        _tasks[task_id]["download_url"] = f"/api/ppt-generator/download/{task_id}"

        logger.info(f"任务 {task_id} PPT生成完成")

    except Exception as e:
        logger.error(f"任务 {task_id} PPT生成失败: {e}")
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["message"] = f"PPT生成失败: {str(e)}"


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = _tasks[task_id]
    return {
        "success": True,
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"]
    }


@router.get("/download/{task_id}")
async def download_ppt(task_id: str):
    """下载生成的PPT"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = _tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"PPT尚未生成完成，当前状态: {task['status']}")

    file_path = task["output_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PPT文件不存在")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=f"ppt_{task_id}.pptx"
    )


@router.post("/generate-sync")
async def generate_ppt_sync(req: GeneratePPTRequest):
    """
    同步生成PPT（适合小文件快速生成）

    直接生成并返回文件
    """
    try:
        task_id = str(uuid.uuid4())[:8]
        output_path = os.path.join(OUTPUT_DIR, f"ppt_{task_id}.pptx")

        # 同步渲染
        await renderer.render(req.config, output_path)

        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"ppt_{task_id}.pptx"
        )
    except Exception as e:
        logger.error(f"同步生成PPT失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_config(config: PPTConfig):
    """验证PPT配置"""
    errors = []
    warnings = []

    # 验证项目名称
    if not config.project_name:
        errors.append("项目名称不能为空")

    # 验证幻灯片
    if not config.slides:
        errors.append("至少需要一页幻灯片")
    else:
        for i, slide in enumerate(config.slides):
            if slide.index <= 0:
                warnings.append(f"第{i+1}页的页码应大于0")

            # 验证封面页
            if slide.layout == LayoutType.COVER:
                if not slide.data.get("title") and not config.project_name:
                    warnings.append(f"封面页（第{slide.index}页）缺少标题")

            # 验证目录页
            if slide.layout == LayoutType.TOC:
                sections = slide.data.get("sections", [])
                if not sections:
                    warnings.append(f"目录页（第{slide.index}页）没有章节内容")

            # 验证卡片页
            if slide.layout == LayoutType.THREE_CARDS:
                cards = slide.data.get("cards", [])
                if len(cards) < 3:
                    warnings.append(f"三卡片页（第{slide.index}页）卡片数量不足3个")

    return {
        "success": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


@router.get("/example-config")
async def get_example_config():
    """获取示例配置"""
    return {
        "success": True,
        "config": {
            "project_name": "示例项目",
            "team_name": "示例团队",
            "theme": "deep-blue",
            "slides": [
                {
                    "index": 1,
                    "layout": "cover",
                    "section": "封面",
                    "data": {
                        "title": "智慧养老健康监测系统",
                        "subtitle": "基于60GHz毫米波雷达与AI知识库的无接触守护方案",
                        "team_name": "示例团队"
                    }
                },
                {
                    "index": 2,
                    "layout": "toc",
                    "section": "目录",
                    "data": {
                        "title": "目录",
                        "sections": ["项目背景", "痛点分析", "解决方案", "技术架构", "商业模式", "团队介绍"]
                    }
                },
                {
                    "index": 3,
                    "layout": "section",
                    "section": "项目背景",
                    "data": {
                        "title": "项目背景",
                        "subtitle": "智慧养老的时代需求"
                    }
                },
                {
                    "index": 4,
                    "layout": "two_column",
                    "section": "痛点分析",
                    "data": {
                        "title": "痛点与方案",
                        "left_title": "核心痛点",
                        "left_content": ["独居老人跌倒无人发现", "传统监测设备佩戴不适", "数据采集不及时", "应急响应速度慢"],
                        "right_title": "我们的方案",
                        "right_content": ["毫米波雷达无接触监测", "AI智能跌倒检测", "实时数据传输", "10秒内响应报警"]
                    }
                },
                {
                    "index": 5,
                    "layout": "three_cards",
                    "section": "核心技术",
                    "data": {
                        "title": "核心技术优势",
                        "cards": [
                            {"title": "毫米波雷达", "content": "60GHz高频雷达，精度达毫米级，穿透性强，不受光照影响"},
                            {"title": "AI算法", "content": "深度学习跌倒检测算法，准确率99.2%，误报率<0.5%"},
                            {"title": "边缘计算", "content": "本地数据处理，保护隐私，响应延迟<100ms"}
                        ]
                    }
                },
                {
                    "index": 6,
                    "layout": "kpi_dashboard",
                    "section": "关键指标",
                    "data": {
                        "title": "关键效能指标",
                        "metrics": [
                            {"name": "跌倒检出率", "value": "99.2%", "unit": "准确率"},
                            {"name": "响应时间", "value": "<10", "unit": "秒"},
                            {"name": "误报率", "value": "0.5%", "unit": "以下"},
                            {"name": "用户满意度", "value": "98", "unit": "%"}
                        ]
                    }
                },
                {
                    "index": 7,
                    "layout": "timeline",
                    "section": "发展规划",
                    "data": {
                        "title": "发展路线图",
                        "items": [
                            {"time": "2024 Q1", "content": "完成产品原型开发"},
                            {"time": "2024 Q2", "content": "启动试点测试（50户）"},
                            {"time": "2024 Q3", "content": "产品迭代优化"},
                            {"time": "2024 Q4", "content": "正式商用发布"}
                        ]
                    }
                },
                {
                    "index": 8,
                    "layout": "ending",
                    "section": "结束",
                    "data": {
                        "title": "感谢聆听",
                        "contact": "联系方式：example@example.com"
                    }
                }
            ]
        }
    }
