from app.services.media_evidence.final_speaker_attribution import (
    build_final_speaker_attribution,
)


def _provider(turns):
    return {
        "contractVersion": "3d-speaker-local-v1",
        "provider": "local_3d_speaker",
        "status": "completed",
        "turns": turns,
        "diagnostics": {},
    }


def _turn(start, end, speaker):
    return {
        "startMs": start,
        "endMs": end,
        "rawSpeakerId": speaker,
        "sourceClusterId": speaker,
        "speakerVerification": "JOINT_AUDIO_VISUAL",
    }


def _asr(segments):
    return {"source": "fun_asr", "segments": segments}


def test_explicit_introductions_bind_four_joint_clusters_to_four_contestants():
    turns = [_turn(index * 1000, (index + 1) * 1000, f"3DSPK_{index}")
             for index in range(4)]
    asr = _asr([
        {"startMs": 0, "endMs": 1000, "text": "大家好，我是一号选手"},
        {"startMs": 1000, "endMs": 2000, "text": "我是二号选手"},
        {"startMs": 2000, "endMs": 3000, "text": "我是三号选手"},
        {"startMs": 3000, "endMs": 4000, "text": "我是四号选手"},
    ])

    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=4000,
        revision=3,
        asr_result=asr,
        three_d_speaker_result=_provider(turns),
        contestant_slots=4,
    )

    assert snapshot["revision"] == 3
    assert snapshot["status"] == "FINAL"
    assert [person["displayName"] for person in snapshot["people"]] == [
        "1号选手", "2号选手", "3号选手", "4号选手"
    ]
    assert [person["voiceClusterIds"] for person in snapshot["people"]] == [
        ["3DSPK_0"], ["3DSPK_1"], ["3DSPK_2"], ["3DSPK_3"]
    ]
    assert all(item["speakerState"] == "CONFIRMED" for item in snapshot["segments"])
    assert snapshot["diagnostics"]["anchoredContestantCount"] == 4


def test_unanchored_extra_cluster_with_external_phrase_stays_visitor():
    """Intro binds A; short external line on B must not become a second contestant."""
    turns = [
        _turn(0, 1000, "3DSPK_A"),
        _turn(1000, 2000, "3DSPK_B"),
    ]
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=2000,
        revision=2,
        asr_result=_asr([
            {"startMs": 0, "endMs": 1000, "text": "我是一号选手"},
            {"startMs": 1000, "endMs": 2000, "text": "请先停一下"},
        ]),
        three_d_speaker_result=_provider(turns),
        contestant_slots=4,
    )

    assert len(snapshot["people"]) == 2
    assert snapshot["people"][0]["personType"] == "CONTESTANT"
    assert snapshot["people"][0]["contestantSlot"] == 1
    assert snapshot["people"][1]["personType"] == "VISITOR"
    assert snapshot["people"][1]["contestantSlot"] is None
    assert snapshot["people"][1]["displayName"] is None
    assert snapshot["segments"][1]["speakerState"] == "PROVISIONAL"
    assert snapshot["diagnostics"]["visitorPersonCount"] == 1


def test_main_speaker_without_number_intro_becomes_contestant_by_airtime():
    """路演主讲不报号：按时长自动成为 1 号选手，不再默认外部人员。"""
    # 90s media, main speaker 60s continuous
    turns = [
        _turn(0, 60_000, "3DSPK_MAIN"),
        _turn(70_000, 72_000, "3DSPK_SIDE"),
    ]
    asr = _asr([
        {
            "startMs": 0,
            "endMs": 60_000,
            "text": "尊敬的各位评委老师好，我们团队带来的参赛作品是智慧温室管理系统。"
                    "我是本项目的嵌入式工程师，接下来由我介绍系统架构。",
        },
        {"startMs": 70_000, "endMs": 72_000, "text": "请问功耗怎么测？"},
    ])
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=90_000,
        revision=1,
        asr_result=asr,
        three_d_speaker_result=_provider(turns),
        contestant_slots=4,
    )

    by_cluster = {
        person["voiceClusterIds"][0]: person for person in snapshot["people"]
    }
    assert by_cluster["3DSPK_MAIN"]["personType"] == "CONTESTANT"
    assert by_cluster["3DSPK_MAIN"]["contestantSlot"] == 1
    assert by_cluster["3DSPK_MAIN"]["displayName"] == "1号选手"
    # short Q-like side speaker → visitor (external)
    assert by_cluster["3DSPK_SIDE"]["personType"] == "VISITOR"
    assert snapshot["diagnostics"]["durationPromotedCount"] >= 1
    assert snapshot["diagnostics"]["anchoredContestantCount"] >= 1


def test_ambiguous_half_and_half_segment_stays_unknown_with_candidates():
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=1000,
        revision=1,
        asr_result=_asr([
            {"startMs": 0, "endMs": 1000, "text": "这段跨越两个人"},
        ]),
        three_d_speaker_result=_provider([
            _turn(0, 500, "3DSPK_A"),
            _turn(500, 1000, "3DSPK_B"),
        ]),
        contestant_slots=4,
    )

    segment = snapshot["segments"][0]
    assert segment["personId"] is None
    assert segment["speakerState"] == "UNKNOWN"
    assert len(segment["candidatePersonIds"]) == 2
    assert snapshot["diagnostics"]["unknownSegmentCount"] == 1


