"""
Project preparation topic planning service.

Uses the configured Mimo web-search capable OpenAI-compatible endpoint and
returns a strict, source-labelled JSON contract for the Java backend.
"""
import json
import logging
import re
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


AGENT_ORDER = [
    ("topic_planner", "赵选题", "选题总策划"),
    ("policy_researcher", "李政策", "赛项与政策研究员"),
    ("industry_researcher", "张调研", "行业与用户调研员"),
    ("feasibility_analyst", "周可行", "落地可行性评估师"),
    ("chief_editor", "刘主编", "策划书主编"),
]


SYSTEM_PROMPT = """你是 OREP 选题专家团接力，服务对象是学生/教师的项目准备工作台。

你必须按以下专家顺序接力完成判断：
1. topic_planner / 赵选题 / 选题总策划：收敛选题边界，明确本轮关键判断。
2. policy_researcher / 李政策 / 赛项与政策研究员：基于赛项、政策和公开资料判断匹配度。
3. industry_researcher / 张调研 / 行业与用户调研员：补充行业趋势、用户场景和需求证据。
4. feasibility_analyst / 周可行 / 落地可行性评估师：评估团队资源、演示闭环和风险控制。
5. chief_editor / 刘主编 / 策划书主编：整合前序专家结论，形成用户可执行的方向池。

后续专家必须引用并使用前序专家的结论，不得各自独立输出互相割裂的判断。
公开网页、政策、行业案例只能作为公开信息引用，不得写成团队已经具备的事实。

你必须遵守：
1. 只能把输入 context 中出现的团队、成员、任务、材料、讲稿当作团队已具备事实。
2. 公开网页趋势、行业政策、案例只能写入 researchSummary 或 researchRefs，必须标注为公开资料，不得写成学校/团队已具备成果。
3. 不得编造学校、企业合作、获奖、设备数量、实验数据、专利、用户规模。
4. 缺少证据时写入 evidenceGaps，不要补假事实。
5. 每个方向必须包含 title、summary、tags、equipmentMatch、competitionMatch、recommendationLevel、expertRationale、scores、evidenceGaps、risks、nextTasks、researchRefs。
6. nextTasks 必须是可创建到项目团队的任务对象，至少包含 title、description、priority、stageKey。
7. 只输出 JSON，不要 Markdown，不要代码块。

JSON 结构：
{
  "accepted": true,
  "message": "简短状态",
  "assistantMessage": "给用户看的中文回复",
  "agentSteps": [
    {
      "agentKey": "topic_planner|policy_researcher|industry_researcher|feasibility_analyst|chief_editor",
      "agentName": "赵选题|李政策|张调研|周可行|刘主编",
      "agentRole": "选题总策划|赛项与政策研究员|行业与用户调研员|落地可行性评估师|策划书主编",
      "status": "COMPLETED|PARTIAL|PENDING|FAILED",
      "inputSummary": "本专家接收的输入和前序结论",
      "outputSummary": "本专家输出的核心结论",
      "findings": ["关键发现"],
      "questions": ["仍需追问的问题"],
      "sources": [
        {"title": "来源标题", "url": "URL或空", "sourceType": "PUBLIC_WEB|USER_INPUT|TEAM_MATERIAL|MODEL_INFERENCE"}
      ]
    }
  ],
  "questions": ["还需要追问的问题"],
  "researchSummary": "联网/公开资料摘要，并区分公开趋势和团队事实",
  "directions": [
    {
      "title": "方向名",
      "summary": "方向摘要",
      "tags": ["标签"],
      "equipmentMatch": "HIGH|MEDIUM|LOW|UNKNOWN",
      "competitionMatch": "HIGH|MEDIUM|LOW|UNKNOWN",
      "recommendationLevel": "STRONGLY_RECOMMENDED|RECOMMENDED|OPTIONAL|NOT_RECOMMENDED|UNKNOWN",
      "expertRationale": "引用专家团接力结论说明推荐原因",
      "scores": {
        "competitionFit": 0,
        "resourceFit": 0,
        "innovation": 0,
        "demoReadiness": 0,
        "riskControl": 0
      },
      "evidenceGaps": ["待补证据"],
      "risks": ["风险"],
      "nextTasks": [
        {"title": "任务", "description": "说明", "priority": "HIGH|MEDIUM|LOW", "stageKey": "TOPIC"}
      ],
      "researchRefs": [
        {"title": "来源标题", "url": "URL或空", "sourceType": "PUBLIC_WEB|USER_INPUT|TEAM_MATERIAL|MODEL_INFERENCE"}
      ]
    }
  ],
  "sources": [
    {"title": "来源标题", "url": "URL或空", "sourceType": "PUBLIC_WEB|USER_INPUT|TEAM_MATERIAL|MODEL_INFERENCE"}
  ],
  "nextActions": ["下一步动作"],
  "model": "模型名"
}
"""


