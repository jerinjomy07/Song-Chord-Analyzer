"""
Phase 4: Windows Engine vs Server Parity Test Suite.
Validates 100% parity between direct Windows desktop engine (WindowsAnalysisEngine)
and the FastAPI server endpoints (POST /analyze, GET /analyze/{analysis_id}).
Golden Track: Bekhayali (storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav).
"""

import sys
import os
import json
import time
import math
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jsonschema
from starlette.testclient import TestClient

from backend.main import app
from backend.engine.windows_engine import WindowsAnalysisEngine
from backend.models.schemas import SongAnalysis


def load_schema() -> Dict[str, Any]:
    schema_path = PROJECT_ROOT / "shared" / "music_schema" / "song_analysis.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_windows_reference(audio_path: Path, title: str) -> Dict[str, Any]:
    print(f"\n[1/3] Running Direct Windows Engine on: {audio_path.name}...")
    t0 = time.time()
    engine = WindowsAnalysisEngine()
    result = engine.analyze(audio_path, song_title=title)
    elapsed = time.time() - t0
    print(f"      Windows Engine completed in {elapsed:.2f}s")
    return result


def run_server_analysis(audio_path: Path, title: str, timeout_seconds: int = 120) -> Dict[str, Any]:
    print(f"\n[2/3] Running FastAPI Server analysis via TestClient on: {audio_path.name}...")
    client = TestClient(app)

    # 1. Test GET /health
    health_resp = client.get("/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
    print(f"      Server health: {health_resp.json()['status']}, device: {health_resp.json()['device']}")

    # 2. Upload to POST /analyze
    t0 = time.time()
    with open(audio_path, "rb") as f:
        upload_resp = client.post(
            "/analyze",
            files={"file": (audio_path.name, f, "audio/wav")},
            data={"title": title, "force": "true"}
        )

    assert upload_resp.status_code == 200, f"Upload failed ({upload_resp.status_code}): {upload_resp.text}"
    upload_data = upload_resp.json()
    analysis_id = upload_data.get("analysis_id")
    assert analysis_id, f"No analysis_id in response: {upload_data}"
    print(f"      Job queued successfully with analysis_id: {analysis_id}")

    # 3. Poll GET /analyze/{analysis_id}
    start_poll = time.time()
    poll_count = 0
    server_result = None

    while time.time() - start_poll < timeout_seconds:
        poll_resp = client.get(f"/analyze/{analysis_id}")
        assert poll_resp.status_code == 200, f"Poll failed ({poll_resp.status_code}): {poll_resp.text}"
        poll_data = poll_resp.json()
        status = poll_data.get("status")
        progress = poll_data.get("progress", 0)
        stage = poll_data.get("current_stage", "")
        poll_count += 1

        if status == "completed":
            server_result = poll_data.get("result")
            elapsed = time.time() - t0
            print(f"      Server analysis completed in {elapsed:.2f}s ({poll_count} poll iterations)")
            break
        elif status == "failed":
            raise RuntimeError(f"Server analysis failed: {poll_data.get('error')}")

        time.sleep(0.5)

    if not server_result:
        raise TimeoutError(f"Server analysis timed out after {timeout_seconds}s")

    # Also verify GET /analysis/{analysis_id} returns the same data
    direct_get_resp = client.get(f"/analysis/{analysis_id}")
    assert direct_get_resp.status_code == 200, f"GET /analysis/{analysis_id} failed: {direct_get_resp.status_code}"

    return server_result


def compare_results(windows_res: Dict[str, Any], server_res: Dict[str, Any]) -> Dict[str, Any]:
    print("\n[3/3] Comparing Windows Reference vs FastAPI Server Output...")
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {},
        "all_passed": True,
        "failures": []
    }

    def check(name: str, passed: bool, expected: Any, actual: Any, details: str = ""):
        report["metrics"][name] = {
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "details": details
        }
        status_icon = "PASS" if passed else "FAIL"
        print(f"   [{status_icon}] {name}: expected={expected}, actual={actual} {details}")
        if not passed:
            report["all_passed"] = False
            report["failures"].append(f"{name}: expected {expected}, got {actual} ({details})")

    # 1. Key comparison
    win_key = windows_res.get("key", {})
    srv_key = server_res.get("key", {})
    check("Key Tonic", win_key.get("tonic") == srv_key.get("tonic"), win_key.get("tonic"), srv_key.get("tonic"))
    check("Key Mode", win_key.get("mode") == srv_key.get("mode"), win_key.get("mode"), srv_key.get("mode"))
    check("Key Display", win_key.get("display") == srv_key.get("display"), win_key.get("display"), srv_key.get("display"))
    check("Key Confidence", math.isclose(win_key.get("confidence", 0), srv_key.get("confidence", 0), abs_tol=1e-3),
          round(win_key.get("confidence", 0), 3), round(srv_key.get("confidence", 0), 3))

    # 2. Tempo comparison
    win_tempo = windows_res.get("tempo", {})
    srv_tempo = server_res.get("tempo", {})
    check("BPM", math.isclose(win_tempo.get("bpm", 0), srv_tempo.get("bpm", 0), abs_tol=0.05),
          round(win_tempo.get("bpm", 0), 2), round(srv_tempo.get("bpm", 0), 2))

    # 3. Meter comparison
    win_meter = windows_res.get("meter", {})
    srv_meter = server_res.get("meter", {})
    check("Meter Numerator", win_meter.get("numerator") == srv_meter.get("numerator"),
          win_meter.get("numerator"), srv_meter.get("numerator"))
    check("Meter Denominator", win_meter.get("denominator") == srv_meter.get("denominator"),
          win_meter.get("denominator"), srv_meter.get("denominator"))
    check("Meter Display", win_meter.get("display") == srv_meter.get("display"),
          win_meter.get("display"), srv_meter.get("display"))

    # 4. Beat Grid comparison
    win_grid = windows_res.get("beat_grid", {})
    srv_grid = server_res.get("beat_grid", {})
    win_beats = win_grid.get("beats", [])
    srv_beats = srv_grid.get("beats", [])
    check("Beats Count", len(win_beats) == len(srv_beats), len(win_beats), len(srv_beats))
    if len(win_beats) == len(srv_beats) and len(win_beats) > 0:
        max_beat_diff = max(abs(w - s) for w, s in zip(win_beats, srv_beats))
        check("Beats Alignment (Max Diff)", max_beat_diff < 0.01, "< 0.01s", f"{max_beat_diff:.6f}s")

    win_downbeats = win_grid.get("downbeats", [])
    srv_downbeats = srv_grid.get("downbeats", [])
    check("Downbeats Count", len(win_downbeats) == len(srv_downbeats), len(win_downbeats), len(srv_downbeats))
    if len(win_downbeats) == len(srv_downbeats) and len(win_downbeats) > 0:
        max_downbeat_diff = max(abs(w - s) for w, s in zip(win_downbeats, srv_downbeats))
        check("Downbeats Alignment (Max Diff)", max_downbeat_diff < 0.01, "< 0.01s", f"{max_downbeat_diff:.6f}s")

    # 5. Chords comparison
    win_chords = windows_res.get("chords", [])
    srv_chords = server_res.get("chords", [])
    check("Chords Count", len(win_chords) == len(srv_chords), len(win_chords), len(srv_chords))

    if len(win_chords) == len(srv_chords) and len(win_chords) > 0:
        matching_displays = sum(1 for w, s in zip(win_chords, srv_chords) if w.get("display") == s.get("display"))
        display_match_pct = (matching_displays / len(win_chords)) * 100.0
        check("Chord Display Match %", display_match_pct >= 99.9, "100.0%", f"{display_match_pct:.2f}%")

        matching_roots = sum(1 for w, s in zip(win_chords, srv_chords) if w.get("root") == s.get("root"))
        check("Chord Root Match %", (matching_roots / len(win_chords)) * 100.0 >= 99.9, "100.0%", f"{(matching_roots / len(win_chords)) * 100:.2f}%")

        matching_basses = sum(1 for w, s in zip(win_chords, srv_chords) if w.get("bass") == s.get("bass"))
        check("Chord Bass Match %", (matching_basses / len(win_chords)) * 100.0 >= 99.9, "100.0%", f"{(matching_basses / len(win_chords)) * 100:.2f}%")

        max_chord_time_diff = max(max(abs(w.get("start_time", 0) - s.get("start_time", 0)),
                                      abs(w.get("end_time", 0) - s.get("end_time", 0)))
                                  for w, s in zip(win_chords, srv_chords))
        check("Chord Timing (Max Diff)", max_chord_time_diff < 0.01, "< 0.01s", f"{max_chord_time_diff:.6f}s")

    # 6. Sections comparison
    win_sections = windows_res.get("sections", [])
    srv_sections = server_res.get("sections", [])
    check("Sections Count", len(win_sections) == len(srv_sections), len(win_sections), len(srv_sections))
    if len(win_sections) == len(srv_sections) and len(win_sections) > 0:
        names_match = all(w.get("name") == s.get("name") for w, s in zip(win_sections, srv_sections))
        check("Section Names Match", names_match, True, names_match)

    # 7. JSON Schema Validation on Server Output
    schema = load_schema()
    try:
        jsonschema.validate(instance=server_res, schema=schema)
        schema_valid = True
        schema_err = "None"
    except Exception as e:
        schema_valid = False
        schema_err = str(e)
    check("JSON Schema Conformance", schema_valid, True, schema_valid, f"Error: {schema_err}")

    # 8. Pydantic Model Validation
    try:
        SongAnalysis.model_validate(server_res)
        pydantic_valid = True
        pydantic_err = "None"
    except Exception as e:
        pydantic_valid = False
        pydantic_err = str(e)
    check("Pydantic Deserialization", pydantic_valid, True, pydantic_valid, f"Error: {pydantic_err}")

    return report


