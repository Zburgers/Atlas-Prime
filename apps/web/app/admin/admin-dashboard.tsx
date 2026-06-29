"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type AdminJob, type AdminOps, type AdminVideoDebug, type Video } from "../components/video-api";
import { formatDate, StatusPill } from "../components/status-ui";

export function AdminDashboard() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [ops, setOps] = useState<AdminOps | null>(null);
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [debug, setDebug] = useState<AdminVideoDebug | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAdmin = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!isSignedIn) {
      setOps(null);
      setJobs([]);
      setVideos([]);
      setDebug(null);
      setLoading(false);
      return;
    }
    try {
      const token = await getToken();
      const [opsResponse, jobsResponse, videosResponse] = await Promise.all([
        apiRequest<AdminOps>("/admin/ops", { token }),
        apiRequest<AdminJob[]>("/admin/jobs", { token }),
        apiRequest<Video[]>("/admin/videos", { token }),
      ]);
      setOps(opsResponse);
      setJobs(jobsResponse);
      setVideos(videosResponse);
      const firstDebugVideo = videosResponse.find((video) => video.status === "failed") ?? videosResponse[0];
      if (firstDebugVideo) {
        setDebug(await apiRequest<AdminVideoDebug>(`/admin/videos/${firstDebugVideo.id}/debug`, { token }));
      } else {
        setDebug(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load admin data.");
      setDebug(null);
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  const loadDebug = useCallback(
    async (videoId: string) => {
      setError(null);
      try {
        const token = isSignedIn ? await getToken() : null;
        setDebug(await apiRequest<AdminVideoDebug>(`/admin/videos/${videoId}/debug`, { token }));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Unable to load debug details.");
      }
    },
    [getToken, isSignedIn],
  );

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void loadAdmin());
    }
  }, [isLoaded, loadAdmin]);

  return (
    <div className="adminStack">
      <section className="surface" aria-labelledby="admin-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Admin</p>
            <h1 id="admin-heading">Operations dashboard</h1>
            <p className="muted">Processing health, recent jobs, and video debug state for the local MVP demo.</p>
          </div>
          <button className="secondaryButton" type="button" onClick={loadAdmin} disabled={loading || !isSignedIn}>
            Refresh
          </button>
        </div>

        <Show when="signed-out">
          <div className="notice">
            <p>Sign in to inspect processing state and worker health.</p>
            <SignInButton mode="modal">
              <button type="button">Sign in</button>
            </SignInButton>
          </div>
        </Show>

        {error ? <p className="errorText">{error}</p> : null}
        {loading ? <p className="muted">Loading admin data...</p> : null}
        {ops ? <OpsPanel ops={ops} /> : null}
      </section>

      <div className="adminGrid">
        <section className="surface compactSurface" aria-labelledby="jobs-heading">
          <div className="sectionHeader">
            <div>
              <p className="eyebrow">Queue</p>
              <h2 id="jobs-heading">Recent jobs</h2>
            </div>
          </div>
          {jobs.length === 0 ? <p className="muted">No jobs yet.</p> : null}
          <div className="adminList" role="list">
            {jobs.map((job) => (
              <article className="adminListItem" key={job.id} role="listitem">
                <div>
                  <h3>{job.video_title ?? job.video_id}</h3>
                  <p className="metaLine">
                    {job.status} · attempts {job.attempt_count} · {formatDate(job.created_at)}
                  </p>
                  {job.error_message || job.video_failure_message ? <p className="errorText">{job.error_message ?? job.video_failure_message}</p> : null}
                </div>
                <button className="secondaryButton" type="button" onClick={() => void loadDebug(job.video_id)}>
                  Inspect
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className="surface compactSurface" aria-labelledby="videos-heading">
          <div className="sectionHeader">
            <div>
              <p className="eyebrow">Videos</p>
              <h2 id="videos-heading">Recent videos</h2>
            </div>
          </div>
          {videos.length === 0 ? <p className="muted">No videos yet.</p> : null}
          <div className="adminList" role="list">
            {videos.map((video) => (
              <article className="adminListItem" key={video.id} role="listitem">
                <div>
                  <h3>{video.title}</h3>
                  <p className="metaLine">
                    {video.privacy} · {formatDate(video.updated_at)}
                  </p>
                </div>
                <div className="adminActions">
                  <StatusPill status={video.status} />
                  <button className="secondaryButton" type="button" onClick={() => void loadDebug(video.id)}>
                    Debug
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>

      {debug ? <DebugPanel debug={debug} /> : null}
    </div>
  );
}

function OpsPanel({ ops }: { ops: AdminOps }) {
  const workerNames = ops.worker.online_workers.join(", ") || "No workers responding";
  return (
    <div className="opsGrid">
      <MetricTile label="API" value={ops.api.ok ? "ok" : "degraded"} tone={ops.api.ok ? "ready" : "failed"} />
      <MetricTile label="Worker" value={ops.worker.ok ? workerNames : ops.worker.error ?? "offline"} tone={ops.worker.ok ? "ready" : "failed"} />
      <MetricTile
        label="Redis media queue"
        value={ops.redis.media_queue_depth === null ? ops.redis.error ?? "unavailable" : String(ops.redis.media_queue_depth)}
        tone={ops.redis.ok ? "ready" : "failed"}
      />
    </div>
  );
}

function MetricTile({ label, value, tone }: { label: string; value: string; tone: "ready" | "failed" }) {
  return (
    <div className={`metricTile metric-${tone}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function DebugPanel({ debug }: { debug: AdminVideoDebug }) {
  const { video } = debug;
  return (
    <section className="surface compactSurface" aria-labelledby="debug-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Debug</p>
          <h2 id="debug-heading">{video.title}</h2>
          <p className="metaLine">{video.id}</p>
        </div>
        <Link className="secondaryLink" href={`/watch/${video.id}`}>
          Watch
        </Link>
      </div>

      <dl className="detailGrid">
        <div>
          <dt>Status</dt>
          <dd>{video.status}</dd>
        </div>
        <div>
          <dt>Failure code</dt>
          <dd>{video.failure_code ?? "None"}</dd>
        </div>
        <div>
          <dt>Original key</dt>
          <dd>{video.original_storage_key ?? "Missing"}</dd>
        </div>
        <div>
          <dt>HLS master key</dt>
          <dd>{video.hls_master_storage_key ?? "Missing"}</dd>
        </div>
      </dl>
      {video.failure_message ? <p className="errorText">{video.failure_message}</p> : null}

      <div className="debugColumns">
        <DebugList
          title="Jobs"
          items={debug.processing_jobs.map((job) => `${job.status} · attempts ${job.attempt_count} · ${job.error_code ?? "no error"} · ${formatDate(job.created_at)}`)}
        />
        <DebugList
          title="Renditions"
          items={debug.renditions.map((rendition) => `${rendition.label} · ${rendition.width}x${rendition.height} · ${rendition.status}`)}
        />
        <DebugList
          title="Playback events"
          items={debug.recent_playback_events.map((event) => `${event.event_type} · ${event.quality_label ?? "auto"} · ${formatDate(event.created_at)}`)}
          empty="No playback events."
        />
      </div>
    </section>
  );
}

function DebugList({ title, items, empty = "None recorded." }: { title: string; items: string[]; empty?: string }) {
  return (
    <div>
      <h3>{title}</h3>
      {items.length === 0 ? <p className="muted">{empty}</p> : null}
      <ul className="plainList">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
