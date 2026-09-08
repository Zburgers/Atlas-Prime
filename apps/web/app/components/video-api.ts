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
  duration_seconds: string | null;
  width: number | null;
  height: number | null;
  video_codec: string | null;
  audio_codec: string | null;
  source_bitrate: number | null;
  view_count: number;
  impression_count: number;
  like_count: number;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
};

export type VideoListItem = {
  id: string;
  channel_id: string | null;
  title: string;
  description: string | null;
  privacy: VideoPrivacy;
  status: VideoStatus;
  thumbnail_url: string | null;
  channel_handle: string | null;
  channel_display_name: string | null;
  caption_snippet: string | null;
  duration_seconds: string | null;
  width: number | null;
  height: number | null;
  view_count: number;
  impression_count: number;
  like_count: number;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
};

export type VideoListResponse = {
  items: VideoListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type WatchHistoryItem = {
  id: string;
  position_seconds: number | null;
  watched_at: string;
  video: VideoListItem;
};

export type WatchHistoryResponse = { items: WatchHistoryItem[] };

export type Playlist = {
  id: string;
  owner_id: string;
  title: string;
  description: string | null;
  privacy: "private" | "public";
  created_at: string;
  updated_at: string;
  items: Array<{ id: string; position: number; created_at: string; video: VideoListItem }>;
};

export type StudioVideoListResponse = VideoListResponse;

export type SearchResponse = {
  query: string;
  items: VideoListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type FeedItem = {
  request_id: string;
  surface: string;
  rank: number;
  score: number;
  reason: string;
  video: VideoListItem;
};

export type FeedResponse = {
  request_id: string;
  surface: string;
  algorithm_version: string;
  items: FeedItem[];
  total: number;
  page: number;
  page_size: number;
};

export type Channel = {
  id: string;
  owner_user_id: string;
  handle: string;
  display_name: string;
  description: string | null;
  avatar_storage_key: string | null;
  banner_storage_key: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicChannelResponse = Channel & {
  videos: VideoListItem[];
};

export type ProcessingJob = {
  id: string;
  video_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  stage: "queued" | "downloading" | "probing" | "packaging" | "uploading" | "complete" | "failed";
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
  playback_session_id: string;
  event_id: string;
  event_type: string;
  position_seconds: string | null;
  quality_label: string | null;
  client_timestamp: string | null;
  request_id: string | null;
  created_at: string;
};

export type PlaybackEventRequest = {
  playback_session_id: string;
  event_id: string;
  event_type: string;
  position_seconds?: number | null;
  quality_label?: string | null;
  client_timestamp?: string | null;
  request_id?: string | null;
};

export function createPlaybackTelemetryUuid(): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }

  const bytes = new Uint8Array(16);
  if (typeof cryptoApi?.getRandomValues === "function") {
    cryptoApi.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function buildPlaybackEventRequest(
  identity: Pick<PlaybackEventRequest, "playback_session_id" | "event_id">,
  fields: Omit<PlaybackEventRequest, "playback_session_id" | "event_id">,
): PlaybackEventRequest {
  return { ...fields, ...identity };
}

export type VideoImpression = {
  id: string;
  user_id: string | null;
  video_id: string;
  surface: string;
  position: number;
  request_id: string | null;
  created_at: string;
};

export type VideoViewResponse = {
  video_id: string;
  counted: boolean;
  view_count: number;
  threshold_seconds: string;
};

export type Thumbnail = {
  id: string;
  source: "generated" | "custom";
  content_type: string;
  width: number;
  height: number;
  selected: boolean;
  url: string;
  created_at: string;
};

export type ThumbnailListResponse = { items: Thumbnail[] };

export type TextTrack = {
  id: string;
  language: string;
  label: string;
  kind: "captions";
  default: boolean;
  url: string;
  created_at: string;
};

export type TextTrackListResponse = { items: TextTrack[] };

export type VideoEngagementResponse = {
  video_id: string;
  liked: boolean;
  like_count: number;
  saved_to_watch_later: boolean;
};

export type Comment = {
  id: string;
  video_id: string;
  body: string;
  author_display_name: string;
  owned_by_current_user: boolean;
  created_at: string;
  updated_at: string;
};

export type CommentListResponse = {
  items: Comment[];
  total: number;
  page: number;
  page_size: number;
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

export type AdminTelemetryHealth = {
  status: "ok" | "degraded";
  accepted_event_count: number | null;
  duplicate_event_count: number | null;
  rate_limited_event_count: number | null;
  purged_event_count: number | null;
  retention_cutoff: string;
};

export type AdminRecommendationRequest = { request_id: string; surface: string; algorithm_version: string; total_results: number; created_at: string };
export type AdminRecommendationDebug = { request_id: string; surface: string; algorithm_version: string; page: number; page_size: number; total_results: number; results: Array<{ video_id: string; rank: number; score: number; reason: string; impression_count: number; playback_event_count: number; view_count: number }> };

export type AdminVideoDebug = {
  video: AdminVideoDebugVideo;
  renditions: AdminRenditionDebug[];
  processing_jobs: ProcessingJob[];
  recent_playback_events: PlaybackEvent[];
};

export type AdminVideoDebugVideo = Video & {
  original_storage_key: string | null;
  hls_master_storage_key: string | null;
  thumbnail_storage_key: string | null;
};

export type AdminRenditionDebug = PlaybackResponse["renditions"][number] & {
  playlist_storage_key: string | null;
};

export type ModerationTargetType = "video" | "comment";
export type ModerationActionName = "remove" | "restore" | "limit";

export type ContentReport = {
  id: string;
  reporter_user_id: string | null;
  target_type: ModerationTargetType;
  target_id: string;
  reason: string;
  details: string | null;
  status: "open" | "actioned" | "dismissed";
  created_at: string;
};

export type ContentReportListResponse = {
  items: ContentReport[];
  total: number;
};

export type ModerationAction = {
  id: string;
  actor_user_id: string | null;
  target_type: ModerationTargetType;
  target_id: string;
  action: ModerationActionName;
  reason: string | null;
  created_at: string;
};

export type ModerationActionResult = {
  report: ContentReport;
  action: ModerationAction;
};

export type AnalyticsTotals = {
  impressions: number;
  views: number;
  watch_time_seconds: string;
};

export type AnalyticsDailyPoint = AnalyticsTotals & {
  date: string;
};

export type AnalyticsTopVideo = AnalyticsTotals & {
  video_id: string;
  title: string;
};

export type StudioAnalytics = {
  date_from: string;
  date_to: string;
  totals: AnalyticsTotals;
  daily: AnalyticsDailyPoint[];
  top_videos: AnalyticsTopVideo[];
};

export type ProcessingStatus = {
  video_id: string;
  video_status: VideoStatus;
  latest_job: Pick<ProcessingJob, "id" | "video_id" | "status" | "stage"> | null;
  failure_code: string | null;
  failure_message: string | null;
};

export type ProcessingTimelineResponse = { items: ProcessingJob[] };

export type VideoChapter = {
  title: string;
  start_seconds: string;
};

export type VideoChapterListResponse = { items: VideoChapter[] };

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
    status: string;
    created_at: string;
  }>;
  text_tracks: TextTrack[];
  chapters: VideoChapter[];
};

export type UploadResponse = {
  video: Video;
  processing_job: ProcessingJob;
  size_bytes: number;
  content_type: string;
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
