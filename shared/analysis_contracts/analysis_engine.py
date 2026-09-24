"""
Shared Analysis Engine Contract for Song Chord Analyzer.

Defines the platform-agnostic interface that all analysis engines
(Windows Desktop, Android Mobile, Cloud / Development HTTP) must implement.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path


class AnalysisProgressCallback:
    """Standard progress signature: (stage_name: str, percent: int, detail_message: str) -> None"""
    pass


class IAnalysisEngine(ABC):
    """
    Abstract interface for music analysis engines.
    Both Desktop (WindowsAnalysisEngine) and Mobile (AndroidAnalysisEngine, DevHttpAnalysisEngine)
    interact via this contract.
    """

    @abstractmethod
    def analyze(
        self,
        audio_file_path: Path,
        song_title: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes full music information retrieval and chord recognition pipeline.
        Returns serialized SongAnalysis dictionary adhering to shared/music_schema/song_analysis.schema.json.
        """
        pass

    @abstractmethod
    def transpose(
        self,
        analysis_data: Dict[str, Any],
        semitones: int
    ) -> Dict[str, Any]:
        """
        Transposes musical chords and key by the given semitone offset (-12 to +12),
        preserving chord quality, root spelling, and slash inversions.
        """
        pass

    @abstractmethod
    def edit_chord(
        self,
        analysis_data: Dict[str, Any],
        chord_index: int,
        new_root: str,
        new_quality: str,
        new_bass: Optional[str] = None,
        new_display: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Applies a user-edited chord to the analysis structure and recomputes bar display.
        """
        pass

    @abstractmethod
    def rename_section(
        self,
        analysis_data: Dict[str, Any],
        section_id: str,
        new_name: str
    ) -> Dict[str, Any]:
        """
        Renames a musical section.
        """
        pass
