const assert = require("node:assert/strict");
const test = require("node:test");

test("web package exposes the expected runtime scripts", () => {
  const pkg = require("../package.json");

  assert.equal(pkg.scripts.build, "next build");
  assert.equal(pkg.scripts.test, "node --test");
});

test("CI smoke mode bypasses Clerk only for the disposable smoke process", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const layout = fs.readFileSync(path.join(__dirname, "../app/layout.tsx"), "utf8");

  assert.match(layout, /process\.env\.ATLAS_CI_SMOKE_MODE === "true"/);
  assert.match(layout, /if \(!smokeMode && !clerkPublishableKey\)/);
  assert.match(layout, /smokeMode \? \(\s+<header className="appHeader">/);
  assert.match(layout, /smokeMode \? \(\s+<section className="surface" aria-labelledby="smoke-heading">/);
  assert.match(layout, /smokeMode \? appShell : <ClerkProvider publishableKey=\{clerkPublishableKey\}>\{appShell\}<\/ClerkProvider>/);
  assert.match(layout, /<ClerkProvider publishableKey=\{clerkPublishableKey\}>/);
  assert.match(layout, /<a className="skipLink" href="#main-content">Skip to main content<\/a>/);
});

test("normal video contracts redact storage and queue internals", () => {
  const source = require("node:fs").readFileSync(require("node:path").join(__dirname, "../app/components/video-api.ts"), "utf8");

  assert.match(source, /export type AdminVideoDebugVideo = Video &/);
  assert.doesNotMatch(source.slice(source.indexOf("export type Video ="), source.indexOf("export type VideoListItem =")), /storage_key/);
  assert.doesNotMatch(source.slice(source.indexOf("export type PlaybackResponse ="), source.indexOf("export type UploadResponse =")), /playlist_storage_key/);
  assert.doesNotMatch(source.slice(source.indexOf("export type UploadResponse ="), source.indexOf("export class ApiError")), /storage_key|celery_task_id/);
});

test("admin dashboard keeps debug rendering behind the operator debug type", () => {
  const source = require("node:fs").readFileSync(require("node:path").join(__dirname, "../app/admin/admin-dashboard.tsx"), "utf8");

  assert.match(source, /apiRequest<AdminVideoDebugVideo\[\]>/);
  assert.match(source, /apiRequest<AdminVideoDebug>/);
  assert.match(source, /video\.original_storage_key/);
});

test("upload and Studio callers use redacted product contracts", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const upload = fs.readFileSync(path.join(__dirname, "../app/upload/upload-form.tsx"), "utf8");
  const studio = fs.readFileSync(path.join(__dirname, "../app/studio/videos/studio-video-manager.tsx"), "utf8");

  assert.match(upload, /apiRequest<UploadResponse>\(`\/videos\/\$\{video\.id\}\/upload`/);
  assert.match(upload, /uploadResult\.video\.id/);
  assert.doesNotMatch(upload, /storage_key|celery_task_id/);
  assert.match(studio, /apiRequest<StudioVideoListResponse>\(`\/studio\/videos/);
  assert.match(studio, /response\.items/);
  assert.doesNotMatch(studio, /storage_key|celery_task_id/);
});

test("watch page presents user-safe processing guidance", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const watch = fs.readFileSync(path.join(__dirname, "../app/watch/[videoId]/watch-client.tsx"), "utf8");
  const statusUi = fs.readFileSync(path.join(__dirname, "../app/components/status-ui.tsx"), "utf8");

  assert.doesNotMatch(watch, /D\/E still own HLS|Sector D owns/);
  assert.doesNotMatch(statusUi, /D\/E still own HLS|Sector D owns|worker|API-owned|The API is receiving/);
  assert.match(watch, /queued for processing/);
  assert.match(watch, /being processed/);
  assert.match(watch, /could not be processed/);
  assert.match(statusUi, /const failureMessage = processingStatus\?\.failure_message \|\| video\.failure_message/);
  assert.match(statusUi, /failureMessage \? <p className="errorText">\{failureMessage\}<\/p>/);
});

test("watch telemetry carries stable session and retry-safe event identities", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const api = fs.readFileSync(path.join(__dirname, "../app/components/video-api.ts"), "utf8");
  const watch = fs.readFileSync(path.join(__dirname, "../app/watch/[videoId]/watch-client.tsx"), "utf8");

  assert.match(api, /export function createPlaybackTelemetryUuid\(\)/);
  assert.match(api, /cryptoApi\.randomUUID\(\)/);
  assert.match(api, /bytes\[6\] = .*0x40/);
  assert.match(api, /bytes\[8\] = .*0x80/);
  assert.match(api, /export function buildPlaybackEventRequest\(/);
  assert.match(watch, /useMemo\(\(\) => \{\s+\/\/ The route key intentionally starts a new telemetry session for a new video\.\s+void videoId;\s+return createPlaybackTelemetryUuid\(\);\s+\}, \[videoId\]\)/);
  assert.match(watch, /const event_id = createPlaybackTelemetryUuid\(\)/);
  assert.match(watch, /playback_session_id: playbackSessionId/);
  assert.match(watch, /event_id \}/);
  assert.match(watch, /body,\n\s+\}\);/);
  assert.match(watch, /for \(let attempt = 0; attempt < MAX_TELEMETRY_ATTEMPTS;/);
  assert.match(watch, /request_id: recommendationRequestId \?\? null/);
  assert.match(watch, /session_id: viewSessionIdRef\.current/);
  assert.doesNotMatch(watch, /\bsession_id:\s*playbackSessionId/);
});

test("home-feed card clicks carry the required telemetry identity", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const source = fs.readFileSync(path.join(__dirname, "../app/components/video-list.tsx"), "utf8");

  assert.match(source, /buildPlaybackEventRequest,\n\s+createPlaybackTelemetryUuid,/);
  assert.match(source, /useState\(\(\) => createPlaybackTelemetryUuid\(\)\)/);
  assert.match(source, /const eventId = createPlaybackTelemetryUuid\(\)/);
  assert.match(source, /playback_session_id: telemetryPlaybackSessionId/);
  assert.match(source, /event_id: eventId/);
  assert.match(source, /event_type: "card_click", request_id: requestId/);
  assert.match(source, /onClick=\{\(\) => void recordClick\(\)\}/);
});

test("thumbnail accessible names include visible duration badges", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const source = fs.readFileSync(path.join(__dirname, "../app/components/video-list.tsx"), "utf8");

  assert.match(source, /const durationLabel = video\.duration_seconds \? formatDuration\(video\.duration_seconds\) : ""/);
  assert.match(source, /const thumbnailAccessibleName = durationLabel\s+\? `Open \$\{video\.title\}, duration \$\{durationLabel\}`/);
  assert.match(source, /aria-label=\{thumbnailAccessibleName\}/);
  assert.match(source, /className="durationBadge">\{durationLabel\}/);
});

test("admin telemetry health stays aggregate-only and degrades safely", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const api = fs.readFileSync(path.join(__dirname, "../app/components/video-api.ts"), "utf8");
  const dashboard = fs.readFileSync(path.join(__dirname, "../app/admin/admin-dashboard.tsx"), "utf8");
  const panel = dashboard.slice(dashboard.indexOf("function TelemetryPanel"), dashboard.indexOf("function OpsPanel"));

  assert.match(api, /export type AdminTelemetryHealth = \{/);
  assert.match(dashboard, /apiRequest<AdminTelemetryHealth>\("\/admin\/telemetry"/);
  assert.match(panel, /Playback telemetry health/);
  assert.match(panel, /Accepted events/);
  assert.match(panel, /Retention cutoff/);
  assert.match(panel, /Telemetry metrics are temporarily unavailable/);
  assert.doesNotMatch(panel, /playback_session_id|event_id|request_id|user_id|video_id|ip_hash|raw event/);
});
