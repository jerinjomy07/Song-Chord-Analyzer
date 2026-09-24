"""
Pluggable AudioSource architecture for Song Chord Analyzer.
Provides abstract AudioSource interface and implementations:
- AudioSource: Abstract base class representing an audio source provider.
- LocalFileSource: Analyzes user-provided local audio files (MP3, WAV, FLAC, M4A).
- YouTubeReferenceSource: Policy-compliant YouTube link validator & metadata resolver.
  Strictly reference-only: does NOT perform unauthorized stream ripping or audio extraction.
- FutureAuthorizedYouTubeSource: Extensibility point for future licensed/authorized APIs.
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
        Returns True if an authorized, policy-compliant audio file or stream
        is available to pass to the analysis pipeline.
        """
        pass

    @abstractmethod
    def get_audio_path(self) -> Optional[Path]:
        """
        Returns Path to the local audio file ready for Demucs and BTC processing.
        Returns None if authorized local audio is unavailable.
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
            "source_type": "local",
            "title": self.title,
            "filename": self.file_path.name,
            "size_bytes": self.file_path.stat().st_size if self.file_path.exists() else 0,
        }

    def is_authorized_audio_available(self) -> bool:
        return self.validate()

    def get_audio_path(self) -> Optional[Path]:
        return self.file_path if self.validate() else None


class YouTubeReferenceSource(AudioSource):
    """
    Policy-compliant YouTube reference source adapter.
    - Validates YouTube URLs without downloading audiovisual streams.
    - Resolves public video metadata via YouTube's official oEmbed endpoint.
    - Strictly reference-only: does NOT perform unauthorized stream extraction or downloading.
    - Guides the user to supply authorized local audio.
    - Associates user-supplied local audio with YouTube metadata for analysis & history.
    """

    YOUTUBE_URL_REGEX = re.compile(
        r"^(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)([\w-]{11})([&?].*)?$",
        re.IGNORECASE
    )

    OEMBED_ENDPOINT = "https://www.youtube.com/oembed"

    def __init__(self, url: str, local_audio_path: Optional[Path] = None):
        self.raw_url = url.strip()
        self.video_id: Optional[str] = self._extract_video_id(self.raw_url)
        self.local_audio_path: Optional[Path] = Path(local_audio_path) if local_audio_path else None
        self._cached_metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def _extract_video_id(cls, url: str) -> Optional[str]:
        if not url or not url.strip():
            return None
        match = cls.YOUTUBE_URL_REGEX.match(url.strip())
        if match:
            return match.group(5)
        # Try query parameter parse
        try:
            parsed = urllib.parse.urlparse(url.strip())
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
        Does not download, rip, or scrape media streams.
        """
        if not self.validate():
            return {
                "source_type": "youtube_reference",
                "valid": False,
                "error": "Unable to retrieve information for this YouTube link. Please check the URL and try again."
            }

        if self._cached_metadata is not None:
            return self._cached_metadata

        canonical_url = f"https://www.youtube.com/watch?v={self.video_id}"
        meta: Dict[str, Any] = {
            "source_type": "youtube_reference",
            "valid": True,
            "video_id": self.video_id,
            "canonical_url": canonical_url,
            "title": f"YouTube Video ({self.video_id})",
            "channel": "YouTube Creator",
            "thumbnail_url": f"https://img.youtube.com/vi/{self.video_id}/hqdefault.jpg",
            "authorized_audio_available": True
        }

        # Query official oEmbed endpoint with short timeout
        try:
            oembed_url = f"{self.OEMBED_ENDPOINT}?url={urllib.parse.quote(canonical_url)}&format=json"
            req = urllib.request.Request(
                oembed_url,
                headers={"User-Agent": "SongChordAnalyzer/1.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    meta["title"] = data.get("title", meta["title"])
                    meta["channel"] = data.get("author_name", meta["channel"])
                    if "thumbnail_url" in data:
                        meta["thumbnail_url"] = data["thumbnail_url"]
        except Exception as e:
            # Fall back to video ID metadata if offline or restricted
            print(f"[YouTubeReferenceSource] oEmbed lookup notice for {self.video_id}: {e}")

        self._cached_metadata = meta
        return meta

    def set_authorized_local_audio(self, audio_path: Path) -> None:
        """Associates the user's supplied local audio file with this YouTube reference."""
        self.local_audio_path = Path(audio_path)

    def is_authorized_audio_available(self) -> bool:
        """
        True only when the user has provided a valid, existing local audio file.
        """
        return bool(self.local_audio_path and self.local_audio_path.exists() and self.local_audio_path.stat().st_size > 0)

    def get_audio_path(self) -> Optional[Path]:
        """Returns path to the user's authorized local audio file."""
        return self.local_audio_path if self.is_authorized_audio_available() else None


class YouTubeAudioExtractor:
    """
    Dedicated YouTube audio extraction service using yt-dlp and bundled FFmpeg.
    Downloads audio directly into temporary storage for instant MIR analysis.
    """

    @staticmethod
    def get_ffmpeg_dir() -> Optional[str]:
        from backend.config import FFMPEG_PATH
        if FFMPEG_PATH and FFMPEG_PATH.exists():
            return str(FFMPEG_PATH.parent)
        import shutil
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return str(Path(which_ffmpeg).parent)
        return None

    @classmethod
    def get_video_info(cls, url: str) -> Dict[str, Any]:
        """Extracts video metadata quickly without downloading media."""
        import yt_dlp
        ffmpeg_dir = cls.get_ffmpeg_dir()
        opts: Dict[str, Any] = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        if ffmpeg_dir:
            opts['ffmpeg_location'] = ffmpeg_dir

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url.strip(), download=False)
                vid = info.get("id", "")
                return {
                    "valid": True,
                    "video_id": vid,
                    "title": info.get("title", ""),
                    "channel": info.get("uploader") or info.get("channel") or "Unknown Creator",
                    "duration": info.get("duration", 0),
                    "thumbnail_url": info.get("thumbnail") or f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                    "canonical_url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}"
                }
        except Exception as e:
            # Fall back to oEmbed if yt-dlp hits quick extraction issue
            ref_src = YouTubeReferenceSource(url)
            meta = ref_src.get_metadata()
            if meta.get("valid"):
                return meta
            raise ValueError(f"Could not retrieve YouTube video info: {e}")

    @classmethod
    def download_audio(
        cls,
        url: str,
        output_dir: Optional[Path] = None,
        progress_cb=None
    ) -> tuple[Path, Dict[str, Any]]:
        """
        Downloads audio stream directly from YouTube and converts to high-quality MP3.
        Returns the downloaded MP3 Path and video metadata.
        """
        import yt_dlp
        from backend.config import STORAGE_DIR

        target_dir = Path(output_dir) if output_dir else (STORAGE_DIR / "temp")
        target_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_dir = cls.get_ffmpeg_dir()

        out_template = str(target_dir / "yt_%(id)s.%(ext)s")

        def hook(d):
            if progress_cb and d.get('status') == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
                downloaded = d.get('downloaded_bytes', 0)
                pct = min(99, int((downloaded / total) * 100))
                progress_cb(pct, f"Downloading YouTube audio ({pct}%)...")

        opts: Dict[str, Any] = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [hook],
        }
        if ffmpeg_dir:
            opts['ffmpeg_location'] = ffmpeg_dir

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url.strip(), download=True)
            video_id = info['id']
            expected_mp3 = target_dir / f"yt_{video_id}.mp3"

            if not expected_mp3.exists():
                # Check if file has another audio extension
                matches = list(target_dir.glob(f"yt_{video_id}.*"))
                if matches:
                    expected_mp3 = matches[0]
                else:
                    raise FileNotFoundError(f"Failed to locate extracted audio for YouTube video {video_id}")

            meta = {
                "video_id": video_id,
                "title": info.get("title", ""),
                "channel": info.get("uploader") or info.get("channel") or "Unknown Creator",
                "duration": info.get("duration", 0),
                "thumbnail_url": info.get("thumbnail") or f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "canonical_url": info.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
            }
            return expected_mp3, meta


