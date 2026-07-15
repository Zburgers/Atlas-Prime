"use client";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ApiError, apiRequest, type Playlist } from "../../components/video-api";

export function NewPlaylistClient() {
  const { getToken, isSignedIn } = useAuth(); const router = useRouter(); const [title, setTitle] = useState(""); const [description, setDescription] = useState(""); const [privacy, setPrivacy] = useState<"private" | "public">("private"); const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); if (!isSignedIn) return; setBusy(true); setError(null); try { const playlist = await apiRequest<Playlist>("/playlists", { method: "POST", token: await getToken(), body: { title, description: description || null, privacy } }); router.push(`/playlists/${playlist.id}`); } catch (err) { setError(err instanceof ApiError ? err.message : "Unable to create playlist."); } finally { setBusy(false); } }
  return <section className="surface" aria-labelledby="playlist-new-heading"><p className="eyebrow">Library</p><h1 id="playlist-new-heading">New playlist</h1>{!isSignedIn ? <p className="muted">Sign in to create a playlist.</p> : <form className="formStack" onSubmit={submit}><label><span>Title</span><input required maxLength={180} value={title} onChange={(event) => setTitle(event.target.value)} /></label><label><span>Description</span><textarea maxLength={2000} value={description} onChange={(event) => setDescription(event.target.value)} /></label><label><span>Visibility</span><select value={privacy} onChange={(event) => setPrivacy(event.target.value as "private" | "public")}><option value="private">Private</option><option value="public">Public</option></select></label><button disabled={busy || !title.trim()} type="submit">{busy ? "Creating..." : "Create playlist"}</button></form>}{error ? <p className="errorText" role="alert">{error}</p> : null}</section>;
}
