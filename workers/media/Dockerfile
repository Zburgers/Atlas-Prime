FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/worker

WORKDIR /worker

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY media_worker ./media_worker
COPY tests ./tests

CMD ["celery", "-A", "media_worker.celery_app", "worker", "--loglevel=info", "--queues=media", "--hostname=media-worker@%h", "--concurrency=1"]
