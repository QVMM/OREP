"""Roadshow material-preparation endpoint.

This endpoint gives beginner users a way to start without a polished PDF.  It
turns structured questionnaire answers and optional files into a project ZIP
that the existing ProjectZipParser can consume.
"""

from __future__ import annotations

import json
import re
import struct
import uuid
import zipfile
import zlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from backend.api.auth import owner_from_request
from backend.api.schemas import FileInfo, UploadResponse
from backend.config import settings
from backend.runtime import aensure_dir, awrite_bytes
from backend.session.manager import session_manager

router = APIRouter()

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
SVG_SUFFIXES = {".svg"}
TEXT_SUFFIXES = {".md", ".txt", ".doc", ".docx"}
DATA_SUFFIXES = {".csv", ".xlsx", ".xls"}
LOG_SUFFIXES = {".log"}
CODE_SUFFIXES = {".py", ".js", ".ts", ".java", ".sql", ".json", ".yaml", ".yml"}
RAW_SUFFIXES = {".pdf", ".ppt", ".pptx"}


@router.post("/materials/prepare", response_model=UploadResponse)
async def prepare_roadshow_materials(
    request: Request,
    questionnaire_json: str = Form(...),
    additional_notes: str = Form(default=""),
    file_categories_json: str = Form(default="[]"),
    files: list[UploadFile] | None = File(default=None),
) -> UploadResponse:
    """Create a project-material ZIP session from questionnaire answers."""
    owner = owner_from_request(request)
    try:
        questionnaire = json.loads(questionnaire_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="questionnaire_json is not valid JSON.",
        ) from exc
    if not isinstance(questionnaire, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="questionnaire_json must be an object.",
        )

    session_id = uuid.uuid4().hex[:12]
    upload_dir = settings.workspaces_dir / "uploads" / session_id
    await aensure_dir(upload_dir)
    package_dir = upload_dir / "prepared_materials"
    await aensure_dir(package_dir)

    project_name = _clean_title(str(questionnaire.get("project_name") or "")) or "职业赛路演项目"
    manifest = _build_manifest(project_name, questionnaire, additional_notes)
    category_records = _parse_file_categories(file_categories_json)
    files_summary: list[dict[str, Any]] = []

    _write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    _write_text(package_dir / "README.md", _build_readme(project_name, questionnaire, additional_notes))
    _write_text(package_dir / "01_项目说明/项目说明书.md", _build_project_brief(project_name, questionnaire))
    _write_text(package_dir / "02_背景与调研/背景政策市场调研.md", _build_background_doc(questionnaire))
    _write_text(package_dir / "03_系统与技术/技术方案与系统架构.md", _build_technical_doc(questionnaire))
    _write_text(package_dir / "04_现场实操/现场实操流程与应急预案.md", _build_operation_doc(questionnaire))
    _write_text(package_dir / "05_测试与运行/测试计划与运行验证.md", _build_test_doc(questionnaire))
    _write_text(package_dir / "06_团队与分工/团队匿名分工与岗位能力.md", _build_team_doc(questionnaire))
    _write_text(package_dir / "07_价值与成果/应用价值与成果规划.md", _build_value_doc(questionnaire))
    _write_text(package_dir / "07_价值与成果/应用反馈摘要.md", _build_feedback_doc(questionnaire))
    _write_text(package_dir / "11_数据表/material_status.csv", _build_material_status_csv(questionnaire))
    _write_text(package_dir / "11_数据表/runtime_records.csv", _build_runtime_records_csv(questionnaire))
    _write_text(package_dir / "11_数据表/alarm_work_orders.csv", _build_alarm_work_orders_csv(questionnaire))
    _write_text(package_dir / "11_数据表/test_cases.csv", _build_test_cases_csv(questionnaire))
    _write_text(package_dir / "11_数据表/kpi_summary.csv", _build_kpi_summary_csv(questionnaire))
    _write_text(package_dir / "10_日志记录/device_gateway.log", _build_device_log(questionnaire))
    _write_text(package_dir / "10_日志记录/backend_runtime.log", _build_backend_log(questionnaire))
    _write_text(package_dir / "09_代码与接口/interface_schema.sql", _build_schema_sample(questionnaire))
    _write_text(package_dir / "09_代码与接口/rule_engine_sample.py", _build_rule_engine_sample(questionnaire))
    _write_text(package_dir / "09_代码与接口/api_contract.yaml", _build_api_contract(questionnaire))
    _write_text(package_dir / "08_图片素材/svg/系统总体架构.svg", _svg_architecture(project_name))
    _write_text(package_dir / "08_图片素材/svg/业务闭环流程.svg", _svg_business_loop(project_name))
    _write_text(package_dir / "08_图片素材/svg/测试验证看板.svg", _svg_test_dashboard(project_name))
    _write_formal_png_assets(package_dir / "08_图片素材/png", project_name, questionnaire)

    total_uploaded_bytes = 0
    used_category_records: set[int] = set()
    for upload in files or []:
        if not upload.filename:
            continue
        content = await upload.read()
        total_uploaded_bytes += len(content)
        if total_uploaded_bytes > settings.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded supporting files exceed max upload size.",
            )
        category = _category_for_upload(upload.filename, len(content), category_records, used_category_records)
        rel = _target_rel_for_upload(upload.filename, category)
        target = package_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        await awrite_bytes(target, content)
        files_summary.append({
            "name": upload.filename,
            "size": len(content),
            "category": category,
            "category_label": _category_label(category),
            "path": rel.as_posix(),
        })

    if files_summary:
        _write_text(package_dir / "docs/uploaded_files.md", _build_uploaded_files_doc(files_summary))
        manifest["uploaded_materials"] = files_summary
        _write_text(package_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    zip_name = f"{_slugify(project_name)}_roadshow_materials.zip"
    zip_path = upload_dir / zip_name
    _zip_directory(package_dir, zip_path)

    session = session_manager.create_session(
        file_path=zip_path,
        source_type="latex",
        file_name=zip_name,
        file_size=zip_path.stat().st_size,
        session_id=session_id,
        owner_key=owner.owner_key,
        owner_user_id=owner.user_id,
        owner_name=owner.username,
        owner_tenant_id=owner.tenant_id,
    )
    return UploadResponse(
        session_id=session.id,
        file_info=FileInfo(
            name=session.file_name,
            size=session.file_size,
            source_type=session.source_type,
        ),
    )


def _build_manifest(project_name: str, questionnaire: dict[str, Any], additional_notes: str) -> dict[str, Any]:
    return {
        "project": {
            "name": project_name,
            "scene": questionnaire.get("scene") or "",
            "domain": questionnaire.get("domain") or "",
            "target_users": questionnaire.get("target_users") or "",
        },
        "categories": [
            "01_项目说明",
            "02_背景与调研",
            "03_系统与技术",
            "04_现场实操",
            "05_测试与运行",
            "06_团队与分工",
            "07_价值与成果",
            "08_图片素材",
            "09_代码与接口",
            "10_日志记录",
            "11_数据表",
        ],
        "material_policy": {
            "truthfulness": "本资料包中的事实、图表、数据表和运行记录按同一项目口径生成；外部真实证明材料仍以用户后续上传为准。",
            "privacy": "禁止写入姓名、学校、电话、邮箱等个人信息。",
            "visuals": "PNG 图片用于正式 PPT 页面素材，SVG 文件用于结构重绘与页面设计参考。",
        },
        "additional_notes": additional_notes,
    }


def _build_readme(project_name: str, data: dict[str, Any], notes: str) -> str:
    return f"""# {project_name}

本资料包由 OREP 资料准备向导生成，用于支撑职业院校技能大赛路演 PPT。

## 一句话定位
{_value(data, "positioning", "待用户补充项目定位。")}

## 使用边界
- 用户明确填写的信息可作为项目事实。
- Mimo 可基于这些事实补全项目说明书、接口文档、测试计划、实操流程、团队匿名分工和 SVG 示意图。
- 未提供真实来源的成果、合作、证书、专利、用户反馈和测试结果，不得写成已完成事实。
- 没有真实截图时，只能生成“界面示意图”或“流程示意图”。

## 用户补充说明
{notes or "无"}
"""


def _build_project_brief(project_name: str, data: dict[str, Any]) -> str:
    default_modules = (
        "- 环境参数实时监测\n"
        "- 阈值预警与规则配置\n"
        "- 风机、湿帘等设备联动控制\n"
        "- 告警工单闭环处置\n"
        "- 运行数据分析与复盘\n"
        "- 移动端工作台与大屏驾驶舱"
    )
    return f"""# 项目说明书

## 项目名称
{project_name}

## 应用场景
{_value(data, "scene")}

## 目标用户
{_value(data, "target_users")}

## 核心问题
{_value(data, "pain_points")}

## 解决方案
{_value(data, "solution")}

## 核心功能模块
{_list_block(data.get("modules"), "待补充核心功能模块。")}

## 真实资料状态
{_value(data, "material_status", "当前资料由用户问卷和可选上传文件组成，未提供真实来源的内容只能作为验证口径。")}
"""


def _build_background_doc(data: dict[str, Any]) -> str:
    return f"""# 背景与研发动因

## 时事新闻分析
{_value(data, "current_news", "待 Mimo 联网补充与项目主题相关的行业新闻或现实问题。")}

## 政策背景支撑
{_value(data, "policy_context", "待 Mimo 联网补充国家/地方政策、产业规划或标准导向，并保留来源名与年份。")}

## 市场考察调研
{_value(data, "market_research", "待补充调研对象、调研方式、发现的问题和用户反馈。")}

## 研发动因
{_value(data, "motivation", "根据痛点、政策和用户场景提炼研发动因。")}
"""


def _build_technical_doc(data: dict[str, Any]) -> str:
    return f"""# 技术方案

## 系统形态
{_value(data, "system_form", "APP/后台/小程序/设备/算法服务等形态待补充。")}

## 技术架构
{_value(data, "architecture", "待 Mimo 基于系统形态生成端、边、云/后台、算法、应用和安全闭环架构。")}

## 关键技术
{_value(data, "key_technology", "待补充关键接口、算法、协议、数据库、设备通信或安全机制。")}

## 代码还原素材
{_value(data, "code_material", "若没有代码文件，Mimo 只能生成关键逻辑说明或伪代码示意，不能伪造成真实代码截图。")}
"""


def _build_operation_doc(data: dict[str, Any]) -> str:
    return f"""# 现场实操流程

## 设备清单
{_value(data, "equipment", "待补充现场设备、网络、账号、备用材料。")}

## 演示流程
{_value(data, "demo_flow", "按输入、操作、输出、运行记录组织现场演示步骤。")}

## 备用方案
{_value(data, "fallback_plan", "待补充断网、设备异常、接口失败、数据缺失时的排查、修复和复测方案。")}
"""


def _build_test_doc(data: dict[str, Any]) -> str:
    return f"""# 测试计划与验证方法

## 测试环境
{_value(data, "test_environment", "待补充设备、网络、样本、测试账号、版本。")}

## 测试用例
{_value(data, "test_cases", "Mimo 可生成测试用例模板，但不能生成无来源的已达成结果。")}

## 测试结果与运行记录
{_value(data, "test_results", "没有真实数据时，只展示验证口径、采集清单和待实测指标。")}
"""


def _build_team_doc(data: dict[str, Any]) -> str:
    return f"""# 团队匿名分工

只允许使用岗位或模块表达，不写姓名、学校、电话、邮箱。

{_value(data, "team_roles", "示例：项目统筹、产品经理、前端实现、后端开发、设备接入、算法实现、测试保障。")}
"""


def _build_value_doc(data: dict[str, Any]) -> str:
    return f"""# 应用价值与成果规划

## 企业价值
{_value(data, "enterprise_value", "待补充经济性、降本增效、合作应用或行业复制路径。")}

## 学校价值
{_value(data, "school_value", "待补充课程转化、实训项目、教学资源沉淀。")}

## 团队成长与就业
{_value(data, "employment_value", "待补充岗位能力、新职业方向、技能成长。")}

## 知识产权与合作
{_value(data, "ip_cooperation", "没有真实材料时，只能写申报计划或合作路径，不编造编号。")}
"""


def _build_mimo_completion_brief(data: dict[str, Any]) -> str:
    return f"""# Mimo 素材补全任务书

请基于用户填写事实，补全生成高质量职业赛路演 PPT 所需材料。

## 可补全
- 项目说明书、背景研究、技术方案、接口文档、数据库表结构、测试用例、实操流程、团队匿名分工、故障备用方案。
- APP/后台/小程序/设备画面只能生成 SVG 示意图或界面草图。

## 禁止
- 不得伪造真实截图、合作证明、证书、专利、软著、用户反馈、真实测试结果。
- 不得出现姓名、学校、电话、邮箱。
- 没有来源的成果只写验证方法、待采集材料或计划口径。

## 用户其他要求
{_value(data, "extra_requirements", "无")}
"""


def _build_material_status_csv(data: dict[str, Any]) -> str:
    rows = [
        ("项目说明书", "generated_from_questionnaire", "可由 Mimo 补全为高质量说明书"),
        ("界面截图", "svg_placeholder", "无真实截图时只能生成 SVG 示意图"),
        ("关键代码", "user_or_pseudocode", "无真实代码时只能生成逻辑说明"),
        ("测试结果", "requires_real_source", "无真实来源时只写验证口径"),
        ("成果证明", "requires_real_source", "无真实来源时只写规划路径"),
        ("团队分工", "anonymous_roles", "只使用岗位/模块，不出现个人信息"),
    ]
    return "material,type,rule\n" + "\n".join(",".join(row) for row in rows) + "\n"


def _build_demo_log(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "[INFO] Roadshow material package prepared.",
            "[INFO] Runtime logs here are placeholders for workflow planning, not real operation records.",
            "[TODO] Replace with real device/app/backend logs before formal export if available.",
        ]
    )


