#!/usr/bin/env bash
# Script to fetch or link static Mach-O FFmpeg binary for macOS
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FFMPEG_OUT="${ROOT_DIR}/resources/ffmpeg"
mkdir -p "${FFMPEG_OUT}"

TARGET="${FFMPEG_OUT}/ffmpeg"

if [[ -f "${TARGET}" && -x "${TARGET}" ]]; then
    echo "FFmpeg binary already present at ${TARGET}:"
    "${TARGET}" -version | head -n 1
    exit 0
fi

# Check if brew ffmpeg is installed
if command -v ffmpeg >/dev/null 2>&1; then
    SYSTEM_FFMPEG="$(command -v ffmpeg)"
    echo "Copying system FFmpeg from ${SYSTEM_FFMPEG} to ${TARGET}..."
    cp "${SYSTEM_FFMPEG}" "${TARGET}"
    chmod +x "${TARGET}"
    echo "FFmpeg successfully installed at ${TARGET}:"
    "${TARGET}" -version | head -n 1
    exit 0
fi

echo "Attempting download of static universal/arm64 FFmpeg binary..."
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

# Download static macOS build from evermeet.cx or osxexperts
URL="https://evermeet.cx/ffmpeg/getrelease/zip"
curl -fSL --retry 3 -o "${TMP_DIR}/ffmpeg.zip" "${URL}" || {
    echo "Error: Failed to download FFmpeg. Please install via 'brew install ffmpeg'."
    exit 1
}

unzip -q "${TMP_DIR}/ffmpeg.zip" -d "${TMP_DIR}"
if [[ -f "${TMP_DIR}/ffmpeg" ]]; then
    cp "${TMP_DIR}/ffmpeg" "${TARGET}"
    chmod +x "${TARGET}"
    echo "FFmpeg successfully installed at ${TARGET}:"
    "${TARGET}" -version | head -n 1
else
    echo "Error: ffmpeg binary not found in downloaded zip."
    exit 1
fi
