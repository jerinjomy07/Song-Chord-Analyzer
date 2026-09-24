"""
Structured JSON exporter.
Preserves full musical metadata, confidence, and chord timings matching prompt schema.
"""

import json
from pathlib import Path
from backend.models.schemas import SongAnalysis


def build_complete_json_export(analysis: SongAnalysis) -> dict:
    """
    Constructs comprehensive structured analysis dictionary matching prompt requirements:
    - song metadata
    - key, mode
    - BPM, time signature
    - beats, bars, sections
    - raw chord predictions if available
    - final chord predictions with root, quality, bass, inversion, timestamps, beat position, bar position, confidence
    - model version, pipeline version
    """
    chords_export = []
    for c in analysis.chords:
        chords_export.append({
            "display_chord": c.display,
            "root": c.root,
            "quality": c.quality,
            "bass": c.bass,
            "inversion": c.inversion,
            "start_time": round(c.start_time, 3),
            "end_time": round(c.end_time, 3),
            "duration": round(c.duration, 3),
            "bar": c.bar_position or 1,
            "beat": c.beat_position or c.beat or 1,
            "beat_duration": c.beat_duration,
            "confidence": round(c.confidence, 4),
            "needs_review": c.needs_review,
            "alternatives": [alt.model_dump() for alt in c.alternatives] if c.alternatives else []
        })

    sections_export = []
    for sec in analysis.sections:
        sec_bars = []
        for b in sec.bars:
            sec_bars.append({
                "bar_number": b.bar_number,
                "start_time": round(b.start_time, 3),
                "end_time": round(b.end_time, 3),
                "beats": b.beats,
                "time_signature": b.time_signature,
                "display": b.display,
                "chords": [
                    {
                        "display_chord": bc.display,
                        "root": bc.root,
                        "quality": bc.quality,
                        "bass": bc.bass,
                        "inversion": bc.inversion,
                        "start_time": round(bc.start_time, 3),
                        "end_time": round(bc.end_time, 3),
                        "beat": bc.beat or 1,
                        "confidence": round(bc.confidence, 4)
                    }
                    for bc in b.chords
                ]
            })
        sections_export.append({
            "section_id": sec.section_id,
            "name": sec.name,
            "start_time": round(sec.start_time, 3),
            "end_time": round(sec.end_time, 3),
            "start_bar": sec.start_bar,
            "end_bar": sec.end_bar,
            "is_repeated": sec.is_repeated,
            "bars": sec_bars
        })

    return {
        "song_metadata": {
            "title": analysis.title,
            "filename": analysis.metadata.filename,
            "duration": round(analysis.metadata.duration, 3),
            "sample_rate": analysis.metadata.sample_rate,
            "channels": analysis.metadata.channels,
            "format": analysis.metadata.format,
            "file_size_bytes": analysis.metadata.file_size_bytes,
            "file_hash": analysis.metadata.file_hash,
        },
        "musical_attributes": {
            "key": analysis.key.tonic,
            "mode": analysis.key.mode,
            "key_display": analysis.key.display,
            "key_confidence": round(analysis.key.confidence, 4),
            "bpm": round(analysis.tempo.bpm, 2),
            "tempo_confidence": round(analysis.tempo.confidence, 4),
            "time_signature": analysis.meter.display,
            "beats": [round(b, 3) for b in (analysis.beat_grid.beats or [])],
            "downbeats": [round(db, 3) for db in (analysis.beat_grid.downbeats or [])],
            "transpose_semitones": analysis.transpose_semitones,
        },
        "pipeline_metadata": {
            "model_version": analysis.pipeline_metadata.model_version,
            "pipeline_version": analysis.pipeline_metadata.app_version,
            "model_name": analysis.pipeline_metadata.model_name,
            "separation_model": analysis.pipeline_metadata.separation_model,
            "device_used": analysis.pipeline_metadata.device_used,
            "timestamp": analysis.pipeline_metadata.timestamp,
        },
        "final_chord_predictions": chords_export,
        "sections": sections_export,
        "raw_chord_predictions": analysis.raw_predictions or []
    }


def export_to_json(analysis: SongAnalysis, output_path: Path) -> Path:
    """Exports complete SongAnalysis object as formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_dict = build_complete_json_export(analysis)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_dict, f, indent=2, ensure_ascii=False)
    return output_path

