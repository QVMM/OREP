import json
from pathlib import Path

from app.config import settings
from app.services.media_evidence.speaker_attribution_recompute import (
    SpeakerAttributionRecomputeError,
    recompute_final_speaker_attribution,
)


def _write_result(tmp_path: Path, session_id: str, payload: dict, monkeypatch) -> None:
    upload = tmp_path / "uploads"
    upload.mkdir(parents=True, exist_ok=True)
    results = upload / "results"
    results.mkdir(parents=True, exist_ok=True)
    (results / f"result_{session_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload))


def test_recompute_promotes_main_speaker_from_asr_clusters(tmp_path, monkeypatch):
    session_id = "901"
    # 90s media, main SPEAKER_0 for 60s, brief SPEAKER_1 with external phrase
    segments = []
    for i in range(6):
        segments.append(
            {
                "text": "我们团队的参赛方案是智慧温室环境监控系统，下面汇报核心指标。",
                "start": i * 10.0,
                "end": (i + 1) * 10.0,
                "speaker": "SPEAKER_0",
                "sourceClusterId": "SPEAKER_0",
            }
        )
    segments.append(
        {
            "text": "请先停一下",
            "start": 70.0,
            "end": 72.0,
            "speaker": "SPEAKER_1",
            "sourceClusterId": "SPEAKER_1",
        }
    )
    _write_result(
        tmp_path,
        session_id,
        {
            "meeting_id": session_id,
            "status": "completed",
            "project_info": {"team_size": 4},
            "asr": {
                "duration": 90.0,
                "source": "fun_asr",
                "segments": segments,
            },
        },
        monkeypatch,
    )

    receipt = recompute_final_speaker_attribution(session_id)
    snapshot = receipt["snapshot"]

    assert receipt["revision"] == 1
    assert snapshot["status"] == "FINAL"
    people = snapshot["people"]
    contestants = [p for p in people if p["personType"] == "CONTESTANT"]
    assert len(contestants) >= 1
    assert contestants[0]["displayName"] == "1号选手"
    # External short side speaker should not steal contestant slot as default
    visitors = [p for p in people if p["personType"] == "VISITOR"]
    assert visitors, "short external-like side speaker should stay VISITOR"
    # Local result file updated for next recompute
    result_path = Path(settings.UPLOAD_DIR) / "results" / f"result_{session_id}.json"
    stored = json.loads(result_path.read_text(encoding="utf-8"))
    assert stored["asr"]["speakerAttribution"]["revision"] == 1

    # Second click bumps revision
    receipt2 = recompute_final_speaker_attribution(session_id)
    assert receipt2["revision"] == 2


def test_recompute_requires_evidence(tmp_path, monkeypatch):
    upload = tmp_path / "uploads"
    upload.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload))
    try:
        recompute_final_speaker_attribution("missing-session")
        assert False, "expected SpeakerAttributionRecomputeError"
    except SpeakerAttributionRecomputeError as exc:
        assert exc.code == "NO_ASR_EVIDENCE"
