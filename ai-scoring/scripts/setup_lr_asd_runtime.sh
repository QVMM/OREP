#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${LOCAL_LR_ASD_RUNTIME_DIR:-${PROJECT_DIR}/models/active-speaker/lr-asd-runtime}"
PYTHON_BIN="${LR_ASD_BOOTSTRAP_PYTHON:-${HOME}/.local/bin/python3.11}"
MODEL_CACHE_DIR="${LR_ASD_MODEL_CACHE_DIR:-}"
REPOSITORY_CACHE="${LR_ASD_REPOSITORY_CACHE:-}"
REPOSITORY_URL="https://github.com/Junhua-Liao/LR-ASD.git"
REPOSITORY_COMMIT="1b6dcd2d8fc2895683de6508ec6294ec47d388ca"
LR_ASD_WEIGHT="weight/pretrain_AVA.model"
LR_ASD_WEIGHT_SHA256="85e6c77fc981595234790d1e128ebb60352d37726b2445e0ef8891e2512fe9e3"
YUNET_FILE="face_detection_yunet_2023mar.onnx"
YUNET_URL="https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/${YUNET_FILE}"
YUNET_SHA256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
SFACE_FILE="face_recognition_sface_2021dec.onnx"
SFACE_URL="https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
SFACE_SHA256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    LC_ALL=C LANG=C openssl dgst -sha256 "$1" | awk '{print $NF}'
  fi
}

verify() {
  local expected="$1"
  local file="$2"
  [[ -f "${file}" ]] || return 1
  local actual
  actual="$(sha256_of "${file}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "checksum_mismatch:${file}" >&2
    return 1
  fi
}

face_models_loadable() {
  "${RUNTIME_DIR}/.venv/bin/python" - \
    "${RUNTIME_DIR}/face-models/${YUNET_FILE}" \
    "${RUNTIME_DIR}/face-models/${SFACE_FILE}" <<'PY'
import sys
import cv2

cv2.FaceDetectorYN.create(sys.argv[1], "", (320, 320))
cv2.FaceRecognizerSF.create(sys.argv[2], "")
PY
}

runtime_ready() {
  [[ -x "${RUNTIME_DIR}/.venv/bin/python" ]] || return 1
  [[ -d "${RUNTIME_DIR}/LR-ASD/.git" ]] || return 1
  [[ "$(git -C "${RUNTIME_DIR}/LR-ASD" rev-parse HEAD 2>/dev/null)" == "${REPOSITORY_COMMIT}" ]] || return 1
  verify "${LR_ASD_WEIGHT_SHA256}" "${RUNTIME_DIR}/LR-ASD/${LR_ASD_WEIGHT}" || return 1
  verify "${YUNET_SHA256}" "${RUNTIME_DIR}/face-models/${YUNET_FILE}" || return 1
  verify "${SFACE_SHA256}" "${RUNTIME_DIR}/face-models/${SFACE_FILE}" || return 1
  "${RUNTIME_DIR}/.venv/bin/python" -c 'import cv2, numpy, python_speech_features, scipy, soundfile, torch' >/dev/null 2>&1 || return 1
  face_models_loadable >/dev/null 2>&1
}

health_check() {
  "${RUNTIME_DIR}/.venv/bin/python" "${PROJECT_DIR}/scripts/lr_asd_worker.py" \
    --model-repository "${RUNTIME_DIR}/LR-ASD" \
    --model-weight "${RUNTIME_DIR}/LR-ASD/${LR_ASD_WEIGHT}" \
    --yunet-model "${RUNTIME_DIR}/face-models/${YUNET_FILE}" \
    --sface-model "${RUNTIME_DIR}/face-models/${SFACE_FILE}" \
    --health-check
}

if runtime_ready; then
  health_check
  echo "lr_asd_runtime_ready:${RUNTIME_DIR}"
  exit 0
fi

