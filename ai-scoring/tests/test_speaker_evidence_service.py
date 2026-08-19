from app.services.speaker_evidence_service import build_speaker_evidence
from app.services.report_service import _add_personal_training_plan


def _forbidden_keys(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = "".join(character for character in key.lower() if character.isalnum())
            if normalized in {"score", "dimensions", "speakerscores", "dimensionscore"}:
                found.append(key)
            found.extend(_forbidden_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_forbidden_keys(child))
    return found


def test_groups_only_by_provider_raw_speaker_and_preserves_quotes_and_ranges():
    result = build_speaker_evidence({
        "segments": [
            {"startMs": 0, "endMs": 2000, "text": "我是算法负责人", "speaker": "SPEAKER_0"},
            {"startMs": 2100, "endMs": 4000, "text": "接下来由我继续介绍", "speaker": "SPEAKER_0"},
            {"startMs": 4100, "endMs": 6000, "text": "下面展示市场数据", "speaker": "SPEAKER_1"},
        ]
    })

    assert len(result) == 2
    assert result[0]["rawSpeakerId"] == "SPEAKER_0"
    assert result[0]["displayName"] == "1号发言人"
    assert result[0]["durationSec"] == 3.9
    assert result[0]["evidenceQuotes"] == ["我是算法负责人", "接下来由我继续介绍"]
    assert result[0]["segments"] == [
        {"startMs": 0, "endMs": 2000},
        {"startMs": 2100, "endMs": 4000},
    ]
    assert _forbidden_keys(result) == []


def test_transition_phrases_do_not_invent_people_when_provider_has_one_cluster():
    result = build_speaker_evidence({
        "segments": [
            {"start": 0, "end": 2, "text": "下面由产品经理介绍", "speaker": "SPEAKER_0"},
            {"start": 2, "end": 4, "text": "大家好我继续介绍", "speaker": "SPEAKER_0"},
        ]
    })

    assert [item["rawSpeakerId"] for item in result] == ["SPEAKER_0"]


def test_unknown_speaker_remains_unknown_without_default_score_or_identity():
    result = build_speaker_evidence({
        "segments": [
            {"start": 1, "end": 3, "text": "无法确认是谁", "speaker": None},
        ]
    })

    assert result == [{
        "rawSpeakerId": None,
        "displayName": "发言人待确认",
        "roleName": None,
        "matchedName": None,
        "status": "UNRESOLVED",
        "source": "final_asr",
        "confidence": None,
        "durationSec": 2.0,
        "evidenceQuotes": ["无法确认是谁"],
        "segments": [{"startMs": 1000, "endMs": 3000}],
    }]
    assert _forbidden_keys(result) == []


def test_display_number_is_derived_from_global_cluster_id_not_encounter_order():
    result = build_speaker_evidence({
        "segments": [
            {"start": 0, "end": 1, "text": "待确认", "speaker": None},
            {"start": 1, "end": 2, "text": "第三个簇", "speaker": "SPEAKER_2"},
            {"start": 2, "end": 3, "text": "第一个簇", "speaker": "SPEAKER_0"},
            {"start": 3, "end": 4, "text": "第二个簇", "speaker": "SPEAKER_1"},
        ]
    })

    names = {item["rawSpeakerId"]: item["displayName"] for item in result}
    assert [item["rawSpeakerId"] for item in result] == [
        "SPEAKER_0",
        "SPEAKER_1",
        "SPEAKER_2",
        None,
    ]
    assert names == {
        None: "发言人待确认",
        "SPEAKER_2": "3号发言人",
        "SPEAKER_0": "1号发言人",
        "SPEAKER_1": "2号发言人",
    }


def test_legacy_hidden_speaker_scores_can_no_longer_render_a_pdf_training_plan():
    story = []

    _add_personal_training_plan(
        story,
        {"speaker_scores": [{"speakerLabel": "S1", "dimensions": {"表达": 60}}]},
        None,
    )

    assert story == []
