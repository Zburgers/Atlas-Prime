"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError,
  apiRequest,
  type ProcessingJob,
  type StudioVideoListResponse,
  type Video,
  type VideoListItem,
  type VideoPrivacy,
  type VideoStatus,
} from "../../components/video-api";

const STATUS_OPTIONS: Array<VideoStatus | "all"> = [
  "all",
  "draft",
  "uploading",
  "uploaded",
  "queued",
  "probing",
  "processing",
  "ready",
  "failed",
];

const PRIVACY_OPTIONS: Array<VideoPrivacy | "all"> = ["all", "private", "public", "unlisted"];

type DraftState = {
  title: string;
  description: string;
  privacy: VideoPrivacy;
};

export function StudioVideoManager() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [statusFilter, setStatusFilter] = useState<VideoStatus | "all">("all");
  const [privacyFilter, setPrivacyFilter] = useState<VideoPrivacy | "all">("all");
  const [videos, setVideos] = useState<VideoListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [drafts, setDrafts] = useState<Record<string, DraftState>>({});
  const [loading, setLoading] = useState(true);
  const [busyVideoId, setBusyVideoId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (statusFilter !== "all") {
      params.set("status", statusFilter);
    }
    if (privacyFilter !== "all") {
      params.set("privacy", privacyFilter);
    }
    return params.toString();
  }, [privacyFilter, statusFilter]);

  const loadVideos = useCallback(async () => {
    setError(null);
    if (!isLoaded) {
      return;
    }
    if (!isSignedIn) {
      setVideos([]);
      setDrafts({});
      setTotal(0);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const token = await getToken();
      const response = await apiRequest<StudioVideoListResponse>(`/studio/videos${query ? `?${query}` : ""}`, { token });
      setVideos(response.items);
      setTotal(response.total);
      setDrafts((current) => {
        const next: Record<string, DraftState> = {};
        for (const video of response.items) {
          next[video.id] = current[video.id] ?? {
            title: video.title,
            description: video.description ?? "",
            privacy: video.privacy,
          };
        }
        return next;
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load Studio videos.");
    } finally {
      setLoading(false);
    }
  }, [getToken, isLoaded, isSignedIn, query]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadVideos();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadVideos]);

  function updateDraft(videoId: string, patch: Partial<DraftState>) {
    setDrafts((current) => ({
      ...current,
      [videoId]: {
        ...current[videoId],
        ...patch,
      },
    }));
  }

  async function saveVideo(event: FormEvent<HTMLFormElement>, videoId: string) {
    event.preventDefault();
    const draft = drafts[videoId];
    if (!draft || !isSignedIn) {
      return;
    }
    setBusyVideoId(videoId);
    setError(null);
    setMessage(null);
    try {
      const token = await getToken();
      const updated = await apiRequest<Video>(`/studio/videos/${videoId}`, {
        method: "PATCH",
        token,
        body: {
          title: draft.title,
          description: draft.description || null,
          privacy: draft.privacy,
        },
      });
      setVideos((current) =>
        current.map((video) =>
          video.id === updated.id
            ? {
                ...video,
                title: updated.title,
                description: updated.description,
                privacy: updated.privacy,
                updated_at: updated.updated_at,
              }
            : video,
        ),
      );
      setMessage("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save video.");
    } finally {
      setBusyVideoId(null);
    }
  }

  async function retryVideo(videoId: string) {
    if (!isSignedIn) {
      return;
    }
    setBusyVideoId(videoId);
    setError(null);
    setMessage(null);
    try {
      const token = await getToken();
      await apiRequest<ProcessingJob>(`/studio/videos/${videoId}/retry-processing`, {
        method: "POST",
        token,
      });
      setVideos((current) =>
        current.map((video) =>
          video.id === videoId
            ? {
                ...video,
                status: "queued",
                failure_code: null,
                failure_message: null,
              }
            : video,
        ),
      );
      setMessage("Retry queued.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to retry processing.");
    } finally {
      setBusyVideoId(null);
    }
  }

  return (
    <div className="studioStack">
      <section className="surface" aria-labelledby="studio-videos-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Studio</p>
            <h1 id="studio-videos-heading">Videos</h1>
          </div>
          <Link className="buttonLink" href="/upload">
            Upload
          </Link>
        </div>

        <Show when="signed-out">
          <div className="notice">
            <p>Sign in to manage videos.</p>
            <SignInButton mode="modal">
              <button type="button">Sign in</button>
            </SignInButton>
          </div>
        </Show>

        <Show when="signed-in">
          <div className="toolbarRow">
            <label>
              <span>Status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as VideoStatus | "all")}>
                {STATUS_OPTIONS.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Privacy</span>
              <select
                value={privacyFilter}
                onChange={(event) => setPrivacyFilter(event.target.value as VideoPrivacy | "all")}
              >
                {PRIVACY_OPTIONS.map((privacy) => (
                  <option key={privacy} value={privacy}>
                    {privacy}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error ? <p className="errorText">{error}</p> : null}
          {message ? <p className="successText">{message}</p> : null}
          {loading ? <p className="muted">Loading videos...</p> : null}
          {!loading && videos.length === 0 ? <p className="muted">No videos match these filters.</p> : null}

          <div className="studioTable" role="table" aria-label="Creator videos">
            <div className="studioTableHeader" role="row">
              <span>Video</span>
              <span>Status</span>
              <span>Privacy</span>
              <span>Updated</span>
              <span>Actions</span>
            </div>
            {videos.map((video) => {
              const draft = drafts[video.id] ?? {
                title: video.title,
                description: video.description ?? "",
                privacy: video.privacy,
              };
              return (
                <form
                  className="studioTableRow"
                  key={video.id}
                  role="row"
                  onSubmit={(event) => saveVideo(event, video.id)}
                >
                  <div className="studioVideoCell">
                    <label>
                      <span className="srOnly">Title</span>
                      <input
                        maxLength={180}
                        required
                        value={draft.title}
                        onChange={(event) => updateDraft(video.id, { title: event.target.value })}
                      />
                    </label>
                    <label>
                      <span className="srOnly">Description</span>
                      <textarea
                        maxLength={5000}
                        value={draft.description}
                        onChange={(event) => updateDraft(video.id, { description: event.target.value })}
                      />
                    </label>
                  </div>
                  <span className={`statusPill status-${video.status}`}>{video.status}</span>
                  <label>
                    <span className="srOnly">Privacy</span>
                    <select
                      value={draft.privacy}
                      onChange={(event) => updateDraft(video.id, { privacy: event.target.value as VideoPrivacy })}
                    >
                      {PRIVACY_OPTIONS.filter((privacy) => privacy !== "all").map((privacy) => (
                        <option key={privacy} value={privacy}>
                          {privacy}
                        </option>
                      ))}
                    </select>
                  </label>
                  <span className="metaLine">{formatDate(video.updated_at)}</span>
                  <div className="studioActions">
                    <button type="submit" disabled={busyVideoId === video.id}>
                      Save
                    </button>
                    <button
                      className="secondaryButton"
                      type="button"
                      onClick={() => retryVideo(video.id)}
                      disabled={video.status !== "failed" || busyVideoId === video.id}
                    >
                      Retry
                    </button>
                    <Link className="buttonLink secondaryButton" href={`/watch/${video.id}`}>
                      Watch
                    </Link>
                  </div>
                </form>
              );
            })}
          </div>
          <p className="metaLine">{total.toLocaleString()} total</p>
        </Show>
      </section>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}
