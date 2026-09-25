FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    APP_ENV=production \
    OCR_ENGINE=tesseract \
    OCR_GPU=false \
    OCR_PRELOAD=false \
    OCR_MODEL_STORAGE_DIR=/app/easyocr-models \
    WEB_CONCURRENCY=1 \
    GUNICORN_THREADS=1 \
    GUNICORN_TIMEOUT=180 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MAX_CARDS_PER_IMAGE=6 \
    DETECTION_TARGET_MAX_DIMENSION=1000 \
    CARD_WARP_WIDTH=336 \
    CARD_WARP_HEIGHT=468

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p data /app/easyocr-models

COPY . .
RUN mkdir -p data /app/easyocr-models

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --workers ${WEB_CONCURRENCY:-1} --threads ${GUNICORN_THREADS:-1} --timeout ${GUNICORN_TIMEOUT:-180} -b 0.0.0.0:${PORT:-5000} run:app"]
