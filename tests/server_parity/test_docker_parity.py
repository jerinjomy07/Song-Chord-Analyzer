"""
Docker / Remote Cloud Run Server Parity Test Suite.
Validates parity between the verified Windows/FastAPI reference analysis and
the Docker/Cloud Run FastAPI server container.

Usage:
  pytest tests/server_parity/test_docker_parity.py -v
  python tests/server_parity/test_docker_parity.py [SERVER_URL]

Environment variables:
  DOCKER_SERVER_URL: Base URL of the running container or Cloud Run service
                     (defaults to http://127.0.0.1:8000 or http://localhost:8000).
"""

import sys
import os
import json
import time
import math
from pathlib import Path
from typing import Dict, Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import httpx
import jsonschema

GOLDEN_AUDIO_PATH = PROJECT_ROOT / "storage" / "cache" / "ecdbc4dd2a6d827b_44k_stereo.wav"
GOLDEN_ANALYSIS_PATH = PROJECT_ROOT / "mobile" / "flutter_app" / "test" / "fixtures" / "bekhayali_golden_analysis.json"
REPORT_PATH = PROJECT_ROOT / "tests" / "server_parity" / "docker_parity_report.json"
SCHEMA_PATH = PROJECT_ROOT / "shared" / "music_schema" / "song_analysis.schema.json"


def get_target_server_url() -> str:
    url = os.environ.get("DOCKER_SERVER_URL") or os.environ.get("CLOUD_API_URL") or "http://127.0.0.1:8000"
    return url.rstrip("/")


def test_docker_health():
    """Verify that the Docker/Cloud Run server reports healthy and has required models."""
    base_url = get_target_server_url()
    health_url = f"{base_url}/api/health"

    try:
        resp = httpx.get(health_url, timeout=10.0)
    except Exception as e:
        pytest.skip(f"Docker/remote server not reachable at {health_url}: {e}")

    assert resp.status_code == 200, f"Health check failed with status {resp.status_code}: {resp.text}"
    data = resp.json()

    assert data.get("status") == "healthy", f"Server status is not healthy: {data}"
    assert data.get("analysis_engine_available") is True, "Analysis engine not reported available"
    models = data.get("models_available", {})
    assert models.get("btc") is True, "BTC model checkpoint not available on server"
    assert models.get("demucs") is True, "Demucs separator not available on server"


