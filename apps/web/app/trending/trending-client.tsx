"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type FeedResponse } from "../components/video-api";
import { VideoCard } from "../components/video-list";

export function TrendingClient() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [requestId] = useState(() => createRequestId());
  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadTrending = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      setFeed(await apiRequest<FeedResponse>(`/feed/trending?request_id=${encodeURIComponent(requestId)}`, { token }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load trending videos.");
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn, requestId]);

  useEffect(() => {
    if (isLoaded) {
      const timeout = window.setTimeout(() => void loadTrending(), 0);
      return () => window.clearTimeout(timeout);
    }
  }, [isLoaded, loadTrending]);

  const getImpressionToken = useCallback(async () => (isSignedIn ? await getToken() : null), [getToken, isSignedIn]);

  return (
    <section className="surface" aria-labelledby="trending-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Discovery</p>
          <h1 id="trending-heading">Trending</h1>
          <p className="muted">Public videos ranked by recent engagement.</p>
        </div>
        <button className="secondaryButton" type="button" onClick={loadTrending} disabled={loading}>Refresh</button>
      </div>
      {loading ? <p className="muted">Loading trending videos...</p> : null}
      {error ? <p className="errorText">{error}</p> : null}
      {!loading && !error && feed?.items.length === 0 ? <p className="muted">No public videos are trending yet.</p> : null}
      {!loading && !error && feed?.items.length ? (
        <div className="videoGrid" role="list">
          {feed.items.map((item) => (
            <VideoCard
              key={item.video.id}
              video={item.video}
              surface={item.surface}
              position={item.rank - 1}
              requestId={item.request_id}
              getToken={getImpressionToken}
              feedRank={item.rank}
              feedReason={item.reason}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function createRequestId() {
  const randomId = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `trending-${randomId}`;
}
