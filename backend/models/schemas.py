"""
Data models and schemas for Song Chord Analyzer.
Represents chords as distinct musical properties (root, quality, bass, inversion)
rather than only raw strings, in strict accordance with the product requirements.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class AnalysisStatusEnum(str, Enum):
    IDLE = "IDLE"
    DOWNLOADING = "DOWNLOADING"
    UPLOADING = "UPLOADING"
    VALIDATING = "VALIDATING"
    PREPROCESSING = "PREPROCESSING"
    SEPARATING = "SEPARATING"
    ANALYZING_BEATS = "ANALYZING_BEATS"
    ANALYZING_KEY = "ANALYZING_KEY"
    ANALYZING_CHORDS = "ANALYZING_CHORDS"
    ANALYZING_INVERSION = "ANALYZING_INVERSION"
    ALIGNING_BARS = "ALIGNING_BARS"
    DETECTING_SECTIONS = "DETECTING_SECTIONS"
    POST_PROCESSING = "POST_PROCESSING"
    BUILDING_SHEET = "BUILDING_SHEET"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChordCandidate(BaseModel):
    chord: str
    probability: float


class ChordPrediction(BaseModel):
    root: str = Field(..., description="Root note of the chord, e.g. 'C', 'F#', 'Bb'")
    quality: str = Field(..., description="Chord quality, e.g. 'major', 'minor', '7', 'maj7', 'min7', 'dim', 'aug', 'sus4', 'add9'")
    bass: str = Field(..., description="Bass note for slash chords / inversions, e.g. 'A#', 'C#'")
    inversion: int = Field(0, description="0=root position, 1=1st inversion, 2=2nd inversion, etc.")
    display: str = Field(..., description="Musician-friendly display string, e.g. 'F#/A#', 'D', 'Am7'")
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
    duration: float = Field(..., description="Duration in seconds")
    beat_position: Optional[int] = Field(None, description="Beat number within bar (1-based)")
    bar_position: Optional[int] = Field(None, description="Bar index (1-based)")
    beat: int = Field(1, description="Beat number within bar (1-based)")
    beat_duration: float = Field(1.0, description="Duration in beats (e.g. 1.0, 2.0, 4.0)")
    confidence: float = Field(..., description="Model confidence score between 0.0 and 1.0")
    needs_review: bool = Field(False, description="True if confidence is below threshold and should be highlighted")
    alternatives: List[ChordCandidate] = Field(default_factory=list, description="Alternative likely candidates with model probabilities")


class Bar(BaseModel):
    bar_number: int
    start_time: float
    end_time: float
    beats: int = 4
    chords: List[ChordPrediction]
    display: str = ""
    time_signature: str = "4/4"


class MusicalSection(BaseModel):
    section_id: str
    name: str = Field(..., description="e.g. 'INTRO', 'VERSE 1', 'CHORUS', 'BRIDGE', 'OUTRO'")
    start_time: float
    end_time: float
    start_bar: int
    end_bar: int
    bars: List[Bar] = Field(default_factory=list)
    is_repeated: bool = False
    repeat_of_section_id: Optional[str] = None


class KeyAnalysis(BaseModel):
    tonic: str = Field(..., description="Tonic note, e.g. 'A', 'F#'")
    mode: str = Field(..., description="'major' or 'minor'")
    display: str = Field(..., description="e.g. 'A Major', 'F# Minor'")
    confidence: float = Field(..., description="Key detection confidence score (0.0 to 1.0)")


class TempoAnalysis(BaseModel):
    bpm: float = Field(..., description="Detected Beats Per Minute")
    confidence: float = Field(..., description="Tempo confidence score")
    is_estimated: bool = False


class MeterAnalysis(BaseModel):
    numerator: int = 4
    denominator: int = 4
    display: str = "4/4"
    confidence: float = 0.95
    is_estimated: bool = False


class BeatGrid(BaseModel):
    bpm: float
    beats: List[float] = Field(default_factory=list, description="Timestamp in seconds for each detected beat")
    downbeats: List[float] = Field(default_factory=list, description="Timestamp in seconds for each bar downbeat")


class AudioMetadata(BaseModel):
    filename: str
    duration: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int
    file_hash: str


class PipelineMetadata(BaseModel):
    app_version: str = "1.0.0"
    model_name: str = "BTC-Transformer + Demucs v4 + BassStem"
    model_version: str = "1.0"
    separation_model: str = "htdemucs"
    device_used: str = "cuda"
    timestamp: str = ""


class SongAnalysis(BaseModel):
    id: str
    title: str
    metadata: AudioMetadata
    pipeline_metadata: PipelineMetadata
    key: KeyAnalysis
    tempo: TempoAnalysis
    meter: MeterAnalysis
    beat_grid: BeatGrid
    sections: List[MusicalSection]
    chords: List[ChordPrediction]
    raw_predictions: Optional[List[Dict[str, Any]]] = None
    debug_view: Optional[List[Dict[str, Any]]] = None
    transpose_semitones: int = 0
    audio_url: Optional[str] = None
    has_stems: bool = False
    source_metadata: Optional[Dict[str, Any]] = None


class AnalysisStatusResponse(BaseModel):
    analysis_id: str
    status: AnalysisStatusEnum
    progress: int = Field(0, ge=0, le=100)
    current_stage: str = ""
    message: str = ""
    error: Optional[str] = None


class EditChordRequest(BaseModel):
    chord_index: int
    new_root: str
    new_quality: str
    new_bass: Optional[str] = None
    new_display: Optional[str] = None


class TransposeRequest(BaseModel):
    semitones: int = Field(..., ge=-12, le=12)


class RenameSectionRequest(BaseModel):
    section_id: str
    new_name: str
