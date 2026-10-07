# Single-stage container for Song Chord Analyzer Server (Cloud Run / Docker)
FROM python:3.11-slim

# Install system dependencies: FFmpeg and libsndfile are essential for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Configure environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    SONG_CHORD_ANALYZER_DATA_DIR=/app/data \
    TORCH_HOME=/app/cache/torch \
    NUMBA_CACHE_DIR=/tmp/numba_cache \
    PYTHONPATH=/app

# Create necessary directories
RUN mkdir -p /app/data /app/cache/torch /tmp/numba_cache

# Copy requirements and install CPU-optimized PyTorch and dependencies
COPY requirements.txt .

# Install CPU PyTorch first to keep image lightweight for serverless Cloud Run
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend, shared schemas/contracts, and model weights
COPY backend/ ./backend/
COPY shared/ ./shared/
COPY models/ ./models/

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000

# Cloud Run injects $PORT dynamically; shell form exec binds to that port
CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
