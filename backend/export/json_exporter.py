"""
Structured JSON exporter.
Preserves full musical metadata, confidence, and chord timings matching prompt schema.
"""

import json
from pathlib import Path
from backend.models.schemas import SongAnalysis


def export_to_json(analysis: SongAnalysis, output_path: Path) -> Path:
    """Exports complete SongAnalysis object as formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(analysis.model_dump_json(indent=2))
    return output_path
