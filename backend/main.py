"""
Main FastAPI Application Entrypoint.
Provides CORS, health check, model diagnostics, and mounts API router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import torch

from backend.config import BASE_DIR, DEVICE_NAME, CUDA_AVAILABLE, FFMPEG_PATH, PYTHON_EXECUTABLE
from backend.api.routes import router

app = FastAPI(
    title="Song Chord Analyzer API",
    description="Automated MIR & Automatic Chord Recognition backend",
    version="1.0.0"
)

# Enable CORS for local Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, prefix="/api")

@app.get("/api/health")
@app.get("/health")
async def health_check():
    """System and hardware diagnostics endpoint."""
    vram_free_mb = 0
    vram_total_mb = 0
    if CUDA_AVAILABLE:
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        vram_free_mb = round(free_bytes / (1024 * 1024), 1)
        vram_total_mb = round(total_bytes / (1024 * 1024), 1)

    return {
        "status": "healthy",
        "device": DEVICE_NAME,
        "cuda_available": CUDA_AVAILABLE,
        "vram_free_mb": vram_free_mb,
        "vram_total_mb": vram_total_mb,
        "ffmpeg_path": FFMPEG_PATH,
        "python_executable": PYTHON_EXECUTABLE
    }

# Serve frontend build if dist exists
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
