"""
End-to-End Song Chord Analyzer Pipeline (v2.0).
Coordinates component-specific audio processing, Demucs stem separation,
sequential VRAM model lifecycle management, beat & downbeat tracking,
multi-source key detection, BTC neural chord recognition, explicit bass note analysis,
ensemble fusion, temporal smoothing, bar alignment, and musical section detection.
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import time
import uuid
import gc
import shutil
import numpy as np
import torch

from backend.config import (
    DEFAULT_DEVICE,
    HARDWARE,
    TEMP_DIR,
    DEMUCS_SAMPLE_RATE,
    BTC_SAMPLE_RATE
)
from backend.models.schemas import (
    SongAnalysis,
    AudioMetadata,
    PipelineMetadata,
    AnalysisStatusEnum,
    ChordPrediction
)
from backend.audio.preprocessor import AudioPreprocessor
from backend.separation.demucs_separator import DemucsSeparator
from backend.beat.beat_tracker import BeatTracker
from backend.key.key_detector import KeyDetector
from backend.meter.meter_detector import MeterDetector
from backend.chord.btc import BTCRecognizer
from backend.chord.bass import BassStemAnalyzer
from backend.chord.ensemble import EnsembleChordAnalyzer
from backend.postprocessing.smoothing import smooth_chord_sequence
from backend.postprocessing.alignment import BarAligner
from backend.sections.section_detector import SectionDetector


class VRAMManager:
    """Manages sequential model lifecycle to safely operate within 6 GB VRAM envelope."""
    @staticmethod
    def release_gpu():
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class SongAnalyzerPipeline:
    def __init__(self):
        self.preprocessor = AudioPreprocessor()
        self.separator = DemucsSeparator()
        self.beat_tracker = BeatTracker()
        self.key_detector = KeyDetector()
        self.meter_detector = MeterDetector()
        self.bass_analyzer = BassStemAnalyzer()
        self.ensemble = EnsembleChordAnalyzer(bass_analyzer=self.bass_analyzer)
        self.bar_aligner = BarAligner()
        self.section_detector = SectionDetector()

    def process(
        self,
        audio_file_path: Path,
        song_title: Optional[str] = None,
        enable_separation: bool = True,
        progress_callback: Optional[Callable[[AnalysisStatusEnum, int, str], None]] = None
    ) -> SongAnalysis:
        """
        Runs the full automated music analysis pipeline with strict VRAM lifecycle management.
        """
        start_wall_time = time.time()
        title = song_title or audio_file_path.stem.replace("_", " ").title()
        session_id = str(uuid.uuid4())[:8]
        session_temp = TEMP_DIR / session_id
        session_temp.mkdir(parents=True, exist_ok=True)

        def report(status: AnalysisStatusEnum, pct: int, msg: str):
            if progress_callback:
                progress_callback(status, pct, msg)
            print(f"[{status.value}] {pct}% - {msg}")

        try:
            # Stage 1: Validation & Component-Specific Preprocessing
            report(AnalysisStatusEnum.PREPROCESSING, 5, "Preprocessing audio for models...")
            stereo_44k, mono_22k, meta_dict = self.preprocessor.preprocess(audio_file_path)
            file_hash = meta_dict["file_hash"]

            metadata = AudioMetadata(
                filename=audio_file_path.name,
                duration=meta_dict["duration"],
                sample_rate=meta_dict["sample_rate"],
                channels=meta_dict["channels"],
                format=meta_dict["format"],
                file_size_bytes=meta_dict["file_size_bytes"],
                file_hash=file_hash
            )

            # Stage 2: Sequential Stem Separation (Demucs on GPU)
            stems: Dict[str, Path] = {}
            if enable_separation:
                report(AnalysisStatusEnum.SEPARATING, 15, "Separating stems with Demucs (Bass + Accompaniment)...")
                def demucs_cb(pct: int, msg: str):
                    overall_pct = 15 + int(pct * 0.25)
                    report(AnalysisStatusEnum.SEPARATING, overall_pct, msg)
                stems = self.separator.separate(stereo_44k, file_hash, progress_callback=demucs_cb)
                
                # CRITICAL VRAM RELEASE: Release separation model and flush GPU cache
                VRAMManager.release_gpu()

            # Stage 3: Beat Tracking & Downbeat Alignment
            report(AnalysisStatusEnum.ANALYZING_BEATS, 45, "Detecting BPM, beats, and downbeats...")
            beat_grid, tempo_info = self.beat_tracker.track_beats(mono_22k)

            # Stage 4: Meter / Time Signature Estimation
            report(AnalysisStatusEnum.ANALYZING_BEATS, 52, "Estimating time signature...")
            meter_info = self.meter_detector.detect_meter(mono_22k, beat_grid.beats, tempo_info.bpm)

            # Stage 5: Sequential Chord Recognition (BTC Model loaded onto GPU)
            report(AnalysisStatusEnum.ANALYZING_CHORDS, 60, "Loading BTC Neural Chord Recognizer...")
            btc = BTCRecognizer()

            report(AnalysisStatusEnum.ANALYZING_CHORDS, 65, "Extracting chord posterior probabilities from Original Mix...")
            mix_probs, mix_times = btc.predict_probabilities(mono_22k)

            # Stage 6: BTC on Accompaniment Stem (Clean harmonic backing without vocal interference)
            other_probs = None
            if "other" in stems and stems["other"].exists():
                report(AnalysisStatusEnum.ANALYZING_CHORDS, 74, "Extracting clean accompaniment harmonic probabilities...")
                other_probs, _ = btc.predict_probabilities(stems["other"])

            # CRITICAL VRAM RELEASE: Free BTC model from GPU memory
            del btc
            VRAMManager.release_gpu()

            # Stage 7: Explicit Sounding Bass Note Analysis on Isolated Bass Stem
            bass_data = None
            if "bass" in stems and stems["bass"].exists():
                report(AnalysisStatusEnum.ANALYZING_INVERSION, 80, "Analyzing sounding bass register for slash chords & inversions...")
                bass_data = self.bass_analyzer.analyze_bass_track(stems["bass"])

            # Stage 8: Key Detection (fusing chroma profiles to inform enharmonic spelling)
            report(AnalysisStatusEnum.ANALYZING_KEY, 84, "Detecting key, scale, and mode...")
            key_info = self.key_detector.detect_key(mono_22k)

            # Stage 9: Beat-Synchronous Multi-Source Ensemble Fusion & Simplicity Regularization
            report(AnalysisStatusEnum.ANALYZING_CHORDS, 88, "Fusing beat-synchronous harmonic evidence & simplifying...")
            fused_beat_chords = self.ensemble.fuse_beat_probabilities(
                mix_probs=mix_probs,
                mix_times=mix_times,
                other_probs=other_probs,
                bass_data=bass_data,
                beat_times=beat_grid.beats,
                key_root=key_info.tonic,
                key_mode=key_info.mode
            )

            # Stage 10: Bar & Measure Alignment (Eliminates boundary overlap blips)
            report(AnalysisStatusEnum.ALIGNING_BARS, 93, "Aligning chords to musical measures...")
            bars = self.bar_aligner.align_to_bars(fused_beat_chords, beat_grid, meter_info)

            # Stage 11: Section Detection & Repetition Clustering (Neutral structural labels)
            report(AnalysisStatusEnum.DETECTING_SECTIONS, 96, "Detecting musical sections & repetitions...")
            sections = self.section_detector.detect_sections(mono_22k, bars, metadata.duration)

            # Stage 12: Build Side-by-Side Debug View (Requirement 16)
            debug_view = []
            beats_per_bar = meter_info.numerator if meter_info and meter_info.numerator > 0 else 4
            idx_to_chord = get_btc_index_map() if 'get_btc_index_map' in dir() else {}
            
            for b in bars:
                # Find frames in this bar
                t_sub = (mix_times >= b.start_time) & (mix_times < b.end_time)
                if np.any(t_sub):
                    raw_argmax = np.argmax(mix_probs[t_sub], axis=1)
                    raw_sample = [self.ensemble.idx_to_chord.get(int(idx), 'N') for idx in raw_argmax[::max(1, len(raw_argmax)//4)]][:4]
                else:
                    raw_sample = ["N"]

                # Beat pooled chords in this bar
                b_start_idx = (b.bar_number - 1) * beats_per_bar
                b_slice = fused_beat_chords[b_start_idx : b_start_idx + beats_per_bar]
                beat_pooled_str = [c.display for c in b_slice]

                # Sounding bass note in this bar
                bar_bass = "None"
                if bass_data is not None:
                    bn, bc = self.bass_analyzer.get_bass_note_at_interval(bass_data, b.start_time, b.end_time)
                    if bn:
                        bar_bass = f"{bn} ({bc:.2f})"

                chords_debug = [
                    {
                        "beat": c.beat,
                        "beat_duration": c.beat_duration,
                        "chord": c.display,
                        "start": round(c.start_time, 2),
                        "end": round(c.end_time, 2),
                        "confidence": round(c.confidence, 2)
                    }
                    for c in b.chords
                ]

                debug_view.append({
                    "bar_number": b.bar_number,
                    "time": f"{b.start_time:.2f}s - {b.end_time:.2f}s",
                    "raw_predictions": raw_sample,
                    "beat_pooled": beat_pooled_str,
                    "sounding_bass": bar_bass,
                    "musical_result": [c.display for c in b.chords],
                    "final_display": b.display,
                    "chord_events": chords_debug
                })

            # Stage 13: Build Final Sheet
            report(AnalysisStatusEnum.BUILDING_SHEET, 99, "Constructing musician-friendly chord sheet...")
            analysis_id = str(uuid.uuid4())[:8]

            pipeline_meta = PipelineMetadata(
                app_version="2.0.0",
                model_name="BTC-Transformer + Demucs v4 + BassStem Inversion Analyzer",
                model_version="2.0",
                separation_model="htdemucs",
                device_used=f"{DEFAULT_DEVICE} ({HARDWARE.gpu_name})",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )

            result = SongAnalysis(
                id=analysis_id,
                title=title,
                metadata=metadata,
                pipeline_metadata=pipeline_meta,
                key=key_info,
                tempo=tempo_info,
                meter=meter_info,
                beat_grid=beat_grid,
                sections=sections,
                chords=fused_beat_chords,
                raw_predictions=[{"bar": d["bar_number"], "raw": d["raw_predictions"]} for d in debug_view],
                debug_view=debug_view,
                transpose_semitones=0,
                has_stems=("bass" in stems and stems["bass"].exists())
            )

            elapsed = time.time() - start_wall_time
            report(AnalysisStatusEnum.COMPLETED, 100, f"Analysis completed in {elapsed:.1f}s!")
            return result

        finally:
            # Clean up per-session scratch directory
            if session_temp.exists():
                shutil.rmtree(session_temp, ignore_errors=True)
            VRAMManager.release_gpu()
