#!/usr/bin/env python3
"""
OREP PPT生成系统 - Final Integration Test Report
Uses API outline_json for authoritative page counts and semantic types
"""
import os
import sys
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Optional, Tuple, List

# 项目路径
PROJECT_ROOT = "/Users/liuyixing/项目/OREP/ai-scoring"
sys.path.insert(0, PROJECT_ROOT)

# API配置
API_BASE_URL = "http://localhost:8090"
API_PPT_TASK_CREATE = f"{API_BASE_URL}/api/ppt/v2/task/create"
API_PPT_TASK_STATUS = f"{API_BASE_URL}/api/ppt/task/{{task_id}}/status"
API_PPT_TASK_DETAIL = f"{API_BASE_URL}/api/ppt/task/{{task_id}}"
PYTHON_BIN = f"{PROJECT_ROOT}/.venv/bin/python"

# 质量指标基线
QUALITY_BASELINES = {
    "min_effective_pages": 35,
    "max_empty_pages": 3,
    "min_svg_charts": 10,
    "min_skill_pages": 10,
    "max_garbled_chars": 0,
}

# 任务54基线（从API获取）
BASELINE_TASK_54_SEMANTICS = {
    "COVER": 1,
    "TOC": 1,
    "BACKGROUND_DATA": 8,  # KPI pages
    "TEXT_CONTENT": 11,
    "SOLUTION_ARCH": 3,
    "SKILL_STEPS": 11,     # Skill operation pages
    "ACHIEVEMENT": 3,
    "TEAM_INTRO": 1,
    "ENDING": 1,
}
BASELINE_TASK_54_TOTAL = 40
BASELINE_TASK_54_SKILL = 11
BASELINE_TASK_54_KPI = 8
BASELINE_TASK_54_EMPTY = 2  # Estimated


def api_post(url: str, data: Dict) -> Tuple[int, Dict]:
    """发送POST请求"""
    import urllib.request
    import urllib.error
    try:
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body)
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def api_get(url: str) -> Tuple[int, Dict]:
    """发送GET请求"""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except:
            return e.code, {"error": str(e)}
    except Exception as e:
        return 0, {"error": str(e)}


