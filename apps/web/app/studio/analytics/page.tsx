"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type StudioAnalytics } from "../../components/video-api";

const DAY_OPTIONS = [7, 28, 90] as const;

export default function StudioAnalyticsPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(28);
  const [analytics, setAnalytics] = useState<StudioAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    if (!isSignedIn) {
      setAnalytics(null);
      setLoading(false);
      return;
    }
    try {
      const token = await getToken();
      setAnalytics(await apiRequest<StudioAnalytics>(`/studio/analytics?days=${days}`, { token }));
    } catch (err) {
      setAnalytics(null);
      setError(err instanceof ApiError ? err.message : "Unable to load creator analytics.");
    } finally {
      setLoading(false);
    }
  }, [days, getToken, isSignedIn]);

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void load());
    }
  }, [isLoaded, load]);

  return (
    <div className="studioStack">
      <section className="surface" aria-labelledby="analytics-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Studio</p>
            <h1 id="analytics-heading">Analytics</h1>
            <p className="muted">Daily creator metrics rebuilt from recorded impressions and counted views.</p>
          </div>
          <div className="actionRow">
            <Link className="secondaryLink" href="/studio">
              Studio
            </Link>
            <label className="srOnly" htmlFor="analytics-days">Date range</label>
            <select id="analytics-days" value={days} onChange={(event) => setDays(Number(event.target.value) as (typeof DAY_OPTIONS)[number])}>
              {DAY_OPTIONS.map((option) => <option key={option} value={option}>Last {option} days</option>)}
            </select>
            <button className="secondaryButton" type="button" onClick={() => void load()} disabled={loading || !isSignedIn}>Refresh</button>
          </div>
        </div>

        <Show when="signed-out">
          <div className="notice">
            <p>Sign in to view creator analytics.</p>
            <SignInButton mode="modal"><button type="button">Sign in</button></SignInButton>
          </div>
        </Show>
        {error ? <p className="errorText">{error}</p> : null}
        {loading ? <p className="muted">Loading analytics...</p> : null}
        {analytics ? <AnalyticsPanel analytics={analytics} /> : null}
      </section>
    </div>
  );
}

function AnalyticsPanel({ analytics }: { analytics: StudioAnalytics }) {
  return (
    <>
      <dl className="opsGrid" aria-label="Analytics totals">
        <Metric label="Views" value={String(analytics.totals.views)} />
        <Metric label="Watch time" value={formatWatchTime(analytics.totals.watch_time_seconds)} />
        <Metric label="Impressions" value={String(analytics.totals.impressions)} />
      </dl>
      <div className="adminGrid">
        <section className="compactSurface" aria-labelledby="daily-heading">
          <h2 id="daily-heading">Daily performance</h2>
          <div className="adminList" role="list">
            {analytics.daily.map((point) => (
              <article className="adminListItem" key={point.date} role="listitem">
                <div><h3>{formatDay(point.date)}</h3><p className="metaLine">{point.impressions} impressions</p></div>
                <div className="adminActions"><span>{point.views} views</span><span>{formatWatchTime(point.watch_time_seconds)}</span></div>
              </article>
            ))}
          </div>
        </section>
        <section className="compactSurface" aria-labelledby="top-videos-heading">
          <h2 id="top-videos-heading">Top videos</h2>
          {analytics.top_videos.length === 0 ? <p className="muted">No aggregated activity in this date range.</p> : null}
          <div className="adminList" role="list">
            {analytics.top_videos.map((video) => (
              <article className="adminListItem" key={video.video_id} role="listitem">
                <div><h3>{video.title}</h3><p className="metaLine">{video.impressions} impressions</p></div>
                <div className="adminActions"><span>{video.views} views</span><span>{formatWatchTime(video.watch_time_seconds)}</span></div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metricTile"><dt>{label}</dt><dd>{value}</dd></div>;
}

function formatDay(value: string) {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function formatWatchTime(value: string) {
  const totalSeconds = Number(value);
  if (!Number.isFinite(totalSeconds)) return "0s";
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.round(totalSeconds % 60);
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
}
