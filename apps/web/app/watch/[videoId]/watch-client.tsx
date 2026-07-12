"use client";

import { useAuth } from "@clerk/nextjs";
import Hls from "hls.js";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { StatusPanel } from "../../components/status-ui";
import {
  ApiError,
  apiRequest,
  backendAssetUrl,
  type Comment,
  type CommentListResponse,
  type PlaybackResponse,
  type ProcessingStatus,
  type Video,
  type VideoEngagementResponse,
  type VideoViewResponse,
} from "../../components/video-api";

const VIEW_COUNT_THRESHOLD_SECONDS = 5;

export function WatchClient({ videoId, recommendationRequestId }: { videoId: string; recommendationRequestId?: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const viewSessionIdRef = useRef(createPlaybackSessionId());
  const viewRecordedRef = useRef(false);
  const viewRequestPendingRef = useRef(false);
  const [video, setVideo] = useState<Video | null>(null);
  const [engagement, setEngagement] = useState<VideoEngagementResponse | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentTotal, setCommentTotal] = useState(0);
  const [commentBody, setCommentBody] = useState("");
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [playback, setPlayback] = useState<PlaybackResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [engagementBusy, setEngagementBusy] = useState(false);
  const [commentsBusy, setCommentsBusy] = useState(false);
  const [engagementError, setEngagementError] = useState<string | null>(null);
  const [commentsError, setCommentsError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playerError, setPlayerError] = useState<string | null>(null);

  const recordPlaybackEvent = useCallback(
    async (event_type: "player_ready" | "error" | "unsupported" | "play" | "pause", quality_label?: string) => {
      try {
        const token = isSignedIn ? await getToken() : null;
        await apiRequest(`/videos/${videoId}/events`, {
          token,
          method: "POST",
          body: {
            event_type,
            position_seconds: videoRef.current?.currentTime ?? null,
            quality_label,
            client_timestamp: new Date().toISOString(),
            request_id: recommendationRequestId ?? null,
          },
        });
      } catch {
        // Playback telemetry should never interrupt viewing.
      }
    },
    [getToken, isSignedIn, recommendationRequestId, videoId],
  );

  const recordView = useCallback(async () => {
    const element = videoRef.current;
    if (!element || viewRecordedRef.current || viewRequestPendingRef.current) {
      return;
    }
    if (element.currentTime < VIEW_COUNT_THRESHOLD_SECONDS) {
      return;
    }

    viewRequestPendingRef.current = true;
    try {
      const token = isSignedIn ? await getToken() : null;
      const result = await apiRequest<VideoViewResponse>(`/videos/${videoId}/views`, {
        token,
        method: "POST",
        body: {
          session_id: viewSessionIdRef.current,
          position_seconds: Number(element.currentTime.toFixed(3)),
          request_id: recommendationRequestId ?? null,
        },
      });
      viewRecordedRef.current = true;
      setVideo((current) => (current ? { ...current, view_count: result.view_count } : current));
    } catch {
      // View telemetry should never interrupt playback.
    } finally {
      viewRequestPendingRef.current = false;
    }
  }, [getToken, isSignedIn, recommendationRequestId, videoId]);

  const applyEngagement = useCallback((result: VideoEngagementResponse) => {
    setEngagement(result);
    setVideo((current) => (current ? { ...current, like_count: result.like_count } : current));
  }, []);

  const updateEngagement = useCallback(
    async (path: string, method: "POST" | "DELETE") => {
      if (!isSignedIn) {
        return;
      }
      setEngagementBusy(true);
      setEngagementError(null);
      try {
        const token = await getToken();
        applyEngagement(await apiRequest<VideoEngagementResponse>(path, { token, method }));
      } catch (err) {
        setEngagementError(err instanceof ApiError ? err.message : "Unable to update engagement.");
      } finally {
        setEngagementBusy(false);
      }
    },
    [applyEngagement, getToken, isSignedIn],
  );

  const toggleLike = useCallback(async () => {
    const method = engagement?.liked ? "DELETE" : "POST";
    await updateEngagement(`/videos/${videoId}/like`, method);
  }, [engagement?.liked, updateEngagement, videoId]);

  const toggleWatchLater = useCallback(async () => {
    const method = engagement?.saved_to_watch_later ? "DELETE" : "POST";
    await updateEngagement(`/videos/${videoId}/watch-later`, method);
  }, [engagement?.saved_to_watch_later, updateEngagement, videoId]);

  const applyComments = useCallback((result: CommentListResponse) => {
    setComments(result.items);
    setCommentTotal(result.total);
  }, []);

  const loadComments = useCallback(async () => {
    setCommentsError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      applyComments(await apiRequest<CommentListResponse>(`/videos/${videoId}/comments`, { token }));
    } catch (err) {
      setComments([]);
      setCommentTotal(0);
      setCommentsError(err instanceof ApiError ? err.message : "Unable to load comments.");
    }
  }, [applyComments, getToken, isSignedIn, videoId]);

  const submitComment = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const body = commentBody.trim();
      if (!body || !isSignedIn) {
        return;
      }
      setCommentsBusy(true);
      setCommentsError(null);
      try {
        const token = await getToken();
        const created = await apiRequest<Comment>(`/videos/${videoId}/comments`, {
          token,
          method: "POST",
          body: { body },
        });
        setComments((current) => [...current, created]);
        setCommentTotal((current) => current + 1);
        setCommentBody("");
      } catch (err) {
        setCommentsError(err instanceof ApiError ? err.message : "Unable to post comment.");
      } finally {
        setCommentsBusy(false);
      }
    },
    [commentBody, getToken, isSignedIn, videoId],
  );

  const deleteComment = useCallback(
    async (commentId: string) => {
      if (!isSignedIn) {
        return;
      }
      setCommentsBusy(true);
      setCommentsError(null);
      try {
        const token = await getToken();
        await apiRequest<void>(`/comments/${commentId}`, { token, method: "DELETE" });
        setComments((current) => current.filter((comment) => comment.id !== commentId));
        setCommentTotal((current) => Math.max(0, current - 1));
      } catch (err) {
        setCommentsError(err instanceof ApiError ? err.message : "Unable to delete comment.");
      } finally {
        setCommentsBusy(false);
      }
    },
    [getToken, isSignedIn],
  );

  const loadVideo = useCallback(async () => {
    setError(null);
    setEngagementError(null);
    setCommentsError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      const [videoResponse, statusResponse, commentsResponse] = await Promise.all([
        apiRequest<Video>(`/videos/${videoId}`, { token }),
        apiRequest<ProcessingStatus>(`/videos/${videoId}/processing-status`, { token }),
        apiRequest<CommentListResponse>(`/videos/${videoId}/comments`, { token }),
      ]);
      setVideo(videoResponse);
      setStatus(statusResponse);
      applyComments(commentsResponse);
      if (statusResponse.video_status === "ready") {
        setPlayback(await apiRequest<PlaybackResponse>(`/videos/${videoId}/playback`, { token }));
      } else {
        setPlayback(null);
      }
      if (isSignedIn) {
        try {
          applyEngagement(await apiRequest<VideoEngagementResponse>(`/videos/${videoId}/engagement`, { token }));
        } catch {
          setEngagement(null);
        }
      } else {
        setEngagement(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load this video.");
    } finally {
      setLoading(false);
    }
  }, [applyComments, applyEngagement, getToken, isSignedIn, videoId]);

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void loadVideo());
    }
  }, [isLoaded, loadVideo]);

  useEffect(() => {
    viewSessionIdRef.current = createPlaybackSessionId();
    viewRecordedRef.current = false;
    viewRequestPendingRef.current = false;
  }, [videoId]);

  useEffect(() => {
    if (!playback?.master_playlist_url || !videoRef.current) {
      return;
    }

    const source = backendAssetUrl(playback.master_playlist_url);
    const element = videoRef.current;
    setPlayerError(null);

    if (element.canPlayType("application/vnd.apple.mpegurl")) {
      element.src = source;
      queueMicrotask(() => void recordPlaybackEvent("player_ready", "native"));
      return;
    }

    if (!Hls.isSupported()) {
      queueMicrotask(() => {
        setPlayerError("This browser does not support HLS playback through Media Source Extensions.");
        void recordPlaybackEvent("unsupported");
      });
      return;
    }

    const hls = new Hls();
    hls.loadSource(source);
    hls.attachMedia(element);
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      void recordPlaybackEvent("player_ready", "hls.js");
    });
    hls.on(Hls.Events.ERROR, (_event, data) => {
      if (data.fatal) {
        setPlayerError("Playback failed while loading the API-owned HLS stream.");
        void recordPlaybackEvent("error", data.type);
      }
    });

    return () => hls.destroy();
  }, [playback, recordPlaybackEvent]);

  return (
    <div className="watchLayout">
      <section className="surface playerSurface" aria-labelledby="watch-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Watch</p>
            <h1 id="watch-heading">{video?.title ?? "Video"}</h1>
          </div>
          <button className="secondaryButton" type="button" onClick={loadVideo} disabled={loading}>
            Refresh
          </button>
        </div>

        <div className="playerFrame">
          {loading ? <p>Loading video...</p> : null}
          {error ? <p className="errorText">{error}</p> : null}
          {!loading && !error && playback?.master_playlist_url ? (
            <video
              ref={videoRef}
              controls
              playsInline
              poster={playback.thumbnail_url ? backendAssetUrl(playback.thumbnail_url) : undefined}
              onPause={() => void recordPlaybackEvent("pause")}
              onPlay={() => void recordPlaybackEvent("play")}
              onTimeUpdate={() => void recordView()}
            />
          ) : null}
          {!loading && !error && !playback?.master_playlist_url ? (
            <div className="playerPlaceholder">
              <h2>Playback is not ready</h2>
              <p>D/E still own HLS generation and proxy delivery. This page will play once the API returns a ready playlist.</p>
            </div>
          ) : null}
        </div>
        {playerError ? <p className="errorText">{playerError}</p> : null}

        <section className="commentThread" aria-labelledby="comments-heading">
          <div className="sectionHeader">
            <div>
              <p className="eyebrow">Comments</p>
              <h2 id="comments-heading">{formatCount(commentTotal, "comment")}</h2>
            </div>
            <button className="secondaryButton" type="button" onClick={loadComments} disabled={commentsBusy || loading}>
              Refresh
            </button>
          </div>

          {isSignedIn ? (
            <form className="commentForm" onSubmit={submitComment}>
              <label>
                <span>Comment</span>
                <textarea
                  maxLength={2000}
                  value={commentBody}
                  onChange={(event) => setCommentBody(event.target.value)}
                  placeholder="Add a comment"
                />
              </label>
              <button type="submit" disabled={commentsBusy || commentBody.trim().length === 0}>
                Post comment
              </button>
            </form>
          ) : (
            <p className="muted">Sign in to comment.</p>
          )}

          {commentsError ? <p className="errorText">{commentsError}</p> : null}
          {comments.length === 0 && !commentsError ? <p className="muted">No comments yet.</p> : null}
          <div className="commentList">
            {comments.map((comment) => (
              <article className="commentItem" key={comment.id}>
                <div>
                  <p className="commentAuthor">{comment.author_display_name}</p>
                  <p>{comment.body}</p>
                  <p className="metaLine">{formatDate(comment.created_at)}</p>
                </div>
                {comment.owned_by_current_user ? (
                  <button
                    className="secondaryButton"
                    type="button"
                    onClick={() => void deleteComment(comment.id)}
                    disabled={commentsBusy}
                  >
                    Delete
                  </button>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      </section>

      <aside className="sideStack">
        {video ? <StatusPanel video={video} processingStatus={status} /> : null}
        {video ? (
          <section className="surface compactSurface">
            <p className="eyebrow">Engagement</p>
            <div className="engagementActions">
              <button className="secondaryButton" type="button" onClick={toggleLike} disabled={!isSignedIn || engagementBusy}>
                {engagement?.liked ? "Liked" : "Like"}
              </button>
              <button className="secondaryButton" type="button" onClick={toggleWatchLater} disabled={!isSignedIn || engagementBusy}>
                {engagement?.saved_to_watch_later ? "Saved" : "Watch later"}
              </button>
            </div>
            <p className="metaLine">
              {formatCount(video.like_count, "like")}
              {!isSignedIn ? " / sign in to save or like" : ""}
            </p>
            {engagementError ? <p className="errorText">{engagementError}</p> : null}
          </section>
        ) : null}
        {video ? (
          <section className="surface compactSurface">
            <p className="eyebrow">Metadata</p>
            <dl className="detailGrid">
              <div>
                <dt>Privacy</dt>
                <dd>{video.privacy}</dd>
              </div>
              <div>
                <dt>Views</dt>
                <dd>{formatViewCount(video.view_count)}</dd>
              </div>
              <div>
                <dt>Resolution</dt>
                <dd>{video.width && video.height ? `${video.width}x${video.height}` : "Pending"}</dd>
              </div>
              <div>
                <dt>Video codec</dt>
                <dd>{video.video_codec ?? "Pending"}</dd>
              </div>
              <div>
                <dt>Audio codec</dt>
                <dd>{video.audio_codec ?? "Pending"}</dd>
              </div>
            </dl>
            <Link className="secondaryLink fullWidth" href="/">
              Back to library
            </Link>
          </section>
        ) : null}
      </aside>
    </div>
  );
}

function createPlaybackSessionId() {
  const randomId =
    typeof globalThis.crypto !== "undefined" && "randomUUID" in globalThis.crypto
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `watch-${randomId}`;
}

function formatViewCount(value: number) {
  return `${value.toLocaleString()} ${value === 1 ? "view" : "views"}`;
}

function formatCount(value: number, label: string) {
  return `${value.toLocaleString()} ${label}${value === 1 ? "" : "s"}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}