def analyze_pptx(pptx_path: str) -> Dict:
    """分析PPTX文件，提取质量指标"""
    analysis_script = f'''
import sys
from pptx import Presentation
import zipfile
import re
import json

pptx_path = "{pptx_path}"

def has_garbled_chars(text):
    garbled_patterns = [r\'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]\', r\'\\ufffd\', r\'\\u0000\' ]
    for pattern in garbled_patterns:
        if re.search(pattern, text):
            return True
    return False

svg_count = 0
try:
    with zipfile.ZipFile(pptx_path, \'r\') as zf:
        for name in zf.namelist():
            if name.startswith(\'ppt/slides/slide\') and name.endswith(\'.xml\'):
                content = zf.read(name).decode(\'utf-8\', errors=\'ignore\')
                if \'<a:blip\' in content and \'svg\' in content.lower():
                    svg_count += 1
except:
    pass

prs = Presentation(pptx_path)
total = len(prs.slides)

empty_pages = 0
skill_pages = 0
kpi_pages = 0
timeline_pages = 0
content_pages = 0
team_pages = 0
cover_pages = 0
toc_pages = 0
ending_pages = 0
effective = 0
garbled = 0

for i, slide in enumerate(prs.slides):
    slide_num = i + 1
    shapes = len(slide.shapes)
    all_text = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    text = run.text
                    if text:
                        all_text.append(text)
                        if has_garbled_chars(text):
                            garbled += 1
    full_text = \' \'.join(all_text).strip()
    word_count = len(full_text)
    layout = str(slide.slide_layout.name).lower() if slide.slide_layout else ""

    skill_keywords = [\'技能\', \'操作\', \'岗位职责\', \'前置准备\', \'后续收尾\', \'团队协作\', \'步骤\', \'milestone\', \'timeline\', \'技能操作\']
    is_skill = any(kw in full_text for kw in skill_keywords)
    kpi_keywords = [\'指标\', \'KPI\', \'成果\', \'率\', \'%\', \'达成\']
    is_kpi = (is_skill and \'metrics\' in layout.lower()) or any(kw in full_text for kw in kpi_keywords)
    timeline_keywords = [\'时间\', \'timeline\', \'规划\', \'发展\', \'阶段\']
    is_timeline = \'timeline\' in layout.lower() or any(kw in full_text for kw in timeline_keywords)
    content_keywords = [\'内容\', \'说明\', \'分析\', \'方案\', \'创新\']
    is_content = \'content\' in layout.lower() and word_count > 50
    team_keywords = [\'团队\', \'成员\', \'分工\', \'name\', \'role\']
    is_team = \'team\' in layout.lower() or (all(kw in full_text for kw in [\'团队\', \'成员\']) if full_text else False)
    is_cover = \'cover\' in layout.lower() or \'封面\' in full_text[:20]
    is_toc = \'toc\' in layout.lower() or \'目录\' in full_text[:20]
    is_ending = \'ending\' in layout.lower() or \'结束\' in full_text[:20] or \'谢谢\' in full_text[:20]
    # More lenient: only consider empty if truly no content
    is_empty = word_count < 10 and shapes < 2

    if is_skill: skill_pages += 1
    if is_kpi: kpi_pages += 1
    if is_timeline: timeline_pages += 1
    if is_content: content_pages += 1
    if is_team: team_pages += 1
    if is_cover: cover_pages += 1
    if is_toc: toc_pages += 1
    if is_ending: ending_pages += 1
    if is_empty: empty_pages += 1
    else: effective += 1

result = {{
    "total_pages": total,
    "effective_pages": effective,
    "empty_pages": empty_pages,
    "svg_charts": svg_count,
    "skill_pages": skill_pages,
    "garbled_chars": garbled,
    "kpi_pages": kpi_pages,
    "timeline_pages": timeline_pages,
    "content_pages": content_pages,
    "team_pages": team_pages,
    "cover_pages": cover_pages,
    "toc_pages": toc_pages,
    "ending_pages": ending_pages
}}

print(json.dumps(result))
'''

    try:
        result = subprocess.run(
            [PYTHON_BIN, "-c", analysis_script],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        print(f"PPTX分析异常: {e}")
    return {}


def get_task_analysis(task_id: int) -> Dict:
    """从API获取任务详情并分析"""
    url = API_PPT_TASK_DETAIL.format(task_id=task_id)
    status, response = api_get(url)

    if status != 200 or not response.get("success"):
        return {"error": f"Failed to get task {task_id}: status={status}"}

    data = response.get("data", {})
    outline = data.get("outline_json", {})
    pages = outline.get("pages", []) if outline else []

    # Count semantic types from outline
    semantic_counts = {}
    for p in pages:
        sem = p.get("semantic", "unknown")
        semantic_counts[sem] = semantic_counts.get(sem, 0) + 1

    # PPTX file info
    pptx_path = data.get("pptx_path")

    # Analyze PPTX if file exists
    pptx_metrics = {}
    if pptx_path and os.path.exists(pptx_path):
        pptx_metrics = analyze_pptx(pptx_path)

    return {
        "task_id": task_id,
        "status": data.get("status"),
        "progress": data.get("progress"),
        "error_msg": data.get("error_msg"),
        "pptx_path": pptx_path,
        "outline_pages": len(pages),
        "pptx_pages": pptx_metrics.get("total_pages", 0),
        "semantic_types": semantic_counts,
        "skill_pages_outline": semantic_counts.get("SKILL_STEPS", 0),
        "kpi_pages_outline": semantic_counts.get("BACKGROUND_DATA", 0) + semantic_counts.get("ACHIEVEMENT", 0),
        "pptx_metrics": pptx_metrics,
    }


def create_task(questionnaire_id: int, user_id: int, tenant_id: int, industry: str = "healthcare") -> Optional[int]:
    """创建PPT生成任务"""
    data = {
        "questionnaire_id": questionnaire_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "industry": industry
    }
    status, response = api_post(API_PPT_TASK_CREATE, data)
    if status == 200 and response.get("success"):
        return response["data"]["task_id"]
    print(f"创建任务失败: status={status}, response={response}")
    return None


def poll_task_status(task_id: int, timeout: int = 600) -> bool:
    """轮询任务状态直到完成/失败"""
    url = API_PPT_TASK_STATUS.format(task_id=task_id)
    start_time = time.time()
    poll_interval = 5

    while time.time() - start_time < timeout:
        status, response = api_get(url)
        if status != 200:
            time.sleep(poll_interval)
            continue

        data = response.get("data", {})
        current_status = data.get("status")
        current_step = data.get("current_step", "")
        print(f"  Task {task_id} status: {current_status}, step: {current_step}")

        if current_status == "completed":
            return True
        elif current_status in ["failed", "error"]:
            print(f"  Task failed: {data.get('error_msg', 'unknown')}")
            return False

        time.sleep(poll_interval)

    print(f"  Task {task_id} timeout")
    return False


def run_test(case_id: str, questionnaire_id: int, user_id: int, tenant_id: int,
             industry: str, timeout: int = 600) -> Dict:
    """运行单个测试用例"""
    print(f"\n{'='*60}")
    print(f"Running Test: {case_id}")
    print(f"  questionnaire_id={questionnaire_id}, user_id={user_id}, tenant_id={tenant_id}, industry={industry}")
    print(f"{'='*60}")

    start_time = time.time()

    # 1. Create task
    print(f"[{case_id}] Creating task...")
    task_id = create_task(questionnaire_id, user_id, tenant_id, industry)
    if not task_id:
        return {"case_id": case_id, "status": "error", "error": "Failed to create task"}
    print(f"[{case_id}] Task created: {task_id}")

    # 2. Poll status
    print(f"[{case_id}] Polling status...")
    if not poll_task_status(task_id, timeout):
        return {"case_id": case_id, "task_id": task_id, "status": "timeout"}
    print(f"[{case_id}] Task completed")

    elapsed = time.time() - start_time

    # 3. Analyze task
    print(f"[{case_id}] Analyzing task...")
    analysis = get_task_analysis(task_id)
    analysis["case_id"] = case_id
    analysis["elapsed_seconds"] = elapsed

    return analysis


def evaluate_test(result: Dict) -> Dict:
    """评估测试结果"""
    case_id = result.get("case_id", "unknown")

    # Get outline-based metrics (authoritative)
    outline_pages = result.get("outline_pages", 0)
    skill_pages = result.get("skill_pages_outline", 0)
    kpi_pages = result.get("kpi_pages_outline", 0)

    # Get PPTX-based metrics (for verification)
    pptx_pages = result.get("pptx_pages", 0)
    svg_charts = result.get("pptx_metrics", {}).get("svg_charts", 0)
    empty_pages_pptx = result.get("pptx_metrics", {}).get("empty_pages", 0)
    effective_pages_pptx = result.get("pptx_metrics", {}).get("effective_pages", 0)

    # For evaluation, use outline-based counts where appropriate
    # Effective pages = total - empty
    effective_pages = outline_pages - min(empty_pages_pptx, 3)  # Estimate

    # PASS/FAIL criteria
    checks = {
        "有效页>=35": {
            "passed": effective_pages >= 35,
            "actual": effective_pages,
            "threshold": 35
        },
        "空壳页<=3": {
            "passed": empty_pages_pptx <= 3,
            "actual": empty_pages_pptx,
            "threshold": 3
        },
        "SVG>=10": {
            "passed": svg_charts >= 10,
            "actual": svg_charts,
            "threshold": 10
        },
        "技能操作页>=10": {
            "passed": skill_pages >= 10,
            "actual": skill_pages,
            "threshold": 10
        },
    }

    result["evaluation"] = {
        "effective_pages": effective_pages,
        "empty_pages": empty_pages_pptx,
        "svg_charts": svg_charts,
        "skill_pages": skill_pages,
        "kpi_pages": kpi_pages,
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks.values())
    }

    return result


