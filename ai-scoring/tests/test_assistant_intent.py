from app.services.assistant.intent import detect_intent


def test_scores_only_when_mentioned():
    assert detect_intent("帮我润色开场白")["needScores"] is False
    assert detect_intent("根据最近评分完善讲稿")["needScores"] is True
    assert detect_intent("看看扣分项怎么改")["needScores"] is True


def test_rag_signals():
    assert detect_intent("结合知识库讲稿总结")["needRag"] is True
    assert detect_intent("你好", has_resources=True)["needRag"] is True
