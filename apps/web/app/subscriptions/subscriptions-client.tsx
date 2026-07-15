"use client";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type VideoListResponse } from "../components/video-api";
import { VideoCard } from "../components/video-list";

export function SubscriptionsClient() {
  const { getToken, isLoaded, isSignedIn } = useAuth(); const [items, setItems] = useState<VideoListResponse["items"]>([]); const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => { if (!isSignedIn) return; try { setItems((await apiRequest<VideoListResponse>("/feed/subscriptions", { token: await getToken() })).items); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load subscriptions."); } }, [getToken, isSignedIn]);
  useEffect(() => { if (!isLoaded) return; const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [isLoaded, load]);
  return <section className="surface" aria-labelledby="subscriptions-heading"><p className="eyebrow">Following</p><h1 id="subscriptions-heading">Subscriptions</h1>{!isSignedIn ? <p className="muted">Sign in to see uploads from channels you follow.</p> : null}{error ? <p className="errorText" role="alert">{error}</p> : null}{isSignedIn && !error && items.length === 0 ? <p className="muted">No public uploads from followed channels yet.</p> : null}<div className="videoGrid" role="list">{items.map((video) => <VideoCard key={video.id} video={video} />)}</div></section>;
}
