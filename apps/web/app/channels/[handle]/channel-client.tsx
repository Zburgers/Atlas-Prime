"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type PublicChannelResponse } from "../../components/video-api";
import { createRequestId, VideoCard } from "../../components/video-list";

export function ChannelClient({ handle }: { handle: string }) {
  const [requestId] = useState(() => createRequestId("channel"));
  const [channel, setChannel] = useState<PublicChannelResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadChannel = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setChannel(await apiRequest<PublicChannelResponse>(`/channels/${handle}`));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load this channel.");
    } finally {
      setLoading(false);
    }
  }, [handle]);

  useEffect(() => {
    queueMicrotask(() => void loadChannel());
  }, [loadChannel]);

  return (
    <div className="homeStack">
      <section className="surface" aria-labelledby="channel-heading">
        <div className="sectionHeader">
          <div>
            <p className="eyebrow">Channel</p>
            <h1 id="channel-heading">{channel?.display_name ?? `@${handle}`}</h1>
            <p className="muted">{channel?.description || "Public ready videos from this creator."}</p>
          </div>
          <Link className="secondaryLink" href="/">
            Home
          </Link>
        </div>

        {loading ? <p className="muted">Loading channel...</p> : null}
        {error ? <p className="errorText">{error}</p> : null}
        {!loading && !error && channel?.videos.length === 0 ? (
          <div className="emptyState">
            <h2>No public videos yet</h2>
            <p>This channel has no public ready videos.</p>
          </div>
        ) : null}
        {!loading && !error && channel && channel.videos.length > 0 ? (
          <div className="videoGrid" role="list">
            {channel.videos.map((video, index) => (
              <VideoCard key={video.id} video={video} surface="channel" position={index} requestId={requestId} />
            ))}
          </div>
        ) : null}
      </section>
    </div>
  );
}
