export interface ChordCandidate {
  chord: string;
  probability: number;
}

export interface ChordPrediction {
  root: string;
  quality: string;
  bass: string;
  inversion: number;
  display: string;
  start_time: number;
  end_time: number;
  duration: number;
  beat_position?: number;
  bar_position?: number;
  beat?: number;
  beat_duration?: number;
  confidence: number;
  needs_review: boolean;
  alternatives: ChordCandidate[];
}

export interface Bar {
  bar_number: number;
  start_time: number;
  end_time: number;
  beats?: number;
  chords: ChordPrediction[];
  time_signature: string;
  display?: string;
}

export interface MusicalSection {
  section_id: string;
  name: string;
  start_time: number;
  end_time: number;
  start_bar: number;
  end_bar: number;
  bars: Bar[];
  is_repeated: boolean;
  repeat_of_section_id?: string;
}

export interface KeyAnalysis {
  tonic: string;
  mode: string;
  display: string;
  confidence: number;
}

export interface TempoAnalysis {
  bpm: number;
  confidence: number;
  is_estimated: boolean;
}

export interface MeterAnalysis {
  numerator: number;
  denominator: number;
  display: string;
  confidence: number;
  is_estimated: boolean;
}

export interface AudioMetadata {
  filename: string;
  duration: number;
  sample_rate: number;
  channels: number;
  format: string;
  file_size_bytes: number;
  file_hash: string;
}

export interface PipelineMetadata {
  app_version: string;
  model_name: string;
  model_version: string;
  separation_model: string;
  device_used: string;
  timestamp: string;
}

export interface ChordEventDebug {
  beat: number;
  beat_duration: number;
  chord: string;
  start: number;
  end: number;
  confidence: number;
}

export interface DebugViewEntry {
  bar_number: number;
  time: string;
  raw_predictions: string[];
  beat_pooled: string[];
  sounding_bass: string;
  musical_result: string[];
  final_display: string;
  chord_events?: ChordEventDebug[];
}

export interface SongAnalysis {
  id: string;
  title: string;
  metadata: AudioMetadata;
  pipeline_metadata: PipelineMetadata;
  key: KeyAnalysis;
  tempo: TempoAnalysis;
  meter: MeterAnalysis;
  sections: MusicalSection[];
  chords: ChordPrediction[];
  transpose_semitones: number;
  audio_url?: string;
  has_stems: boolean;
  debug_view?: DebugViewEntry[];
}

export type AnalysisStatus = 
  | "IDLE"
  | "UPLOADING"
  | "VALIDATING"
  | "PREPROCESSING"
  | "SEPARATING"
  | "ANALYZING_BEATS"
  | "ANALYZING_KEY"
  | "ANALYZING_CHORDS"
  | "ANALYZING_INVERSION"
  | "ALIGNING_BARS"
  | "DETECTING_SECTIONS"
  | "POST_PROCESSING"
  | "BUILDING_SHEET"
  | "COMPLETED"
  | "FAILED";

export interface AnalysisStatusResponse {
  analysis_id: string;
  status: AnalysisStatus;
  progress: number;
  current_stage: string;
  message: string;
  error?: string;
}

export interface DesktopAPI {
  isElectron: boolean;
  platform: string;
  versions: {
    electron: string;
    chrome: string;
    node: string;
  };
  openFileDialog: () => Promise<{ canceled: boolean; filePaths: string[] }>;
  showSaveDialog: (options: any) => Promise<{ canceled: boolean; filePath?: string }>;
  saveExportFile: (payload: {
    defaultFilename: string;
    format: 'pdf' | 'txt' | 'json';
    content: string;
    isBase64?: boolean;
  }) => Promise<{ success: boolean; canceled?: boolean; filePath?: string; filename?: string; error?: string }>;
  minimizeWindow: () => void;
  maximizeWindow: () => void;
  closeWindow: () => void;
  getBackendInfo: () => Promise<{ port: number; python: string }>;
}

export interface HistorySong {
  id: string;
  title: string;
  original_filename: string;
  file_hash: string;
  duration: number;
  format: string;
  key_display: string;
  key_mode: string;
  bpm: number;
  time_signature: string;
  transpose_value: number;
  is_favorite: number | boolean;
  created_at: string;
  updated_at: string;
  last_opened_at: string;
  model_version?: string;
  pipeline_version?: string;
  edit_count: number;
}

export interface DuplicateCheckResponse {
  status: "DUPLICATE_FOUND";
  existing_song: HistorySong;
  message: string;
}

declare global {
  interface Window {
    desktopAPI?: DesktopAPI;
  }
}