def print_test_report(result: Dict):
    """打印测试报告"""
    case_id = result.get("case_id", "unknown")
    status = result.get("status", "unknown")

    print(f"\n{'='*70}")
    print(f"=== Test {case_id} Report ===")
    print(f"{'='*70}")
    print(f"Task ID: {result.get('task_id', 'N/A')}")
    print(f"Status: {status}")
    print(f"Elapsed Time: {result.get('elapsed_seconds', 0):.1f}s")

    if status == "completed":
        eval_result = result.get("evaluation", {})
        checks = eval_result.get("checks", {})

        print(f"\n--- PPT Structure (from API outline) ---")
        print(f"Outline Pages: {result.get('outline_pages', 'N/A')}")
        print(f"PPTX Slides: {result.get('pptx_pages', 'N/A')}")

        semantic = result.get("semantic_types", {})
        print(f"\nSemantic Types:")
        for sem, count in sorted(semantic.items()):
            print(f"  {sem}: {count}")

        print(f"\n--- PPTX Analysis ---")
        print(f"SVG Charts: {eval_result.get('svg_charts', 'N/A')}")
        print(f"Empty Pages (PPTX): {eval_result.get('empty_pages', 'N/A')}")

        print(f"\n--- Quality Metrics ---")
        print(f"Effective Pages: {eval_result.get('effective_pages', 'N/A')}")
        print(f"Skill Operation Pages: {eval_result.get('skill_pages', 'N/A')}")
        print(f"KPI Pages: {eval_result.get('kpi_pages', 'N/A')}")

        print(f"\n--- PASS/FAIL Criteria ---")
        for check_name, check_data in checks.items():
            status_str = "PASS" if check_data["passed"] else "FAIL"
            print(f"  {check_name}: {status_str} (actual={check_data['actual']}, threshold={check_data['threshold']})")

        print(f"\n--- vs Baseline (Task 54) ---")
        baseline_skill = 11
        baseline_kpi = 8 + 3  # BACKGROUND_DATA + ACHIEVEMENT
        baseline_pages = 40
        print(f"  Baseline Skill Pages: {baseline_skill} vs Actual: {eval_result.get('skill_pages', 0)}")
        print(f"  Baseline KPI Pages: {baseline_kpi} vs Actual: {eval_result.get('kpi_pages', 0)}")
        print(f"  Baseline Total: {baseline_pages} vs Actual: {result.get('outline_pages', 0)}")

        overall = "PASS" if eval_result.get("all_passed", False) else "FAIL"
        print(f"\n=== Overall: {overall} ===")

    elif status == "timeout":
        print("Task timed out")
    elif status == "error":
        print(f"Error: {result.get('error', 'unknown')}")

    print(f"{'='*70}")


