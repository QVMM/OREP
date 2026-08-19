#!/usr/bin/env python3
"""
OREP PPT生成系统 - 测试用例矩阵
Test Case Matrix for OREP PPT Generation System

测试覆盖范围:
1. 不同行业PPT生成测试（医疗/教育/制造/金融）
2. 边界条件（极少数据/极多数据/缺失字段）
3. 回归测试用例（确保修复不破坏已有功能）

Quality Metrics Baseline:
- 有效页数 ≥ 35
- 空壳页 ≤ 3
- SVG图表 ≥ 10
- 技能操作页 ≥ 10
- 零乱码
"""

import json
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class Industry(Enum):
    """行业枚举"""
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    MANUFACTURING = "manufacturing"
    FINANCE = "finance"
    TECH = "tech"
    AI_IOT = "ai_iot"


class TestPriority(Enum):
    """测试优先级"""
    P0_CRITICAL = "P0_Critical"  # 核心功能
    P1_HIGH = "P1_High"         # 高优先级
    P2_MEDIUM = "P2_Medium"      # 中优先级
    P3_LOW = "P3_Low"           # 低优先级


@dataclass
class TestCase:
    """测试用例结构"""
    case_id: str
    name: str
    industry: Industry
    priority: TestPriority
    questionnaire_id: int
    user_id: int
    tenant_id: int
    description: str
    expected_pages_min: int = 35
    expected_empty_max: int = 3
    expected_svg_min: int = 10
    expected_skill_pages_min: int = 10
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


# ============================================================
# 测试用例矩阵
# ============================================================

TEST_CASE_MATRIX: List[TestCase] = [
    # ========== P0: 核心功能测试 ==========

    TestCase(
        case_id="P0-001",
        name="基线测试-任务54(Healthcare完整数据)",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P0_CRITICAL,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="基于任务54基线的完整Healthcare行业测试，验证当前最佳实践",
        expected_pages_min=40,
        expected_empty_max=3,
        expected_svg_min=13,
        expected_skill_pages_min=10,
        tags=["baseline", "healthcare", "full_data"]
    ),

    TestCase(
        case_id="P0-002",
        name="多行业回归测试-HealthCare",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P0_CRITICAL,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="Healthcare行业回归测试，确保修复不破坏现有功能",
        tags=["regression", "healthcare"]
    ),

    TestCase(
        case_id="P0-003",
        name="多行业回归测试-AIIoT",
        industry=Industry.AI_IOT,
        priority=TestPriority.P0_CRITICAL,
        questionnaire_id=25,
        user_id=1,
        tenant_id=1,
        description="AIoT行业回归测试",
        tags=["regression", "ai_iot"]
    ),

    # ========== P1: 行业测试 ==========

    TestCase(
        case_id="P1-001",
        name="Healthcare行业-云边协同慢病预测",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P1_HIGH,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="测试Healthcare行业PPT生成，验证医疗场景KPI指标页和技能操作页",
        tags=["healthcare", "kpi", "skill_pages"]
    ),

    TestCase(
        case_id="P1-002",
        name="Education行业-智慧教育平台",
        industry=Industry.EDUCATION,
        priority=TestPriority.P1_HIGH,
        questionnaire_id=0,  # 需要创建/使用实际存在的问卷
        user_id=1,
        tenant_id=1,
        description="测试教育行业PPT生成",
        tags=["education"]
    ),

    TestCase(
        case_id="P1-003",
        name="Manufacturing行业-智能制造",
        industry=Industry.MANUFACTURING,
        priority=TestPriority.P1_HIGH,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试制造业PPT生成",
        tags=["manufacturing"]
    ),

    TestCase(
        case_id="P1-004",
        name="Finance行业-金融科技",
        industry=Industry.FINANCE,
        priority=TestPriority.P1_HIGH,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试金融行业PPT生成",
        tags=["finance"]
    ),

    TestCase(
        case_id="P1-005",
        name="Tech行业-技术创新",
        industry=Industry.TECH,
        priority=TestPriority.P1_HIGH,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试科技行业PPT生成",
        tags=["tech"]
    ),

    # ========== P2: 边界条件测试 ==========

    TestCase(
        case_id="P2-001",
        name="极少数据-最小问卷",
        industry=Industry.TECH,
        priority=TestPriority.P2_MEDIUM,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试极少数据场景，只有最基本的必填字段",
        expected_pages_min=20,  # 降低期望
        expected_empty_max=5,    # 允许更多空壳
        expected_svg_min=5,
        expected_skill_pages_min=5,
        tags=["boundary", "minimal_data"]
    ),

    TestCase(
        case_id="P2-002",
        name="极多数据-超长文本",
        industry=Industry.TECH,
        priority=TestPriority.P2_MEDIUM,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试极多数据场景，超长文本内容",
        expected_pages_min=45,  # 期望更多页
        expected_empty_max=2,
        expected_svg_min=15,
        expected_skill_pages_min=12,
        tags=["boundary", "max_data"]
    ),

    TestCase(
        case_id="P2-003",
        name="缺失字段-可选字段为空",
        industry=Industry.TECH,
        priority=TestPriority.P2_MEDIUM,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试可选字段缺失的情况",
        expected_pages_min=30,
        expected_empty_max=4,
        expected_svg_min=8,
        expected_skill_pages_min=8,
        tags=["boundary", "missing_optional"]
    ),

    TestCase(
        case_id="P2-004",
        name="缺失字段-必填字段为空",
        industry=Industry.TECH,
        priority=TestPriority.P2_MEDIUM,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试必填字段缺失，验证错误处理",
        expected_pages_min=0,  # 可能失败
        expected_empty_max=99,
        expected_svg_min=0,
        expected_skill_pages_min=0,
        tags=["boundary", "missing_required"]
    ),

    TestCase(
        case_id="P2-005",
        name="特殊字符测试",
        industry=Industry.TECH,
        priority=TestPriority.P2_MEDIUM,
        questionnaire_id=0,
        user_id=1,
        tenant_id=1,
        description="测试特殊字符、emoji、LaTeX公式等",
        expected_pages_min=30,
        expected_empty_max=4,
        expected_svg_min=8,
        expected_skill_pages_min=8,
        tags=["boundary", "special_chars"]
    ),

    # ========== P3: 稳定性测试 ==========

    TestCase(
        case_id="P3-001",
        name="稳定性测试-相同数据多次生成",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P3_LOW,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="使用相同数据连续生成3次，验证结果一致性",
        tags=["stability", "repeatability"]
    ),

    TestCase(
        case_id="P3-002",
        name="并发测试-多任务同时生成",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P3_LOW,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="同时发起3个生成任务，验证并发处理",
        tags=["stability", "concurrency"]
    ),

    TestCase(
        case_id="P3-003",
        name="生成时间性能测试",
        industry=Industry.HEALTHCARE,
        priority=TestPriority.P3_LOW,
        questionnaire_id=28,
        user_id=1,
        tenant_id=1,
        description="测量PPT生成耗时，验证性能基线",
        tags=["performance", "timing"]
    ),
]


