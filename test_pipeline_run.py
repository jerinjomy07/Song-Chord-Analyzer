"""
Verification script: runs the end-to-end Song Chord Analyzer pipeline on a real audio file.
"""

import os
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from backend.pipeline import SongAnalyzerPipeline
from backend.export.txt_exporter import export_to_txt
from backend.export.pdf_exporter import export_to_pdf
from backend.export.json_exporter import export_to_json

def test_full_pipeline():
    pipeline = SongAnalyzerPipeline()

    # First check uploads for Radhimaa
    upload_dir = Path(os.path.expandvars(r'%LOCALAPPDATA%\SongChordAnalyzer\uploads'))
    radhimaa_files = list(upload_dir.glob('*Radhimaa*')) if upload_dir.exists() else []

    if radhimaa_files:
        test_audio = radhimaa_files[0]
        song_title = "Radhimaa"
    else:
        appdata_dir = os.environ.get("APPDATA", "")
        test_audio = Path(appdata_dir) / "StemKit" / "songs" / "-hZIVX0iv9w" / "mix.wav"
        song_title = "Real Song Pipeline Test"
        if not test_audio.exists():
            downloads = Path(os.path.expanduser("~/Downloads"))
            alternatives = list(downloads.glob("*.mp3")) + list(downloads.glob("*.wav"))
            if alternatives:
                test_audio = alternatives[0]
                song_title = test_audio.stem
            else:
                print("No test file found!")
                return
        if alternatives:
            test_audio = alternatives[0]
        else:
            print("No test file found!")
            return

    print(f"\n==========================================")
    print(f"RUNNING REAL PIPELINE TEST ON: {test_audio.name}")
    print(f"==========================================\n")

    # Run pipeline with separation enabled
    result = pipeline.process(
        audio_file_path=test_audio,
        song_title=song_title,
        enable_separation=True
    )

    print("\n" + "=" * 50)
    print("PIPELINE EXECUTION SUCCESSFUL!")
    print("=" * 50)
    print(f"Title:          {result.title}")
    print(f"Key:            {result.key.display} (confidence: {result.key.confidence})")
    print(f"Tempo:          {result.tempo.bpm} BPM")
    print(f"Time Signature: {result.meter.display}")
    print(f"Total Chords:   {len(result.chords)}")
    print(f"Sections Count: {len(result.sections)}")
    print("-" * 50)

    # Print first 10 chords
    print("\nFIRST 10 CHORDS:")
    for c in result.chords[:10]:
        print(f"  {c.start_time:05.2f}s - {c.end_time:05.2f}s | {c.display:<8} (Root: {c.root:<3} Qual: {c.quality:<5} Bass: {c.bass:<3} Conf: {c.confidence:.2f})")

    # Print sections summary
    print("\nDETECTED SECTIONS:")
    for s in result.sections:
        chords_in_sec = " | ".join(" ".join(c.display for c in b.chords if c.display != 'N') for b in s.bars[:4])
        print(f"  [{s.name}] ({s.start_time:.1f}s - {s.end_time:.1f}s, Bars {s.start_bar}-{s.end_bar}): {chords_in_sec}")

    # Test Exporters
    txt_out = export_to_txt(result)
    print("\n--- GENERATED TEXT CHORD SHEET SNIPPET ---")
    print("\n".join(txt_out.splitlines()[:25]))

    pdf_path = Path("storage/exports/test_sheet.pdf")
    export_to_pdf(result, pdf_path)
    print(f"\nPDF successfully generated at: {pdf_path.resolve()} ({pdf_path.stat().st_size} bytes)")

    json_path = Path("storage/exports/test_analysis.json")
    export_to_json(result, json_path)
    print(f"JSON successfully exported at: {json_path.resolve()} ({json_path.stat().st_size} bytes)")

if __name__ == "__main__":
    test_full_pipeline()
