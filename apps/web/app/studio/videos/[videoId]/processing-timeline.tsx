"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type ProcessingJob, type ProcessingTimelineResponse } from "../../../components/video-api";
import { formatDate } from "../../../components/status-ui";

const STAGE_LABELS: Record<ProcessingJob["stage"], string> = {
  queued: "Queued",
  downloading: "Downloading original",
  probing: "Inspecting media",
  packaging: "Generating HLS",
  uploading: "Publishing assets",
  complete: "Completed",
  failed: "Failed",
};

export function ProcessingTimeline({ videoId }: { videoId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<ProcessingJob[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const token = await getToken();
      setItems((await apiRequest<ProcessingTimelineResponse>(`/studio/videos/${videoId}/processing-timeline`, { token })).items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load processing history.");
    }
  }, [getToken, isLoaded, isSignedIn, videoId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  return (
    <section className="surface" aria-labelledby="processing-timeline-heading">
      <div className="sectionHeader"><div><p className="eyebrow">Studio</p><h2 id="processing-timeline-heading">Processing history</h2></div></div>
      {error ? <p className="errorText" role="alert">{error}</p> : null}
      {items.length === 0 ? <p className="muted">No processing attempts yet.</p> : null}
      <ol className="processingTimeline">
        {items.map((item) => (
          <li key={item.id}>
            <div><strong>{STAGE_LABELS[item.stage]}</strong><span className="metaLine">Attempt {item.attempt_count || 1} / {item.status}</span></div>
            <time dateTime={item.finished_at ?? item.started_at ?? item.created_at}>{formatDate(item.finished_at ?? item.started_at ?? item.created_at)}</time>
            {item.error_message ? <p className="errorText">{item.error_message}</p> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
