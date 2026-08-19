#!/usr/bin/env python3
"""
测试新 Pipeline 流程：问卷 → Round 1/2/3/4 → HTML
"""
import asyncio
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')

# 模拟问卷数据 - 简化版用于测试
SAMPLE_QUESTIONNAIRE = {
    "project_name": "智慧农业物联网大数据平台",
    "team_name": "田野智联团队",
    "school_name": "华东职业技术学院",
    "industry": "agriculture",
    "team_members": "4人团队，包含1名前端开发、1名后端开发、1名算法工程师、1名项目经理",

    # 项目背景和意义（6分）
    "strategic_alignment": "对接《十四五数字乡村发展战略》，响应国家乡村振兴战略。",
    "industry_trend": "智慧农业市场规模持续增长，2024年达到约6000亿元。",
    "social_need": "农村劳动力短缺问题日益严重，传统农业生产效率低下。",
    "project_significance": "通过物联网传感器采集环境数据，运用AI算法优化种植方案。",

    # 调研分析（8分）
    "target_users": "规模化农业生产者、农业合作社、家庭农场主。",
    "market_research": "目标市场规模约3000亿元。",
    "competitor_analysis": "主要竞争对手包括托普农业云、极飞科技等。",
    "user_pain_points": "痛点1：设备维护困难；痛点2：数据分析复杂。",
    "research_method": "问卷调查、用户访谈、实地考察。",

    # 方案设计（10分）
    "solution_overview": "项目名称为智农云，核心功能包括环境监测、智能灌溉、产量预测。",
    "data_collection_method": "采集来源：土壤传感器、气象站。",
    "data_cleaning_process": "去重处理、异常值处理、缺失值填充、数据标准化。",
    "data_analysis_method": "分析模型：LSTM神经网络预测产量。",
    "data_visualization": "可视化工具：ECharts。",
    "workflow_design": "用户操作流程：注册登录 → 添加农场 → 查看数据。",

    # 功能实现（10分）
    "core_functions": "功能1：实时环境监测；功能2：智能灌溉控制；功能3：产量预测模型。",
    "tech_stack": "Python、Vue3、FastAPI、TensorFlow。",
    "database_design": "MySQL + InfluxDB时序库。",
    "api_design": "RESTful API。",
    "code_standards": "PEP8、Google Style。",

    # 功能展示（6分）
    "demo_description": "演示环境：阿里云服务器；演示时长：约5分钟。",
    "demo_screenshots": "首页、数据大屏、设备管理。",
    "demo_workflow": "注册登录 → 添加农场 → 查看数据。",

    # 创新性（8分）
    "tech_innovation": "创新点1：轻量化LSTM模型；创新点2：联邦学习应用于农业数据。",
    "innovation_value": "技术价值：推动农业数字化转型。",
    "patent_status": "已申请发明专利2项。",

    # 团队协作（6分）
    "team_structure": "团队规模4人；角色分配：项目经理、前端、后端、算法工程师各1人。",
    "member_roles": "成员A（前端）：小程序开发；成员B（后端）：API开发；成员C（算法）：LSTM模型。",
    "collaboration_process": "使用Teambition管理任务，每日站会。",

    # 技术技能（10分）
    "skill_requirements": "Python、Vue3、FastAPI、MySQL、TensorFlow。",
    "skill_achievements": "LSTM产量预测模型准确率达92%。",
    "technical_challenges": "挑战1：边缘设备算力有限；挑战2：传感器数据噪声大。",

    # 应用价值（6分）
    "social_value": "服务了1000+农户，提升农业生产效率。",
    "economic_value": "预计市场规模500万元/年。",
    "user_feedback": "用户满意度达92%。",

    # 产业应用（6分）
    "application_scenarios": "大田作物种植、设施农业、果园管理。",
    "promotion_plan": "建立示范农场，带动周边农户。",
    "business_model": "SaaS年费订阅+硬件销售。",
}


async def run_pipeline():
    """执行新 Pipeline"""
    from app.services.ppt.adapter_code.pipeline_coordinator import PipelineCoordinator

    print("=" * 60)
    print("开始执行新 Pipeline (Round 1/2/3/4)")
    print("=" * 60)

    # 创建 Pipeline 协调器
    coordinator = PipelineCoordinator(timeout=600)

    # 进度回调
    def progress_callback(task_id: int, progress: int, step: str):
        print(f"[{progress:3d}%] {step}")

    # 执行 Pipeline
    print("\n正在执行 Round 1/2/3/4...\n")
    result = await coordinator.execute(
        task_id=999,  # 测试用 task_id
        questionnaire_data=SAMPLE_QUESTIONNAIRE,
        progress_callback=progress_callback
    )

    return result


def save_html_preview(result: dict, output_dir: str):
    """保存 HTML 预览"""
    os.makedirs(output_dir, exist_ok=True)

    html_pages = result.get("html_pages", [])
    print(f"\n保存 {len(html_pages)} 个 HTML 页面到 {output_dir}")

    for i, html in enumerate(html_pages):
        page_file = os.path.join(output_dir, f"page_{i+1}.html")
        with open(page_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  - {page_file}")

    # 保存 enriched_pages (中间结果)
    enriched_pages = result.get("enriched_pages", [])
    if enriched_pages:
        enriched_file = os.path.join(output_dir, "enriched_pages.json")
        with open(enriched_file, "w", encoding="utf-8") as f:
            json.dump(enriched_pages, f, ensure_ascii=False, indent=2)
        print(f"  - {enriched_file}")

    # 保存 outline_json
    outline_json = result.get("outline_json", {})
    if outline_json:
        outline_file = os.path.join(output_dir, "outline_json.json")
        with open(outline_file, "w", encoding="utf-8") as f:
            json.dump(outline_json, f, ensure_ascii=False, indent=2)
        print(f"  - {outline_file}")

    # 保存 meta 信息
    meta = result.get("meta", {})
    if meta:
        meta_file = os.path.join(output_dir, "meta.json")
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"  - {meta_file}")

    return output_dir


def main():
    print("=" * 60)
    print("新 Pipeline 测试 - 智慧农业物联网大数据平台")
    print("=" * 60)

    # 打印问卷摘要
    print("\n【问卷数据摘要】")
    print(f"  项目名称: {SAMPLE_QUESTIONNAIRE['project_name']}")
    print(f"  团队名称: {SAMPLE_QUESTIONNAIRE['team_name']}")
    print(f"  所属行业: {SAMPLE_QUESTIONNAIRE['industry']}")
    print(f"  字段数量: {len(SAMPLE_QUESTIONNAIRE)} 项")

    # 执行 Pipeline
    result = asyncio.run(run_pipeline())

    # 保存 HTML 预览
    output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output/new_pipeline_preview"
    save_html_preview(result, output_dir)

    print("\n" + "=" * 60)
    print("Pipeline 执行完成！")
    print("=" * 60)
    print(f"\nHTML 文件位置: {output_dir}/")
    print("\n可以打开 page_1.html 检查第一个页面是否符合预期")


if __name__ == "__main__":
    main()
