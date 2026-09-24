"""
Windows Desktop implementation of IAnalysisEngine.
Wraps the existing SongAnalyzerPipeline and transposition engine
without altering existing desktop behavior.
"""

from pathlib import Path
from typing import Callable, Optional, Dict, Any
import sys

from shared.analysis_contracts.analysis_engine import IAnalysisEngine
from backend.pipeline import SongAnalyzerPipeline
from backend.models.schemas import AnalysisStatusEnum, SongAnalysis
from backend.transpose.transpose_engine import transpose_song, transpose_chord


class WindowsAnalysisEngine(IAnalysisEngine):
    """
    Desktop reference implementation using PyTorch CUDA, Demucs v4,
    BTC Transformer, Sub-bass tracking, and K-S key detector.
    """

    def __init__(self, pipeline: Optional[SongAnalyzerPipeline] = None):
        self.pipeline = pipeline or SongAnalyzerPipeline()

    def analyze(
        self,
        audio_file_path: Path,
        song_title: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        def internal_progress(status: AnalysisStatusEnum, pct: int, msg: str):
            if progress_callback:
                progress_callback(status.value, pct, msg)

        analysis = self.pipeline.process(
            audio_file_path=audio_file_path,
            song_title=song_title,
            enable_separation=True,
            progress_callback=internal_progress if progress_callback else None
        )
        return analysis.model_dump()

    def transpose(
        self,
        analysis_data: Dict[str, Any],
        semitones: int
    ) -> Dict[str, Any]:
        analysis_obj = SongAnalysis.model_validate(analysis_data)
        transposed_obj = transpose_song(analysis_obj, semitones)
        return transposed_obj.model_dump()

    def edit_chord(
        self,
        analysis_data: Dict[str, Any],
        chord_index: int,
        new_root: str,
        new_quality: str,
        new_bass: Optional[str] = None,
        new_display: Optional[str] = None
    ) -> Dict[str, Any]:
        analysis = SongAnalysis.model_validate(analysis_data)
        if chord_index < 0 or chord_index >= len(analysis.chords):
            raise IndexError(f"Chord index {chord_index} out of range")

        old_chord = analysis.chords[chord_index]
        disp = new_display
        if not disp:
            disp = f"{new_root}{new_quality}"
            if new_bass and new_bass != new_root:
                disp += f"/{new_bass}"

        analysis.chords[chord_index].root = new_root
        analysis.chords[chord_index].quality = new_quality
        analysis.chords[chord_index].bass = new_bass or new_root
        analysis.chords[chord_index].display = disp

        # Re-sync into sections and bars
        bar_idx = old_chord.bar_position or 1
        for sec in analysis.sections:
            for bar in sec.bars:
                if bar.bar_number == bar_idx:
                    for i, c in enumerate(bar.chords):
                        if abs(c.start_time - old_chord.start_time) < 0.05:
                            bar.chords[i].root = new_root
                            bar.chords[i].quality = new_quality
                            bar.chords[i].bass = new_bass or new_root
                            bar.chords[i].display = disp
                    bar.display = " | ".join(c.display for c in bar.chords)

        return analysis.model_dump()

    def rename_section(
        self,
        analysis_data: Dict[str, Any],
        section_id: str,
        new_name: str
    ) -> Dict[str, Any]:
        analysis = SongAnalysis.model_validate(analysis_data)
        for sec in analysis.sections:
            if sec.section_id == section_id:
                sec.name = new_name.strip().upper()
                break
        return analysis.model_dump()
