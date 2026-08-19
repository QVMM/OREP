#!/usr/bin/env python3
"""
执行完整的 Round 1 → Round 2 → Round 3 → Round 4 Pipeline
测试用：智慧农业物联网大数据平台
"""
import asyncio
import json
import os
import sys
import time
import logging

# 设置调试日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("pipeline_test")

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')

from app.services.ppt.adapter_code.pipeline_coordinator import PipelineCoordinator
from dotenv import load_dotenv

load_dotenv()


def progress_callback(task_id: int, progress: int, step: str):
    """进度回调"""
    print(f"[Task {task_id}] 进度 {progress}%: {step}")


async def run_full_pipeline():
    """运行完整Pipeline"""
    print("=" * 70)
    print("智慧农业物联网大数据平台 - 完整Pipeline测试")
    print("=" * 70)

    # 读取问卷数据
    questionnaire_file = "/Users/liuyixing/项目/OREP/ai-scoring/output/test_questionnaire_智慧农业.json"
    with open(questionnaire_file, "r", encoding="utf-8") as f:
        questionnaire_data = json.load(f)

    print(f"\n问卷数据已加载: {questionnaire_data['project_name']}")
    print(f"团队: {questionnaire_data['team_name']}")
    print(f"学校: {questionnaire_data['school_name']}")

    # 执行Pipeline
    start_time = time.time()

    coordinator = PipelineCoordinator(timeout=900)

    try:
        print("\n开始执行 Pipeline...")
        result = await coordinator.execute(
            task_id=9999,
            questionnaire_data=questionnaire_data,
            progress_callback=progress_callback
        )

        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("Pipeline 执行完成！")
        print(f"耗时: {elapsed:.1f} 秒")
        print("=" * 70)

        # 保存结果
        output_dir = "/Users/liuyixing/项目/OREP/ai-scoring/output"
        os.makedirs(output_dir, exist_ok=True)

        # 保存完整结果
        result_file = os.path.join(output_dir, "pipeline_result_full.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n✅ 完整结果已保存: {result_file}")

        # 显示结果摘要
        if "rounds" in result:
            rounds = result["rounds"]
            print("\n--- 各轮次结果摘要 ---")

            if "round1" in rounds:
                r1 = rounds["round1"]
                print(f"\n📋 Round 1 (问卷结构化):")
                if "structured_data" in r1:
                    sd = r1["structured_data"]
                    print(f"   项目名称: {sd.get('project', {}).get('name', 'N/A')}")
                    print(f"   阶段数: {len(sd.get('phases', []))}")

            if "round2" in rounds:
                r2 = rounds["round2"]
                print(f"\n📑 Round 2 (生成大纲):")
                if "narrative_framework" in r2:
                    nf = r2["narrative_framework"]
                    print(f"   标题: {nf.get('meta', {}).get('title', 'N/A')}")
                    print(f"   页数: {len(nf.get('pages', []))}")

            if "round3" in rounds:
                r3 = rounds["round3"]
                print(f"\n📝 Round 3 (生成详细内容):")
                if "enriched_pages" in r3:
                    print(f"   页面数量: {len(r3['enriched_pages'])}")

            if "round4" in rounds:
                r4 = rounds["round4"]
                print(f"\n🎨 Round 4 (生成HTML):")
                if "html_files" in r4:
                    print(f"   HTML文件数量: {len(r4['html_files'])}")

        return result

    except Exception as e:
        print(f"\n❌ Pipeline 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    result = asyncio.run(run_full_pipeline())
    if result:
        print("\n✅ 测试完成!")
    else:
        print("\n❌ 测试失败!")
        sys.exit(1)


if __name__ == "__main__":
    main()