[[ -x "${PYTHON_BIN}" ]] || {
  echo "python_3_11_missing:${PYTHON_BIN}" >&2
  exit 1
}
command -v git >/dev/null 2>&1 || { echo "git_missing" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl_missing" >&2; exit 1; }
command -v uv >/dev/null 2>&1 || { echo "uv_missing" >&2; exit 1; }

PARENT_DIR="$(dirname "${RUNTIME_DIR}")"
mkdir -p "${PARENT_DIR}"
STAGE_DIR="$(mktemp -d "${PARENT_DIR}/.lr-asd-stage.XXXXXX")"
cleanup() {
  rm -rf "${STAGE_DIR}"
}
trap cleanup EXIT

if [[ -n "${REPOSITORY_CACHE}" && -d "${REPOSITORY_CACHE}/.git" ]]; then
  git clone --no-local "${REPOSITORY_CACHE}" "${STAGE_DIR}/LR-ASD"
else
  git clone "${REPOSITORY_URL}" "${STAGE_DIR}/LR-ASD"
fi
git -C "${STAGE_DIR}/LR-ASD" checkout --detach "${REPOSITORY_COMMIT}"
[[ "$(git -C "${STAGE_DIR}/LR-ASD" rev-parse HEAD)" == "${REPOSITORY_COMMIT}" ]]
verify "${LR_ASD_WEIGHT_SHA256}" "${STAGE_DIR}/LR-ASD/${LR_ASD_WEIGHT}"

mkdir -p "${STAGE_DIR}/face-models"
fetch_model() {
  local filename="$1"
  local url="$2"
  local expected="$3"
  local destination="${STAGE_DIR}/face-models/${filename}"
  if [[ -n "${MODEL_CACHE_DIR}" ]] && verify "${expected}" "${MODEL_CACHE_DIR}/${filename}"; then
    install -m 0644 "${MODEL_CACHE_DIR}/${filename}" "${destination}"
  else
    curl -fL --retry 5 --retry-all-errors -o "${destination}" "${url}"
  fi
  verify "${expected}" "${destination}"
}
fetch_model "${YUNET_FILE}" "${YUNET_URL}" "${YUNET_SHA256}"
fetch_model "${SFACE_FILE}" "${SFACE_URL}" "${SFACE_SHA256}"

"${PYTHON_BIN}" -m venv "${STAGE_DIR}/.venv"
uv pip install --python "${STAGE_DIR}/.venv/bin/python" \
  "numpy==2.2.6" \
  "scipy==1.16.3" \
  "torch==2.9.1" \
  "opencv-python-headless==4.12.0.88" \
  "python_speech_features==0.6" \
  "soundfile==0.13.1"

"${STAGE_DIR}/.venv/bin/python" -c 'import cv2, numpy, python_speech_features, scipy, soundfile, torch'

PREVIOUS_DIR="${RUNTIME_DIR}.previous"
if [[ -e "${PREVIOUS_DIR}" ]]; then
  rm -rf "${PREVIOUS_DIR}"
fi
if [[ -e "${RUNTIME_DIR}" ]]; then
  mv "${RUNTIME_DIR}" "${PREVIOUS_DIR}"
fi
mv "${STAGE_DIR}" "${RUNTIME_DIR}"
trap - EXIT
if ! health_check; then
  FAILED_DIR="${RUNTIME_DIR}.failed"
  [[ -e "${FAILED_DIR}" ]] && rm -rf "${FAILED_DIR}"
  mv "${RUNTIME_DIR}" "${FAILED_DIR}"
  if [[ -e "${PREVIOUS_DIR}" ]]; then
    mv "${PREVIOUS_DIR}" "${RUNTIME_DIR}"
  fi
  echo "lr_asd_health_check_failed" >&2
  exit 1
fi
[[ -e "${PREVIOUS_DIR}" ]] && rm -rf "${PREVIOUS_DIR}"
echo "lr_asd_runtime_ready:${RUNTIME_DIR}"
