"""
Base abstraction for all Automatic Chord Recognition (ACR) models.
Enables plug-and-play swapping of chord recognition algorithms.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.models.schemas import ChordPrediction


class ChordRecognizer(ABC):
    """Abstract interface for all chord recognition models."""

    @abstractmethod
    def analyze(self, audio_path: Path, **kwargs) -> List[ChordPrediction]:
        """Runs chord recognition directly on an audio file and returns timestamped ChordPredictions."""
        pass

    @abstractmethod
    def predict_features(self, features: Any) -> List[ChordPrediction]:
        """Runs inference on pre-extracted feature representation (e.g. CQT or Chroma)."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns model identifier, vocabulary size, and licensing info."""
        pass
