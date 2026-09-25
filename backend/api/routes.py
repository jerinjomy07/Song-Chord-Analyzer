"""
FastAPI REST routes for Song Chord Analyzer.
Provides endpoints for audio upload, asynchronous analysis status polling,
transposition, chord editing, section renaming, audio streaming, and exports.
"""

import os
import shutil
import uuid
import threading
import re
from urllib.parse import quote
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from pydantic import BaseModel

from backend.config import UPLOADS_DIR, EXPORTS_DIR
from backend.models.schemas import (
    SongAnalysis,
    AnalysisStatusResponse,
    AnalysisStatusEnum,
    TransposeRequest,
    EditChordRequest,
    RenameSectionRequest
)
from backend.pipeline import SongAnalyzerPipeline
from backend.transpose.transpose_engine import transpose_song, transpose_chord
from backend.export.pdf_exporter import export_to_pdf
from backend.export.txt_exporter import export_to_txt
from backend.export.json_exporter import export_to_json, build_complete_json_export
from backend.database.repository import SongRepository

router = APIRouter()

# In-memory session store
ACTIVE_TASKS: Dict[str, AnalysisStatusResponse] = {}
ANALYSIS_RESULTS: Dict[str, SongAnalysis] = {}
AUDIO_FILE_PATHS: Dict[str, Path] = {}

# Pipeline singleton
PIPELINE = SongAnalyzerPipeline()


def run_pipeline_worker(
    analysis_id: str,
    audio_path: Path,
    song_title: str,
    source_type: str = "local",
    youtube_video_id: Optional[str] = None,
    youtube_url: Optional[str] = None,
    youtube_title: Optional[str] = None,
    youtube_channel: Optional[str] = None
):
    """Worker function running the analysis pipeline in a background thread."""
    try:
        def update_progress(status: AnalysisStatusEnum, pct: int, msg: str):
            if analysis_id in ACTIVE_TASKS:
                ACTIVE_TASKS[analysis_id].status = status
                ACTIVE_TASKS[analysis_id].progress = pct
                ACTIVE_TASKS[analysis_id].message = msg
                ACTIVE_TASKS[analysis_id].current_stage = status.value

        ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
            analysis_id=analysis_id,
            status=AnalysisStatusEnum.PREPROCESSING,
            progress=5,
            current_stage="PREPROCESSING",
            message="Starting automatic audio analysis..."
        )

        analysis = PIPELINE.process(
            audio_file_path=audio_path,
            song_title=song_title,
            enable_separation=True,
            progress_callback=update_progress
        )

        # Attach audio playback URL
        analysis.id = analysis_id
        analysis.audio_url = f"/api/analysis/{analysis_id}/audio"

        ANALYSIS_RESULTS[analysis_id] = analysis
        AUDIO_FILE_PATHS[analysis_id] = audio_path

        # Auto-persist analysis and ingest user-supplied local audio into library
        try:
            SongRepository.save_analysis(
                analysis=analysis,
                source_audio_path=audio_path,
                song_id=analysis_id,
                source_type=source_type,
                youtube_video_id=youtube_video_id,
                youtube_url=youtube_url,
                youtube_title=youtube_title,
                youtube_channel=youtube_channel
            )
        except Exception as repo_err:
            print(f"[Warning] Failed to persist analysis {analysis_id} to SQLite: {repo_err}")

        ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.COMPLETED
        ACTIVE_TASKS[analysis_id].progress = 100
        ACTIVE_TASKS[analysis_id].message = "Analysis complete!"
        ACTIVE_TASKS[analysis_id].current_stage = "COMPLETED"

    except Exception as e:
        import traceback
        traceback.print_exc()
        if analysis_id in ACTIVE_TASKS:
            ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.FAILED
            ACTIVE_TASKS[analysis_id].error = str(e)
            ACTIVE_TASKS[analysis_id].message = f"Analysis failed: {str(e)}"