class PrepTopicPlanningService:
    def __init__(self, client: OpenAI | None = None):
        self.client = client

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "service": "prep_topic_planning",
            "mimoWebConfigured": bool(settings.MIMO_WEB_API_KEY),
            "mimoConfigured": bool(settings.MIMO_API_KEY or settings.PPT_TEXT_API_KEY),
            "model": self._model(),
            "baseUrlConfigured": bool(settings.MIMO_WEB_BASE_URL or settings.MIMO_BASE_URL),
        }

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            client = self._client()
        except RuntimeError as exc:
            return self._error(str(exc))

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "context": payload.get("context", {}),
                        "historyMessages": payload.get("messages", []),
                        "latestUserMessage": payload.get("latestUserMessage", ""),
                    },
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ]

        try:
            response = client.chat.completions.create(
                model=self._model(),
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            data = self._parse_json(content)
            data = self._normalize(data)
            data["model"] = self._model()
            return data
        except Exception as exc:
            logger.exception("Prep topic planning failed")
            return self._error(f"Mimo 联网模型调用失败: {exc}")

    def _client(self) -> OpenAI:
        if self.client is not None:
            return self.client
        api_key = settings.MIMO_WEB_API_KEY or settings.MIMO_API_KEY or settings.PPT_TEXT_API_KEY
        if not api_key:
            raise RuntimeError("MIMO_WEB_API_KEY/MIMO_API_KEY 未配置")
        self.client = OpenAI(
            api_key=api_key,
            base_url=self._normalize_openai_base_url(settings.MIMO_WEB_BASE_URL or settings.MIMO_BASE_URL),
        )
        return self.client

    def _model(self) -> str:
        return settings.MIMO_WEB_MODEL or settings.MIMO_MODEL or settings.PPT_TEXT_MODEL

    def _normalize_openai_base_url(self, base_url: str | None) -> str | None:
        if not base_url:
            return None
        normalized = base_url.strip().rstrip("/")
        suffix = "/chat/completions"
        if normalized.lower().endswith(suffix):
            normalized = normalized[: -len(suffix)].rstrip("/")
        return normalized or None

    def _parse_json(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("模型输出不是 JSON object")
        return parsed

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        directions = data.get("directions")
        if not isinstance(directions, list):
            directions = []
        normalized_directions = [self._normalize_direction(item) for item in directions if isinstance(item, dict)]
        if not normalized_directions:
            normalized_directions = [self._fallback_direction()]
        return {
            "accepted": self._bool_value(data.get("accepted", True)),
            "message": str(data.get("message") or "已生成选题策划建议"),
            "assistantMessage": str(data.get("assistantMessage") or data.get("assistant_message") or "已基于真实团队资料生成方向池。"),
            "agentSteps": self._normalize_agent_steps(data.get("agentSteps") or data.get("agent_steps")),
            "questions": self._string_list(data.get("questions")),
            "researchSummary": str(data.get("researchSummary") or data.get("research_summary") or "暂无可确认的联网摘要。"),
            "directions": normalized_directions,
            "sources": self._dict_list(data.get("sources")),
            "nextActions": self._string_list(data.get("nextActions") or data.get("next_actions")),
        }

    def _normalize_direction(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": str(item.get("title") or "待命名方向"),
            "summary": str(item.get("summary") or "待补充方向摘要。"),
            "tags": self._string_list(item.get("tags")),
            "equipmentMatch": self._match_value(item.get("equipmentMatch") or item.get("equipment_match")),
            "competitionMatch": self._match_value(item.get("competitionMatch") or item.get("competition_match")),
            "recommendationLevel": self._recommendation_level(item.get("recommendationLevel") or item.get("recommendation_level")),
            "expertRationale": str(item.get("expertRationale") or item.get("expert_rationale") or "专家团建议补齐证据后再确认推荐级别。"),
            "scores": self._normalize_scores(item.get("scores") or item.get("directionScores") or item.get("direction_scores")),
            "evidenceGaps": self._string_list(item.get("evidenceGaps") or item.get("evidence_gaps")),
            "risks": self._string_list(item.get("risks")),
            "nextTasks": self._normalize_tasks(item.get("nextTasks") or item.get("next_tasks")),
            "researchRefs": self._normalize_refs(item.get("researchRefs") or item.get("research_refs")),
        }

    def _fallback_direction(self) -> dict[str, Any]:
        return {
            "title": "待补证据后生成方向",
            "summary": "当前真实材料不足，建议先补齐赛项要求、目标用户、设备条件和已有成果。",
            "tags": ["待补材料"],
            "equipmentMatch": "UNKNOWN",
            "competitionMatch": "UNKNOWN",
            "recommendationLevel": "UNKNOWN",
            "expertRationale": "专家团无法基于当前材料形成明确推荐，需先补齐基础证据。",
            "scores": self._normalize_scores(None),
            "evidenceGaps": ["赛项类别", "学校/团队已有设备", "目标用户或场景", "已有成果"],
            "risks": ["材料不足时无法判断赛项匹配度"],
            "nextTasks": [
                {
                    "title": "补充选题基础材料",
                    "description": "上传赛项规则、团队已有设备和初步调研材料。",
                    "priority": "HIGH",
                    "stageKey": "TOPIC",
                }
            ],
            "researchRefs": [],
        }

    def _normalize_agent_steps(self, value: Any) -> list[dict[str, Any]]:
        items = self._dict_list(value)
        if not items:
            return [
                {
                    "agentKey": key,
                    "agentName": name,
                    "agentRole": role,
                    "status": "PENDING",
                    "inputSummary": "等待本轮选题输入。",
                    "outputSummary": "尚未形成专家判断。",
                    "findings": [],
                    "questions": [],
                    "sources": [],
                }
                for key, name, role in AGENT_ORDER
            ]

        normalized = []
        for index, item in enumerate(items):
            default_key, default_name, default_role = AGENT_ORDER[min(index, len(AGENT_ORDER) - 1)]
            normalized.append(
                {
                    "agentKey": str(item.get("agentKey") or item.get("agent_key") or default_key),
                    "agentName": str(item.get("agentName") or item.get("agent_name") or default_name),
                    "agentRole": str(item.get("agentRole") or item.get("agent_role") or default_role),
                    "status": self._agent_status(item.get("status")),
                    "inputSummary": str(item.get("inputSummary") or item.get("input_summary") or "接收上一位专家结论。"),
                    "outputSummary": str(item.get("outputSummary") or item.get("output_summary") or "已完成本角色判断。"),
                    "findings": self._string_list(item.get("findings")),
                    "questions": self._string_list(item.get("questions")),
                    "sources": self._normalize_refs(item.get("sources")),
                }
            )
        return normalized

    def _agent_status(self, value: Any) -> str:
        normalized = str(value or "PENDING").upper()
        return normalized if normalized in {"COMPLETED", "PARTIAL", "PENDING", "FAILED"} else "PENDING"

    def _score_value(self, value: Any) -> int:
        try:
            score = int(float(value))
        except (TypeError, ValueError):
            return 0
        return max(0, min(10, score))

    def _normalize_scores(self, value: Any) -> dict[str, int]:
        scores = value if isinstance(value, dict) else {}
        return {
            "competitionFit": self._score_value(self._alias_value(scores, "competitionFit", "competition_fit")),
            "resourceFit": self._score_value(self._alias_value(scores, "resourceFit", "resource_fit")),
            "innovation": self._score_value(scores.get("innovation")),
            "demoReadiness": self._score_value(self._alias_value(scores, "demoReadiness", "demo_readiness")),
            "riskControl": self._score_value(self._alias_value(scores, "riskControl", "risk_control")),
        }

    def _alias_value(self, data: dict[str, Any], primary_key: str, fallback_key: str) -> Any:
        if primary_key in data:
            return data[primary_key]
        return data.get(fallback_key)

    def _bool_value(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"false", "no", "0", "rejected"}:
                return False
            if normalized in {"true", "yes", "1", "accepted"}:
                return True
            return True
        return bool(value) if value is not None else True

    def _recommendation_level(self, value: Any) -> str:
        normalized = str(value or "UNKNOWN").upper()
        allowed = {"STRONGLY_RECOMMENDED", "RECOMMENDED", "OPTIONAL", "NOT_RECOMMENDED", "UNKNOWN"}
        return normalized if normalized in allowed else "UNKNOWN"

    def _normalize_tasks(self, value: Any) -> list[dict[str, Any]]:
        tasks = self._dict_list(value)
        normalized = []
        for task in tasks:
            normalized.append(
                {
                    "title": str(task.get("title") or task.get("name") or "补充选题任务"),
                    "description": str(task.get("description") or task.get("detail") or ""),
                    "priority": self._priority(task.get("priority")),
                    "stageKey": str(task.get("stageKey") or task.get("stage_key") or "TOPIC"),
                }
            )
        return normalized

    def _normalize_refs(self, value: Any) -> list[dict[str, Any]]:
        refs = []
        for ref in self._dict_list(value):
            refs.append(
                {
                    "title": str(ref.get("title") or ref.get("name") or "公开资料"),
                    "url": str(ref.get("url") or ""),
                    "sourceType": str(ref.get("sourceType") or ref.get("source_type") or "PUBLIC_WEB"),
                }
            )
        return refs

    def _match_value(self, value: Any) -> str:
        normalized = str(value or "UNKNOWN").upper()
        return normalized if normalized in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"} else "UNKNOWN"

    def _priority(self, value: Any) -> str:
        normalized = str(value or "MEDIUM").upper()
        return normalized if normalized in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if item is not None and str(item).strip()]

    def _dict_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "accepted": False,
            "message": message,
            "assistantMessage": message,
            "agentSteps": [],
            "questions": [],
            "researchSummary": "",
            "directions": [],
            "sources": [],
            "nextActions": ["检查 Mimo 联网模型配置后重试"],
            "model": self._model(),
        }
