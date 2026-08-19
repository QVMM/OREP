from pathlib import Path


def test_setup_uses_verified_git_lfs_object_and_loads_face_models_before_ready():
    project_root = Path(__file__).resolve().parents[1]
    script = (project_root / "scripts" / "setup_lr_asd_runtime.sh").read_text(
        encoding="utf-8"
    )

    assert (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
        "models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ) in script
    assert "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79" in script
    assert "FaceDetectorYN.create" in script
    assert "FaceRecognizerSF.create" in script
