#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
fi

docker compose config -q
docker compose up --build -d

api_url="${API_SMOKE_URL:-http://127.0.0.1:8000}"
web_url="${WEB_SMOKE_URL:-http://127.0.0.1:${WEB_PORT:-3001}}"

wait_for_http() {
  name="$1"
  url="$2"
  attempts=60
  while [ "$attempts" -gt 0 ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      printf '%s ready: %s\n' "$name" "$url"
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done
  printf '%s did not become ready: %s\n' "$name" "$url" >&2
  docker compose ps >&2
  return 1
}

wait_for_http api "$api_url/healthz"
wait_for_http web "$web_url"

wait_for_health() {
  service="$1"
  attempts=30
  container_id="$(docker compose ps -q "$service")"
  while [ "$attempts" -gt 0 ]; do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
    if [ "$status" = "healthy" ] || [ "$status" = "none" ]; then
      printf '%s container health: %s\n' "$service" "$status"
      return 0
    fi
    attempts=$((attempts - 1))
    sleep 2
  done
  printf '%s did not become healthy\n' "$service" >&2
  docker compose ps >&2
  return 1
}

wait_for_health postgres
wait_for_health redis
wait_for_health minio
wait_for_health api
wait_for_health web
wait_for_health worker

contract="$(curl -fsS "$api_url/dev/mvp-contract")"
printf '%s' "$contract" | grep -q '"default_privacy":"private"'
printf '%s' "$contract" | grep -q '"upload_transport":"api-mediated"'
printf '%s' "$contract" | grep -q '"playback_delivery":"api-proxied-hls"'

docker compose exec -T worker celery -A media_worker.celery_app inspect ping --timeout=5 | grep -q pong
docker compose ps
