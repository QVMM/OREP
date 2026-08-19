from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "setup_3d_speaker_runtime.sh"


def test_setup_is_pinned_hash_verified_and_local_only():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "065629c313eaf1a01c65c640c46d77e61e9607b4" in text
    assert "68bbbaa1023629ab4967c735c133ec2d440d94941cdcb4e0d9c9cd2ab0c83c0d" in text
    assert "b020ff7104cad71e14a51c7cedfa614ded2de7befe5c73f88c50792a2933783c" in text
    assert "4d0e02b72f987989b5fe0447745521e16067b10777b66a1fb89362fb1ca08183" in text
    assert "1695521d026730358b7304a35542a86dad2aa4cad4f8bc25043975f4b6f679fb" in text
    assert "92f29b94e6948786a26778c9e302525d185bb08c8b9f5252ed98776902840199" in text
    assert "uv venv --python 3.11" in text
    assert "Darwin" in text and "Linux" in text
    assert "--health-check" in text
    assert "Apache-2.0" in text
    lowered = text.lower()
    assert "oss://" not in lowered
    assert "minio" not in lowered
    assert "s3://" not in lowered


def test_setup_uses_an_isolated_runtime_and_offline_inference_cache():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "models/3d-speaker/runtime" in text
    assert "MODELSCOPE_CACHE" in text
    assert "MODELSCOPE_OFFLINE" in text
    assert "THREED_SPEAKER_CAMPPLUS" in text
    assert "THREED_SPEAKER_VAD_MODEL" in text
    assert "torchrun --standalone --nnodes=1" in text
