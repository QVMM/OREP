from app.routers import scoring_router


def session():
    return {
        "session_id": "live-1",
        "meeting_id": "26",
        "transcript_protocol": "media-evidence-v2",
        "status": "recording",
    }


def test_live_finish_integration_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(
        scoring_router.settings, "UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED", False
    )
    monkeypatch.setattr(
        scoring_router,
        "get_audio_chunk_journal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    value = session()
    assert scoring_router._finalize_live_evidence_if_enabled(value) is None
    assert "evidence_status" not in value


def test_live_finish_freezes_and_saves_evidence(monkeypatch):
    value = session()
    package = {"snapshotHash": "sha256:evidence", "status": "FINAL"}
    captured = {}

    class Journal:
        def finalize(self):
            return {"status": "FINAL", "integrityStatus": "complete"}

    monkeypatch.setattr(
        scoring_router.settings, "UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED", True
    )
    monkeypatch.setattr(
        scoring_router, "get_audio_chunk_journal", lambda *_args, **_kwargs: Journal()
    )
    monkeypatch.setattr(
        scoring_router, "_read_transcript_events", lambda _sid: [{"type": "transcript"}]
    )
    monkeypatch.setattr(
        scoring_router, "_read_visual_frame_events", lambda _sid: [{"frame_id": "f1"}]
    )
    monkeypatch.setattr(
        scoring_router,
        "_read_live_camera_frame_events",
        lambda _sid: [{"frame_id": "live-f1", "frame_type": "live_camera_sample"}],
    )

    def finalize(**kwargs):
        captured["finalize"] = kwargs
        return package

    def save(upload_dir, session_id, value_to_save):
        captured["save"] = (upload_dir, session_id, value_to_save)
        return "/tmp/evidence_live_live-1.json"

    monkeypatch.setattr(scoring_router, "finalize_live_evidence", finalize)
    monkeypatch.setattr(scoring_router, "save_live_evidence_package", save)

    result = scoring_router._finalize_live_evidence_if_enabled(value)

    assert result == package
    assert captured["finalize"]["session_id"] == "live-1"
    assert [
        item["frame_id"] for item in captured["finalize"]["visual_frames"]
    ] == ["f1", "live-f1"]
    assert captured["save"] == (scoring_router.settings.UPLOAD_DIR, "live-1", package)
    assert value["evidence_status"] == "final"
    assert value["evidence_snapshot_hash"] == "sha256:evidence"
    assert value["evidence_snapshot_path"] == "/tmp/evidence_live_live-1.json"


def test_live_finish_failure_is_isolated_from_meeting_finish(monkeypatch):
    value = session()
    monkeypatch.setattr(
        scoring_router.settings, "UNIFIED_LIVE_MEDIA_GATEWAY_ENABLED", True
    )
    monkeypatch.setattr(
        scoring_router,
        "get_audio_chunk_journal",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("disk unavailable")),
    )

    assert scoring_router._finalize_live_evidence_if_enabled(value) is None
    assert value["evidence_status"] == "evidence_failed"
    assert value["evidence_error_code"] == "LIVE_EVIDENCE_FINALIZE_FAILED"
