"""
Pluggable AudioSource architecture for Song Chord Analyzer.
Provides abstract AudioSource interface and implementations:
- LocalFileSource: Analyzes user-provided audio files.
- YouTubeSource: Policy-compliant YouTube link validator & metadata resolver.
- FutureAuthorizedSource: Extensibility point for licensed/authorized music APIs.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import re
import urllib.request
import urllib.parse
import json


class AudioSource(ABC):
    """Abstract base class representing an audio source provider."""

    @abstractmethod
    def validate(self) -> bool:
        """Validates that the source identifier or reference is structurally valid."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata such as title, artist/channel, duration, thumbnail."""
        pass

    @abstractmethod
    def is_authorized_audio_available(self) -> bool:
        """
        Returns True if an authorized, policy-compliant audio stream or file
        is legally available to pass to the analysis pipeline.
        """
        pass

    @abstractmethod
    def get_audio_path(self) -> Optional[Path]:
        """
        Returns Path to the local audio file ready for Demucs and BTC processing.
        Returns None if authorized audio is unavailable.
        """
        pass


class LocalFileSource(AudioSource):
    """AudioSource implementation for local audio files provided directly by the user."""

    def __init__(self, file_path: Path, title: Optional[str] = None):
        self.file_path = Path(file_path)
        self.title = title or self.file_path.stem

    def validate(self) -> bool:
        return self.file_path.exists() and self.file_path.stat().st_size > 0

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "local_file",
            "title": self.title,
            "filename": self.file_path.name,
            "size_bytes": self.file_path.stat().st_size if self.file_path.exists() else 0,
        }

    def is_authorized_audio_available(self) -> bool:
        return self.validate()

    def get_audio_path(self) -> Optional[Path]:
        return self.file_path if self.validate() else None


class YouTubeSource(AudioSource):
    """
    Policy-compliant YouTube source adapter.
    - Validates YouTube URLs
    - Extracts video ID
    - Resolves public video metadata via YouTube's official oEmbed endpoint (no scraping)
    - Strictly obeys copyright policy: does NOT perform unauthorized stream ripping
    - Guides user to provide authorized audio files
    """

    YOUTUBE_URL_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)([\w-]{11})([&?].*)?$",
        re.IGNORECASE
    )

    OEMBED_ENDPOINT = "https://www.youtube.com/oembed"

    def __init__(self, url: str):
        self.raw_url = url.strip()
        self.video_id: Optional[str] = self._extract_video_id(self.raw_url)
        self._cached_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def _extract_video_id(cls, url: str) -> Optional[str]:
        match = cls.YOUTUBE_URL_REGEX.match(url)
        if match:
            return match.group(5)
        # Try query parameter parse
        try:
            parsed = urllib.parse.urlparse(url)
            if "youtube.com" in parsed.netloc:
                qs = urllib.parse.parse_qs(parsed.query)
                if "v" in qs and len(qs["v"][0]) == 11:
                    return qs["v"][0]
        except Exception:
            pass
        return None

    def validate(self) -> bool:
        return self.video_id is not None and len(self.video_id) == 11

    def get_metadata(self) -> Dict[str, Any]:
        """
        Fetches public video metadata using YouTube's official oEmbed standard.
        Does not require API keys, credentials, or scraping.
        """
        if not self.validate():
            return {
                "source_type": "youtube",
                "valid": False,
                "error": "Invalid YouTube URL"
            }

        if self._cached_metadata is not None:
            return self._cached_metadata

        canonical_url = f"https://www.youtube.com/watch?v={self.video_id}"
        meta: Dict[str, Any] = {
            "source_type": "youtube",
            "valid": True,
            "video_id": self.video_id,
            "canonical_url": canonical_url,
            "title": f"YouTube Video ({self.video_id})",
            "channel": "YouTube Creator",
            "thumbnail_url": f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg",
            "authorized_audio_available": False,
            "compliance_message": (
                "This YouTube video cannot be imported directly for audio analysis. "
                "Please upload an audio file you are authorized to analyze."
            )
        }

        # Query official oEmbed endpoint with short timeout
        try:
            oembed_url = f"{self.OEMBED_ENDPOINT}?url={urllib.parse.quote(canonical_url)}&format=json"
            req = urllib.request.Request(
                oembed_url,
                headers={"User-Agent": "SongChordAnalyzer/1.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    meta["title"] = data.get("title", meta["title"])
                    meta["channel"] = data.get("author_name", meta["channel"])
                    if "thumbnail_url" in data:
                        meta["thumbnail_url"] = data["thumbnail_url"]
        except Exception as e:
            # Fall back to video ID metadata if offline or restricted
            print(f"[YouTubeSource] oEmbed lookup notice for {self.video_id}: {e}")

        self._cached_metadata = meta
        return meta

    def is_authorized_audio_available(self) -> bool:
        """
        Returns False for standard YouTube URLs because arbitrary audio downloading
        or stream ripping from YouTube is unauthorized.
        """
        return False

    def get_audio_path(self) -> Optional[Path]:
        """
        Returns None: unauthorized extraction is prohibited.
        """
        return None


class FutureAuthorizedSource(AudioSource):
    """
    Extensibility adapter for future licensed B2B music partnerships,
    creative commons registries, or approved stem libraries.
    """

    def __init__(self, source_id: str, provider_name: str, stream_url: Optional[str] = None):
        self.source_id = source_id
        self.provider_name = provider_name
        self.stream_url = stream_url

    def validate(self) -> bool:
        return bool(self.source_id and self.provider_name)

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_type": "authorized_provider",
            "provider": self.provider_name,
            "source_id": self.source_id
        }

    def is_authorized_audio_available(self) -> bool:
        return bool(self.stream_url)

    def get_audio_path(self) -> Optional[Path]:
        return None
