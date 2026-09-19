# SDC video-worker — separate process that runs FFmpeg off the web process.
# FFmpeg is installed from the distro packages; inside Linux containers the
# encoder profile must be libx264 (videotoolbox/nvenc need matching hosts/GPUs).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIDEO_ENCODER_PROFILE=libx264

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY video_worker ./video_worker

# Healthcheck: the worker is ready when ffmpeg exists and the queue DB answers.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD ffmpeg -version >/dev/null 2>&1 && python -c "import os,psycopg;psycopg.connect(os.environ.get('VIDEO_DATABASE_URL') or os.environ.get('NEON_DATABASE_URL') or os.environ['DATABASE_URL']).close()"

CMD ["python", "-m", "video_worker"]