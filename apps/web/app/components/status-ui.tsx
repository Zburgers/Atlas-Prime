import type { ProcessingStatus, Video, VideoStatus } from "./video-api";

const STATUS_LABELS: Record<VideoStatus, string> = {
  draft: "Draft",
  uploading: "Uploading",
  uploaded: "Uploaded",
  queued: "Queued",
  probing: "Probing",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const STATUS_HINTS: Record<VideoStatus, string> = {
  draft: "Metadata exists. Upload an original video file to continue.",
  uploading: "The API is receiving the original video.",
  uploaded: "The original is stored and ready to be queued.",
  queued: "Processing has been queued. Sector D owns the worker path.",
  probing: "The worker is inspecting media metadata.",
  processing: "The worker is generating HLS output.",
  ready: "Playback metadata is available.",
  failed: "The backend marked this video failed. Check the message below.",
};

export function StatusPill({ status }: { status: VideoStatus }) {
  return <span className={`statusPill status-${status}`}>{STATUS_LABELS[status]}</span>;
}

export function StatusTimeline({ status }: { status: VideoStatus }) {
  const statuses: VideoStatus[] = ["draft", "uploading", "uploaded", "queued", "probing", "processing", "ready"];
  const activeIndex = statuses.indexOf(status);

  return (
    <ol className="statusTimeline" aria-label="Video lifecycle">
      {statuses.map((item, index) => (
        <li key={item} className={index <= activeIndex ? "complete" : ""}>
          <span>{STATUS_LABELS[item]}</span>
        </li>
      ))}
      {status === "failed" ? (
        <li className="failed">
          <span>Failed</span>
        </li>
      ) : null}
    </ol>
  );
}

export function StatusPanel({
  video,
  processingStatus,
}: {
  video: Video;
  processingStatus?: ProcessingStatus | null;
}) {
  const failureMessage = processingStatus?.failure_message || video.failure_message;

  return (
    <section className="surface compactSurface" aria-labelledby="status-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Status</p>
          <h2 id="status-heading">Processing state</h2>
        </div>
        <StatusPill status={processingStatus?.video_status ?? video.status} />
      </div>
      <StatusTimeline status={processingStatus?.video_status ?? video.status} />
      <p className="muted">{STATUS_HINTS[processingStatus?.video_status ?? video.status]}</p>
      {processingStatus?.latest_job ? (
        <dl className="detailGrid">
          <div>
            <dt>Latest job</dt>
            <dd>{processingStatus.latest_job.status}</dd>
          </div>
          <div>
            <dt>Attempts</dt>
            <dd>{processingStatus.latest_job.attempt_count}</dd>
          </div>
        </dl>
      ) : null}
      {failureMessage ? <p className="errorText">{failureMessage}</p> : null}
    </section>
  );
}

export function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
