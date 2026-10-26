FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    git ffmpeg libjpeg62-turbo libffi8 openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . .
RUN find . -type d -name "__pycache__" -prune -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete

CMD ["python", "bot.py"]