def test_dominant_overlap_assigns_segment_but_reports_derived_confidence():
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=1000,
        revision=1,
        asr_result=_asr([
            {"startMs": 0, "endMs": 1000, "text": "主要是同一人发言"},
        ]),
        three_d_speaker_result=_provider([
            _turn(0, 800, "3DSPK_A"),
            _turn(800, 1000, "3DSPK_B"),
        ]),
        contestant_slots=4,
    )

    segment = snapshot["segments"][0]
    assert segment["personId"] is not None
    assert segment["speakerState"] in {"CONFIRMED", "PROVISIONAL"}
    assert segment["speakerConfidence"] == 0.8
    assert snapshot["diagnostics"]["transcriptCoverageRatio"] == 1.0
    # main airtime cluster should be promoted to contestant
    main = next(p for p in snapshot["people"] if p["voiceClusterIds"] == ["3DSPK_A"])
    assert main["personType"] == "CONTESTANT"


def test_conflicting_introduction_falls_back_to_duration_contestant():
    """同一声纹簇内两段不同报号：P1 用 intro 时间线拆成两位选手，而不是全归外部。"""
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=2000,
        revision=1,
        asr_result=_asr([
            {"startMs": 0, "endMs": 1000, "text": "我是一号选手"},
            {"startMs": 1000, "endMs": 2000, "text": "我是二号选手"},
        ]),
        three_d_speaker_result=_provider([
            _turn(0, 2000, "3DSPK_A"),
        ]),
        contestant_slots=4,
    )

    contestants = [p for p in snapshot["people"] if p["personType"] == "CONTESTANT"]
    assert len(contestants) >= 2
    slots = sorted(p["contestantSlot"] for p in contestants)
    assert slots[:2] == [1, 2]
    assert snapshot["diagnostics"]["introTimelineMode"] is True
    # 两段转写应分别落到 1/2 号
    by_start = {s["startMs"]: s for s in snapshot["segments"]}
    assert by_start[0]["personId"] != by_start[1000]["personId"]


def test_missing_joint_turns_preserves_transcript_as_unknown():
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=1000,
        revision=5,
        asr_result=_asr([
            {"startMs": 0, "endMs": 1000, "text": "转写不能丢"},
        ]),
        three_d_speaker_result=_provider([]),
        contestant_slots=4,
    )

    assert snapshot["people"] == []
    assert snapshot["turns"] == []
    assert snapshot["segments"][0]["speakerState"] == "UNKNOWN"
    assert snapshot["segments"][0]["isFinal"] is True
    assert snapshot["status"] == "FINAL"


def test_collapsed_diarization_splits_four_intros_into_four_contestants():
    """真实失败模式：整场只有 SPEAKER_0，但转写里有四人报号。"""
    turns = [_turn(0, 120_000, "SPEAKER_0")]
    asr = _asr([
        {
            "startMs": 10_000,
            "endMs": 25_000,
            "text": "我是医药选手，是物联网应用开发工程师，负责环境检测和预警模块。",
        },
        {
            "startMs": 30_000,
            "endMs": 45_000,
            "text": "我是二号选手，是物联网应用开发工程师，负责智能排风模块。",
        },
        {
            "startMs": 50_000,
            "endMs": 65_000,
            "text": "我是三号选手，是 AI 法工程师，负责 AI 问答模块。",
        },
        {
            "startMs": 70_000,
            "endMs": 90_000,
            "text": "我是四号选手，是本项目的项目经理，同时兼任测试工程师。",
        },
        {
            "startMs": 100_000,
            "endMs": 102_000,
            "text": "请问功耗怎么测？",
        },
    ])
    snapshot = build_final_speaker_attribution(
        session_id="roadshow",
        duration_ms=120_000,
        revision=1,
        asr_result=asr,
        three_d_speaker_result=_provider(turns),
        contestant_slots=4,
    )
    contestants = [p for p in snapshot["people"] if p["personType"] == "CONTESTANT"]
    assert len(contestants) == 4
    assert sorted(p["contestantSlot"] for p in contestants) == [1, 2, 3, 4]
    assert snapshot["diagnostics"]["introTimelineMode"] is True
    # 各段应落到不同选手（评委提问段可为 visitor/unknown）
    person_ids = {
        s["personId"]
        for s in snapshot["segments"]
        if s["startMs"] < 95_000 and s["personId"]
    }
    assert len(person_ids) == 4


def test_multi_intro_in_one_asr_line_is_split():
    """一行 ASR 里挤进 1 号+2 号时，拆成两段转写。"""
    snapshot = build_final_speaker_attribution(
        session_id="26",
        duration_ms=20_000,
        revision=1,
        asr_result=_asr([
            {
                "startMs": 0,
                "endMs": 20_000,
                "text": "各位评委老师好，我是一号选手，在本项目中担任视觉营销师。"
                        "我是二号选手，主要在本项目中担任内容营销师。",
            },
        ]),
        three_d_speaker_result=_provider([_turn(0, 20_000, "SPEAKER_0")]),
        contestant_slots=4,
    )
    assert snapshot["diagnostics"]["multiIntroSegmentSplitCount"] >= 1
    contestants = [p for p in snapshot["people"] if p["personType"] == "CONTESTANT"]
    assert len(contestants) >= 2
    assert len(snapshot["segments"]) >= 2
    slots_hit = set()
    for person in contestants:
        slots_hit.add(person["contestantSlot"])
    assert 1 in slots_hit and 2 in slots_hit
