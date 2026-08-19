from app.services.media_evidence.transcript_attributor import attribute_transcript


def test_assigns_one_asr_segment_to_one_confirmed_person():
    result = attribute_transcript(
        {"segments": [{"startMs": 0, "endMs": 2000, "text": "项目开始"}]},
        [
            {
                "turnId": "TURN_1",
                "startMs": 0,
                "endMs": 2000,
                "personId": "PERSON_1",
                "speakerState": "CONFIRMED",
                "confidence": 0.92,
            }
        ],
        revision=1,
        is_final=True,
    )

    assert result[0]["personId"] == "PERSON_1"
    assert result[0]["speakerState"] == "CONFIRMED"
    assert result[0]["text"] == "项目开始"


def test_word_timestamps_split_contestant_and_visitor_at_the_real_boundary():
    result = attribute_transcript(
        {
            "segments": [
                {
                    "startMs": 0,
                    "endMs": 3000,
                    "text": "我们开始 请暂停一下",
                    "words": [
                        {"startMs": 0, "endMs": 700, "text": "我们"},
                        {"startMs": 700, "endMs": 1400, "text": "开始"},
                        {"startMs": 1600, "endMs": 2200, "text": "请暂停"},
                        {"startMs": 2200, "endMs": 3000, "text": "一下"},
                    ],
                }
            ]
        },
        [
            {"turnId": "T1", "startMs": 0, "endMs": 1500, "personId": "PERSON_1",
             "speakerState": "CONFIRMED", "confidence": 0.9},
            {"turnId": "T2", "startMs": 1500, "endMs": 3000, "personId": "PERSON_5",
             "speakerState": "CONFIRMED", "confidence": 0.93},
        ],
        revision=2,
        is_final=True,
    )

    assert [(item["personId"], item["text"]) for item in result] == [
        ("PERSON_1", "我们开始"),
        ("PERSON_5", "请暂停一下"),
    ]
    assert all(item["revision"] == 2 and item["isFinal"] for item in result)


def test_unknown_turn_preserves_text_without_nearest_contestant_assignment():
    result = attribute_transcript(
        {"segments": [{"startMs": 0, "endMs": 1000, "text": "听不清是谁"}]},
        [
            {"turnId": "T1", "startMs": 0, "endMs": 1000, "personId": None,
             "speakerState": "UNKNOWN", "confidence": 0.3}
        ],
        revision=1,
        is_final=False,
    )

    assert result[0]["personId"] is None
    assert result[0]["speakerState"] == "UNKNOWN"
    assert result[0]["text"] == "听不清是谁"


def test_overlap_preserves_candidates_and_does_not_choose_one():
    result = attribute_transcript(
        {"segments": [{"startMs": 0, "endMs": 1000, "text": "同时说话"}]},
        [
            {"turnId": "T1", "startMs": 0, "endMs": 1000, "personId": None,
             "speakerState": "OVERLAP", "confidence": 0.8,
             "candidatePersonIds": ["PERSON_2", "PERSON_1"]}
        ],
        revision=1,
        is_final=True,
    )

    assert result[0]["personId"] is None
    assert result[0]["speakerState"] == "OVERLAP"
    assert result[0]["candidatePersonIds"] == ["PERSON_1", "PERSON_2"]


def test_output_is_deterministic_for_the_same_inputs():
    asr = {"segments": [{"start": 1.0, "end": 2.0, "text": "稳定输出"}]}
    turns = [{"turnId": "T1", "startMs": 1000, "endMs": 2000,
              "personId": "PERSON_1", "speakerState": "CONFIRMED", "confidence": 0.9}]

    first = attribute_transcript(asr, turns, revision=3, is_final=True)
    second = attribute_transcript(asr, turns, revision=3, is_final=True)

    assert first == second
    assert first[0]["segmentId"] == "SEG_1"