# ============================================================
# 测试用例矩阵表格输出
# ============================================================

def print_test_case_matrix():
    """打印测试用例矩阵表格"""
    print("\n" + "=" * 120)
    print("OREP PPT生成系统 - 测试用例矩阵 (Test Case Matrix)")
    print("=" * 120)

    # 表头
    print(f"{'Case ID':<10} {'Name':<40} {'Industry':<12} {'Priority':<12} {'Expected Pages':<16} {'Tags':<30}")
    print("-" * 120)

    for tc in TEST_CASE_MATRIX:
        tags_str = ", ".join(tc.tags) if tc.tags else ""
        print(f"{tc.case_id:<10} {tc.name[:38]:<40} {tc.industry.value:<12} {tc.priority.value:<12} "
              f"≥{tc.expected_pages_min:<14} {tags_str[:28]:<30}")

    print("-" * 120)
    print(f"Total Test Cases: {len(TEST_CASE_MATRIX)}")


def get_test_cases_by_industry(industry: Industry) -> List[TestCase]:
    """按行业筛选测试用例"""
    return [tc for tc in TEST_CASE_MATRIX if tc.industry == industry]


def get_test_cases_by_priority(priority: TestPriority) -> List[TestCase]:
    """按优先级筛选测试用例"""
    return [tc for tc in TEST_CASE_MATRIX if tc.priority == priority]


def get_test_cases_by_tag(tag: str) -> List[TestCase]:
    """按标签筛选测试用例"""
    return [tc for tc in TEST_CASE_MATRIX if tag in (tc.tags or [])]


def export_test_matrix_json(filepath: str):
    """导出测试矩阵为JSON格式"""
    data = {
        "test_cases": [
            {
                "case_id": tc.case_id,
                "name": tc.name,
                "industry": tc.industry.value,
                "priority": tc.priority.value,
                "questionnaire_id": tc.questionnaire_id,
                "user_id": tc.user_id,
                "tenant_id": tc.tenant_id,
                "description": tc.description,
                "expected_pages_min": tc.expected_pages_min,
                "expected_empty_max": tc.expected_empty_max,
                "expected_svg_min": tc.expected_svg_min,
                "expected_skill_pages_min": tc.expected_skill_pages_min,
                "tags": tc.tags
            }
            for tc in TEST_CASE_MATRIX
        ]
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print_test_case_matrix()
    print("\n" + "=" * 120)
    print("按行业统计:")
    for industry in Industry:
        count = len(get_test_cases_by_industry(industry))
        if count > 0:
            print(f"  {industry.value}: {count} cases")

    print("\n按优先级统计:")
    for priority in TestPriority:
        count = len(get_test_cases_by_priority(priority))
        if count > 0:
            print(f"  {priority.value}: {count} cases")

    # 导出JSON
    export_path = "/Users/liuyixing/项目/OREP/ai-scoring/tests/integration/test_case_matrix.json"
    export_test_matrix_json(export_path)
    print(f"\nTest matrix exported to: {export_path}")