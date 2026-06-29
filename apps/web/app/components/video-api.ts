export type VideoStatus =
  | "draft"
  | "uploading"
  | "uploaded"
  | "queued"
  | "probing"
  | "processing"
  | "ready"
  | "failed";

export type VideoPrivacy = "private" | "public" | "unlisted";

export type Video = {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  privacy: VideoPrivacy;
  status: VideoStatus;
  original_storage_key: string | null;
  hls_master_storage_key: string | null;
  thumbnail_storage_key: string | null;
  duration_seconds: string | null;
  width: number | null;
  height: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  source_bitrate: number | null;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
};

export type VideoListResponse = {
  items: Video[];
  total: number;
  page: number;
  page_size: number;
};

export type ProcessingJob = {
  id: string;
  video_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  attempt_count: number;
  worker_id: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
};

export type AdminJob = ProcessingJob & {
  video_title: string | null;
  video_status: VideoStatus | null;
  video_failure_code: string | null;
  video_failure_message: string | null;
};

export type PlaybackEvent = {
  id: string;
  user_id: string | null;
  video_id: string;
  event_type: string;
  position_seconds: string | null;
  quality_label: string | null;
  client_timestamp: string | null;
  created_at: string;
};

export type AdminOps = {
  status: "ok" | "degraded";
  api: Record<string, unknown>;
  worker: {
    ok: boolean;
    online_workers: string[];
    active_queues: Record<string, string[]>;
    error: string | null;
  };
  redis: {
    ok: boolean;
    media_queue_depth: number | null;
    error: string | null;
  };
};

export type AdminVideoDebug = {
  video: Video;
  renditions: PlaybackResponse["renditions"];
  processing_jobs: ProcessingJob[];
  recent_playback_events: PlaybackEvent[];
};

export type ProcessingStatus = {
  video_id: string;
  video_status: VideoStatus;
  latest_job: ProcessingJob | null;
  failure_code: string | null;
  failure_message: string | null;
};

export type PlaybackResponse = {
  video_id: string;
  status: VideoStatus;
  master_playlist_url: string | null;
  thumbnail_url: string | null;
  renditions: Array<{
    id: string;
    video_id: string;
    label: string;
    width: number;
    height: number;
    target_bitrate: number;
    playlist_storage_key: string | null;
    status: string;
    created_at: string;
  }>;
};

export type UploadResponse = {
  video: Video;
  processing_job: ProcessingJob;
  storage_key: string;
  size_bytes: number;
  content_type: string;
  celery_task_id: string;
};

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

type RequestOptions = {
  token?: string | null;
  method?: string;
  body?: BodyInit | object;
  headers?: HeadersInit;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  const response = await fetch(`/api/backend${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });

  if (!response.ok) {
    const details = await readErrorDetails(response);
    throw new ApiError(response.status, errorMessage(details, response.status), details);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function backendAssetUrl(apiOwnedPath: string): string {
  return `/api/backend${apiOwnedPath.startsWith("/") ? apiOwnedPath : `/${apiOwnedPath}`}`;
}

async function readErrorDetails(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

function errorMessage(details: unknown, status: number): string {
  if (typeof details === "object" && details !== null && "detail" in details) {
    const detail = (details as { detail: unknown }).detail;
    if (typeof detail === "object" && detail !== null && "message" in detail) {
      const message = (detail as { message: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
  }
  if (status === 401 || status === 403) {
    return "Sign in with an account that has access to this video.";
  }
  return `API request failed with status ${status}`;
}
