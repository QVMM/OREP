from app.services.prep_topic_planning_service import PrepTopicPlanningService


class _Message:
    content = """
    {
      "accepted": true,
      "message": "ok",
      "assistantMessage": "已基于团队真实材料生成方向。",
      "questions": ["赛项类别是什么？"],
      "researchSummary": "公开资料显示农业节能是趋势；团队事实仅限已上传材料。",
      "directions": [
        {
          "title": "温室能耗诊断",
          "summary": "基于已有传感器材料分析能耗异常。",
          "tags": ["农业", "节能"],
          "equipmentMatch": "HIGH",
          "competitionMatch": "MEDIUM",
          "evidenceGaps": ["补充历史能耗数据"],
          "risks": ["数据周期不足"],
          "nextTasks": [{"title": "整理传感器字段", "description": "列出字段和采样频率", "priority": "HIGH", "stageKey": "TOPIC"}],
          "researchRefs": [{"title": "农业节能公开趋势", "url": "https://example.com", "sourceType": "PUBLIC_WEB"}]
        }
      ],
      "sources": [{"title": "用户补充", "sourceType": "USER_INPUT"}],
      "nextActions": ["采纳方向"]
    }
    """


class _Choice:
    message = _Message()


class _Response:
    choices = [_Choice()]


class _Completions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _Response()


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class _FakeClient:
    def __init__(self):
        self.chat = _Chat()


def test_analyze_normalizes_mimo_json_contract():
    fake_client = _FakeClient()
    service = PrepTopicPlanningService(client=fake_client)

    result = service.analyze(
        {
            "context": {"team": {"name": "真实团队"}, "materials": []},
            "messages": [{"role": "USER", "content": "我们有传感器"}],
            "latestUserMessage": "我们有传感器",
        }
    )

    assert result["accepted"] is True
    assert result["assistantMessage"].startswith("已基于团队真实材料")
    assert result["directions"][0]["title"] == "温室能耗诊断"
    assert result["directions"][0]["nextTasks"][0]["stageKey"] == "TOPIC"
    assert result["directions"][0]["researchRefs"][0]["sourceType"] == "PUBLIC_WEB"
    assert fake_client.chat.completions.last_kwargs["response_format"] == {"type": "json_object"}


def test_analyze_normalizes_agent_steps_and_direction_scores():
    class _MessageWithAgents:
        content = """
        {
          "accepted": true,
          "message": "ok",
          "assistantMessage": "专家团已完成本轮判断。",
          "agentSteps": [
            {
              "agentKey": "topic_planner",
              "agentName": "赵选题",
              "agentRole": "选题总策划",
              "status": "COMPLETED",
              "inputSummary": "用户希望做温室选题。",
              "outputSummary": "建议收窄到温室诊断。",
              "findings": ["边界清晰"],
              "questions": ["是否有传感器数据？"],
              "sources": [{"title": "用户补充", "sourceType": "USER_INPUT"}]
            }
          ],
          "directions": [
            {
              "title": "温室诊断",
              "summary": "基于真实材料做温室环境诊断。",
              "scores": {"competitionFit": 8, "resourceFit": 7, "innovation": 6, "demoReadiness": 8, "riskControl": 6},
              "recommendationLevel": "RECOMMENDED",
              "expertRationale": "赵选题和周可行均建议优先推进。"
            }
          ]
        }
        """

    class _ChoiceWithAgents:
        message = _MessageWithAgents()

    class _ResponseWithAgents:
        choices = [_ChoiceWithAgents()]

    class _CompletionsWithAgents:
        def create(self, **kwargs):
            return _ResponseWithAgents()

    class _ChatWithAgents:
        completions = _CompletionsWithAgents()

    class _ClientWithAgents:
        chat = _ChatWithAgents()

    service = PrepTopicPlanningService(client=_ClientWithAgents())
    result = service.analyze({"context": {"team": {"name": "真实团队"}}, "latestUserMessage": "做温室"})

    assert result["agentSteps"][0]["agentKey"] == "topic_planner"
    assert result["agentSteps"][0]["agentName"] == "赵选题"
    assert result["agentSteps"][0]["status"] == "COMPLETED"
    assert result["directions"][0]["scores"]["competitionFit"] == 8
    assert result["directions"][0]["recommendationLevel"] == "RECOMMENDED"


def test_normalize_scores_keeps_zero_when_camel_case_key_exists():
    service = PrepTopicPlanningService(client=None)

    result = service._normalize_scores(
        {
            "competitionFit": 0,
            "competition_fit": 9,
            "resourceFit": 0,
            "resource_fit": 8,
            "innovation": 0,
            "demoReadiness": 0,
            "demo_readiness": 7,
            "riskControl": 0,
            "risk_control": 6,
        }
    )

    assert result == {
        "competitionFit": 0,
        "resourceFit": 0,
        "innovation": 0,
        "demoReadiness": 0,
        "riskControl": 0,
    }


def test_normalize_parses_accepted_string_values_safely():
    service = PrepTopicPlanningService(client=None)

    assert service._normalize({"accepted": "false", "directions": []})["accepted"] is False
    assert service._normalize({"accepted": "no", "directions": []})["accepted"] is False
    assert service._normalize({"accepted": "0", "directions": []})["accepted"] is False
    assert service._normalize({"accepted": "rejected", "directions": []})["accepted"] is False
    assert service._normalize({"accepted": "true", "directions": []})["accepted"] is True
    assert service._normalize({"accepted": "yes", "directions": []})["accepted"] is True
    assert service._normalize({"accepted": "1", "directions": []})["accepted"] is True
    assert service._normalize({"accepted": "accepted", "directions": []})["accepted"] is True
    assert service._normalize({"accepted": "unexpected", "directions": []})["accepted"] is True


def test_analyze_returns_structured_error_when_client_creation_fails(monkeypatch):
    service = PrepTopicPlanningService(client=None)
    monkeypatch.setattr("app.services.prep_topic_planning_service.settings.MIMO_WEB_API_KEY", "")
    monkeypatch.setattr("app.services.prep_topic_planning_service.settings.MIMO_API_KEY", "")
    monkeypatch.setattr("app.services.prep_topic_planning_service.settings.PPT_TEXT_API_KEY", "")

    result = service.analyze({"context": {}})

    assert result["accepted"] is False
    assert "未配置" in result["message"]
    assert result["directions"] == []
