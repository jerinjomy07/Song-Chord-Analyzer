#!/usr/bin/env bash
# ==============================================================================
# Song Chord Analyzer — macOS Local Server Launcher
# Binds to loopback 127.0.0.1:8000 with Apple Silicon Metal (MPS) or CPU
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "========================================================"
echo "    Song Chord Analyzer — Starting macOS Engine         "
echo "========================================================"

# Locate Python 3 runtime
PYTHON_CMD="python3"
if [ -f "${PROJECT_ROOT}/.venv/bin/python3" ]; then
    PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python3"
elif [ -f "${PROJECT_ROOT}/venv/bin/python3" ]; then
    PYTHON_CMD="${PROJECT_ROOT}/venv/bin/python3"
elif [ -f "${HOME}/Library/Application Support/SongChordAnalyzer/venv/bin/python3" ]; then
    PYTHON_CMD="${HOME}/Library/Application Support/SongChordAnalyzer/venv/bin/python3"
fi

echo "[INFO] Using Python: ${PYTHON_CMD}"

# Ensure macOS Application Support directory exists
MAC_DATA_DIR="${HOME}/Library/Application Support/SongChordAnalyzer"
mkdir -p "${MAC_DATA_DIR}"
export SONG_CHORD_ANALYZER_DATA_DIR="${MAC_DATA_DIR}"

# Run backend on local loopback
exec "${PYTHON_CMD}" run_app.py --host 127.0.0.1 --port 8000 --no-browser