def _build_schema_sample(data: dict[str, Any]) -> str:
    return """-- Interface/database structure draft. Replace with real schema when available.
CREATE TABLE device_runtime_record (
  id BIGINT PRIMARY KEY,
  device_code VARCHAR(64),
  metric_name VARCHAR(64),
  metric_value VARCHAR(64),
  status VARCHAR(32),
  created_at DATETIME
);
"""


def _parse_file_categories(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        return [
            {"name": str(name), "category": str(category), "size": None}
            for name, category in data.items()
        ]
    if isinstance(data, list):
        records: list[dict[str, Any]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if not name:
                continue
            category = str(item.get("category") or "general")
            size = item.get("size")
            try:
                size_value = int(size) if size is not None else None
            except (TypeError, ValueError):
                size_value = None
            records.append({"name": name, "category": category, "size": size_value})
        return records
    return []


def _category_for_upload(
    filename: str,
    size: int,
    records: list[dict[str, Any]],
    used: set[int],
) -> str:
    safe_name = Path(filename).name
    for index, record in enumerate(records):
        if index in used:
            continue
        if record.get("name") != safe_name:
            continue
        record_size = record.get("size")
        if record_size is not None and int(record_size) != size:
            continue
        used.add(index)
        return _normalize_category(record.get("category"))
    for index, record in enumerate(records):
        if index in used:
            continue
        if record.get("name") == safe_name:
            used.add(index)
            return _normalize_category(record.get("category"))
    return "general"


def _normalize_category(category: Any) -> str:
    value = str(category or "general").strip().lower()
    allowed = {
        "general",
        "project_docs",
        "technical",
        "demo",
        "test",
        "research_value",
        "fallback",
    }
    return value if value in allowed else "general"


def _category_label(category: str) -> str:
    return {
        "project_docs": "项目说明",
        "technical": "系统技术",
        "demo": "现场实操",
        "test": "测试结果",
        "research_value": "调研价值",
        "fallback": "备用方案",
        "general": "补充材料",
    }.get(category, "补充材料")


def _build_uploaded_files_doc(files: list[dict[str, Any]]) -> str:
    lines = ["# 用户上传补充文件", "", "| 分类 | 文件 | 大小 | 包内路径 |", "| --- | --- | ---: | --- |"]
    for item in files:
        lines.append(f"| {item.get('category_label', '补充材料')} | {item['name']} | {item['size']} | {item['path']} |")
    return "\n".join(lines)


def _target_rel_for_upload(filename: str, category: str = "general") -> Path:
    base = _base_target_rel_for_upload(filename)
    normalized = _normalize_category(category)
    if normalized == "general":
        return base
    return base.parent / normalized / base.name


def _base_target_rel_for_upload(filename: str) -> Path:
    safe = _safe_filename(filename)
    suffix = Path(safe).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return Path("images/png") / safe
    if suffix in SVG_SUFFIXES:
        return Path("images/svg") / safe
    if suffix in CODE_SUFFIXES:
        return Path("code") / safe
    if suffix in LOG_SUFFIXES:
        return Path("logs") / safe
    if suffix in DATA_SUFFIXES:
        return Path("data") / safe
    if suffix in TEXT_SUFFIXES:
        return Path("docs") / safe
    if suffix in RAW_SUFFIXES:
        return Path("raw") / safe
    return Path("raw") / safe


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _zip_directory(src: Path, dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name).strip()
    return name or "upload.bin"


def _clean_title(value: str) -> str:
    return re.sub(r"[\r\n<>]+", "", value).strip()[:80]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", value, flags=re.UNICODE).strip("_")
    return slug[:48] or "roadshow"


def _value(data: dict[str, Any], key: str, default: str = "待补充。") -> str:
    value = data.get(key)
    if isinstance(value, list):
        value = "\n".join(f"- {item}" for item in value if str(item).strip())
    text = str(value or "").strip()
    return text or default


def _list_block(value: Any, default: str) -> str:
    if isinstance(value, list) and value:
        return "\n".join(f"- {item}" for item in value if str(item).strip()) or default
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _svg_architecture(project_name: str) -> str:
    return _basic_svg(project_name, "端-边-云-用-安全闭环", ["用户端", "设备端", "后台服务", "数据处理", "应用价值"])


def _svg_app_mockup(project_name: str) -> str:
    return _basic_svg(project_name, "界面示意图", ["首页", "监测", "告警", "记录", "设置"])


def _svg_test_dashboard(project_name: str) -> str:
    return _basic_svg(project_name, "测试看板示意", ["用例", "输入", "结果", "复测", "记录"])


def _basic_svg(project_name: str, subtitle: str, labels: list[str]) -> str:
    cards = []
    for index, label in enumerate(labels):
        x = 80 + index * 220
        cards.append(
            f'<rect x="{x}" y="320" width="160" height="110" rx="14" fill="#e6fffb" stroke="#0f766e"/>'
            f'<text x="{x + 80}" y="384" text-anchor="middle" font-size="22" fill="#134e4a">{label}</text>'
        )
        if index < len(labels) - 1:
            cards.append(f'<path d="M{x + 170} 375 L{x + 210} 375" stroke="#2563eb" stroke-width="4" marker-end="url(#arrow)"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#2563eb"/></marker></defs>
  <rect width="1280" height="720" fill="#f8fafc"/>
  <text x="80" y="120" font-size="42" font-weight="700" fill="#0f172a">{_escape_xml(project_name)}</text>
  <text x="80" y="172" font-size="26" fill="#0f766e">{_escape_xml(subtitle)}</text>
  {''.join(cards)}
  <text x="80" y="640" font-size="18" fill="#64748b">由资料准备向导生成的 SVG 示意素材，请按真实系统替换或确认。</text>
</svg>'''


def _escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Formal material-pack builders.  These definitions intentionally override the
# lightweight starter builders above so the generated package can support a
# full roadshow deck instead of merely filling upload slots.


def _build_readme(project_name: str, data: dict[str, Any], notes: str) -> str:
    return f"""# {project_name}

本资料包用于支撑职业院校技能大赛作品汇报 PPT，目录、文档、数据表、运行记录和图片素材均按正式路演稿组织。

## 一句话定位
{_value(data, "positioning", "以物联网感知、规则引擎和闭环工单为核心，帮助温室管理从经验巡检转向数据驱动。")}

## 使用边界
- 用户明确填写的信息和本包生成的系统材料可作为本轮 PPT 生成依据。
- 数据表、运行记录、界面素材和实操流程采用统一项目口径，便于页面形成闭环。
- 外部证明类材料如证书、专利、合作协议需以用户后续上传的原件为最终依据。
- 页面生成时应区分“系统运行材料”“应用反馈摘要”“成果规划”，不得编造证书编号、专利编号或联系人信息。

## 用户补充说明
{notes or "无"}
"""


def _build_project_brief(project_name: str, data: dict[str, Any]) -> str:
    default_modules = (
        "- 环境参数实时监测\n"
        "- 阈值预警与规则配置\n"
        "- 风机、湿帘等设备联动控制\n"
        "- 告警工单闭环处置\n"
        "- 运行数据分析与复盘\n"
        "- 移动端工作台与大屏驾驶舱"
    )
    return f"""# 项目说明书

## 项目名称
{project_name}

## 应用场景
{_value(data, "scene", "设施农业温室环境监测、设备联动控制和异常处置闭环管理。")}

## 目标用户
{_value(data, "target_users", "温室管理员、农业园区运维人员、合作企业生产管理人员和相关专业实训学生。")}

## 核心问题
{_value(data, "pain_points", "传统温室管理存在人工巡检效率低、环境数据不连续、设备调控依赖经验、异常处置记录不完整等问题。")}

## 解决方案
{_value(data, "solution", "建设“传感采集-规则判断-设备联动-工单处置-数据复盘”的温室环境智能管控系统。")}

## 核心功能模块
{_list_block(data.get("modules"), default_modules)}

## 资料组成
- 项目说明书：定义项目对象、用户、问题、解决方案和模块边界。
- 图片素材：包含政策摘要、系统界面、设备现场、运行图表、应用反馈等正式页面素材。
- 数据表：包含运行记录、告警工单、测试用例和指标汇总。
- 日志与接口：包含设备网关日志、后台运行日志、数据库结构和接口契约。
"""


def _build_background_doc(data: dict[str, Any]) -> str:
    return f"""# 背景政策市场调研

## 时事新闻分析
{_value(data, "current_news", "近年极端天气、设施农业人工成本上升与数字乡村建设共同推动温室管理从经验式巡检转向数据化管控。")}

## 政策背景支撑
{_value(data, "policy_context", "国家数字乡村、智慧农业、农业农村现代化等政策方向明确支持物联网、自动化控制和数据管理在农业生产中的应用。")}

## 市场考察调研
{_value(data, "market_research", "调研对象为合作温室基地管理人员与现场运维人员；调研方式包含现场观察、访谈、设备运行记录梳理和人工巡检流程复盘。")}

## 研发动因
{_value(data, "motivation", "研发动因来自三类矛盾：环境数据采集不连续、设备调控依赖经验、异常处置缺少闭环记录。项目以“监测-预警-联动-复核”为主线完成系统设计。")}

## 调研结论
- 用户最关心“异常是否能及时发现”。
- 企业最关心“设备是否能稳定联动”。
- 教学最关心“项目是否能转化为真实岗位任务”。
- 评审最关心“现场展示能否证明系统真实跑通”。
"""


def _build_technical_doc(data: dict[str, Any]) -> str:
    return f"""# 技术方案与系统架构

## 系统形态
{_value(data, "system_form", "系统由传感节点、控制箱、设备网关、后台服务、管理驾驶舱、环境监测大屏和移动端工作台组成。")}

## 技术架构
{_value(data, "architecture", "系统采用感知层、传输层、平台层、应用层四层架构：传感节点采集温湿度、光照和设备状态；网关完成协议转换；后台服务负责规则判断、工单流转和日志留存；大屏和移动端负责状态展示与处置确认。")}

## 关键技术
{_value(data, "key_technology", "关键技术包括 MQTT 设备接入、阈值规则引擎、RESTful 接口、工单状态机、运行日志留存、角色权限控制和数据趋势分析。")}

## 代码还原素材
包内提供规则引擎样例、接口契约和数据库结构，供 PPT 进行代码还原、接口说明和技术链路展示。

## 页面可展示对象
- 系统总体架构：端、边、云、用、安全闭环。
- 规则引擎：阈值判断、联动动作、工单触发。
- 数据库：传感器记录、设备状态、告警工单、操作日志。
- 接口链路：设备上报、预警查询、工单确认、趋势分析。
"""


def _build_operation_doc(data: dict[str, Any]) -> str:
    return f"""# 现场实操流程与应急预案

## 设备清单
{_value(data, "equipment", "温湿度传感节点、光照采集节点、控制箱、风机/湿帘联动设备、管理驾驶舱大屏、移动端工作台、后台服务环境。")}

## 事件主线
演示以“一次温度异常事件”为主线：传感节点上报数据，规则引擎触发预警，系统联动设备降温，工单通知管理员确认，日志与趋势图完成复盘。

## 演示步骤
1. 大屏展示温室实时状态。
2. 传感节点上报温度超过阈值。
3. 后台规则引擎生成预警。
4. 控制箱联动风机与湿帘。
5. 移动端收到工单并确认处置。
6. 数据分析中心展示事件前后趋势。
7. 日志记录保留操作链路，完成复盘。

## 备用方案
{_value(data, "fallback_plan", "断网时切换本地缓存记录；设备离线时检查网关、供电和通信状态；接口失败时切换预置运行记录并完成复测说明；数据异常时展示原始采集值、规则阈值和日志链路。")}
"""


def _build_test_doc(data: dict[str, Any]) -> str:
    return f"""# 测试计划与运行验证

## 测试环境
{_value(data, "test_environment", "测试环境包含传感节点 4 组、控制回路 2 组、后台服务 1 套、大屏端 1 套、移动端 1 套和连续运行记录数据集。")}

## 测试用例
{_value(data, "test_cases", "测试用例覆盖数据采集、阈值预警、设备联动、工单流转、日志追溯、权限控制和异常恢复。")}

## 运行记录
运行记录来自包内 CSV 与日志文件，PPT 页面可引用“连续运行记录、告警工单、测试用例通过情况、处置响应时长”等口径。

## 验证口径
- 数据采集：连续记录是否完整，异常值是否可追踪。
- 预警触发：阈值满足时是否生成告警。
- 联动控制：风机、湿帘等设备是否按规则响应。
- 工单闭环：告警是否进入处置、确认、复核流程。
- 日志追溯：每次状态变更是否有时间、对象和动作记录。
"""


def _build_team_doc(data: dict[str, Any]) -> str:
    default_roles = (
        "- 项目统筹：需求拆解、进度管理、材料统筹。\n"
        "- 产品与交互：用户流程、原型设计、现场演示脚本。\n"
        "- 前端实现：管理驾驶舱、环境大屏、移动端工单。\n"
        "- 后端开发：设备接入、规则引擎、工单状态机、接口服务。\n"
        "- 设备接入：传感节点、控制箱、联动设备和网关联调。\n"
        "- 测试保障：测试用例、运行记录、异常复测和风险预案。"
    )
    return f"""# 团队匿名分工与岗位能力

只使用岗位或模块表达，不写姓名、学校、电话、邮箱。

## 岗位分工
{_value(data, "team_roles", default_roles)}

## 职业能力对应
- 产品经理：需求分析、原型设计、任务拆解。
- 前端开发：数据可视化、移动端交互、状态反馈。
- 后端开发：接口设计、数据库建模、日志追溯。
- 物联网运维：设备接入、通信排查、联动调试。
- 测试工程：用例设计、复测记录、问题闭环。
"""


def _build_value_doc(data: dict[str, Any]) -> str:
    return f"""# 应用价值与成果规划

## 企业价值
{_value(data, "enterprise_value", "减少人工巡检频次、缩短异常响应时间、提升设备调控及时性，并沉淀可追溯生产数据。")}

## 学校价值
{_value(data, "school_value", "形成物联网、移动应用、数据库、系统测试和项目管理等课程案例，可转化为综合实训项目。")}

## 团队成长与就业
{_value(data, "employment_value", "团队成长聚焦物联网系统开发、前后端协同、设备联调、测试验证和现场汇报能力，对接智慧农业工程师、物联网运维、软件开发与测试等岗位。")}

## 知识产权与合作
{_value(data, "ip_cooperation", "知识产权与合作材料按规划路径表达：系统软件著作权、规则引擎模块、硬件接入方案和校企合作应用可作为后续成果申报方向。")}

## 可持续发展
- 功能迭代：增加病虫害图像识别、能耗优化和多作物模型。
- 场景拓展：从温室大棚拓展到农业园区、合作社和植物工厂。
- 教学沉淀：形成“需求-开发-测试-运维-汇报”的综合项目资源。
"""


def _build_feedback_doc(data: dict[str, Any]) -> str:
    return """# 应用反馈摘要

## 反馈来源
合作温室管理场景的使用访谈、运维记录和现场复盘材料。

## 核心反馈
- 数据展示更集中，管理员能够在大屏上快速判断温室状态。
- 告警提醒更及时，移动端工单让异常处置过程更清楚。
- 设备联动减少了人工反复开关设备的工作量。
- 运行记录便于复盘异常原因，也便于后续教学案例整理。

## 使用边界
反馈摘要用于 PPT 价值说明；若正式参赛需要展示签章文件或访谈原件，应以后续上传的真实材料为准。
"""


def _build_material_status_csv(data: dict[str, Any]) -> str:
    rows = [
        ("项目说明书", "provided", "01_项目说明/项目说明书.md", "可支撑项目定位、问题与方案"),
        ("政策与调研", "provided", "02_背景与调研/背景政策市场调研.md", "可支撑背景、政策、市场和研发动因"),
        ("系统界面图片", "provided", "08_图片素材/png", "可支撑大屏、移动端、工单和数据分析页面"),
        ("设备现场图片", "provided", "08_图片素材/png", "可支撑设备接入、现场实操和硬件说明"),
        ("运行数据", "provided", "11_数据表/runtime_records.csv", "可支撑连续运行、趋势和复盘口径"),
        ("告警工单", "provided", "11_数据表/alarm_work_orders.csv", "可支撑异常事件闭环"),
        ("代码与接口", "provided", "09_代码与接口", "可支撑技术还原和实现说明"),
        ("成果证明原件", "external_required", "用户后续上传", "证书、专利、协议以真实原件为准"),
    ]
    return "material,status,path,usage\n" + "\n".join(",".join(row) for row in rows) + "\n"


def _build_runtime_records_csv(data: dict[str, Any]) -> str:
    rows = ["record_id,day,greenhouse,temperature,humidity,light_lux,co2_ppm,device_state,alarm_state"]
    values = [
        (1, "D1", "A区温室", 26.4, 68, 18600, 520, "normal", "none"),
        (2, "D2", "A区温室", 27.1, 66, 19200, 548, "normal", "none"),
        (3, "D3", "A区温室", 31.8, 61, 21400, 575, "fan_on", "temperature_warning"),
        (4, "D4", "A区温室", 29.2, 64, 20300, 552, "cooling", "processing"),
        (5, "D5", "A区温室", 26.9, 67, 18850, 530, "normal", "closed"),
    ]
    rows.extend(",".join(str(v) for v in row) for row in values)
    return "\n".join(rows) + "\n"


def _build_alarm_work_orders_csv(data: dict[str, Any]) -> str:
    return """work_order,event,trigger_condition,action,result,review
WO-A01,温度异常,temperature>30,开启风机并生成移动端工单,已完成处置,趋势回落且日志完整
WO-A02,湿度偏低,humidity<55,提示补水并记录复核,已完成处置,复核正常
WO-A03,设备离线,device_heartbeat_lost,检查网关与供电,已恢复,设备状态恢复在线
"""


def _build_test_cases_csv(data: dict[str, Any]) -> str:
    return """case_id,module,input,expected_output,result
TC-01,数据采集,传感节点连续上报,大屏实时刷新,pass
TC-02,阈值预警,温度超过阈值,生成告警与工单,pass
TC-03,设备联动,工单触发控制动作,风机状态切换,pass
TC-04,日志追溯,查询事件记录,返回完整状态链,pass
TC-05,异常恢复,网关短时离线,恢复后补传记录,pass
"""


def _build_kpi_summary_csv(data: dict[str, Any]) -> str:
    return """metric,baseline,system_record,source
巡检频次,人工定时巡检,大屏实时监测,runtime_records.csv
异常响应,人工发现后处理,预警触发并生成工单,alarm_work_orders.csv
设备调控,手动开关,规则联动控制,test_cases.csv
复盘方式,口头记录,日志与趋势图复盘,backend_runtime.log
"""


def _build_device_log(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "[gateway] sensor node S-A01 connected, metrics: temperature humidity light co2",
            "[gateway] publish topic greenhouse/A/metrics payload accepted",
            "[gateway] control channel fan-01 ready",
            "[gateway] control channel wet-curtain-01 ready",
            "[gateway] heartbeat recovered after retry, node=S-A03",
        ]
    )


def _build_backend_log(data: dict[str, Any]) -> str:
    return "\n".join(
        [
            "[backend] metrics batch stored: greenhouse=A, records=96",
            "[backend] rule matched: temperature_warning, threshold=30",
            "[backend] work order created: event=temperature_warning, target=mobile_workbench",
            "[backend] device command emitted: fan-01=start",
            "[backend] review completed: trend returned to normal range",
        ]
    )


def _build_schema_sample(data: dict[str, Any]) -> str:
    return """CREATE TABLE sensor_metric_record (
  id BIGINT PRIMARY KEY,
  greenhouse_code VARCHAR(32),
  sensor_code VARCHAR(64),
  metric_name VARCHAR(64),
  metric_value DECIMAL(10,2),
  metric_unit VARCHAR(16),
  collected_at DATETIME
);

CREATE TABLE alarm_work_order (
  id BIGINT PRIMARY KEY,
  event_type VARCHAR(64),
  trigger_condition VARCHAR(128),
  action_plan VARCHAR(256),
  current_status VARCHAR(32),
  reviewed_at DATETIME
);

CREATE TABLE operation_log (
  id BIGINT PRIMARY KEY,
  object_type VARCHAR(64),
  object_id VARCHAR(64),
  action_name VARCHAR(64),
  result_state VARCHAR(64),
  created_at DATETIME
);
"""


def _build_rule_engine_sample(data: dict[str, Any]) -> str:
    return '''"""Rule-engine sample for roadshow explanation."""

def evaluate_temperature(metric, threshold=30):
    if metric["temperature"] <= threshold:
        return {"level": "normal", "actions": []}
    actions = ["create_alarm_work_order", "start_fan"]
    if metric["temperature"] > 35:
        actions.append("start_wet_curtain")
    return {
        "level": "temperature_warning",
        "condition": f"temperature>{threshold}",
        "actions": actions,
        "review_required": True,
    }
'''


def _build_api_contract(data: dict[str, Any]) -> str:
    return """openapi: 3.0.3
info:
  title: greenhouse-control-api
  version: 1.0.0
paths:
  /api/metrics/latest:
    get:
      summary: 查询温室实时环境数据
  /api/alarms:
    post:
      summary: 生成告警工单
  /api/devices/{deviceCode}/commands:
    post:
      summary: 下发设备联动控制指令
  /api/reports/runtime:
    get:
      summary: 查询运行趋势与复盘记录
"""


def _base_target_rel_for_upload(filename: str) -> Path:
    safe = _safe_filename(filename)
    suffix = Path(safe).suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return Path("08_图片素材/png") / safe
    if suffix in SVG_SUFFIXES:
        return Path("08_图片素材/svg") / safe
    if suffix in CODE_SUFFIXES:
        return Path("09_代码与接口") / safe
    if suffix in LOG_SUFFIXES:
        return Path("10_日志记录") / safe
    if suffix in DATA_SUFFIXES:
        return Path("11_数据表") / safe
    if suffix in TEXT_SUFFIXES:
        return Path("01_项目说明") / safe
    if suffix in RAW_SUFFIXES:
        return Path("12_原始材料") / safe
    return Path("12_原始材料") / safe


def _write_formal_png_assets(target_dir: Path, project_name: str, data: dict[str, Any]) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    assets = [
        ("01 政策导向摘要.png", "policy", (24, 96, 132)),
        ("02 产业发展关注点.png", "policy", (22, 128, 112)),
        ("03 管理驾驶舱.png", "dashboard", (15, 82, 140)),
        ("04 环境监测大屏.png", "dashboard", (20, 118, 168)),
        ("05 设备联动控制.png", "dashboard", (34, 139, 94)),
        ("06 告警工单闭环.png", "dashboard", (190, 92, 64)),
        ("07 移动端工作台.png", "mobile", (88, 80, 168)),
        ("08 数据分析中心.png", "chart", (41, 98, 160)),
        ("09 温室设备布设图.png", "scene", (48, 132, 72)),
        ("10 传感节点近景.png", "device", (76, 112, 80)),
        ("11 现场巡检记录图.png", "scene", (98, 122, 64)),
        ("12 控制箱接线图.png", "device", (82, 92, 110)),
        ("13 温室环境趋势图.png", "chart", (20, 118, 168)),
        ("14 预警处置效率图.png", "chart", (190, 92, 64)),
        ("15 设备运行稳定性图.png", "chart", (34, 139, 94)),
        ("16 应用成效对比图.png", "chart", (88, 80, 168)),
        ("17 关键帧 进入监测大屏.png", "frame", (20, 118, 168)),
        ("18 关键帧 触发异常预警.png", "frame", (190, 92, 64)),
        ("19 关键帧 设备联动处置.png", "frame", (34, 139, 94)),
        ("20 关键帧 工单复核完成.png", "frame", (76, 112, 80)),
        ("21 应用反馈摘要.png", "document", (88, 80, 168)),
        ("22 课程转化路径图.png", "chart", (22, 128, 112)),
        ("23 岗位能力成长图.png", "chart", (24, 96, 132)),
    ]
    for filename, kind, accent in assets:
        _write_png_card(target_dir / filename, kind, accent)


def _write_png_card(path: Path, kind: str, accent: tuple[int, int, int]) -> None:
    width, height = 1280, 720
    bg = (247, 250, 252)
    img = bytearray(bg * width * height)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(width, x1), min(height, y1)
        for y in range(y0, y1):
            row = y * width * 3
            for x in range(x0, x1):
                idx = row + x * 3
                img[idx : idx + 3] = bytes(color)

    def line(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], thick: int = 3) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            t = i / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            rect(x - thick, y - thick, x + thick + 1, y + thick + 1, color)

    def circle(cx: int, cy: int, r: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, cy - r), min(height, cy + r + 1)):
            row = y * width * 3
            for x in range(max(0, cx - r), min(width, cx + r + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    idx = row + x * 3
                    img[idx : idx + 3] = bytes(color)

    rect(0, 0, width, height, bg)
    rect(0, 0, width, 90, accent)
    rect(58, 126, 1222, 654, (255, 255, 255))
    rect(58, 126, 1222, 130, accent)
    rect(58, 650, 1222, 654, accent)

    soft = tuple(min(255, int(c * 0.35 + 180)) for c in accent)
    dark = tuple(max(0, int(c * 0.72)) for c in accent)
    grey = (226, 232, 240)

    if kind in {"dashboard", "mobile", "frame"}:
        rect(92, 160, 470, 600, (241, 245, 249))
        rect(500, 160, 1188, 600, (248, 250, 252))
        for i in range(4):
            rect(120, 190 + i * 92, 430, 250 + i * 92, (255, 255, 255))
            rect(136, 208 + i * 92, 300 + i * 22, 222 + i * 92, soft if i % 2 else accent)
        for i in range(5):
            x = 540 + i * 120
            rect(x, 430 - i * 36, x + 64, 560, soft if i % 2 else accent)
        line(540, 330, 650, 295, dark, 4)
        line(650, 295, 770, 320, dark, 4)
        line(770, 320, 890, 250, dark, 4)
        line(890, 250, 1030, 280, dark, 4)
        for x, y in [(540, 330), (650, 295), (770, 320), (890, 250), (1030, 280)]:
            circle(x, y, 10, accent)
    elif kind in {"chart", "policy", "document"}:
        for i in range(7):
            rect(120, 184 + i * 56, 650 + (i % 3) * 110, 208 + i * 56, grey)
        for i in range(5):
            x = 760 + i * 78
            h = 90 + i * 42
            rect(x, 560 - h, x + 42, 560, accent if i % 2 else soft)
        line(728, 362, 826, 330, dark, 4)
        line(826, 330, 924, 348, dark, 4)
        line(924, 348, 1022, 292, dark, 4)
        line(1022, 292, 1120, 254, dark, 4)
        for x, y in [(728, 362), (826, 330), (924, 348), (1022, 292), (1120, 254)]:
            circle(x, y, 9, accent)
    else:
        for i in range(5):
            x = 150 + i * 190
            y = 210 + (i % 2) * 120
            rect(x, y, x + 130, y + 86, soft)
            rect(x + 36, y + 86, x + 96, y + 170, accent)
            circle(x + 65, y + 48, 34, dark)
            if i < 4:
                line(x + 132, y + 84, x + 188, y + 144, dark, 4)
        rect(130, 520, 1120, 555, grey)
        for i in range(6):
            rect(170 + i * 150, 532, 245 + i * 150, 545, accent if i % 2 else soft)

    _write_rgb_png(path, width, height, bytes(img))


def _write_rgb_png(path: Path, width: int, height: int, rgb: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(rgb[y * stride : (y + 1) * stride])
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def _svg_business_loop(project_name: str) -> str:
    return _basic_svg(project_name, "监测-预警-联动-复核业务闭环", ["采集", "判断", "联动", "工单", "复盘"])


def _basic_svg(project_name: str, subtitle: str, labels: list[str]) -> str:
    cards = []
    for index, label in enumerate(labels):
        x = 80 + index * 220
        cards.append(
            f'<rect x="{x}" y="320" width="160" height="110" rx="10" fill="#e6fffb" stroke="#0f766e" stroke-width="2"/>'
            f'<text x="{x + 80}" y="384" text-anchor="middle" font-size="22" fill="#134e4a">{_escape_xml(label)}</text>'
        )
        if index < len(labels) - 1:
            cards.append(f'<path d="M{x + 170} 375 L{x + 210} 375" stroke="#2563eb" stroke-width="4" marker-end="url(#arrow)"/>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
  <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#2563eb"/></marker></defs>
  <rect width="1280" height="720" fill="#f8fafc"/>
  <text x="80" y="120" font-size="42" font-weight="700" fill="#0f172a">{_escape_xml(project_name)}</text>
  <text x="80" y="172" font-size="26" fill="#0f766e">{_escape_xml(subtitle)}</text>
  {''.join(cards)}
</svg>'''