def run_youtube_pipeline_worker(
    analysis_id: str,
    youtube_url: str,
    song_title: Optional[str] = None
):
    """Downloads audio directly from YouTube and runs end-to-end MIR chord pipeline."""
    try:
        from backend.sources.audio_source import YouTubeAudioExtractor

        def update_download_progress(pct: int, msg: str):
            if analysis_id in ACTIVE_TASKS:
                ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.DOWNLOADING
                ACTIVE_TASKS[analysis_id].progress = max(5, int(pct * 0.15))
                ACTIVE_TASKS[analysis_id].message = msg
                ACTIVE_TASKS[analysis_id].current_stage = "DOWNLOADING"

        ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
            analysis_id=analysis_id,
            status=AnalysisStatusEnum.DOWNLOADING,
            progress=5,
            current_stage="DOWNLOADING",
            message="Connecting to YouTube and extracting audio stream..."
        )

        audio_path, meta = YouTubeAudioExtractor.download_audio(
            url=youtube_url,
            progress_cb=update_download_progress
        )
        audio_path = Path(audio_path)

        final_title = song_title.strip() if song_title and song_title.strip() else meta.get("title", "YouTube Song")

        def update_progress(status: AnalysisStatusEnum, pct: int, msg: str):
            if analysis_id in ACTIVE_TASKS:
                scaled_pct = 15 + int(pct * 0.85)
                ACTIVE_TASKS[analysis_id].status = status
                ACTIVE_TASKS[analysis_id].progress = scaled_pct
                ACTIVE_TASKS[analysis_id].message = msg
                ACTIVE_TASKS[analysis_id].current_stage = status.value

        ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.PREPROCESSING
        ACTIVE_TASKS[analysis_id].progress = 15
        ACTIVE_TASKS[analysis_id].message = "Audio extracted. Preprocessing audio..."
        ACTIVE_TASKS[analysis_id].current_stage = "PREPROCESSING"

        analysis = PIPELINE.process(
            audio_file_path=audio_path,
            song_title=final_title,
            enable_separation=True,
            progress_callback=update_progress
        )

        analysis.id = analysis_id
        analysis.audio_url = f"/api/analysis/{analysis_id}/audio"
        analysis.source_metadata = {
            "type": "youtube",
            "video_id": meta.get("video_id"),
            "youtube_video_id": meta.get("video_id"),
            "url": meta.get("canonical_url", youtube_url),
            "youtube_url": meta.get("canonical_url", youtube_url),
            "title": meta.get("title"),
            "channel": meta.get("channel"),
        }

        ANALYSIS_RESULTS[analysis_id] = analysis
        AUDIO_FILE_PATHS[analysis_id] = audio_path

        try:
            SongRepository.save_analysis(
                analysis=analysis,
                source_audio_path=audio_path,
                song_id=analysis_id,
                source_type="youtube",
                youtube_video_id=meta.get("video_id"),
                youtube_url=meta.get("canonical_url", youtube_url),
                youtube_title=meta.get("title"),
                youtube_channel=meta.get("channel")
            )
        except Exception as repo_err:
            print(f"[Warning] Failed to persist YouTube analysis {analysis_id}: {repo_err}")

        ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.COMPLETED
        ACTIVE_TASKS[analysis_id].progress = 100
        ACTIVE_TASKS[analysis_id].message = "Analysis complete!"
        ACTIVE_TASKS[analysis_id].current_stage = "COMPLETED"

    except Exception as e:
        import traceback
        traceback.print_exc()
        if analysis_id in ACTIVE_TASKS:
            ACTIVE_TASKS[analysis_id].status = AnalysisStatusEnum.FAILED
            ACTIVE_TASKS[analysis_id].error = str(e)
            ACTIVE_TASKS[analysis_id].message = f"YouTube audio analysis failed: {str(e)}"


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    force: bool = Form(False),
    source_type: str = Form("local"),
    youtube_video_id: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    youtube_title: Optional[str] = Form(None),
    youtube_channel: Optional[str] = Form(None)
):
    """
    Accepts user-authorized MP3, WAV, FLAC, or M4A audio files and initiates automatic analysis.
    Performs duplicate detection by content hash and/or YouTube Video ID unless force=True.
    """
    valid_extensions = [".mp3", ".wav", ".flac", ".m4a", ".ogg"]
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in valid_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{file_ext}'. Supported: MP3, WAV, FLAC, M4A"
        )

    analysis_id = str(uuid.uuid4())[:8]
    song_title = title or Path(file.filename).stem.replace("_", " ").title()

    # Save uploaded file to uploads directory
    target_path = UPLOADS_DIR / f"{analysis_id}_{file.filename}"
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Duplicate detection
    if not force:
        try:
            # 1. Check duplicate by YouTube Video ID if present
            if youtube_video_id:
                existing_yt = SongRepository.find_by_youtube_id(youtube_video_id)
                if existing_yt:
                    return {
                        "status": "DUPLICATE_FOUND",
                        "existing_song": existing_yt,
                        "message": "This YouTube video has already been analyzed and is in your History library."
                    }

            # 2. Check duplicate by audio content hash
            import hashlib
            hasher = hashlib.sha256()
            with open(target_path, "rb") as f:
                hasher.update(f.read(2 * 1024 * 1024))
            file_hash = hasher.hexdigest()
            existing = SongRepository.find_by_file_hash(file_hash)
            if existing:
                return {
                    "status": "DUPLICATE_FOUND",
                    "existing_song": existing,
                    "message": "This audio file is already in your History library."
                }
        except Exception as hash_err:
            print(f"[Analyze] Duplicate check error: {hash_err}")

    # Initialize status
    ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=AnalysisStatusEnum.UPLOADING,
        progress=2,
        current_stage="UPLOADING",
        message="Audio received successfully, queuing analysis..."
    )

    # Launch processing in background thread
    worker = threading.Thread(
        target=run_pipeline_worker,
        args=(analysis_id, target_path, song_title, source_type, youtube_video_id, youtube_url, youtube_title, youtube_channel),
        daemon=True
    )
    worker.start()

    return {"analysis_id": analysis_id, "title": song_title, "status": "QUEUED"}


