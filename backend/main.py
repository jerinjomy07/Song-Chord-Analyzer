"""
Main FastAPI Application Entrypoint.
Provides CORS, health check, model diagnostics, and mounts API router.
"""

import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import torch

from backend.config import (
    BASE_DIR, DEVICE_NAME, CUDA_AVAILABLE, FFMPEG_PATH, PYTHON_EXECUTABLE,
    BTC_CHECKPOINT_PATH, HARDWARE
)
from backend.api.routes import router, shutdown_analysis_executor



@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await asyncio.to_thread(shutdown_analysis_executor)

app = FastAPI(
    title="Song Chord Analyzer API",
    description="Automated MIR & Automatic Chord Recognition backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration supporting environment override and explicit dev defaults
cors_origins_env = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
if cors_origins_env:
    if cors_origins_env == "*":
        allowed_origins = ["*"]
        allow_credentials = False
    else:
        allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
        allow_credentials = True
else:
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_AUTH_KEY = os.environ.get("API_AUTH_KEY", "").strip() or os.environ.get("SONG_CHORD_ANALYZER_API_KEY", "").strip()

@app.middleware("http")
async def api_key_auth_middleware(request, call_next):
    """Protects remote tunnel endpoints from unauthorized compute access if API_AUTH_KEY is set."""
    if API_AUTH_KEY:
        path = request.url.path
        # Exclude health probe and static assets
        if not (path in ["/health", "/api/health", "/docs", "/openapi.json", "/redoc"] or path.startswith("/assets/")):
            req_key = request.headers.get("x-api-key", "").strip()
            if req_key != API_AUTH_KEY:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Unauthorized: Invalid or missing X-API-Key header"}
                )
    return await call_next(request)

# Mount API routes
app.include_router(router, prefix="/api")
app.include_router(router)

@app.get("/api/health")
@app.get("/health")
async def health_check():
    """System, MIR engine, and hardware diagnostics endpoint."""
    vram_free_mb = 0
    vram_total_mb = 0
    if CUDA_AVAILABLE:
        free_bytes, total_bytes = torch.cuda.mem_get_info()
        vram_free_mb = round(free_bytes / (1024 * 1024), 1)
        vram_total_mb = round(total_bytes / (1024 * 1024), 1)

    btc_ready = BTC_CHECKPOINT_PATH.exists() and BTC_CHECKPOINT_PATH.stat().st_size > 1_000_000

    return {
        "status": "healthy",
        "api_version": "1.0.0",
        "schema_version": "1.0.0",
        "analysis_engine": "WindowsAnalysisEngine (Authoritative MIR Pipeline)",
        "analysis_engine_available": True,
        "auth_required": bool(API_AUTH_KEY),
        "models_available": {
            "btc": btc_ready,
            "demucs": True
        },
        "device": DEVICE_NAME,
        "cuda_available": CUDA_AVAILABLE,
        "cpu_count": HARDWARE.cpu_count,
        "ram_total_gb": HARDWARE.ram_total_gb,
        "vram_free_mb": vram_free_mb,
        "vram_total_mb": vram_total_mb,
        "ffmpeg_path": FFMPEG_PATH,
        "python_executable": PYTHON_EXECUTABLE
    }

# Serve frontend build if dist exists
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Explicitly return 404 for missing static assets instead of serving index.html
        static_exts = {".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".json", ".ico", ".woff", ".woff2", ".ttf", ".map"}
        if full_path.startswith("assets/") or file_path.suffix.lower() in static_exts:
            raise HTTPException(status_code=404, detail="Static asset not found")

        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Page not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
