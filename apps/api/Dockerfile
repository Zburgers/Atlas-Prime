FROM python:3.12-slim

ARG ATLAS_BUILD_SHA=unknown
ARG ATLAS_BUILD_TIME=unknown

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_BUILD_SHA=$ATLAS_BUILD_SHA \
    ATLAS_BUILD_TIME=$ATLAS_BUILD_TIME

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pytest.ini .
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["/bin/sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