class YouTubeInfoRequest(BaseModel):
    url: str


class YouTubeAnalyzeRequest(BaseModel):
    url: str
    title: Optional[str] = None
    force: bool = False


@router.post("/sources/youtube/info")
async def get_youtube_info(req: YouTubeInfoRequest):
    """
    Validates a YouTube URL and retrieves public video metadata (title, channel, thumbnail, duration).
    Uses fast direct inspection with oEmbed fallback.
    """
    from backend.sources.audio_source import YouTubeReferenceSource, YouTubeAudioExtractor

    clean_url = req.url.strip()
    video_id = YouTubeReferenceSource._extract_video_id(clean_url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Unable to parse this YouTube link. Please check the URL and try again."
        )

    try:
        metadata = YouTubeAudioExtractor.get_video_info(clean_url)
    except Exception:
        source = YouTubeReferenceSource(clean_url)
        metadata = source.get_metadata()
        if not metadata.get("valid"):
            raise HTTPException(
                status_code=400,
                detail=metadata.get("error", "Unable to retrieve information for this YouTube link.")
            )

    # Check if this YouTube video has already been analyzed in user's library
    existing = SongRepository.find_by_youtube_id(video_id)
    if existing:
        metadata["already_in_history"] = True
        metadata["in_library"] = True
        metadata["existing_song"] = existing
        metadata["existing_song_id"] = existing["id"]
        metadata["existing_song_title"] = existing["title"]
    else:
        metadata["in_library"] = False

    return metadata


@router.post("/analyze/youtube")
async def analyze_youtube_endpoint(req: YouTubeAnalyzeRequest):
    """
    Directly extracts audio from a YouTube video and runs full automatic chord recognition.
    Performs duplicate check in SQLite library unless force=True.
    """
    from backend.sources.audio_source import YouTubeReferenceSource

    clean_url = req.url.strip()
    video_id = YouTubeReferenceSource._extract_video_id(clean_url)
    if not video_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube link. Please enter a valid YouTube video or music URL."
        )

    # Duplicate check by video ID unless force=True
    if not req.force:
        existing = SongRepository.find_by_youtube_id(video_id)
        if existing:
            return {
                "status": "DUPLICATE_FOUND",
                "existing_song": existing,
                "message": f"This YouTube video ('{existing['title']}') was already analyzed."
            }

    analysis_id = str(uuid.uuid4())[:8]

    ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=AnalysisStatusEnum.DOWNLOADING,
        progress=5,
        current_stage="DOWNLOADING",
        message="Connecting to YouTube and extracting audio stream..."
    )

    worker = threading.Thread(
        target=run_youtube_pipeline_worker,
        args=(analysis_id, clean_url, req.title),
        daemon=True
    )
    worker.start()

    return {
        "analysis_id": analysis_id,
        "title": req.title or "YouTube Video",
        "status": "QUEUED"
    }


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """Returns the current real-time processing status of the analysis."""
    if analysis_id not in ACTIVE_TASKS:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    return ACTIVE_TASKS[analysis_id]


