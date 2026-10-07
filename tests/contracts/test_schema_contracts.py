import json
from pathlib import Path
import unittest
import jsonschema

from backend.models.schemas import (
    SongAnalysis,
    AudioMetadata,
    PipelineMetadata,
    MeterAnalysis,
    TempoAnalysis,
    KeyAnalysis,
    BeatGrid,
    MusicalSection,
    Bar,
    ChordPrediction
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class TestSchemaContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_path = PROJECT_ROOT / "shared" / "music_schema" / "song_analysis.schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            cls.schema = json.load(f)

    def test_schema_json_is_valid_draft202012(self):
        validator_cls = jsonschema.validators.validator_for(self.schema)
        validator_cls.check_schema(self.schema)

    def test_canonical_song_analysis_validates_against_schema(self):
        chord = ChordPrediction(
            root="Bb",
            quality="min",
            bass="Bb",
            inversion=0,
            display="Bbm",
            start_time=0.0,
            end_time=1.5,
            duration=1.5,
            confidence=0.96
        )
        bar = Bar(
            bar_number=1,
            start_time=0.0,
            end_time=2.0,
            beats=4,
            chords=[chord],
            display="Bbm",
            time_signature="4/4"
        )
        section = MusicalSection(
            section_id="sec-1",
            name="INTRO",
            start_time=0.0,
            end_time=2.0,
            start_bar=1,
            end_bar=1,
            bars=[bar]
        )
        analysis = SongAnalysis(
            schema_version="1.0.0",
            id="contract-test-01",
            title="Golden Contract Track",
            metadata=AudioMetadata(
                filename="golden.wav",
                duration=120.0,
                sample_rate=44100,
                channels=2,
                format="wav",
                file_size_bytes=21168000,
                file_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
            ),
            pipeline_metadata=PipelineMetadata(),
            key=KeyAnalysis(
                tonic="Bb",
                mode="minor",
                display="Bb Minor",
                confidence=0.98
            ),
            tempo=TempoAnalysis(
                bpm=86.1,
                confidence=0.95
            ),
            meter=MeterAnalysis(
                numerator=4,
                denominator=4,
                display="4/4",
                confidence=0.99
            ),
            beat_grid=BeatGrid(
                bpm=86.1,
                beats=[0.0, 0.697, 1.394],
                downbeats=[0.0]
            ),
            sections=[section],
            chords=[chord],
            transpose_semitones=0
        )

        data = json.loads(analysis.model_dump_json())
        jsonschema.validate(instance=data, schema=self.schema)

    def test_schema_rejects_out_of_bounds_transpose(self):
        # Transpose > 12 or < -12 must fail JSON schema validation
        chord = ChordPrediction(
            root="C",
            quality="maj",
            bass="C",
            inversion=0,
            display="C",
            start_time=0.0,
            end_time=1.0,
            duration=1.0,
            confidence=1.0
        )
        analysis = SongAnalysis(
            schema_version="1.0.0",
            id="bad-trans-01",
            title="Bad Transpose",
            metadata=AudioMetadata(
                filename="a.wav",
                duration=10.0,
                sample_rate=44100,
                channels=2,
                format="wav",
                file_size_bytes=1000,
                file_hash="hash"
            ),
            pipeline_metadata=PipelineMetadata(),
            key=KeyAnalysis(tonic="C", mode="major", display="C Major", confidence=1.0),
            tempo=TempoAnalysis(bpm=120.0, confidence=1.0),
            meter=MeterAnalysis(),
            beat_grid=BeatGrid(bpm=120.0, beats=[0.0], downbeats=[0.0]),
            sections=[],
            chords=[chord],
            transpose_semitones=0
        )

        data = json.loads(analysis.model_dump_json())
        data["transpose_semitones"] = 15  # Violates schema maximum 12

        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=self.schema)

    def test_supported_time_signatures_contract(self):
        supported = ["2/4", "3/4", "4/4", "6/8", "7/8", "12/8"]
        for ts in supported:
            num, den = map(int, ts.split("/"))
            meter = MeterAnalysis(numerator=num, denominator=den, display=ts)
            self.assertEqual(meter.display, ts)
            self.assertEqual(meter.numerator, num)
            self.assertEqual(meter.denominator, den)

if __name__ == "__main__":
    unittest.main()
