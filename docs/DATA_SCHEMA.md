# Data Schema Contract (`SongAnalysis` v1.0.0)

The `SongAnalysis` JSON schema is the **central shared contract** defining musical data exchange across the Python MIR backend, FastAPI server, Flutter Android application, and Electron desktop shell.

**Formal Specification:** `shared/music_schema/song_analysis.schema.json`  
**JSON Schema Dialect:** JSON Schema Draft 2020-12  
**Contract Version:** `1.0.0`  

---

## 1. Root Object Hierarchy

```
SongAnalysis
├── schema_version: "1.0.0"
├── id: string (UUID8)
├── title: string
├── audio_url: string (optional)
├── metadata: AudioMetadata
├── pipeline_metadata: PipelineMetadata
├── key: KeyInfo
├── tempo: TempoInfo
├── meter: MeterInfo
├── beat_grid: BeatGrid
├── sections: MusicalSection[]
├── chords: ChordPrediction[]
├── bars: Bar[]
├── raw_predictions: RawPrediction[] (optional)
└── debug_view: DebugBarEntry[] (optional)
```

---

## 2. Field-by-Field Technical Reference

### 2.1 Metadata Objects

#### `metadata` (`AudioMetadata`)
- `filename` *(string, required)*: Original filename (e.g. `"Bekhayali.mp3"`).
- `duration` *(number, required, $\ge 0$)*: Total audio duration in seconds.
- `sample_rate` *(integer, required)*: Audio sample rate in Hz (e.g. `44100` or `22050`).
- `channels` *(integer, required)*: Channel count (`1` = mono, `2` = stereo).
- `format` *(string, required)*: Container format (`"mp3"`, `"wav"`, etc.).
- `file_size_bytes` *(integer, optional)*: Audio file size on disk.
- `file_hash` *(string, optional)*: SHA-256 audio content digest.

#### `pipeline_metadata` (`PipelineMetadata`)
- `app_version` *(string)*: Application version (e.g. `"1.0.0"`).
- `model_name` *(string)*: Chord recognition model identifier (`"BTC-Transformer"`).
- `model_version` *(string)*: Model weights version (`"large_voca_170"`).
- `separation_model` *(string)*: Stem separation architecture (`"htdemucs_v4"`).
- `device_used` *(string)*: Hardware execution target (`"cuda:0"` or `"cpu"`).
- `timestamp` *(string)*: ISO 8601 UTC analysis timestamp.

---

### 2.2 Harmonic & Metric Descriptors

#### `key` (`KeyInfo`)
- `tonic` *(string, required)*: Root note letter (e.g. `"Bb"`, `"C"`, `"F#"`).
- `mode` *(string, required)*: `"major"` or `"minor"`.
- `display` *(string, required)*: Formatted key string (e.g. `"Bb Minor"`).
- `confidence` *(number, required, $0.0 \le c \le 1.0$)*: K-S profile correlation confidence score.

#### `tempo` (`TempoInfo`)
- `bpm` *(number, required, $30.0 \le 	ext{bpm} \le 300.0$)*: Master tempo in beats per minute (e.g. `86.1`).
- `confidence` *(number, required)*: Autocorrelation peak confidence score.
- `candidate_bpms` *(number[], optional)*: Multi-hypothesis tempo candidates (e.g. `[43.05, 86.1, 172.2]`).
- `beat_period` *(number, optional)*: Average duration between beats ($60.0 / 	ext{bpm}$).

#### `meter` (`MeterInfo`)
- `numerator` *(integer, required, $\ge 1$)*: Beats per measure (`2`, `3`, `4`, `6`, `7`, `12`).
- `denominator` *(integer, required, $\ge 1$)*: Note value receiving one beat (`4` or `8`).
- `display` *(string, required)*: Standard time signature string (e.g. `"4/4"`, `"3/4"`, `"7/8"`).
- `confidence` *(number, required)*: Metric classification confidence score.
- `subdivisions` *(integer[], optional)*: Additive meter subdivisions (e.g. `[2, 2, 3]` for 7/8).

---

### 2.3 Rhythmic Grids & Structure

#### `beat_grid` (`BeatGrid`)
- `bpm` *(number, required)*: Calibrated tempo.
- `beats` *(number[], required)*: Array of floating-point timestamps in seconds for every detected musical beat.
- `downbeats` *(number[], required)*: Array of timestamps marking the first beat of each musical bar.
- `confidence` *(number, optional)*: Overall beat tracking reliability metric.

#### `sections` (`MusicalSection[]`)
- Array of structural sections detected via recurrence matrix clustering:
  - `name` *(string)*: Neutral structural label (`"INTRO"`, `"SECTION A"`, `"SECTION B"`, `"OUTRO"`).
  - `start_time` *(number)*: Start time in seconds.
  - `end_time` *(number)*: End time in seconds.
  - `bar_start` *(integer)*: 0-indexed starting bar number.
  - `bar_end` *(integer)*: 0-indexed ending bar number.

---

### 2.4 Chords & Bar Measures

#### `chords` (`ChordPrediction[]`)
Continuous array of recognized chords aligned to beat intervals:
- `root` *(string, required)*: Chord root note (e.g. `"D"`, `"Bb"`).
- `quality` *(string, required)*: Harmonic quality (`"maj"`, `"min"`, `"7"`, `"sus4"`, etc.).
- `bass` *(string, optional)*: Physical sounding bass note for slash chords (e.g. `"F#"` in `D/F#`).
- `display` *(string, required)*: Formatted chord label (e.g. `"Dm"`, `"Asus4"`, `"C/E"`).
- `start_time` *(number, required)*: Chord start timestamp in seconds.
- `end_time` *(number, required)*: Chord end timestamp in seconds.
- `confidence` *(number, required)*: Posterior probability score ($0.0 \le c \le 1.0$).

#### `bars` (`Bar[]`)
Structured musical measures for chord sheet and PDF formatting:
- `bar_number` *(integer, required)*: 0-indexed measure index (`0`, `1`, `2`, ...).
- `start_time` *(number, required)*: Exact measure start timestamp.
- `end_time` *(number, required)*: Exact measure end timestamp.
- `chords` *(ChordPrediction[], required)*: Chords sounding within this specific measure.
- `time_signature` *(string, optional)*: Time signature override if metric modulation occurs.
