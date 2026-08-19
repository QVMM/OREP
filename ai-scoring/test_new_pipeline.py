"""
测试新PPT生成Pipeline（Round 1-4 + Self-Check）
直接读取问卷数据，跑新pipeline，输出结果到文件
"""
import asyncio
import json
import sys
import os
import logging
import pymysql
import re

# 清除可能导致连接问题的代理设置
for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
    os.environ.pop(var, None)

# 设置路径
sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')
sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def parse_json_response(content: str) -> dict:
    """
    健壮的JSON解析函数，处理各种格式问题
    """
    if not content:
        raise ValueError("响应内容为空")

    # 原始内容记录日志
    logger.info(f"解析JSON响应，长度: {len(content)}")

    # Step 1: 去除markdown代码块包裹
    cleaned = content.strip()

    # 处理 ```json ... ``` 或 ``` ... ```
    if cleaned.startswith('```'):
        # 找到第一个换行后的位置
        first_newline = cleaned.find('\n')
        if first_newline > 0:
            # 去掉开头的```json或```和语言标识
            cleaned = cleaned[first_newline+1:]
        # 去掉结尾的```
        if cleaned.rstrip().endswith('```'):
            cleaned = cleaned.rstrip()[:-3]
        cleaned = cleaned.strip()

    # Step 2: 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: 尝试提取JSON对象（查找{...}模式）
    # 匹配第一个{到最后一个}之间的内容
    brace_start = cleaned.find('{')
    brace_end = cleaned.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        json_candidate = cleaned[brace_start:brace_end+1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass

    # Step 4: 尝试修复常见JSON问题
    # 4.1 修复单引号问题
    fixed = cleaned.replace("'", '"')
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4.2 移除尾部逗号
    fixed = re.sub(r',(\s*[}\]])', r'\1', cleaned)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 4.3 尝试提取数组（用于pages数组）
    array_match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass

    # 最终失败，记录详细信息
    logger.error(f"JSON解析失败，响应内容前500字符: {cleaned[:500]}")
    raise ValueError(f"无法解析JSON响应，内容长度: {len(cleaned)}")

async def main():
    # 1. 读取问卷数据
    conn = pymysql.connect(
        host='localhost', user='root', password='12345678',
        database='orep', charset='utf8mb4'
    )
    with conn.cursor() as cur:
        cur.execute("""
            SELECT q.id, q.domain, q.project_name, q.team_name, q.responses
            FROM ppt_questionnaire q WHERE q.id = 28
        """)
        row = cur.fetchone()
        questionnaire_id, domain, project_name, team_name, responses_str = row
        responses = json.loads(responses_str) if isinstance(responses_str, str) else responses_str
    conn.close()

    logger.info(f"问卷: {project_name} (domain={domain})")

    # 2. 初始化pipeline（使用Qwen）
    from app.services.ppt.qwen_client import QwenClient
    from app.config import settings

    qwen = QwenClient(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    # 3. 加载prompts
    prompts_dir = '/Users/liuyixing/项目/OREP/ai-scoring/app/services/ppt/prompts'
    def load_prompt(name):
        with open(f'{prompts_dir}/{name}', 'r', encoding='utf-8') as f:
            return f.read()

    round1_prompt = load_prompt('round1_structurize.md')
    round2_prompt = load_prompt('round2_narrative.md')
    round3_prompt = load_prompt('round3_enrich.md')
    round4_prompt = load_prompt('round4_html_generation.md')
    selfcheck_prompt = load_prompt('self_check.md')

    # 4. 构建问卷数据
    questionnaire_data = {
        "project_name": project_name,
        "team_name": team_name,
        "domain": domain,
        "responses": responses
    }

    output_dir = '/Users/liuyixing/项目/OREP/ai-scoring/uploads/ppt/new_pipeline_test'
    os.makedirs(output_dir, exist_ok=True)

    # 使用安全替换（避免JSON中的{}被format误解析）
    def safe_format(template, **kwargs):
        """安全替换占位符，不破坏JSON中的{}"""
        result = template
        for key, value in kwargs.items():
            result = result.replace('{' + key + '}', value)
        return result

    # ========== Round 1: 结构化 ==========
    logger.info("=== Round 1: Structurize ===")
    r1_input = safe_format(round1_prompt,
        user_survey_data=json.dumps(questionnaire_data, ensure_ascii=False, indent=2),
        ai_generated_items=json.dumps({}, ensure_ascii=False, indent=2)
    )
    r1_response = await qwen.chat(r1_input, json_mode=True, max_tokens=32000)
    if not r1_response:
        logger.error("Round 1 无响应")
        return

    # 解析JSON
    r1_content = r1_response.strip()
    if r1_content.startswith('```'):
        r1_content = r1_content.split('\n', 1)[1].rsplit('```', 1)[0].strip()

    structured_data = json.loads(r1_content)
    with open(f'{output_dir}/round1_structured.json', 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Round 1 完成: {len(json.dumps(structured_data))} chars")

    # ========== Round 2: 叙事框架 ==========
    logger.info("=== Round 2: Narrative ===")
    competition_rules = {
        "competition_meta": {"name": "全职业技能大赛", "format": "operation_plus_presentation"},
        "scoring_criteria": [
            {"item": "创新性", "weight": 25},
            {"item": "技术实现", "weight": 30},
            {"item": "路演表达", "weight": 20}
        ]
    }
    roadshow_template = {
        "total_slides": "40-50页",
        "phases": [
            {"phase_id": 1, "phase_name": "开场路演", "duration_min": 5},
            {"phase_id": 2, "phase_name": "问题与市场", "duration_min": 5},
            {"phase_id": 3, "phase_name": "操作演示", "duration_min": 25},
            {"phase_id": 4, "phase_name": "成果与总结", "duration_min": 10}
        ]
    }

    r2_input = safe_format(round2_prompt,
        structured_data=json.dumps(structured_data, ensure_ascii=False, indent=2),
        competition_rules=json.dumps(competition_rules, ensure_ascii=False, indent=2),
        roadshow_template=json.dumps(roadshow_template, ensure_ascii=False, indent=2)
    )
    r2_response = await qwen.chat(r2_input, json_mode=True, max_tokens=60000)
    if not r2_response:
        logger.error("Round 2 无响应")
        return

    narrative = parse_json_response(r2_response)
    with open(f'{output_dir}/round2_narrative.json', 'w', encoding='utf-8') as f:
        json.dump(narrative, f, ensure_ascii=False, indent=2)
    pages_count = len(narrative.get('pages', []))
    logger.info(f"Round 2 完成: {pages_count} 页")

    # ========== Round 3: 内容填充 ==========
    logger.info("=== Round 3: Enrich ===")
    r3_input = safe_format(round3_prompt,
        confirmed_framework=json.dumps({
            "meta": narrative.get("meta", {}),
            "pages": narrative.get("pages", [])
        }, ensure_ascii=False, indent=2),
        original_data=json.dumps(structured_data, ensure_ascii=False, indent=2)
    )
    r3_response = await qwen.chat(r3_input, json_mode=True, max_tokens=60000)
    if not r3_response:
        logger.error("Round 3 无响应")
        return

    r3_result = parse_json_response(r3_response)
    enriched_pages = r3_result.get('pages', r3_result) if isinstance(r3_result, dict) else r3_result
    with open(f'{output_dir}/round3_enriched.json', 'w', encoding='utf-8') as f:
        json.dump(enriched_pages, f, ensure_ascii=False, indent=2)
    logger.info(f"Round 3 完成: {len(enriched_pages)} 页")

    # ========== Self-Check ==========
    logger.info("=== Self-Check ===")
    sc_content_json = json.dumps({
        "meta": {"total_pages": len(enriched_pages)},
        "pages": enriched_pages
    }, ensure_ascii=False, indent=2)
    sc_full_prompt = selfcheck_prompt + "\n\n## 待检查内容\n\n```json\n" + sc_content_json + "\n```"
    sc_response = await qwen.chat(sc_full_prompt, json_mode=True)
    if sc_response:
        check_report = parse_json_response(sc_response)
        with open(f'{output_dir}/self_check_report.json', 'w', encoding='utf-8') as f:
            json.dump(check_report, f, ensure_ascii=False, indent=2)
        verdict = check_report.get('check_summary', {}).get('overall_verdict', 'UNKNOWN')
        logger.info(f"Self-Check: {verdict}")
    else:
        logger.warning("Self-Check 无响应")

    # ========== 汇总 ==========
    logger.info(f"\n{'='*50}")
    logger.info(f"新Pipeline测试完成")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"Round 1 结构化数据: {len(json.dumps(structured_data))} chars")
    logger.info(f"Round 2 叙事框架: {pages_count} 页")
    logger.info(f"Round 3 丰富内容: {len(enriched_pages)} 页")
    logger.info(f"{'='*50}")

    # 显示前3页内容摘要
    for i, page in enumerate(enriched_pages[:3]):
        title = page.get('title', page.get('page_title', '(no title)'))
        body = page.get('body', page.get('content', ''))
        body_preview = body[:100] + '...' if len(str(body)) > 100 else body
        logger.info(f"  P{i+1}: {title} — {body_preview}")

asyncio.run(main())
