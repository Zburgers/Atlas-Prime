"use client";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type WatchHistoryResponse } from "../components/video-api";
import { formatDate } from "../components/status-ui";

export function LibraryClient() {
  const { getToken, isLoaded, isSignedIn } = useAuth(); const [items, setItems] = useState<WatchHistoryResponse["items"]>([]); const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => { if (!isSignedIn) return; try { setItems((await apiRequest<WatchHistoryResponse>("/library/history", { token: await getToken() })).items); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load history."); } }, [getToken, isSignedIn]);
  useEffect(() => { if (isLoaded) void load(); }, [isLoaded, load]);
  return <section className="surface" aria-labelledby="history-heading"><p className="eyebrow">Library</p><h1 id="history-heading">Watch history</h1>{!isSignedIn ? <p className="muted">Sign in to keep a viewing history.</p> : null}{error ? <p className="errorText" role="alert">{error}</p> : null}<ul className="captionList">{items.map((item) => <li key={item.id}><Link href={`/watch/${item.video.id}`}>{item.video.title}</Link><span className="metaLine">Watched {formatDate(item.watched_at)}</span></li>)}</ul>{isSignedIn && !error && items.length === 0 ? <p className="muted">Your watched videos will appear here.</p> : null}</section>;
}