@router.get("/analysis/{analysis_id}", response_model=SongAnalysis)
async def get_analysis_result(analysis_id: str):
    """Returns the completed SongAnalysis object, restoring from SQLite if needed."""
    if analysis_id in ANALYSIS_RESULTS:
        return ANALYSIS_RESULTS[analysis_id]

    # Try restoring from SQLite persistent library
    analysis = SongRepository.get_analysis(analysis_id)
    if analysis:
        ANALYSIS_RESULTS[analysis_id] = analysis
        song = SongRepository.get_song(analysis_id)
        if song and song.get("audio_path"):
            AUDIO_FILE_PATHS[analysis_id] = Path(song["audio_path"])
        return analysis

    # Check if still running
    if analysis_id in ACTIVE_TASKS and ACTIVE_TASKS[analysis_id].status != AnalysisStatusEnum.COMPLETED:
        raise HTTPException(status_code=202, detail="Analysis still in progress")
    raise HTTPException(status_code=404, detail="Analysis not found")


@router.post("/analysis/{analysis_id}/transpose", response_model=SongAnalysis)
async def transpose_song_chords(analysis_id: str, req: TransposeRequest):
    """
    Transposes song chords by +/- N semitones preserving root, quality, and bass/inversion.
    Operates instantly without re-running audio analysis and auto-persists to SQLite.
    """
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis

    analysis = ANALYSIS_RESULTS[analysis_id]
    transposed = transpose_song(analysis, req.semitones)
    ANALYSIS_RESULTS[analysis_id] = transposed

    try:
        SongRepository.update_analysis_state(
            song_id=analysis_id,
            updated_analysis=transposed,
            transpose_value=req.semitones
        )
    except Exception as err:
        print(f"[Warning] Failed to record transpose in SQLite: {err}")

    return transposed


@router.post("/analysis/{analysis_id}/edit", response_model=SongAnalysis)
async def edit_single_chord(analysis_id: str, req: EditChordRequest):
    """
    Edits a specific chord in the transcription.
    Updates root, quality, bass, and musician display notation,
    logs manual correction for ML feedback learning, and persists to SQLite.
    """
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis

    analysis = ANALYSIS_RESULTS[analysis_id]
    if req.chord_index < 0 or req.chord_index >= len(analysis.chords):
        raise HTTPException(status_code=400, detail="Invalid chord index")

    target = analysis.chords[req.chord_index]
    new_bass = req.new_bass or req.new_root
    from backend.chord.vocabulary import calculate_inversion, QUALITY_DISPLAY_MAP
    new_inv = calculate_inversion(req.new_root, req.new_quality, new_bass) if new_bass != req.new_root else 0
    
    qual_disp = QUALITY_DISPLAY_MAP.get(req.new_quality, req.new_quality)
    display = req.new_display or f"{req.new_root}{qual_disp}"
    if new_bass != req.new_root and not req.new_display:
        display = f"{display}/{new_bass}"

    updated_chord = target.model_copy(update={
        "root": req.new_root,
        "quality": req.new_quality,
        "bass": new_bass,
        "inversion": new_inv,
        "display": display,
        "confidence": 1.0,  # User verified
        "needs_review": False
    })

    analysis.chords[req.chord_index] = updated_chord
    
    # Also update nested bar
    for sec in analysis.sections:
        for b in sec.bars:
            for i, bc in enumerate(b.chords):
                if bc.start_time == target.start_time:
                    b.chords[i] = updated_chord
                    b.display = format_bar_str(b)

    ANALYSIS_RESULTS[analysis_id] = analysis

    # Log manual correction and persist
    try:
        SongRepository.record_chord_edit(
            song_id=analysis_id,
            chord_index=req.chord_index,
            original_chord=target.display,
            updated_chord=updated_chord,
            bar_number=updated_chord.bar_position or 1,
            beat=updated_chord.beat_position or updated_chord.beat or 1,
            updated_analysis=analysis
        )
    except Exception as err:
        print(f"[Warning] Failed to record chord edit in SQLite: {err}")

    return analysis


@router.post("/analysis/{analysis_id}/rename-section", response_model=SongAnalysis)
async def rename_section(analysis_id: str, req: RenameSectionRequest):
    """Renames a musical section (e.g. from 'SECTION A' to 'VERSE 1' or 'CHORUS')."""
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis

    analysis = ANALYSIS_RESULTS[analysis_id]
    found = False
    for sec in analysis.sections:
        if sec.section_id == req.section_id:
            sec.name = req.new_name.strip().upper()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Section ID not found")

    ANALYSIS_RESULTS[analysis_id] = analysis
    try:
        SongRepository.update_analysis_state(
            song_id=analysis_id,
            updated_analysis=analysis
        )
    except Exception as err:
        print(f"[Warning] Failed to persist section rename in SQLite: {err}")

    return analysis


