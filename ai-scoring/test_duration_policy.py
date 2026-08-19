from app.services.pipeline_service import determine_duration_adjustment


def test_duration_policy_caps_below_35_minutes_only():
    assert determine_duration_adjustment(34 * 60 + 59)["score_cap"] == 35
    assert determine_duration_adjustment(35 * 60)["score_cap"] is None
    assert determine_duration_adjustment(2345.576917)["score_cap"] is None


def test_duration_policy_keeps_short_video_rules():
    assert determine_duration_adjustment(599)["skip_llm"] is True
    assert determine_duration_adjustment(10 * 60)["score_cap"] == 20
    assert determine_duration_adjustment(29 * 60 + 59)["score_cap"] == 20
