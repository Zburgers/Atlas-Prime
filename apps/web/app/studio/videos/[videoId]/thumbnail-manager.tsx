"use client";

import { useAuth } from "@clerk/nextjs";
import Image from "next/image";
import Link from "next/link";
import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, backendAssetUrl, type Thumbnail, type ThumbnailListResponse } from "../../../components/video-api";

export function ThumbnailManager({ videoId }: { videoId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<Thumbnail[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const token = await getToken();
      setItems((await apiRequest<ThumbnailListResponse>(`/studio/videos/${videoId}/thumbnails`, { token })).items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load thumbnails.");
    }
  }, [getToken, isLoaded, isSignedIn, videoId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !isSignedIn) return;
    setBusy(true); setError(null);
    try {
      const token = await getToken();
      const form = new FormData(); form.set("file", file);
      await apiRequest<Thumbnail>(`/studio/videos/${videoId}/thumbnails`, { method: "POST", token, body: form });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to upload thumbnail.");
    } finally { setBusy(false); event.target.value = ""; }
  }

  async function select(thumbnailId: string) {
    if (!isSignedIn) return;
    setBusy(true); setError(null);
    try {
      const token = await getToken();
      await apiRequest<Thumbnail>(`/studio/videos/${videoId}/thumbnails/${thumbnailId}/select`, { method: "POST", token });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to select thumbnail.");
    } finally { setBusy(false); }
  }

  return <section className="surface" aria-labelledby="thumbnail-heading">
    <div className="sectionHeader"><div><p className="eyebrow">Studio</p><h1 id="thumbnail-heading">Thumbnails</h1></div><Link className="secondaryLink" href="/studio/videos">Back</Link></div>
    <label className="buttonLink">Upload custom<input className="srOnly" type="file" accept="image/png,image/jpeg" onChange={upload} disabled={busy} /></label>
    {error ? <p className="errorText">{error}</p> : null}
    <div className="thumbnailGrid">{items.map((item) => <article className="thumbnailCandidate" key={item.id}>
      <Image alt="" src={backendAssetUrl(item.url)} width={320} height={180} unoptimized />
      <div><span>{item.source}</span><button type="button" className="secondaryButton" disabled={busy || item.selected} onClick={() => void select(item.id)}>{item.selected ? "Selected" : "Select"}</button></div>
    </article>)}</div>
  </section>;
}