@router.get("/analysis/{analysis_id}/audio")
async def stream_audio(analysis_id: str):
    """Streams original uploaded or library-managed audio for waveform playback."""
    if analysis_id in AUDIO_FILE_PATHS and Path(AUDIO_FILE_PATHS[analysis_id]).exists():
        return FileResponse(str(AUDIO_FILE_PATHS[analysis_id]))

    # Check managed audio library in SQLite
    song = SongRepository.get_song(analysis_id)
    if song and song.get("audio_path") and Path(song["audio_path"]).exists():
        audio_path = Path(song["audio_path"])
        AUDIO_FILE_PATHS[analysis_id] = audio_path
        return FileResponse(str(audio_path))

    raise HTTPException(status_code=404, detail="Audio file not found in library")


# ==========================================================
# HISTORY & SONG LIBRARY ENDPOINTS
# ==========================================================

class RenameSongRequest(BaseModel):
    title: str


@router.get("/history")
async def list_history_songs(
    query: Optional[str] = None,
    sort_by: str = "last_opened",
    favorites_only: bool = False,
    limit: int = 100
):
    """Lists songs in user's library with search, sort, and favorites filter."""
    return SongRepository.list_songs(
        query=query,
        sort_by=sort_by,
        favorites_only=favorites_only,
        limit=limit
    )


@router.get("/history/recent")
async def list_recent_songs(limit: int = 5):
    """Fetches recent songs for quick-access cards on Home screen."""
    return SongRepository.get_recent_songs(limit=limit)


