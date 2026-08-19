#!/usr/bin/env bash
# Reproducible local-only 3D-Speaker runtime. Upstream and model artifacts are Apache-2.0.
set -euo pipefail

UPSTREAM_COMMIT="065629c313eaf1a01c65c640c46d77e61e9607b4"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME="${LOCAL_3D_SPEAKER_RUNTIME_DIR:-$ROOT/models/3d-speaker/runtime}"
REPOSITORY="$RUNTIME/repository"
VENV="$RUNTIME/.venv"
PYTHON="$VENV/bin/python"
MODELS="$RUNTIME/models"
ONNX="$MODELS/onnx"
MODELSCOPE_CACHE="$MODELS/modelscope-cache"

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) echo "unsupported_platform: use Linux/WSL2 or Docker on Windows" >&2; exit 2 ;;
esac
command -v uv >/dev/null || { echo "uv_required" >&2; exit 2; }
command -v git >/dev/null || { echo "git_required" >&2; exit 2; }
command -v curl >/dev/null || { echo "curl_required" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg_required" >&2; exit 2; }

mkdir -p "$RUNTIME" "$ONNX" "$MODELSCOPE_CACHE" "$RUNTIME/licenses"
if [[ ! -d "$REPOSITORY/.git" ]]; then
  git clone --filter=blob:none --no-checkout https://github.com/modelscope/3D-Speaker.git "$REPOSITORY"
fi
git -C "$REPOSITORY" fetch --depth 1 origin "$UPSTREAM_COMMIT"
git -C "$REPOSITORY" checkout --detach --force "$UPSTREAM_COMMIT"
test "$(git -C "$REPOSITORY" rev-parse HEAD)" = "$UPSTREAM_COMMIT"
cp "$REPOSITORY/LICENSE" "$RUNTIME/licenses/3D-Speaker-Apache-2.0.txt"

if [[ ! -x "$PYTHON" ]]; then
  uv venv --python 3.11 "$VENV"
else
  # Keep the literal command in the manifest for reproducibility: uv venv --python 3.11
  "$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11)'
fi
uv pip install --python "$PYTHON" \
  "torch==2.3.1" "torchaudio==2.3.1" \
  "numpy==1.26.4" "scipy==1.12.0" "scikit-learn==1.4.2" \
  "soundfile==0.12.1" "kaldiio==2.18.0" "pyyaml==6.0.2" \
  "matplotlib==3.8.4" "pandas==2.2.2" "openpyxl==3.1.5" "tqdm==4.66.4" \
  "onnxruntime==1.18.1" "opencv-python-headless==4.10.0.84" \
  "modelscope==1.17.1" "funasr==1.1.6" "datasets==2.20.0" \
  "transformers==4.41.2" "python-speech-features==0.6" \
  "addict==2.4.0" "simplejson==3.19.2" "sortedcontainers==2.4.0" \
  "setuptools==70.3.0" "wheel==0.43.0" "fastcluster==1.2.6" \
  "umap-learn==0.5.6" "hdbscan==0.8.40"

download_verified() {
  local url="$1"
  local destination="$2"
  local expected="$3"
  local actual=""
  if [[ -f "$destination" ]]; then
    actual="$(openssl dgst -sha256 "$destination" | awk '{print $NF}')"
  fi
  if [[ "$actual" != "$expected" ]]; then
    rm -f "$destination.tmp"
    curl --fail --location --retry 4 --retry-delay 2 --output "$destination.tmp" "$url"
    actual="$(openssl dgst -sha256 "$destination.tmp" | awk '{print $NF}')"
    [[ "$actual" = "$expected" ]] || { echo "model_hash_mismatch:$destination" >&2; exit 3; }
    mv "$destination.tmp" "$destination"
  fi
}

MODEL_BASE="https://modelscope.cn/models/iic/speech_campplus_speaker-diarization_common/resolve/master/onnx"
download_verified "$MODEL_BASE/version-RFB-320.onnx" "$ONNX/version-RFB-320.onnx" "68bbbaa1023629ab4967c735c133ec2d440d94941cdcb4e0d9c9cd2ab0c83c0d"
download_verified "$MODEL_BASE/asd.onnx" "$ONNX/asd.onnx" "b020ff7104cad71e14a51c7cedfa614ded2de7befe5c73f88c50792a2933783c"
download_verified "$MODEL_BASE/fqa.onnx" "$ONNX/fqa.onnx" "4d0e02b72f987989b5fe0447745521e16067b10777b66a1fb89362fb1ca08183"
download_verified "$MODEL_BASE/face_recog_ir101.onnx" "$ONNX/face_recog_ir101.onnx" "1695521d026730358b7304a35542a86dad2aa4cad4f8bc25043975f4b6f679fb"
download_verified \
  "https://modelscope.cn/models/iic/speech_campplus_sv_zh_en_16k-common_advanced/resolve/v1.0.0/campplus_cn_en_common.pt" \
  "$MODELS/campplus_cn_en_common.pt" \
  "92f29b94e6948786a26778c9e302525d185bb08c8b9f5252ed98776902840199"

export MODELSCOPE_CACHE
export MODELSCOPE_OFFLINE=0
"$PYTHON" - "$MODELS/vad" <<'PY'
from pathlib import Path
import shutil
import sys
from modelscope.hub.snapshot_download import snapshot_download

target = Path(sys.argv[1])
source = Path(snapshot_download(
    "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    revision="v2.0.4",
))
target.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, dirs_exist_ok=True)
PY

