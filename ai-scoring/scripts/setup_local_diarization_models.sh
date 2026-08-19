#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODEL_DIR="${LOCAL_DIARIZATION_MODEL_DIR:-${PROJECT_DIR}/models/speaker-diarization}"
SEGMENTATION_ARCHIVE="sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
SEGMENTATION_DIR="sherpa-onnx-pyannote-segmentation-3-0"
EMBEDDING_MODEL="3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"

SEGMENTATION_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/${SEGMENTATION_ARCHIVE}"
EMBEDDING_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/${EMBEDDING_MODEL}"
SEGMENTATION_ARCHIVE_SHA256="24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488"
SEGMENTATION_MODEL_SHA256="d582f4b4c6b48205de7e0643c57df0df5615a3c176189be3fc461e9d18827b5d"
EMBEDDING_MODEL_SHA256="1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

verify() {
  local expected="$1"
  local file="$2"
  local actual
  actual="$(sha256_of "${file}")"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "checksum_mismatch:${file}" >&2
    return 1
  fi
}

SEGMENTATION_MODEL_PATH="${MODEL_DIR}/${SEGMENTATION_DIR}/model.int8.onnx"
EMBEDDING_MODEL_PATH="${MODEL_DIR}/${EMBEDDING_MODEL}"
if [[ -f "${SEGMENTATION_MODEL_PATH}" && -f "${EMBEDDING_MODEL_PATH}" ]] \
  && verify "${SEGMENTATION_MODEL_SHA256}" "${SEGMENTATION_MODEL_PATH}" \
  && verify "${EMBEDDING_MODEL_SHA256}" "${EMBEDDING_MODEL_PATH}"; then
  echo "local_diarization_models_ready:${MODEL_DIR}"
  exit 0
fi

mkdir -p "${MODEL_DIR}"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT

curl -fL --retry 3 -o "${TEMP_DIR}/${SEGMENTATION_ARCHIVE}" "${SEGMENTATION_URL}"
curl -fL --retry 3 -o "${TEMP_DIR}/${EMBEDDING_MODEL}" "${EMBEDDING_URL}"
verify "${SEGMENTATION_ARCHIVE_SHA256}" "${TEMP_DIR}/${SEGMENTATION_ARCHIVE}"
verify "${EMBEDDING_MODEL_SHA256}" "${TEMP_DIR}/${EMBEDDING_MODEL}"

# Some deployment shells export an unsupported UTF-8 locale. Force the
# POSIX locale only for archive extraction so installation stays deterministic.
(
  unset LC_CTYPE
  export LC_ALL=C
  export LANG=C
  tar -xjf "${TEMP_DIR}/${SEGMENTATION_ARCHIVE}" -C "${MODEL_DIR}"
)
install -m 0644 "${TEMP_DIR}/${EMBEDDING_MODEL}" "${EMBEDDING_MODEL_PATH}"
verify "${SEGMENTATION_MODEL_SHA256}" "${SEGMENTATION_MODEL_PATH}"
verify "${EMBEDDING_MODEL_SHA256}" "${EMBEDDING_MODEL_PATH}"
echo "local_diarization_models_ready:${MODEL_DIR}"