@router.get("/history/{song_id}/open", response_model=SongAnalysis)
async def open_song_from_history(song_id: str):
    """
    Opens a previously analyzed song instantly from SQLite.
    Does NOT rerun Demucs, BTC, or beat tracking.
    """
    analysis = SongRepository.get_analysis(song_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Song not found in library")

    song = SongRepository.get_song(song_id)
    if song and song.get("audio_path"):
        AUDIO_FILE_PATHS[song_id] = Path(song["audio_path"])
    ANALYSIS_RESULTS[song_id] = analysis
    return analysis


@router.post("/history/{song_id}/open", response_model=SongAnalysis)
async def open_song_from_history_post(song_id: str):
    return await open_song_from_history(song_id)


@router.patch("/history/{song_id}/rename")
async def rename_song_entry(song_id: str, req: RenameSongRequest):
    """Renames a song in the library."""
    success = SongRepository.rename_song(song_id, req.title)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to rename song")
    if song_id in ANALYSIS_RESULTS:
        ANALYSIS_RESULTS[song_id].title = req.title.strip()
    return {"success": True, "title": req.title.strip()}


@router.post("/history/{song_id}/favorite")
async def toggle_song_favorite(song_id: str):
    """Toggles song favorite star."""
    is_fav = SongRepository.toggle_favorite(song_id)
    return {"success": True, "is_favorite": is_fav}


@router.post("/history/{song_id}/duplicate")
async def duplicate_song_entry(song_id: str):
    """Duplicates a song analysis record for alternate charts / transpositions."""
    new_id = SongRepository.duplicate_song(song_id)
    if not new_id:
        raise HTTPException(status_code=404, detail="Could not duplicate song")
    return {"success": True, "new_song_id": new_id}


@router.delete("/history/{song_id}")
async def delete_song_entry(song_id: str):
    """Deletes song record from SQLite and managed audio library."""
    success = SongRepository.delete_song(song_id)
    if song_id in ANALYSIS_RESULTS:
        del ANALYSIS_RESULTS[song_id]
    if song_id in AUDIO_FILE_PATHS:
        del AUDIO_FILE_PATHS[song_id]
    return {"success": success}


@router.post("/analysis/{song_id}/reanalyze")
@router.post("/history/{song_id}/reanalyze")
async def reanalyze_song_entry(song_id: str):
    """Explicitly re-analyzes a historical song using the stored library audio and latest music engine."""
    song = SongRepository.get_song(song_id)
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    audio_path = Path(song["audio_path"])
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file missing from library")

    # Clear cached in-memory analysis so fresh results are picked up
    if song_id in ANALYSIS_RESULTS:
        del ANALYSIS_RESULTS[song_id]

    ACTIVE_TASKS[song_id] = AnalysisStatusResponse(
        analysis_id=song_id,
        status=AnalysisStatusEnum.PREPROCESSING,
        progress=5,
        current_stage="PREPROCESSING",
        message="Queuing re-analysis with latest music engine..."
    )

    worker = threading.Thread(
        target=run_pipeline_worker,
        kwargs={
            "analysis_id": song_id,
            "audio_path": audio_path,
            "song_title": song["title"],
            "source_type": song.get("source_type", "local"),
            "youtube_video_id": song.get("youtube_video_id"),
            "youtube_url": song.get("youtube_url"),
            "youtube_title": song.get("youtube_title"),
            "youtube_channel": song.get("youtube_channel")
        },
        daemon=True
    )
    worker.start()

    return {"analysis_id": song_id, "title": song["title"], "status": "QUEUED"}


def sanitize_filename_title(title: str) -> str:
    """
    Sanitizes title to produce safe, clean Windows filenames.
    Replaces / and \\ with -, replaces illegal characters with _,
    condenses delimiters and trims.
    Example: 'Song: A/B * Live?' -> 'Song_A-B_Live'
    """
    clean = re.sub(r'[/\\]', '-', title)
    clean = re.sub(r'[<>:"|?*\x00-\x1f\uff5c]', '_', clean)
    clean = re.sub(r'\s+', ' ', clean)
    clean = re.sub(r'\s*_\s*', '_', clean)
    clean = re.sub(r'_+', '_', clean).strip(' ._-')
    return clean or "Song"


def get_safe_export_filename(title: str, extension: str) -> tuple[str, str]:
    """
    Returns (ascii_filename, content_disposition_header).
    Prevents UnicodeEncodeError in HTTP headers by ensuring latin-1 compatibility
    while supplying UTF-8 encoded names via RFC 5987 / RFC 6266.
    Follows required naming convention:
    - pdf:  {clean_title}_ChordSheet.pdf
    - txt:  {clean_title}_ChordSheet.txt
    - json: {clean_title}_Analysis.json
    """
    clean_title = sanitize_filename_title(title)
    
    if extension == "pdf":
        suffix = "ChordSheet.pdf"
    elif extension == "txt":
        suffix = "ChordSheet.txt"
    elif extension == "json":
        suffix = "Analysis.json"
    else:
        suffix = f"Chords.{extension}"

    filename_utf8 = f"{clean_title}_{suffix}"

    # ASCII-only fallback for HTTP latin-1 header requirement
    ascii_title = clean_title.encode('ascii', 'ignore').decode('ascii').strip(' ._-') or "Song"
    filename_ascii = f"{ascii_title}_{suffix}"

    disposition = f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{quote(filename_utf8)}'
    return filename_ascii, disposition


@router.get("/analysis/{analysis_id}/export/pdf")
async def export_pdf(analysis_id: str):
    """Downloads clean, printable PDF chord sheet."""
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis
    analysis = ANALYSIS_RESULTS[analysis_id]
    filename_ascii, disposition = get_safe_export_filename(analysis.title, "pdf")
    pdf_path = EXPORTS_DIR / filename_ascii
    export_to_pdf(analysis, pdf_path)
    return FileResponse(
        str(pdf_path),
        media_type="application/pdf",
        filename=filename_ascii,
        headers={"Content-Disposition": disposition}
    )


@router.get("/analysis/{analysis_id}/export/txt")
async def export_txt(analysis_id: str):
    """Downloads monospace plain-text chord chart."""
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis
    analysis = ANALYSIS_RESULTS[analysis_id]
    txt_content = export_to_txt(analysis)
    filename_ascii, disposition = get_safe_export_filename(analysis.title, "txt")
    return PlainTextResponse(
        txt_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": disposition}
    )


@router.get("/analysis/{analysis_id}/export/json")
async def export_json_endpoint(analysis_id: str):
    """Downloads complete structured transcription JSON."""
    if analysis_id not in ANALYSIS_RESULTS:
        analysis = SongRepository.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        ANALYSIS_RESULTS[analysis_id] = analysis
    analysis = ANALYSIS_RESULTS[analysis_id]
    filename_ascii, disposition = get_safe_export_filename(analysis.title, "json")
    export_dict = build_complete_json_export(analysis)
    return JSONResponse(
        content=export_dict,
        headers={"Content-Disposition": disposition}
    )
