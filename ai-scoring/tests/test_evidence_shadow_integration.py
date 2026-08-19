from app.services import pipeline_service


def _inputs():
    return {
        "meeting_id": "26",
        "asr_result": {"duration": 10, "segments": []},
        "speech_quality": {},
        "video_analysis": {"frame_count": 0, "per_frame": []},
        "fusion": {},
    }


def test_shadow_integration_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(
        pipeline_service.settings, "UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED", False
    )
    monkeypatch.setattr(
        pipeline_service,
        "build_legacy_evidence_package",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must not build")),
    )

    assert pipeline_service._write_evidence_shadow_if_enabled(**_inputs()) is None


def test_shadow_integration_builds_and_persists_when_enabled(monkeypatch):
    package = {"snapshotHash": "sha256:ok"}
    captured = {}

    def build(**kwargs):
        captured["build"] = kwargs
        return package

    def save(upload_dir, meeting_id, value):
        captured["save"] = (upload_dir, meeting_id, value)
        return "/tmp/evidence-shadow.json"

    monkeypatch.setattr(
        pipeline_service.settings, "UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED", True
    )
    monkeypatch.setattr(pipeline_service, "build_legacy_evidence_package", build)
    monkeypatch.setattr(pipeline_service, "save_shadow_package", save)

    path = pipeline_service._write_evidence_shadow_if_enabled(**_inputs())

    assert path == "/tmp/evidence-shadow.json"
    assert captured["build"]["session_id"] == "26"
    assert captured["build"]["source_type"] == "UPLOAD_VIDEO"
    assert captured["save"] == (pipeline_service.settings.UPLOAD_DIR, "26", package)


def test_shadow_failure_does_not_fail_official_pipeline(monkeypatch, caplog):
    monkeypatch.setattr(
        pipeline_service.settings, "UNIFIED_EVIDENCE_PIPELINE_SHADOW_ENABLED", True
    )
    monkeypatch.setattr(
        pipeline_service,
        "build_legacy_evidence_package",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("invalid shadow")),
    )

    assert pipeline_service._write_evidence_shadow_if_enabled(**_inputs()) is None
    assert "影子证据包生成失败" in caplog.text
