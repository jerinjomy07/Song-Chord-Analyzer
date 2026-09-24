"""
Application configuration, hardware probing, and Windows path resolution.
Uses standard Windows AppData directories, bundled application resources,
and dynamic hardware detection (CUDA GPU / CPU fallback).
"""

import os
import sys
import shutil
from pathlib import Path
import torch

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Standard Windows AppData directory for application storage
# %LOCALAPPDATA%\SongChordAnalyzer or %APPDATA%\SongChordAnalyzer
custom_data_dir = os.environ.get("SONG_CHORD_ANALYZER_DATA_DIR")
if custom_data_dir:
    STORAGE_DIR = Path(custom_data_dir)
else:
    local_app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    STORAGE_DIR = Path(local_app_data) / "SongChordAnalyzer"

# Application storage subdirectories
MODELS_DIR = STORAGE_DIR / "models"
CACHE_DIR = STORAGE_DIR / "cache"
TEMP_DIR = STORAGE_DIR / "temp"
EXPORTS_DIR = STORAGE_DIR / "exports"
LOGS_DIR = STORAGE_DIR / "logs"
UPLOADS_DIR = STORAGE_DIR / "uploads"
STEMS_DIR = STORAGE_DIR / "stems"

for d in [MODELS_DIR, CACHE_DIR, TEMP_DIR, EXPORTS_DIR, LOGS_DIR, UPLOADS_DIR, STEMS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Also check project-level models directory for bundled/downloaded weights
PROJECT_MODELS_DIR = BASE_DIR / "models"

# Dynamic FFmpeg detection:
# 1. Environment variable override
# 2. Bundled resource path in desktop app (resources/ffmpeg/ffmpeg.exe)
# 3. System PATH
def resolve_ffmpeg_path() -> str:
    env_ffmpeg = os.environ.get("SONG_CHORD_ANALYZER_FFMPEG")
    if env_ffmpeg and os.path.exists(env_ffmpeg):
        return env_ffmpeg

    # Check Electron / packaged resources directory (dev & prod)
    candidates = [
        BASE_DIR / "resources" / "ffmpeg" / "ffmpeg.exe",
        BASE_DIR.parent / "ffmpeg" / "ffmpeg.exe",
        BASE_DIR.parent / "resources" / "ffmpeg" / "ffmpeg.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    # Check system PATH
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg

    return "ffmpeg"

FFMPEG_PATH = resolve_ffmpeg_path()

# Dynamic Python executable resolution:
def resolve_python_path() -> str:
    env_py = os.environ.get("SONG_CHORD_ANALYZER_PYTHON")
    if env_py and os.path.exists(env_py):
        return env_py

    candidates = [
        BASE_DIR / "resources" / "python" / "python.exe",
        BASE_DIR.parent / "python" / "python.exe",
        BASE_DIR.parent / "resources" / "python" / "python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)

    return sys.executable

PYTHON_EXECUTABLE = resolve_python_path()

# Hardware capabilities probing
class HardwareCapabilities:
    def __init__(self):
        self.cuda_available = torch.cuda.is_available()
        self.device = "cuda" if self.cuda_available else "cpu"
        self.gpu_name = torch.cuda.get_device_name(0) if self.cuda_available else "CPU"
        
        self.vram_total_mb = 0.0
        self.vram_free_mb = 0.0
        if self.cuda_available:
            try:
                free_b, total_b = torch.cuda.mem_get_info()
                self.vram_free_mb = round(free_b / (1024 * 1024), 1)
                self.vram_total_mb = round(total_b / (1024 * 1024), 1)
            except Exception:
                pass

        self.cpu_count = os.cpu_count() or 4
        
        # Calculate total RAM (psutil or Windows API fallback)
        ram_gb = 16.0
        try:
            import psutil
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        except Exception:
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                ram_gb = round(stat.ullTotalPhys / (1024 ** 3), 1)
            except Exception:
                pass
        self.ram_total_gb = ram_gb

    def to_dict(self):
        return {
            "cuda_available": self.cuda_available,
            "device": self.device,
            "gpu_name": self.gpu_name,
            "vram_total_mb": self.vram_total_mb,
            "vram_free_mb": self.vram_free_mb,
            "cpu_count": self.cpu_count,
            "ram_total_gb": self.ram_total_gb
        }

HARDWARE = HardwareCapabilities()
DEFAULT_DEVICE = HARDWARE.device
CUDA_AVAILABLE = HARDWARE.cuda_available
DEVICE_NAME = HARDWARE.gpu_name

# Component-specific audio parameters
DEMUCS_SAMPLE_RATE = 44100
BTC_SAMPLE_RATE = 22050
BASS_SAMPLE_RATE = 22050
BEAT_SAMPLE_RATE = 22050
TARGET_SAMPLE_RATE = 22050
SEPARATION_SAMPLE_RATE = 44100

CQT_HOP_LENGTH = 2048
CQT_N_BINS = 144
CQT_BINS_PER_OCTAVE = 24
BTC_TIMESTEP = 108

BTC_MODEL_DOWNLOAD_URL = "https://raw.githubusercontent.com/ptnghia-j/ChordMini/main/checkpoints/btc_model_large_voca.pt"

# Model checkpoint paths
def resolve_btc_checkpoint() -> Path:
    # First check AppData models directory
    appdata_ckpt = MODELS_DIR / "btc_model_large_voca.pt"
    if appdata_ckpt.exists() and appdata_ckpt.stat().st_size > 1_000_000:
        return appdata_ckpt

    # Check project-level directory
    project_ckpt = PROJECT_MODELS_DIR / "btc" / "btc_model_large_voca.pt"
    if project_ckpt.exists() and project_ckpt.stat().st_size > 1_000_000:
        return project_ckpt

    # Auto-download on first launch if missing
    try:
        import urllib.request
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Config] Fetching BTC chord recognition checkpoint from {BTC_MODEL_DOWNLOAD_URL}...")
        urllib.request.urlretrieve(BTC_MODEL_DOWNLOAD_URL, str(appdata_ckpt))
        print(f"[Config] Successfully downloaded model checkpoint ({appdata_ckpt.stat().st_size} bytes)")
        return appdata_ckpt
    except Exception as e:
        print(f"[Config] Warning: Could not auto-download model checkpoint: {e}")
        return appdata_ckpt

BTC_CHECKPOINT_PATH = resolve_btc_checkpoint()

print(f"[Config] Initialized Storage: {STORAGE_DIR}")
print(f"[Config] Device: {DEVICE_NAME} ({DEFAULT_DEVICE}) | VRAM: {HARDWARE.vram_free_mb}/{HARDWARE.vram_total_mb} MB")
print(f"[Config] FFmpeg: {FFMPEG_PATH}")
