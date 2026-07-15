"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type SearchResponse, type VideoListItem } from "../components/video-api";
import { createRequestId, VideoCard } from "../components/video-list";

export function SearchClient({ initialQuery }: { initialQuery: string }) {
  const normalizedQuery = initialQuery.trim();
  const [requestId] = useState(() => createRequestId("search"));
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(Boolean(normalizedQuery));
  const [error, setError] = useState<string | null>(null);

  const loadResults = useCallback(async () => {
    if (!normalizedQuery) {
      setVideos([]);
      setTotal(0);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<SearchResponse>(`/search?q=${encodeURIComponent(normalizedQuery)}`);
      setVideos(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to search videos.");
    } finally {
      setLoading(false);
    }
  }, [normalizedQuery]);

  useEffect(() => {
    queueMicrotask(() => void loadResults());
  }, [loadResults]);

  return (
    <section className="surface" aria-labelledby="search-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Search</p>
          <h1 id="search-heading">Search videos</h1>
          <p className="muted">Find public ready videos by title, description, or channel.</p>
        </div>
      </div>

      <form className="searchForm" action="/search" method="get" role="search">
        <label className="srOnly" htmlFor="search-page-query">
          Search public videos
        </label>
        <input id="search-page-query" name="q" defaultValue={initialQuery} placeholder="Search videos" type="search" />
        <button type="submit">Search</button>
      </form>

      {!normalizedQuery ? (
        <div className="emptyState">
          <h2>Search public videos</h2>
          <p>Enter a title, topic, or channel name.</p>
        </div>
      ) : null}
      {loading ? <SearchSkeleton /> : null}
      {error ? <p className="errorText" role="alert">{error}</p> : null}
      {!loading && !error && normalizedQuery && videos.length === 0 ? (
        <div className="emptyState">
          <h2>No results</h2>
          <p>No public ready videos matched this search.</p>
        </div>
      ) : null}
      {!loading && !error && videos.length > 0 ? (
        <>
          <div className="toolbar" aria-live="polite" role="status">
            <span>
              {total.toLocaleString()} result{total === 1 ? "" : "s"}
            </span>
          </div>
          <div className="videoGrid" role="list">
            {videos.map((video, index) => (
              <VideoCard key={video.id} video={video} surface="search" position={index} requestId={requestId} />
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function SearchSkeleton() {
  return (
    <div className="skeletonStack" aria-label="Loading search results" aria-live="polite" role="status">
      <span />
      <span />
      <span />
    </div>
  );
}