# The official recipe normally resolves VAD and CAM++ at job time. Patch only
# those two boundaries to deterministic local artifacts; inference code remains pinned upstream.
"$PYTHON" - "$REPOSITORY" <<'PY'
from pathlib import Path
import sys

repo = Path(sys.argv[1])
recipe = repo / "egs/3dspeaker/speaker-diarization"
path_sh = recipe / "path.sh"
text = path_sh.read_text(encoding="utf-8")
old = "export OMP_NUM_THREADS=1"
new = "export OMP_NUM_THREADS=${THREED_SPEAKER_OMP_NUM_THREADS:-1}"
if old not in text and new not in text:
    raise SystemExit("upstream_thread_patch_context_changed")
path_sh.write_text(text.replace(old, new), encoding="utf-8")

audio = recipe / "run_audio.sh"
text = audio.read_text(encoding="utf-8")
old = "--model_id $speaker_model_id --conf $conf_file \\\n          --subseg_json"
new = "--pretrained_model $THREED_SPEAKER_CAMPPLUS --conf $conf_file \\\n          --subseg_json"
if old not in text and new not in text:
    raise SystemExit("upstream_audio_patch_context_changed")
audio.write_text(text.replace(old, new), encoding="utf-8")
text = audio.read_text(encoding="utf-8")
audio.write_text(
    text.replace("torchrun --nproc_per_node=$nj", "torchrun --standalone --nnodes=1 --nproc_per_node=$nj"),
    encoding="utf-8",
)

video = recipe / "run_video.sh"
text = video.read_text(encoding="utf-8")
old = "bash run_audio.sh --stage 2 --stop_stage 4 --examples $raw_data_dir --exp $exp"
new = "bash run_audio.sh --stage 2 --stop_stage 4 --examples $raw_data_dir --exp $exp --nj $nj --gpus $gpus"
if old not in text and new not in text:
    raise SystemExit("upstream_video_parallelism_patch_context_changed")
text = text.replace(old, new)
video.write_text(
    text.replace("torchrun --nproc_per_node=$nj", "torchrun --standalone --nnodes=1 --nproc_per_node=$nj"),
    encoding="utf-8",
)

vad = recipe / "local/voice_activity_detection.py"
text = vad.read_text(encoding="utf-8")
old = "model=VAD_PRETRAINED['model_id'], \n        model_revision=VAD_PRETRAINED['model_revision'],"
new = "model=os.environ.get('THREED_SPEAKER_VAD_MODEL', VAD_PRETRAINED['model_id']), \n        model_revision=(None if os.environ.get('THREED_SPEAKER_VAD_MODEL') else VAD_PRETRAINED['model_revision']),"
if old not in text and new not in text:
    raise SystemExit("upstream_vad_patch_context_changed")
vad.write_text(text.replace(old, new), encoding="utf-8")

PY

export MODELSCOPE_OFFLINE=1
export THREED_SPEAKER_CAMPPLUS="$MODELS/campplus_cn_en_common.pt"
export THREED_SPEAKER_VAD_MODEL="$MODELS/vad"
export PYTHONPATH="$ROOT:$REPOSITORY${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" "$ROOT/scripts/three_d_speaker_worker.py" \
  --runtime-dir "$RUNTIME" --health-check
