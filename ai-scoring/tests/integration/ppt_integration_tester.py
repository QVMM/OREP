#!/usr/bin/env python3
"""
OREP PPT生成系统 - 自动化集成测试脚本
Automated Integration Test Script for OREP PPT Generation System

功能:
1. 生成任务 -> 轮询状态 -> 检查输出页数/空壳率/SVG数
2. 对比多次生成结果的稳定性
3. 竞品PPT质量对比自动化脚本

使用方法:
    .venv/bin/python ppt_integration_tester.py [--case CASE_ID] [--all] [--stability]
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict

# 添加项目路径
PROJECT_ROOT = Path("/Users/liuyixing/项目/OREP/ai-scoring")
sys.path.insert(0, str(PROJECT_ROOT))

# API配置
API_BASE_URL = "http://localhost:8090"
API_PPT_TASK_CREATE = f"{API_BASE_URL}/api/ppt/v2/task/create"
API_PPT_TASK_STATUS = f"{API_BASE_URL}/api/ppt/task/{{task_id}}/status"
API_PPT_TASK_DETAIL = f"{API_BASE_URL}/api/ppt/task/{{task_id}}"
API_PPT_DOWNLOAD = f"{API_BASE_URL}/api/ppt/task/{{task_id}}/download"
API_PPT_FORMS = f"{API_BASE_URL}/api/ppt/forms/{{domain}}"

# PPT分析工具路径
PYTHON_BIN = "/Users/liuyixing/项目/OREP/ai-scoring/.venv/bin/python"

# 质量指标基线
QUALITY_BASELINES = {
    "min_effective_pages": 35,     # 有效页数 >= 35
    "max_empty_pages": 3,          # 空壳页 <= 3
    "min_svg_charts": 10,          # SVG图表 >= 10
    "min_skill_pages": 10,         # 技能操作页 >= 10
    "max_garbled_chars": 0,        # 零乱码
}

# 测试结果目录
RESULTS_DIR = PROJECT_ROOT / "tests" / "integration" / "results"
os.makedirs(RESULTS_DIR, exist_ok=True)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class QualityMetrics:
    """PPT质量指标"""
    total_pages: int = 0
    effective_pages: int = 0
    empty_pages: int = 0
    svg_charts: int = 0
    skill_pages: int = 0
    garbled_chars: int = 0
    kpi_pages: int = 0
    timeline_pages: int = 0
    content_pages: int = 0
    team_pages: int = 0
    cover_pages: int = 0
    toc_pages: int = 0
    ending_pages: int = 0

    # 详细内容（用于调试）
    page_details: List[Dict] = field(default_factory=list)
    svg_details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "total_pages": self.total_pages,
            "effective_pages": self.effective_pages,
            "empty_pages": self.empty_pages,
            "svg_charts": self.svg_charts,
            "skill_pages": self.skill_pages,
            "garbled_chars": self.garbled_chars,
            "kpi_pages": self.kpi_pages,
            "timeline_pages": self.timeline_pages,
            "content_pages": self.content_pages,
            "team_pages": self.team_pages,
            "cover_pages": self.cover_pages,
            "toc_pages": self.toc_pages,
            "ending_pages": self.ending_pages,
        }

    def check_baseline(self) -> Tuple[bool, List[str]]:
        """检查是否满足质量基线"""
        issues = []
        passed = True

        if self.effective_pages < QUALITY_BASELINES["min_effective_pages"]:
            issues.append(f"有效页数不足: {self.effective_pages} < {QUALITY_BASELINES['min_effective_pages']}")
            passed = False

        if self.empty_pages > QUALITY_BASELINES["max_empty_pages"]:
            issues.append(f"空壳页过多: {self.empty_pages} > {QUALITY_BASELINES['max_empty_pages']}")
            passed = False

        if self.svg_charts < QUALITY_BASELINES["min_svg_charts"]:
            issues.append(f"SVG图表不足: {self.svg_charts} < {QUALITY_BASELINES['min_svg_charts']}")
            passed = False

        if self.skill_pages < QUALITY_BASELINES["min_skill_pages"]:
            issues.append(f"技能操作页不足: {self.skill_pages} < {QUALITY_BASELINES['min_skill_pages']}")
            passed = False

        if self.garbled_chars > QUALITY_BASELINES["max_garbled_chars"]:
            issues.append(f"存在乱码字符: {self.garbled_chars} 个")
            passed = False

        return passed, issues


@dataclass
class TestResult:
    """测试结果"""
    case_id: str
    task_id: Optional[int]
    status: str  # passed, failed, error, timeout
    start_time: datetime
    end_time: Optional[datetime] = None
    metrics: Optional[QualityMetrics] = None
    baseline_passed: bool = False
    issues: List[str] = field(default_factory=list)
    task_detail: Optional[Dict] = None
    error_message: Optional[str] = None

    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "task_id": self.task_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration,
            "baseline_passed": self.baseline_passed,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "issues": self.issues,
            "error_message": self.error_message,
        }


# ============================================================
# API客户端
# ============================================================

import urllib.request
import urllib.error


def api_post(url: str, data: Dict) -> Tuple[int, Dict]:
    """发送POST请求"""
    try:
        body = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=body)
        req.add_header('Content-Type', 'application/json')
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}


def api_get(url: str) -> Tuple[int, Dict]:
    """发送GET请求"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return 0, {"error": str(e)}


