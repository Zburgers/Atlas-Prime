"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { ChangeEvent, FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type TextTrack, type TextTrackListResponse } from "../../../components/video-api";

export function CaptionManager({ videoId }: { videoId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<TextTrack[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("en");
  const [label, setLabel] = useState("English");
  const [isDefault, setIsDefault] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const token = await getToken();
      setItems((await apiRequest<TextTrackListResponse>(`/studio/videos/${videoId}/captions`, { token })).items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load captions.");
    }
  }, [getToken, isLoaded, isSignedIn, videoId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !isSignedIn) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const token = await getToken();
      const form = new FormData();
      form.set("file", file);
      form.set("language", language);
      form.set("label", label);
      form.set("is_default", String(isDefault));
      await apiRequest<TextTrack>(`/studio/videos/${videoId}/captions`, { method: "POST", token, body: form });
      setFile(null);
      setMessage("Caption track uploaded.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to upload caption track.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="surface" aria-labelledby="captions-heading">
      <div className="sectionHeader">
        <div>
          <p className="eyebrow">Studio</p>
          <h2 id="captions-heading">Captions</h2>
        </div>
        <Link className="secondaryLink" href="/studio/videos">Back</Link>
      </div>
      <form className="captionForm" onSubmit={upload}>
        <label>
          <span>WebVTT file</span>
          <input type="file" accept=".vtt,text/vtt" required onChange={chooseFile} disabled={busy} />
        </label>
        <label>
          <span>Language</span>
          <input value={language} onChange={(event) => setLanguage(event.target.value)} pattern="[a-z]{2,3}(-[A-Z]{2})?" required disabled={busy} />
        </label>
        <label>
          <span>Label</span>
          <input value={label} onChange={(event) => setLabel(event.target.value)} maxLength={80} required disabled={busy} />
        </label>
        <label className="captionDefault">
          <input type="checkbox" checked={isDefault} onChange={(event) => setIsDefault(event.target.checked)} disabled={busy} />
          <span>Use as default</span>
        </label>
        <button type="submit" disabled={busy || !file}>{busy ? "Uploading..." : "Upload captions"}</button>
      </form>
      {error ? <p className="errorText" role="alert">{error}</p> : null}
      {message ? <p className="successText" role="status">{message}</p> : null}
      {items.length === 0 ? <p className="muted">No caption tracks uploaded.</p> : null}
      <ul className="captionList" aria-label="Caption tracks">
        {items.map((item) => (
          <li key={item.id}>
            <span>{item.label}</span>
            <span className="metaLine">{item.language}{item.default ? " / default" : ""}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
