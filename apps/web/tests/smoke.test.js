const assert = require("node:assert/strict");
const test = require("node:test");

test("web package exposes the expected runtime scripts", () => {
  const pkg = require("../package.json");

  assert.equal(pkg.scripts.build, "next build");
  assert.equal(pkg.scripts.test, "node --test");
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
