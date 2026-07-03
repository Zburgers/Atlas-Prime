"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  apiRequest,
  backendAssetUrl,
  type VideoImpression,
  type VideoListItem,
  type VideoListResponse,
} from "./video-api";
import { formatDate, StatusPill } from "./status-ui";

type ImpressionTokenProvider = () => Promise<string | null>;

export function VideoList() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [requestId] = useState(() => createRequestId("home"));
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const getImpressionToken = useCallback(async () => {
    return isSignedIn ? await getToken() : null;
  }, [getToken, isSignedIn]);

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
          <p className="eyebrow">Home</p>
          <h1 id="library-heading">Browse videos</h1>
          <p className="muted">Watch ready public videos, or sign in to manage private drafts and uploads.</p>
        </div>
        <Link className="buttonLink" href="/upload">
          Upload video
        </Link>
      </div>

      <Show when="signed-out">
        <div className="notice">
          <p>Sign in to see your private drafts, uploads, and processing videos.</p>
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
        <div className="videoGrid" role="list">
          {videos.map((video, index) => (
            <VideoCard
              key={video.id}
              video={video}
              surface="home"
              position={index}
              requestId={requestId}
              getToken={getImpressionToken}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function VideoCard({
  video,
  surface,
  position,
  requestId,
  getToken,
}: {
  video: VideoListItem;
  surface?: string;
  position?: number;
  requestId?: string;
  getToken?: ImpressionTokenProvider;
}) {
  const cardRef = useRef<HTMLElement | null>(null);
  const impressionRecordedRef = useRef(false);
  const channelLabel = video.channel_display_name ?? "Channel pending";

  useEffect(() => {
    impressionRecordedRef.current = false;
  }, [position, surface, video.id]);

  useEffect(() => {
    if (!surface || position === undefined || !cardRef.current || typeof IntersectionObserver === "undefined") {
      return;
    }

    const element = cardRef.current;
    const recordImpression = async () => {
      if (impressionRecordedRef.current) {
        return;
      }
      impressionRecordedRef.current = true;
      try {
        const token = getToken ? await getToken() : null;
        await apiRequest<VideoImpression>(`/videos/${video.id}/impressions`, {
          token,
          method: "POST",
          body: {
            surface,
            position,
            request_id: requestId ?? null,
          },
        });
      } catch {
        // Impression telemetry should never block browsing.
      }
    };

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting && entry.intersectionRatio >= 0.5)) {
          void recordImpression();
          observer.disconnect();
        }
      },
      { threshold: 0.5 },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [getToken, position, requestId, surface, video.id]);

  return (
    <article className="videoCard" role="listitem" ref={cardRef}>
      <Link className="thumbnailFrame" href={`/watch/${video.id}`} aria-label={`Open ${video.title}`}>
        {video.thumbnail_url ? (
          <Image
            alt=""
            fill
            sizes="(max-width: 820px) 100vw, 33vw"
            src={backendAssetUrl(video.thumbnail_url)}
            unoptimized
          />
        ) : (
          <div className="thumbnailFallback">
            <StatusPill status={video.status} />
          </div>
        )}
        {video.duration_seconds ? <span className="durationBadge">{formatDuration(video.duration_seconds)}</span> : null}
      </Link>
      <div className="videoCardBody">
        <div>
          <h2>{video.title}</h2>
          {video.channel_handle ? (
            <Link className="channelLink" href={`/channels/${video.channel_handle}`}>
              {channelLabel}
            </Link>
          ) : (
            <span className="channelLink muted">{channelLabel}</span>
          )}
          <p>{video.description || "No description provided."}</p>
          <p className="metaLine">{videoMeta(video)}</p>
        </div>
        <div className="cardActions">
          <StatusPill status={video.status} />
          <Link className="secondaryLink" href={`/watch/${video.id}`}>
            Open
          </Link>
        </div>
      </div>
    </article>
  );
}

function EmptyLibrary() {
  return (
    <div className="emptyState">
      <h2>No videos yet</h2>
      <p>Public ready videos will appear here. Sign in to create a private upload.</p>
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

function formatDuration(value: string) {
  const seconds = Math.max(0, Math.round(Number.parseFloat(value)));
  if (!Number.isFinite(seconds)) {
    return "";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, "0")}:${remainingSeconds.toString().padStart(2, "0")}`;
  }
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function videoMeta(video: VideoListItem) {
  const parts = [formatCount(video.view_count, "view"), video.privacy, `created ${formatDate(video.created_at)}`];
  if (video.width && video.height) {
    parts.push(`${video.width}x${video.height}`);
  }
  return parts.join(" / ");
}

export function createRequestId(prefix: string) {
  const randomId =
    typeof globalThis.crypto !== "undefined" && "randomUUID" in globalThis.crypto
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${randomId}`;
}

function formatCount(value: number, label: string) {
  return `${value.toLocaleString()} ${label}${value === 1 ? "" : "s"}`;
}
