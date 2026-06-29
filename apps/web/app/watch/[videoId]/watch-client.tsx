"use client";

import { useAuth } from "@clerk/nextjs";
import Hls from "hls.js";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { StatusPanel } from "../../components/status-ui";
import {
  ApiError,
  apiRequest,
  backendAssetUrl,
  type PlaybackResponse,
  type ProcessingStatus,
  type Video,
} from "../../components/video-api";

export function WatchClient({ videoId }: { videoId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [video, setVideo] = useState<Video | null>(null);
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [playback, setPlayback] = useState<PlaybackResponse | null>(null);
  const [loading, setLoading] = useState(true);
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
          },
        });
      } catch {
        // Playback telemetry should never interrupt viewing.
      }
    },
    [getToken, isSignedIn, videoId],
  );

  const loadVideo = useCallback(async () => {
    setError(null);
    try {
      const token = isSignedIn ? await getToken() : null;
      const [videoResponse, statusResponse] = await Promise.all([
        apiRequest<Video>(`/videos/${videoId}`, { token }),
        apiRequest<ProcessingStatus>(`/videos/${videoId}/processing-status`, { token }),
      ]);
      setVideo(videoResponse);
      setStatus(statusResponse);
      if (statusResponse.video_status === "ready") {
        setPlayback(await apiRequest<PlaybackResponse>(`/videos/${videoId}/playback`, { token }));
      } else {
        setPlayback(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load this video.");
    } finally {
      setLoading(false);
    }
  }, [getToken, isSignedIn, videoId]);

  useEffect(() => {
    if (isLoaded) {
      queueMicrotask(() => void loadVideo());
    }
  }, [isLoaded, loadVideo]);

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
      </section>

      <aside className="sideStack">
        {video ? <StatusPanel video={video} processingStatus={status} /> : null}
        {video ? (
          <section className="surface compactSurface">
            <p className="eyebrow">Metadata</p>
            <dl className="detailGrid">
              <div>
                <dt>Privacy</dt>
                <dd>{video.privacy}</dd>
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
