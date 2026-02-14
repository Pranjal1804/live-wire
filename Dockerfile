# ────────────────────────────────────────────────────────────
# MAESTRO Backend
# Build:  docker build -t maestro-backend .
# Run:    docker run -p 8000:8000 --env-file .env maestro-backend
# ────────────────────────────────────────────────────────────

FROM python:3.11-slim

# System deps for sounddevice, scipy, torch, chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libportaudio2 \
    libsndfile1 \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy config
COPY config/ ./config/

# Create data dir for JSON-file session fallback
RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