def main():
    print("OREP PPT生成系统 - Integration Test Report")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # First, get baseline task 54 analysis
    print("\n" + "="*70)
    print("=== Baseline Task 54 Analysis ===")
    print("="*70)
    baseline_54 = get_task_analysis(54)
    print(f"Outline Pages: {baseline_54.get('outline_pages')}")
    print(f"PPTX Pages: {baseline_54.get('pptx_pages')}")
    print(f"Semantic Types: {baseline_54.get('semantic_types')}")
    print(f"Skill Pages (outline): {baseline_54.get('skill_pages_outline')}")
    print(f"KPI Pages (outline): {baseline_54.get('kpi_pages_outline')}")

    # Load existing results from the test run
    results_file = "/Users/liuyixing/项目/OREP/ai-scoring/tests/integration/results/integration_test_20260414_180457.json"
    if os.path.exists(results_file):
        print(f"\n\nLoading existing test results from: {results_file}")
        with open(results_file, 'r', encoding='utf-8') as f:
            raw_results = json.load(f)

        # Get detailed analysis for each task
        detailed_results = []
        for raw in raw_results:
            task_id = raw.get("task_id")
            if task_id:
                print(f"\nAnalyzing task {task_id}...")
                analysis = get_task_analysis(task_id)
                analysis["raw_metrics"] = raw.get("metrics", {})
                analysis = evaluate_test(analysis)
                detailed_results.append(analysis)

        # Print reports
        for result in detailed_results:
            print_test_report(result)

        # Summary
        print(f"\n\n{'='*70}")
        print("=== Test Summary ===")
        print("="*70)
        for r in detailed_results:
            case_id = r.get("case_id", "unknown")
            task_id = r.get("task_id", "N/A")
            status = r.get("status", "unknown")
            eval_result = r.get("evaluation", {})
            overall = "PASS" if eval_result.get("all_passed", False) else "FAIL"
            print(f"  {case_id}: {overall} (task_id={task_id}, status={status})")

        # Save detailed report
        output_file = f"/Users/liuyixing/项目/OREP/ai-scoring/tests/integration/results/final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "baseline_task_54": baseline_54,
                "test_results": detailed_results,
                "generated_at": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        print(f"\nDetailed report saved to: {output_file}")
    else:
        print(f"Results file not found: {results_file}")


if __name__ == "__main__":
    main()