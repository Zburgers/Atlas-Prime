"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type Video, type VideoListResponse } from "./video-api";
import { formatDate, StatusPill } from "./status-ui";

export function VideoList() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [videos, setVideos] = useState<Video[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVideos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      const response = await apiRequest<VideoListResponse>("/videos", { token });
      setVideos(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load videos.");
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn]);

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void loadVideos());
    }
  }, [isLoaded, loadVideos]);

  return (
    <section className="surface" aria-labelledby="library-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Library</p>
          <h1 id="library-heading">Your video loop</h1>
          <p className="muted">Upload, watch status, and open ready videos from one place.</p>
        </div>
        <Link className="buttonLink" href="/upload">
          Upload video
        </Link>
      </div>

      <Show when="signed-out">
        <div className="notice">
          <p>Sign in to see private drafts, uploads, and processing videos.</p>
          <SignInButton mode="modal">
            <button type="button">Sign in</button>
          </SignInButton>
        </div>
      </Show>

      <Show when="signed-in">
        <div className="toolbar">
          <span>{total} visible videos</span>
          <button className="secondaryButton" type="button" onClick={loadVideos} disabled={loading}>
            Refresh
          </button>
        </div>
      </Show>

      {loading ? <VideoListSkeleton /> : null}
      {error ? <p className="errorText">{error}</p> : null}
      {!loading && !error && videos.length === 0 ? <EmptyLibrary /> : null}
      {!loading && !error && videos.length > 0 ? (
        <div className="videoTable" role="list">
          {videos.map((video) => (
            <article className="videoRow" key={video.id} role="listitem">
              <div>
                <h2>{video.title}</h2>
                <p>{video.description || "No description provided."}</p>
                <p className="metaLine">
                  {video.privacy} · created {formatDate(video.created_at)}
                </p>
              </div>
              <div className="rowActions">
                <StatusPill status={video.status} />
                <Link className="secondaryLink" href={`/watch/${video.id}`}>
                  Open
                </Link>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function EmptyLibrary() {
  return (
    <div className="emptyState">
      <h2>No videos yet</h2>
      <p>Create a private video record, upload a small MP4/MOV/WebM, and the UI will show the queued processing state.</p>
      <Link className="buttonLink" href="/upload">
        Start upload
      </Link>
    </div>
  );
}

function VideoListSkeleton() {
  return (
    <div className="skeletonStack" aria-label="Loading videos">
      <span />
      <span />
      <span />
    </div>
  );
}
