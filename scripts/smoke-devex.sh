#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
fi

export ATLAS_ALLOW_DEV_AUTH_HEADERS="${ATLAS_ALLOW_DEV_AUTH_HEADERS:-true}"

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

docker compose run --rm api alembic upgrade head

contract="$(curl -fsS "$api_url/dev/mvp-contract")"
printf '%s' "$contract" | grep -q '"default_privacy":"private"'
printf '%s' "$contract" | grep -q '"upload_transport":"api-mediated"'
printf '%s' "$contract" | grep -q '"playback_delivery":"api-proxied-hls"'
printf '%s' "$contract" | grep -q '"upload_process_playback_metadata":"implemented-by-wave-3-smoke"'

docker compose exec -T worker celery -A media_worker.celery_app inspect ping --timeout=5 | grep -q pong

fixture_path="fixtures/media/sample-2s.mp4"
if [ ! -f "$fixture_path" ]; then
  mkdir -p fixtures/media
  docker compose run --rm -v "$ROOT_DIR/fixtures/media:/fixtures" worker \
    ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i testsrc=size=640x360:rate=24 \
    -f lavfi -i sine=frequency=1000:sample_rate=48000 \
    -t 2 \
    -c:v libx264 -pix_fmt yuv420p \
    -c:a aac -b:a 96k \
    /fixtures/sample-2s.mp4
fi

if ! command -v python3 >/dev/null 2>&1; then
  printf 'python3 is required for the integration smoke client\n' >&2
  exit 1
fi

API_SMOKE_URL="$api_url" SAMPLE_VIDEO_PATH="$fixture_path" python3 <<'PY'
import json
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

api_url = os.environ["API_SMOKE_URL"].rstrip("/")
sample_path = os.environ["SAMPLE_VIDEO_PATH"]
owner_headers = {
    "X-Atlas-Dev-Clerk-User-Id": "smoke-owner",
    "X-Atlas-Dev-Email": "smoke-owner@example.com",
}
other_headers = {
    "X-Atlas-Dev-Clerk-User-Id": "smoke-other",
    "X-Atlas-Dev-Email": "smoke-other@example.com",
}


def request(method, path, *, headers=None, body=None, content_type=None, expect=200):
    request_headers = dict(headers or {})
    if content_type:
        request_headers["Content-Type"] = content_type
    req = urllib.request.Request(
        f"{api_url}{path}",
        data=body,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read()
            if response.status != expect:
                raise AssertionError(f"{method} {path}: expected {expect}, got {response.status}: {data[:500]!r}")
            return response.status, response.headers, data
    except urllib.error.HTTPError as exc:
        data = exc.read()
        if exc.code == expect:
            return exc.code, exc.headers, data
        raise AssertionError(f"{method} {path}: expected {expect}, got {exc.code}: {data[:500]!r}") from exc


def json_request(method, path, *, headers=None, payload=None, expect=200):
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    _status, _headers, data = request(
        method,
        path,
        headers=headers,
        body=body,
        content_type="application/json" if payload is not None else None,
        expect=expect,
    )
    return json.loads(data.decode("utf-8")) if data else None


def multipart_file(field_name, file_name, content_type, data):
    boundary = f"atlas-smoke-{uuid.uuid4().hex}"
    parts = [
        f"--{boundary}\r\n".encode("utf-8"),
        (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_name}"\r\n'
        ).encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        data,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def upload(video_id, file_name, data, content_type):
    body, multipart_type = multipart_file("file", file_name, content_type, data)
    _status, _headers, response = request(
        "POST",
        f"/videos/{video_id}/upload",
        headers=owner_headers,
        body=body,
        content_type=multipart_type,
        expect=200,
    )
    return json.loads(response.decode("utf-8"))


def wait_for_terminal_status(video_id, wanted):
    deadline = time.time() + 120
    last = None
    while time.time() < deadline:
        status = json_request("GET", f"/videos/{video_id}/processing-status", headers=owner_headers)
        last = status
        if status["video_status"] in wanted:
            return status
        time.sleep(2)
    raise AssertionError(f"video {video_id} did not reach {wanted}; last status: {last}")


def first_media_line(playlist):
    for line in playlist.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    raise AssertionError(f"playlist had no media URI: {playlist[:500]!r}")


good = json_request(
    "POST",
    "/videos",
    headers=owner_headers,
    payload={"title": f"Wave 3 smoke good {int(time.time())}", "description": "End-to-end smoke upload"},
    expect=201,
)
assert good["privacy"] == "private"
assert good["status"] == "draft"
good_id = good["id"]
with open(sample_path, "rb") as handle:
    sample_data = handle.read()
upload_response = upload(good_id, "sample-2s.mp4", sample_data, mimetypes.guess_type(sample_path)[0] or "video/mp4")
assert upload_response["video"]["status"] == "queued"
ready = wait_for_terminal_status(good_id, {"ready", "failed"})
if ready["video_status"] != "ready":
    raise AssertionError(f"good sample failed processing: {ready}")

playback = json_request("GET", f"/videos/{good_id}/playback", headers=owner_headers)
master_url = playback["master_playlist_url"]
assert master_url == f"/videos/{good_id}/hls/master.m3u8"

request("PATCH", f"/videos/{good_id}", headers=other_headers, body=b'{"title":"stolen"}', content_type="application/json", expect=403)
request("GET", f"/videos/{good_id}/playback", headers=other_headers, expect=403)

_status, _headers, master_body = request("GET", master_url, headers=owner_headers)
master_playlist = master_body.decode("utf-8")
rendition_path = first_media_line(master_playlist)
_status, _headers, rendition_body = request("GET", f"/videos/{good_id}/hls/{rendition_path}", headers=owner_headers)
segment_path = first_media_line(rendition_body.decode("utf-8"))
segment_url = f"/videos/{good_id}/hls/{urllib.parse.urljoin(rendition_path, segment_path)}"
_status, segment_headers, segment_body = request("GET", segment_url, headers=owner_headers)
assert segment_body, "segment response was empty"
assert "immutable" in segment_headers.get("Cache-Control", "")
request("GET", f"/videos/{good_id}/hls/thumbnail.jpg", headers=owner_headers)

bad = json_request(
    "POST",
    "/videos",
    headers=owner_headers,
    payload={"title": f"Wave 3 smoke bad {int(time.time())}"},
    expect=201,
)
bad_id = bad["id"]
upload(bad_id, "bad.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isomnot-real-video", "video/mp4")
failed = wait_for_terminal_status(bad_id, {"ready", "failed"})
if failed["video_status"] != "failed":
    raise AssertionError(f"bad sample unexpectedly became ready: {failed}")
assert failed["failure_code"], f"failed video lacked failure_code: {failed}"

print(
    "wave3 integration smoke passed: "
    f"ready_video={good_id} bad_video={bad_id} failure_code={failed['failure_code']}"
)
PY

docker compose ps
