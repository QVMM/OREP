#!/usr/bin/env python3
"""
Test V6 + Fireworks integration: generate pages with Fireworks-powered diagrams.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.services.ppt.v6.pipeline import build_v6_pipeline, render_v6_html_pages

# Realistic outline JSON for testing (simulates what OutlineGenerator produces)
TEST_OUTLINE = {
    "project": {"name": "智慧农业物联网大数据平台"},
    "project_name": "智慧农业物联网大数据平台",
    "pages": [
        {
            "page_index": 1,
            "title": "项目背景与行业痛点",
            "page_series_type": "background_data",
            "core_argument": "传统农业面临劳动力短缺和管理粗放的双重挑战",
            "page_goal": "用数据建立紧迫感",
            "ppt_text": "农业劳动力老龄化 传感器覆盖率不足 管理决策依赖经验 缺乏数据支撑",
            "key_points": [
                {"label": "农业劳动力老龄化", "value": "65岁以上占比28%", "description": "每年以1.5%速度上升"},
                {"label": "传感器覆盖率", "value": "不足15%", "description": "远低于工业物联网45%"},
                {"label": "管理效率损失", "value": "约35%", "description": "因信息不对称导致"},
            ],
        },
        {
            "page_index": 2,
            "title": "政策与市场机遇",
            "page_series_type": "background_data",
            "core_argument": "国家政策大力推动智慧农业发展",
            "page_goal": "说明政策利好",
            "ppt_text": "数字乡村战略 农业农村现代化 农业补贴政策 智慧农业市场规模",
            "key_points": [
                {"label": "市场规模", "value": "680亿", "description": "据中国信通院2025预测"},
                {"label": "年增长率", "value": "35%", "description": "远高于GDP增速"},
                {"label": "政策支持力度", "value": "中央一号文件", "description": "连续5年聚焦农业数字化"},
            ],
        },
        {
            "page_index": 3,
            "title": "核心痛点分析",
            "page_series_type": "pain_points",
            "core_argument": "传统农业存在四大核心痛点",
            "page_goal": "直击要害",
            "ppt_text": "数据采集难 决策滞后 响应慢 成本高",
            "key_points": [
                {"title": "数据采集依赖人工", "description": "巡检效率低，数据不连续"},
                {"title": "决策滞后", "description": "发现问题时已错过最佳处理窗口"},
                {"title": "响应速度慢", "description": "从发现到处置平均需要8小时"},
            ],
        },
        {
            "page_index": 4,
            "title": "系统总体架构",
            "page_series_type": "architecture_system",
            "core_argument": "采用端-边-云三层架构，实现数据全链路闭环",
            "page_goal": "展示技术架构完整性",
            "ppt_text": "物联网设备层 边缘计算层 平台服务层 应用决策层 端边云 架构 技术栈 模块 数据库",
        },
        {
            "page_index": 5,
            "title": "数据采集与边缘预处理",
            "page_series_type": "skill_steps",
            "core_argument": "标准化数据采集流程",
            "page_goal": "展示实操技能",
            "ppt_text": "设备部署 传感器校准 数据采集 边缘预处理 流程 步骤 输入 输出 闭环 链路",
            "steps_detail": [
                {"action": "设备部署与校准", "key_point": "精度±0.5%", "result": "传感器就绪", "tool": "IoT网关"},
                {"action": "多源数据采集", "key_point": "10秒/次", "result": "数据入库", "tool": "MQTT协议"},
                {"action": "边缘预处理", "key_point": "异常过滤率95%", "result": "有效数据", "tool": "边缘计算盒"},
            ],
        },
        {
            "page_index": 6,
            "title": "AI智能分析引擎",
            "page_series_type": "skill_steps",
            "core_argument": "AI算法实现精准诊断和预测",
            "page_goal": "展示AI技术深度",
            "ppt_text": "深度学习 图像识别 预测模型 智能诊断 流程 步骤 输入 输出 闭环",
            "steps_detail": [
                {"action": "数据预处理", "key_point": "特征提取", "result": "标准化向量", "tool": "Python/PyTorch"},
                {"action": "模型推理", "key_point": "准确率95.6%", "result": "诊断报告", "tool": "YOLOv8+LSTM"},
                {"action": "结果输出", "key_point": "延迟<3秒", "result": "告警推送", "tool": "Redis+WebSocket"},
            ],
        },
        {
            "page_index": 7,
            "title": "智能灌溉决策流程",
            "page_series_type": "skill_steps",
            "core_argument": "从数据采集到精准灌溉的完整闭环",
            "page_goal": "展示决策链路",
            "ppt_text": "土壤湿度 气象数据 AI决策 灌溉执行 流程 步骤 链路 闭环",
            "steps_detail": [
                {"action": "土壤湿度监测", "key_point": "精度±2%", "result": "实时数据", "tool": "土壤传感器"},
                {"action": "AI灌溉决策", "key_point": "节水率40%", "result": "灌溉方案", "tool": "决策引擎"},
                {"action": "自动执行", "key_point": "延迟<5分钟", "result": "精准灌溉", "tool": "电磁阀控制器"},
            ],
        },
        {
            "page_index": 8,
            "title": "平台服务架构详解",
            "page_series_type": "architecture_system",
            "core_argument": "微服务架构支撑高并发场景",
            "page_goal": "展示平台技术选型",
            "ppt_text": "微服务 Docker K8s API网关 架构 技术栈 模块 数据库",
        },
        {
            "page_index": 9,
            "title": "数据底座设计",
            "page_series_type": "text_content",
            "core_argument": "多源异构数据统一管理",
            "page_goal": "展示数据层设计",
            "ppt_text": "MySQL时序 MongoDB Redis ES 数据湖 数据底座",
            "key_points": [
                "采用MySQL存储结构化业务数据，支持复杂查询和事务",
                "MongoDB存储半结构化日志和传感器原始数据",
                "Redis作为实时缓存层，热点数据响应<10ms",
                "Elasticsearch支撑全文检索和日志分析",
            ],
        },
        {
            "page_index": 10,
            "title": "功能对比：传统方式 vs 智能系统",
            "page_series_type": "data_compare",
            "core_argument": "全方位提升显著",
            "page_goal": "用对比证明价值",
            "ppt_text": "对比 改良前 改良后 创新",
            "comparison_mode": "before_after",
            "key_points": [
                {"dimension": "巡检效率", "before": "人工2小时/次", "after": "自动实时监测", "improvement": "效率提升60倍"},
                {"dimension": "响应时间", "before": "平均8小时", "after": "3分钟内", "improvement": "提速160倍"},
                {"dimension": "用水量", "before": "经验估算", "after": "AI精准灌溉", "improvement": "节水40%"},
            ],
        },
        {
            "page_index": 11,
            "title": "系统运行效果指标",
            "page_series_type": "achievement",
            "core_argument": "系统运行数据证明方案有效性",
            "page_goal": "用数据说话",
            "ppt_text": "指标 收益 成果 数据验证",
            "key_points": [
                {"label": "设备在线率", "value": "99.2%", "description": "连续运行6个月"},
                {"label": "AI诊断准确率", "value": "95.6%", "description": "覆盖12种常见病害"},
                {"label": "平均响应时间", "value": "2.8秒", "description": "满足实时需求"},
                {"label": "产量提升", "value": "18%", "description": "试点区域对比数据"},
            ],
        },
        {
            "page_index": 12,
            "title": "实操验证：设备联调",
            "page_series_type": "practice_evidence",
            "core_argument": "真实现场设备联调记录",
            "page_goal": "证明方案可落地",
            "ppt_text": "实操 现场 截图 验证 演示",
        },
        {
            "page_index": 13,
            "title": "系统界面与数据看板",
            "page_series_type": "practice_evidence",
            "core_argument": "系统实际运行界面展示",
            "page_goal": "证明系统可运行",
            "ppt_text": "系统 平台 界面 看板 数据",
        },
        {
            "page_index": 14,
            "title": "团队分工与职责",
            "page_series_type": "team_intro",
            "core_argument": "团队成员分工明确",
            "page_goal": "展示团队能力",
            "ppt_text": "团队成员角色与分工",
            "key_points": ["张明：项目负责人，统筹全局", "李华：IoT工程师，负责设备接入", "王芳：算法工程师，负责AI模型", "赵强：前端开发，负责数据看板"],
        },
        {
            "page_index": 15,
            "title": "总结与展望",
            "page_series_type": "text_content",
            "core_argument": "项目已验证可行性，未来可复制推广",
            "page_goal": "收束全篇",
            "ppt_text": "总结 成果 未来规划 推广",
            "key_points": [
                "端-边-云三层架构已验证，设备在线率99.2%",
                "AI诊断准确率95.6%，响应时间<3秒",
                "节水40%，产量提升18%，经济效果显著",
                "可复制推广至其他农业场景和区域",
            ],
        },
    ],
}


def main():
    print("=" * 60)
    print("V6 + Fireworks Integration Test")
    print("=" * 60)

    pages = TEST_OUTLINE["pages"]
    print(f"\nOutline: {len(pages)} pages")

    # Run V6 pipeline
    print("\nBuilding V6 pipeline...")
    pipeline = build_v6_pipeline(TEST_OUTLINE)
    print(f"  expression_plans: {len(pipeline.get('expression_plans', []))}")
    print(f"  blueprints: {len(pipeline.get('page_blueprints', []))}")
    print(f"  layouts: {len(pipeline.get('layout_plans', []))}")
    print(f"  diagram_schemas: {len(pipeline.get('diagram_schemas', []))}")

    # Check rendered SVGs for fireworks source
    svgs = pipeline.get("rendered_svgs", [])
    fireworks_count = sum(1 for s in svgs if (s.get("audit") or {}).get("source") == "fireworks")
    local_count = len(svgs) - fireworks_count
    print(f"\n  SVGs rendered: {len(svgs)}")
    print(f"    Fireworks: {fireworks_count}")
    print(f"    Local: {local_count}")

    for svg in svgs:
        src = (svg.get("audit") or {}).get("source", "local")
        print(f"    Page {svg['page_index']:02d}: {svg['diagram_type']:25s} -> {src}")

    # Generate HTML pages
    print("\nRendering HTML pages...")
    html_pages = render_v6_html_pages(TEST_OUTLINE, pipeline_payload=pipeline)
    print(f"  HTML pages generated: {len(html_pages)}")

    # Save output
    out_dir = os.path.join(os.path.dirname(__file__), "output", "v6_fireworks_test")
    os.makedirs(out_dir, exist_ok=True)

    for i, html in enumerate(html_pages):
        # Extract page index from expression plans
        plan = pipeline["expression_plans"][i] if i < len(pipeline["expression_plans"]) else {}
        page_idx = plan.get("page_index", i + 1)
        fpath = os.path.join(out_dir, f"page_{page_idx:02d}.html")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"\n  HTML files saved to: {out_dir}/")

    # Save pipeline report
    report = {
        "total_pages": len(html_pages),
        "fireworks_count": fireworks_count,
        "local_count": local_count,
        "svg_details": [
            {
                "page_index": s["page_index"],
                "diagram_type": s["diagram_type"],
                "source": (s.get("audit") or {}).get("source", "local"),
            }
            for s in svgs
        ],
    }
    report_path = os.path.join(out_dir, "integration_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Report saved to: {report_path}")

    print("\n✅ Integration test complete!")


if __name__ == "__main__":
    main()
