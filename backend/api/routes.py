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
from backend.export.json_exporter import export_to_json

router = APIRouter()

# In-memory session store
ACTIVE_TASKS: Dict[str, AnalysisStatusResponse] = {}
ANALYSIS_RESULTS: Dict[str, SongAnalysis] = {}
AUDIO_FILE_PATHS: Dict[str, Path] = {}

# Pipeline singleton
PIPELINE = SongAnalyzerPipeline()


def run_pipeline_worker(analysis_id: str, audio_path: Path, song_title: str):
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


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None)
):
    """
    Accepts MP3, WAV, FLAC, or M4A audio files and initiates automatic analysis.
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

    # Initialize status
    ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
        analysis_id=analysis_id,
        status=AnalysisStatusEnum.UPLOADING,
        progress=2,
        current_stage="UPLOADING",
        message="File uploaded successfully, queuing analysis..."
    )

    # Launch processing in background thread
    worker = threading.Thread(
        target=run_pipeline_worker,
        args=(analysis_id, target_path, song_title),
        daemon=True
    )
    worker.start()

    return {"analysis_id": analysis_id, "title": song_title, "status": "QUEUED"}


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatusResponse)
async def get_analysis_status(analysis_id: str):
    """Returns the current real-time processing status of the analysis."""
    if analysis_id not in ACTIVE_TASKS:
        raise HTTPException(status_code=404, detail="Analysis ID not found")
    return ACTIVE_TASKS[analysis_id]


@router.get("/analysis/{analysis_id}", response_model=SongAnalysis)
async def get_analysis_result(analysis_id: str):
    """Returns the completed SongAnalysis object."""
    if analysis_id not in ANALYSIS_RESULTS:
        # Check if still running
        if analysis_id in ACTIVE_TASKS and ACTIVE_TASKS[analysis_id].status != AnalysisStatusEnum.COMPLETED:
            raise HTTPException(status_code=202, detail="Analysis still in progress")
        raise HTTPException(status_code=404, detail="Analysis not found")
    return ANALYSIS_RESULTS[analysis_id]


@router.post("/analysis/{analysis_id}/transpose", response_model=SongAnalysis)
async def transpose_song_chords(analysis_id: str, req: TransposeRequest):
    """
    Transposes song chords by +/- N semitones preserving root, quality, and bass/inversion.
    Operates instantly without re-running audio analysis.
    """
    if analysis_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = ANALYSIS_RESULTS[analysis_id]
    transposed = transpose_song(analysis, req.semitones)
    ANALYSIS_RESULTS[analysis_id] = transposed
    return transposed


@router.post("/analysis/{analysis_id}/edit", response_model=SongAnalysis)
async def edit_single_chord(analysis_id: str, req: EditChordRequest):
    """
    Edits a specific chord in the transcription.
    Updates root, quality, bass, and musician display notation.
    """
    if analysis_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis not found")

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
    return analysis


@router.post("/analysis/{analysis_id}/rename-section", response_model=SongAnalysis)
async def rename_section(analysis_id: str, req: RenameSectionRequest):
    """Renames a musical section (e.g. from 'SECTION A' to 'VERSE 1' or 'CHORUS')."""
    if analysis_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis not found")

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
    return analysis


@router.get("/analysis/{analysis_id}/audio")
async def stream_audio(analysis_id: str):
    """Streams original uploaded audio for waveform playback."""
    if analysis_id not in AUDIO_FILE_PATHS:
        raise HTTPException(status_code=404, detail="Audio file not found")
    audio_path = AUDIO_FILE_PATHS[analysis_id]
    return FileResponse(str(audio_path))


def get_safe_export_filename(title: str, extension: str) -> tuple[str, str]:
    """
    Returns (ascii_filename, content_disposition_header).
    Prevents UnicodeEncodeError in HTTP headers by ensuring latin-1 compatibility
    while supplying UTF-8 encoded names via RFC 5987 / RFC 6266.
    """
    # Replace illegal/troublesome characters for Windows paths and headers
    safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f\uff5c]', '_', title).strip()
    safe_title = re.sub(r'_+', '_', safe_title).strip(' ._')
    if not safe_title:
        safe_title = "Song"

    # ASCII-only fallback for HTTP latin-1 header requirement
    ascii_title = safe_title.encode('ascii', 'ignore').decode('ascii').strip(' ._')
    if not ascii_title:
        ascii_title = "Song"

    filename_ascii = f"{ascii_title}_Chords.{extension}"
    filename_utf8 = f"{safe_title}_Chords.{extension}"

    disposition = f'attachment; filename="{filename_ascii}"; filename*=UTF-8\'\'{quote(filename_utf8)}'
    return filename_ascii, disposition


@router.get("/analysis/{analysis_id}/export/pdf")
async def export_pdf(analysis_id: str):
    """Downloads clean, printable PDF chord sheet."""
    if analysis_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis not found")
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
        raise HTTPException(status_code=404, detail="Analysis not found")
    analysis = ANALYSIS_RESULTS[analysis_id]
    txt_content = export_to_txt(analysis)
    _, disposition = get_safe_export_filename(analysis.title, "txt")
    return PlainTextResponse(
        txt_content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": disposition}
    )


@router.get("/analysis/{analysis_id}/export/json")
async def export_json_endpoint(analysis_id: str):
    """Downloads complete structured transcription JSON."""
    if analysis_id not in ANALYSIS_RESULTS:
        raise HTTPException(status_code=404, detail="Analysis not found")
    analysis = ANALYSIS_RESULTS[analysis_id]
    _, disposition = get_safe_export_filename(analysis.title, "json")
    return JSONResponse(
        content=analysis.model_dump(),
        headers={"Content-Disposition": disposition}
    )
