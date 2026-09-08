"use client";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type Playlist } from "../../components/video-api";

export function PlaylistClient({ playlistId }: { playlistId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth(); const [playlist, setPlaylist] = useState<Playlist | null>(null); const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => { try { setPlaylist(await apiRequest<Playlist>(`/playlists/${playlistId}`, { token: isSignedIn ? await getToken() : null })); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to load playlist."); } }, [getToken, isSignedIn, playlistId]);
  useEffect(() => { if (!isLoaded) return; const timer = window.setTimeout(() => void load(), 0); return () => window.clearTimeout(timer); }, [isLoaded, load]);
  return <section className="surface" aria-labelledby="playlist-heading">{error ? <p className="errorText" role="alert">{error}</p> : null}{playlist ? <><p className="eyebrow">Playlist / {playlist.privacy}</p><h1 id="playlist-heading">{playlist.title}</h1>{playlist.description ? <p className="muted">{playlist.description}</p> : null}<ol className="captionList">{playlist.items.map((item) => <li key={item.id}><Link href={`/watch/${item.video.id}`}>{item.video.title}</Link><span className="metaLine">{item.position + 1}</span></li>)}</ol>{playlist.items.length === 0 ? <p className="muted">This playlist has no videos yet.</p> : null}</> : !error ? <p className="muted">Loading playlist...</p> : null}</section>;
}