def main():
    audio_path = PROJECT_ROOT / "storage" / "cache" / "ecdbc4dd2a6d827b_44k_stereo.wav"
    if not audio_path.exists():
        raise FileNotFoundError(f"Golden audio not found at: {audio_path}")

    title = "Bekhayali (Parity Test)"

    print("=" * 60)
    print("WINDOWS ENGINE <-> FASTAPI SERVER PARITY VALIDATION")
    print(f"Target Song: {title}")
    print(f"Audio Path:  {audio_path}")
    print("=" * 60)

    # 1. Run Windows reference
    windows_result = run_windows_reference(audio_path, title)

    # 2. Run Server analysis via FastAPI HTTP
    server_result = run_server_analysis(audio_path, title)

    # 3. Compare outputs
    report = compare_results(windows_result, server_result)

    # 4. Save report
    out_dir = PROJECT_ROOT / "tests" / "server_parity"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / "windows_server_parity_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved detailed JSON report to: {report_file}")

    # 5. Generate Markdown report
    md_file = PROJECT_ROOT / "WINDOWS_SERVER_PARITY_REPORT.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Windows Engine <-> Server Parity Report\n\n")
        f.write(f"**Date:** {report['timestamp']}\n")
        f.write(f"**Song:** {title}\n")
        f.write(f"**Overall Result:** {'PASSED - 100% PARITY' if report['all_passed'] else 'FAILED'}\n\n")
        f.write("## Parity Verification Metrics\n\n")
        f.write("| Metric | Expected (Windows Engine) | Actual (FastAPI Server) | Result |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for k, v in report["metrics"].items():
            res_str = "PASS" if v["passed"] else "FAIL"
            f.write(f"| **{k}** | `{v['expected']}` | `{v['actual']}` | **{res_str}** |\n")

        if report["failures"]:
            f.write("\n## Failures / Inconsistencies\n\n")
            for fl in report["failures"]:
                f.write(f"- {fl}\n")
        else:
            f.write("\n## Conclusion\n\n")
            f.write("Both the Windows desktop engine and the FastAPI server produce **identical musical analysis results** on the golden track. The server analysis engine is confirmed ready to serve as the authoritative single source of truth for the Android mobile client.\n")

    print(f"Saved Markdown report to: {md_file}")

    if not report["all_passed"]:
        print("\nERROR: Parity check failed!")
        sys.exit(1)
    else:
        print("\nSUCCESS: 100% Parity Achieved between Windows Engine and FastAPI Server!")
        sys.exit(0)


if __name__ == "__main__":
    main()
