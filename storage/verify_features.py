import json
from pathlib import Path
from backend.models.schemas import SongAnalysis
from backend.export.pdf_exporter import export_to_pdf
from backend.export.txt_exporter import export_to_txt
from backend.transpose.transpose_engine import transpose_song

def test_full_features():
    json_path = Path("storage/exports/test_analysis.json")
    assert json_path.exists(), "test_analysis.json must exist"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    analysis = SongAnalysis.model_validate(data)
    print(f"Loaded Analysis: '{analysis.title}', Key: {analysis.key.display}, BPM: {analysis.tempo.bpm}")
    print(f"Total Bars: {sum(len(s.bars) for s in analysis.sections)}")
    print(f"Debug View Entries: {len(analysis.debug_view) if analysis.debug_view else 0}")

    # Test PDF Export
    pdf_out = Path("storage/exports/verification_sheet.pdf")
    export_to_pdf(analysis, pdf_out)
    assert pdf_out.exists() and pdf_out.stat().st_size > 1000, "PDF export failed"
    print(f"Verified PDF Export ({pdf_out.stat().st_size} bytes)")

    # Test TXT Export
    txt_out = export_to_txt(analysis)
    assert "Sec A:" in txt_out and "|Gm|" in txt_out, "TXT export format incorrect"
    print("Verified TXT Export format")

    # Test Transpose (+2 semitones -> A minor)
    transposed = transpose_song(analysis, 2)
    assert transposed.key.display.startswith("A"), f"Transposed key should be A minor, got {transposed.key.display}"
    # Section A bar 1 chord in G minor was Gm, now should be Am
    sec_a_bar1 = transposed.sections[1].bars[0]
    print(f"Transposed +2 Semitones: Key = {transposed.key.display}, Bar 9 Display = | {sec_a_bar1.display} |")
    assert "Am" in sec_a_bar1.display, f"Expected Am in transposed bar 9, got {sec_a_bar1.display}"

    print("\nALL SYSTEM VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_features()