def test_docker_bekhayali_parity():
    """
    Submits Bekhayali to the server container, polls to completion,
    and asserts musical parity against the golden reference.
    """
    base_url = get_target_server_url()

    # Check server availability first
    try:
        h = httpx.get(f"{base_url}/api/health", timeout=5.0)
        if h.status_code != 200:
            pytest.skip(f"Target server at {base_url} returned status {h.status_code}")
    except Exception as e:
        pytest.skip(f"Target server not reachable at {base_url}: {e}")

    if not GOLDEN_AUDIO_PATH.exists():
        pytest.skip(f"Golden audio file not found at {GOLDEN_AUDIO_PATH}")

    if not GOLDEN_ANALYSIS_PATH.exists():
        pytest.skip(f"Golden reference JSON not found at {GOLDEN_ANALYSIS_PATH}")

    with open(GOLDEN_ANALYSIS_PATH, "r", encoding="utf-8") as f:
        golden_ref = json.load(f)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    print(f"\n[1/4] Uploading {GOLDEN_AUDIO_PATH.name} to {base_url}/api/analyze...")
    t0 = time.time()
    with open(GOLDEN_AUDIO_PATH, "rb") as f:
        files = {"file": (GOLDEN_AUDIO_PATH.name, f, "audio/wav")}
        data = {"title": "Bekhayali", "force": "true"}
        upload_resp = httpx.post(f"{base_url}/api/analyze", files=files, data=data, timeout=180.0)

    assert upload_resp.status_code == 200, f"Upload failed ({upload_resp.status_code}): {upload_resp.text}"
    analysis_id = upload_resp.json().get("analysis_id")
    assert analysis_id, f"No analysis_id in response: {upload_resp.json()}"
    print(f"      Job queued with analysis_id: {analysis_id}")

    # Poll status
    print("[2/4] Polling analysis status...")
    poll_start = time.time()
    server_result = None
    timeout_sec = 300  # Up to 5 minutes for CPU stem separation

    while time.time() - poll_start < timeout_sec:
        poll_resp = httpx.get(f"{base_url}/api/analyze/{analysis_id}", timeout=10.0)
        assert poll_resp.status_code == 200, f"Poll error: {poll_resp.text}"
        poll_data = poll_resp.json()
        status = poll_data.get("status")
        progress = poll_data.get("progress", 0)

        if status == "completed":
            server_result = poll_data.get("result")
            elapsed = time.time() - t0
            print(f"      Analysis completed in {elapsed:.2f}s!")
            break
        elif status == "failed":
            raise RuntimeError(f"Server analysis failed: {poll_data.get('error')}")

        time.sleep(2.0)

    assert server_result is not None, f"Analysis timed out after {timeout_sec}s"

    print("[3/4] Validating schema contract...")
    jsonschema.validate(instance=server_result, schema=schema)

    print("[4/4] Comparing musical parity against Golden Bekhayali Reference...")
    metrics = {}

    def record_check(name: str, passed: bool, exp: Any, act: Any, details: str = ""):
        metrics[name] = {
            "passed": bool(passed),
            "expected": exp,
            "actual": act,
            "details": details
        }
        status_str = "PASS" if passed else "FAIL"
        print(f"  [{status_str}] {name}: Expected={exp}, Actual={act} {details}")
        assert passed, f"Parity mismatch on {name}: Expected {exp}, got {act}. {details}"

    # 1. Key Tonic & Mode
    record_check("Key Tonic", server_result["key"]["tonic"] == golden_ref["key"]["tonic"],
                 golden_ref["key"]["tonic"], server_result["key"]["tonic"])
    record_check("Key Mode", server_result["key"]["mode"] == golden_ref["key"]["mode"],
                 golden_ref["key"]["mode"], server_result["key"]["mode"])
    record_check("Key Display", server_result["key"]["display"] == golden_ref["key"]["display"],
                 golden_ref["key"]["display"], server_result["key"]["display"])

    # 2. BPM
    bpm_diff = abs(server_result["tempo"]["bpm"] - golden_ref["tempo"]["bpm"])
    record_check("BPM Parity", bpm_diff <= 0.5, golden_ref["tempo"]["bpm"],
                 server_result["tempo"]["bpm"], f"diff={bpm_diff:.2f}")

    # 3. Meter
    record_check("Meter Numerator", server_result["meter"]["numerator"] == golden_ref["meter"]["numerator"],
                 golden_ref["meter"]["numerator"], server_result["meter"]["numerator"])
    record_check("Meter Denominator", server_result["meter"]["denominator"] == golden_ref["meter"]["denominator"],
                 golden_ref["meter"]["denominator"], server_result["meter"]["denominator"])

    # 4. Beat Grid
    beats_count_match = len(server_result["beat_grid"]["beats"]) == len(golden_ref["beat_grid"]["beats"])
    record_check("Beats Count", beats_count_match, len(golden_ref["beat_grid"]["beats"]), len(server_result["beat_grid"]["beats"]))

    downbeats_count_match = len(server_result["beat_grid"]["downbeats"]) == len(golden_ref["beat_grid"]["downbeats"])
    record_check("Downbeats Count", downbeats_count_match, len(golden_ref["beat_grid"]["downbeats"]), len(server_result["beat_grid"]["downbeats"]))

    # 5. Chords
    chord_count_match = len(server_result["chords"]) == len(golden_ref["chords"])
    record_check("Chord Count", chord_count_match, len(golden_ref["chords"]), len(server_result["chords"]))

    # Check chord display and root matches across all chords
    min_chords = min(len(server_result["chords"]), len(golden_ref["chords"]))
    exact_matches = sum(
        1 for i in range(min_chords)
        if server_result["chords"][i]["display"] == golden_ref["chords"][i]["display"]
        and server_result["chords"][i]["root"] == golden_ref["chords"][i]["root"]
    )
    pct_match = (exact_matches / min_chords) * 100 if min_chords > 0 else 0
    record_check("Chord Symbol Parity (%)", pct_match >= 95.0, ">= 95%", f"{pct_match:.1f}% ({exact_matches}/{min_chords})")

    # 6. Sections
    sec_count_match = len(server_result["sections"]) == len(golden_ref["sections"])
    record_check("Sections Count", sec_count_match, len(golden_ref["sections"]), len(server_result["sections"]))

    # Save parity report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server_url": base_url,
        "metrics": metrics,
        "overall_parity_passed": all(m["passed"] for m in metrics.values())
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nParity report successfully saved to {REPORT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
        os.environ["DOCKER_SERVER_URL"] = sys.argv[1]
    pytest.main(["-s", __file__])