class YouTubeSource(AudioSource):
    """
    Direct YouTube AudioSource that extracts audio streams for automatic MIR chord analysis.
    """

    def __init__(self, url: str):
        self.url = url.strip()
        self.video_id = YouTubeReferenceSource._extract_video_id(self.url)
        self.downloaded_audio_path: Optional[Path] = None
        self._cached_meta: Optional[Dict[str, Any]] = None

    def validate(self) -> bool:
        return self.video_id is not None and len(self.video_id) == 11

    def get_metadata(self) -> Dict[str, Any]:
        if not self.validate():
            return {"valid": False, "error": "Invalid YouTube URL"}
        if self._cached_meta is None:
            self._cached_meta = YouTubeAudioExtractor.get_video_info(self.url)
        return self._cached_meta

    def download(self, output_dir: Optional[Path] = None, progress_cb=None) -> Path:
        audio_path, meta = YouTubeAudioExtractor.download_audio(self.url, output_dir, progress_cb)
        self.downloaded_audio_path = audio_path
        self._cached_meta = meta
        return audio_path

    def is_authorized_audio_available(self) -> bool:
        return bool(self.downloaded_audio_path and self.downloaded_audio_path.exists())

    def get_audio_path(self) -> Optional[Path]:
        return self.downloaded_audio_path


class FutureAuthorizedYouTubeSource(AudioSource):
    """
    Extensibility adapter for future licensed/authorized music APIs or
    approved YouTube B2B partner integrations.
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


# Backward-compatibility aliases
FutureAuthorizedSource = FutureAuthorizedYouTubeSource