# ============================================================
# PPT分析器
# ============================================================

def analyze_pptx(pptx_path: str) -> QualityMetrics:
    """
    分析PPTX文件，提取质量指标

    分析内容:
    - 总页数
    - 有效页数（非空壳）
    - 空壳页数
    - SVG图表数量
    - 技能操作页数量
    - 乱码字符检测
    """
    metrics = QualityMetrics()

    # 使用python-pptx分析
    analysis_script = f"""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
import re
import zipfile
import xml.etree.ElementTree as ET

pptx_path = "{pptx_path}"

# 乱码检测函数
def has_garbled_chars(text):
    # 检测常见乱码模式
    garbled_patterns = [
        r'[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]',  # 控制字符
        r'\\ufffd',  # Unicode替换字符
        r'\\u0000',  # 空字符
    ]
    for pattern in garbled_patterns:
        if re.search(pattern, text):
            return True
    return False

# 统计SVG
svg_count = 0
svg_details = []

try:
    with zipfile.ZipFile(pptx_path, 'r') as zf:
        for name in zf.namelist():
            if name.startswith('ppt/slides/slide') and name.endswith('.xml'):
                content = zf.read(name).decode('utf-8', errors='ignore')
                # 检测SVG图片引用
                if '<a:blip' in content and 'svg' in content.lower():
                    svg_count += 1
                    svg_details.append(name)
except Exception as e:
    print(f"SVG统计错误: {{e}}", file=sys.stderr)

# 分析幻灯片
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

page_details = []

for i, slide in enumerate(prs.slides):
    slide_num = i + 1
    shapes = len(slide.shapes)

    # 收集所有文本
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

    full_text = ' '.join(all_text).strip()
    word_count = len(full_text)

    # 判断页面类型
    layout = str(slide.slide_layout.name).lower() if slide.slide_layout else ""

    # 检测技能操作页（通过关键词）
    skill_keywords = ['技能', '操作', '岗位职责', '前置准备', '后续收尾', '团队协作',
                      '步骤', 'milestone', 'timeline', '技能操作']
    is_skill = any(kw in full_text for kw in skill_keywords)

    # 检测KPI页面
    kpi_keywords = ['指标', 'KPI', '成果', '率', '%', '达成']
    is_kpi = (is_skill and 'metrics' in layout.lower()) or any(kw in full_text for kw in kpi_keywords)

    # 检测时间线
    timeline_keywords = ['时间', 'timeline', '规划', '发展', '阶段']
    is_timeline = 'timeline' in layout.lower() or any(kw in full_text for kw in timeline_keywords)

    # 检测内容页
    content_keywords = ['内容', '说明', '分析', '方案', '创新']
    is_content = 'content' in layout.lower() and word_count > 50

    # 检测团队页
    team_keywords = ['团队', '成员', '分工', 'name', 'role']
    is_team = 'team' in layout.lower() or (all(kw in full_text for kw in ['团队', '成员']) if full_text else False)

    # 检测封面/目录/结束
    is_cover = 'cover' in layout.lower() or '封面' in full_text[:20]
    is_toc = 'toc' in layout.lower() or '目录' in full_text[:20]
    is_ending = 'ending' in layout.lower() or '结束' in full_text[:20] or '谢谢' in full_text[:20]

    # 判断是否为空壳页（几乎无内容）
    is_empty = word_count < 20 and shapes < 3

    if is_skill:
        skill_pages += 1
    if is_kpi:
        kpi_pages += 1
    if is_timeline:
        timeline_pages += 1
    if is_content:
        content_pages += 1
    if is_team:
        team_pages += 1
    if is_cover:
        cover_pages += 1
    if is_toc:
        toc_pages += 1
    if is_ending:
        ending_pages += 1
    if is_empty:
        empty_pages += 1
    else:
        effective += 1

    page_details.append({{
        "slide_num": slide_num,
        "shapes": shapes,
        "word_count": word_count,
        "is_empty": is_empty,
        "is_skill": is_skill,
        "is_kpi": is_kpi,
        "is_timeline": is_timeline,
        "layout": layout,
        "preview": full_text[:100] if full_text else "(empty)"
    }})

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
    "ending_pages": ending_pages,
    "page_details": page_details,
    "svg_details": svg_details
}}

import json
print(json.dumps(result))
"""

    try:
        result = subprocess.run(
            [PYTHON_BIN, "-c", analysis_script],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            metrics.total_pages = data.get("total_pages", 0)
            metrics.effective_pages = data.get("effective_pages", 0)
            metrics.empty_pages = data.get("empty_pages", 0)
            metrics.svg_charts = data.get("svg_charts", 0)
            metrics.skill_pages = data.get("skill_pages", 0)
            metrics.garbled_chars = data.get("garbled_chars", 0)
            metrics.kpi_pages = data.get("kpi_pages", 0)
            metrics.timeline_pages = data.get("timeline_pages", 0)
            metrics.content_pages = data.get("content_pages", 0)
            metrics.team_pages = data.get("team_pages", 0)
            metrics.cover_pages = data.get("cover_pages", 0)
            metrics.toc_pages = data.get("toc_pages", 0)
            metrics.ending_pages = data.get("ending_pages", 0)
            metrics.page_details = data.get("page_details", [])
            metrics.svg_details = data.get("svg_details", [])
        else:
            print(f"PPTX分析脚本错误: {result.stderr}", file=sys.stderr)

    except subprocess.TimeoutExpired:
        print(f"PPTX分析超时: {pptx_path}", file=sys.stderr)
    except Exception as e:
        print(f"PPTX分析异常: {e}", file=sys.stderr)

    return metrics


# ============================================================
# PPT生成器测试核心
# ============================================================

class PPTIntegrationTester:
    """PPT集成测试器"""

    def __init__(self, case_id: str, questionnaire_id: int, user_id: int, tenant_id: int,
                 industry: str = "tech"):
        self.case_id = case_id
        self.questionnaire_id = questionnaire_id
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.industry = industry

        self.result: Optional[TestResult] = None
        self.task_id: Optional[int] = None

    def run(self, timeout: int = 600) -> TestResult:
        """运行完整测试流程"""
        self.result = TestResult(
            case_id=self.case_id,
            task_id=None,
            status="running",
            start_time=datetime.now()
        )

        try:
            # 1. 创建任务
            print(f"[{self.case_id}] 创建PPT生成任务...")
            task_id = self._create_task()
            self.task_id = task_id
            self.result.task_id = task_id
            print(f"[{self.case_id}] 任务创建成功, task_id={task_id}")

            # 2. 轮询状态
            print(f"[{self.case_id}] 轮询任务状态...")
            if not self._poll_task_status(task_id, timeout):
                self.result.status = "timeout"
                self.result.end_time = datetime.now()
                self.result.issues.append("任务超时未完成")
                return self.result

            # 3. 获取任务详情
            print(f"[{self.case_id}] 获取任务详情...")
            task_detail = self._get_task_detail(task_id)
            self.result.task_detail = task_detail

            # 4. 分析PPT
            if task_detail and task_detail.get("data", {}).get("pptx_path"):
                pptx_path = task_detail["data"]["pptx_path"]
                print(f"[{self.case_id}] 分析PPT: {pptx_path}")
                self.result.metrics = analyze_pptx(pptx_path)

                # 5. 检查基线
                if self.result.metrics:
                    passed, issues = self.result.metrics.check_baseline()
                    self.result.baseline_passed = passed
                    self.result.issues = issues
                    self.result.status = "passed" if passed else "failed"
            else:
                self.result.status = "error"
                self.result.error_message = "PPT文件路径不存在"
                self.result.issues.append("pptx_path is null")

            self.result.end_time = datetime.now()

        except Exception as e:
            self.result.status = "error"
            self.result.error_message = str(e)
            self.result.end_time = datetime.now()
            self.result.issues.append(f"Exception: {e}")

        return self.result

    def _create_task(self) -> int:
        """创建PPT生成任务"""
        data = {
            "questionnaire_id": self.questionnaire_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "industry": self.industry
        }

        status, response = api_post(API_PPT_TASK_CREATE, data)

        if status != 200 or not response.get("success"):
            raise Exception(f"创建任务失败: status={status}, response={response}")

        return response["data"]["task_id"]

    def _poll_task_status(self, task_id: int, timeout: int) -> bool:
        """轮询任务状态直到完成/失败"""
        url = API_PPT_TASK_STATUS.format(task_id=task_id)
        start_time = time.time()
        poll_interval = 5  # 秒

        while time.time() - start_time < timeout:
            status, response = api_get(url)

            if status != 200:
                print(f"[{self.case_id}] 状态查询失败: status={status}")
                time.sleep(poll_interval)
                continue

            data = response.get("data", {})
            current_status = data.get("status")
            current_step = data.get("current_step", "")

            print(f"[{self.case_id}] 当前状态: {current_status}, 步骤: {current_step}")

            if current_status == "completed":
                return True
            elif current_status in ["failed", "error"]:
                self.result.issues.append(f"任务失败: {data.get('error_msg', 'unknown')}")
                return False

            time.sleep(poll_interval)

        return False

    def _get_task_detail(self, task_id: int) -> Optional[Dict]:
        """获取任务详情"""
        url = API_PPT_TASK_DETAIL.format(task_id=task_id)
        status, response = api_get(url)

        if status == 200 and response.get("success"):
            return response

        return None


# ============================================================
# 竞品PPT质量对比
# ============================================================

class CompetitiveAnalyzer:
    """竞品PPT质量对比分析器"""

    # 竞品基线数据（基于行业标准）
    COMPETITIVE_BASELINES = {
        "healthcare": {
            "min_pages": 30,
            "min_svg": 8,
            "min_skill_pages": 8,
            "min_kpi_pages": 6,
        },
        "ai_iot": {
            "min_pages": 35,
            "min_svg": 10,
            "min_skill_pages": 10,
            "min_kpi_pages": 8,
        },
        "tech": {
            "min_pages": 28,
            "min_svg": 6,
            "min_skill_pages": 6,
            "min_kpi_pages": 5,
        },
        "default": {
            "min_pages": 25,
            "min_svg": 5,
            "min_skill_pages": 5,
            "min_kpi_pages": 4,
        }
    }

    @classmethod
    def compare_with_competitive(cls, metrics: QualityMetrics, industry: str) -> Dict:
        """对比竞品基线"""
        baseline = cls.COMPETITIVE_BASELINES.get(industry, cls.COMPETITIVE_BASELINES["default"])

        comparison = {
            "industry": industry,
            "vs_competitive": {},
            "score": 0,
            "max_score": 100,
            "grade": "F"
        }

        # 计算各维度得分
        page_score = min(25, (metrics.total_pages / baseline["min_pages"]) * 25)
        svg_score = min(25, (metrics.svg_charts / baseline["min_svg"]) * 25)
        skill_score = min(25, (metrics.skill_pages / baseline["min_skill_pages"]) * 25)
        kpi_score = min(25, (metrics.kpi_pages / baseline["min_kpi_pages"]) * 25)

        total_score = page_score + svg_score + skill_score + kpi_score

        comparison["vs_competitive"] = {
            "pages": {
                "actual": metrics.total_pages,
                "baseline": baseline["min_pages"],
                "score": round(page_score, 1),
                "pass": metrics.total_pages >= baseline["min_pages"]
            },
            "svg_charts": {
                "actual": metrics.svg_charts,
                "baseline": baseline["min_svg"],
                "score": round(svg_score, 1),
                "pass": metrics.svg_charts >= baseline["min_svg"]
            },
            "skill_pages": {
                "actual": metrics.skill_pages,
                "baseline": baseline["min_skill_pages"],
                "score": round(skill_score, 1),
                "pass": metrics.skill_pages >= baseline["min_skill_pages"]
            },
            "kpi_pages": {
                "actual": metrics.kpi_pages,
                "baseline": baseline["min_kpi_pages"],
                "score": round(kpi_score, 1),
                "pass": metrics.kpi_pages >= baseline["min_kpi_pages"]
            }
        }

        comparison["score"] = round(total_score, 1)

        # 评级
        if total_score >= 90:
            comparison["grade"] = "A+"
        elif total_score >= 80:
            comparison["grade"] = "A"
        elif total_score >= 70:
            comparison["grade"] = "B"
        elif total_score >= 60:
            comparison["grade"] = "C"
        elif total_score >= 50:
            comparison["grade"] = "D"
        else:
            comparison["grade"] = "F"

        return comparison


# ============================================================
# 稳定性测试
# ============================================================

def run_stability_test(case_id: str, questionnaire_id: int, user_id: int,
                        tenant_id: int, industry: str, runs: int = 3) -> List[TestResult]:
    """运行稳定性测试（多次生成对比）"""
    print(f"\n{'='*60}")
    print(f"稳定性测试: {case_id}, 连续{runs}次生成")
    print(f"{'='*60}")

    results = []

    for i in range(runs):
        print(f"\n--- Run {i+1}/{runs} ---")
        tester = PPTIntegrationTester(
            case_id=f"{case_id}-run{i+1}",
            questionnaire_id=questionnaire_id,
            user_id=user_id,
            tenant_id=tenant_id,
            industry=industry
        )
        result = tester.run()
        results.append(result)

        # 保存单个结果
        save_result(result)

        time.sleep(5)  # 间隔5秒

    # 分析稳定性
    stability_analysis = analyze_stability(results)

    return results, stability_analysis


def analyze_stability(results: List[TestResult]) -> Dict:
    """分析多次测试的稳定性"""
    if not results:
        return {}

    # 提取指标
    total_pages_list = [r.metrics.total_pages for r in results if r.metrics]
    effective_pages_list = [r.metrics.effective_pages for r in results if r.metrics]
    svg_charts_list = [r.metrics.svg_charts for r in results if r.metrics]
    skill_pages_list = [r.metrics.skill_pages for r in results if r.metrics]

    def calc_variance(lst):
        if len(lst) < 2:
            return 0
        avg = sum(lst) / len(lst)
        return sum((x - avg) ** 2 for x in lst) / len(lst)

    def calc_stability(lst):
        if not lst:
            return "N/A"
        variance = calc_variance(lst)
        if variance == 0:
            return "完全稳定"
        avg = sum(lst) / len(lst)
        cv = (variance ** 0.5) / avg if avg > 0 else 0
        if cv < 0.05:
            return "非常稳定"
        elif cv < 0.10:
            return "稳定"
        elif cv < 0.20:
            return "轻微波动"
        else:
            return "波动较大"

    analysis = {
        "total_pages": {
            "values": total_pages_list,
            "variance": round(calc_variance(total_pages_list), 2),
            "stability": calc_stability(total_pages_list)
        },
        "effective_pages": {
            "values": effective_pages_list,
            "variance": round(calc_variance(effective_pages_list), 2),
            "stability": calc_stability(effective_pages_list)
        },
        "svg_charts": {
            "values": svg_charts_list,
            "variance": round(calc_variance(svg_charts_list), 2),
            "stability": calc_stability(svg_charts_list)
        },
        "skill_pages": {
            "values": skill_pages_list,
            "variance": round(calc_variance(skill_pages_list), 2),
            "stability": calc_stability(skill_pages_list)
        }
    }

    return analysis


# ============================================================
# 工具函数
# ============================================================

def save_result(result: TestResult):
    """保存测试结果到文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{result.case_id}_{timestamp}.json"
    filepath = RESULTS_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

    print(f"结果已保存: {filepath}")


def save_stability_report(case_id: str, results: List[TestResult], analysis: Dict):
    """保存稳定性测试报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"stability_{case_id}_{timestamp}.json"
    filepath = RESULTS_DIR / filename

    report = {
        "case_id": case_id,
        "timestamp": timestamp,
        "runs": len(results),
        "results": [r.to_dict() for r in results],
        "stability_analysis": analysis
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"稳定性报告已保存: {filepath}")


def print_result_summary(result: TestResult):
    """打印测试结果摘要"""
    print(f"\n{'='*60}")
    print(f"测试结果: {result.case_id}")
    print(f"{'='*60}")
    print(f"状态: {result.status}")
    print(f"任务ID: {result.task_id}")
    print(f"耗时: {result.duration:.1f}秒")

    if result.metrics:
        print(f"\n质量指标:")
        print(f"  总页数: {result.metrics.total_pages}")
        print(f"  有效页数: {result.metrics.effective_pages} (基线≥35)")
        print(f"  空壳页数: {result.metrics.empty_pages} (基线≤3)")
        print(f"  SVG图表: {result.metrics.svg_charts} (基线≥10)")
        print(f"  技能操作页: {result.metrics.skill_pages} (基线≥10)")
        print(f"  乱码字符: {result.metrics.garbled_chars} (基线=0)")
        print(f"\n  KPI页: {result.metrics.kpi_pages}")
        print(f"  时间线页: {result.metrics.timeline_pages}")
        print(f"  内容页: {result.metrics.content_pages}")
        print(f"  团队页: {result.metrics.team_pages}")

    if result.baseline_passed:
        print(f"\n基线检查: 通过")
    else:
        print(f"\n基线检查: 未通过")
        for issue in result.issues:
            print(f"  - {issue}")

    if result.error_message:
        print(f"\n错误: {result.error_message}")


def print_stability_summary(results: List[TestResult], analysis: Dict):
    """打印稳定性测试摘要"""
    print(f"\n{'='*60}")
    print(f"稳定性测试摘要 ({len(results)}次运行)")
    print(f"{'='*60}")

    for metric, data in analysis.items():
        print(f"\n{metric}:")
        print(f"  数值: {data['values']}")
        print(f"  方差: {data['variance']}")
        print(f"  稳定性: {data['stability']}")


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="OREP PPT集成测试")
    parser.add_argument("--case", type=str, help="测试用例ID (如 P0-001)")
    parser.add_argument("--all", action="store_true", help="运行所有测试")
    parser.add_argument("--stability", action="store_true", help="运行稳定性测试")
    parser.add_argument("--questionnaire-id", type=int, default=28, help="问卷ID")
    parser.add_argument("--user-id", type=int, default=1, help="用户ID")
    parser.add_argument("--tenant-id", type=int, default=1, help="租户ID")
    parser.add_argument("--industry", type=str, default="healthcare", help="行业")
    parser.add_argument("--runs", type=int, default=3, help="稳定性测试运行次数")

    args = parser.parse_args()

    # 导入测试用例矩阵
    from test_case_matrix import TEST_CASE_MATRIX, get_test_cases_by_tag

    if args.stability:
        # 运行稳定性测试
        results, analysis = run_stability_test(
            case_id=f"{args.case}-stability" if args.case else "stability-test",
            questionnaire_id=args.questionnaire_id,
            user_id=args.user_id,
            tenant_id=args.tenant_id,
            industry=args.industry,
            runs=args.runs
        )
        print_stability_summary(results, analysis)
        save_stability_report(args.case or "stability", results, analysis)

    elif args.all:
        # 运行所有测试
        print(f"\n{'='*60}")
        print("运行所有测试用例")
        print(f"{'='*60}")

        all_results = []
        for tc in TEST_CASE_MATRIX:
            if tc.questionnaire_id == 0:
                print(f"\n跳过 {tc.case_id}: 问卷ID未配置")
                continue

            print(f"\n{'='*60}")
            print(f"运行测试: {tc.case_id} - {tc.name}")
            print(f"{'='*60}")

            tester = PPTIntegrationTester(
                case_id=tc.case_id,
                questionnaire_id=tc.questionnaire_id,
                user_id=tc.user_id,
                tenant_id=tc.tenant_id,
                industry=tc.industry.value
            )

            result = tester.run()
            all_results.append(result)
            save_result(result)
            print_result_summary(result)

            time.sleep(3)

        # 统计汇总
        passed = sum(1 for r in all_results if r.status == "passed")
        failed = sum(1 for r in all_results if r.status == "failed")
        errors = sum(1 for r in all_results if r.status == "error")

        print(f"\n{'='*60}")
        print("全部测试完成")
        print(f"{'='*60}")
        print(f"通过: {passed}/{len(all_results)}")
        print(f"失败: {failed}/{len(all_results)}")
        print(f"错误: {errors}/{len(all_results)}")

    elif args.case:
        # 运行单个测试
        tester = PPTIntegrationTester(
            case_id=args.case,
            questionnaire_id=args.questionnaire_id,
            user_id=args.user_id,
            tenant_id=args.tenant_id,
            industry=args.industry
        )

        result = tester.run()
        save_result(result)
        print_result_summary(result)

        # 竞品对比
        if result.metrics:
            comparison = CompetitiveAnalyzer.compare_with_competitive(
                result.metrics, args.industry
            )
            print(f"\n{'='*60}")
            print("竞品质量对比")
            print(f"{'='*60}")
            print(f"行业: {comparison['industry']}")
            print(f"总分: {comparison['score']}/{comparison['max_score']}")
            print(f"评级: {comparison['grade']}")
            print("\n各维度:")
            for dim, data in comparison["vs_competitive"].items():
                status = "通过" if data["pass"] else "未达标"
                print(f"  {dim}: {data['actual']}/{data['baseline']} (得分:{data['score']}) - {status}")

    else:
        # 默认运行基线测试
        print(f"\n{'='*60}")
        print("运行基线测试 (P0-001)")
        print(f"{'='*60}")

        tester = PPTIntegrationTester(
            case_id="P0-001",
            questionnaire_id=28,  # 使用存在的问卷
            user_id=1,
            tenant_id=1,
            industry="healthcare"
        )

        result = tester.run()
        save_result(result)
        print_result_summary(result)


if __name__ == "__main__":
    main()