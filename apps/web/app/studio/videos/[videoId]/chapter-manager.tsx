"use client";

import { useAuth } from "@clerk/nextjs";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, apiRequest, type VideoChapter, type VideoChapterListResponse } from "../../../components/video-api";

type DraftChapter = { title: string; start_seconds: string };

export function ChapterManager({ videoId }: { videoId: string }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [items, setItems] = useState<DraftChapter[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const token = await getToken();
      const response = await apiRequest<VideoChapterListResponse>(`/studio/videos/${videoId}/chapters`, { token });
      setItems(response.items.map(toDraft));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to load chapters.");
    }
  }, [getToken, isLoaded, isSignedIn, videoId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function update(index: number, key: keyof DraftChapter, value: string) {
    setItems((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isSignedIn) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      const token = await getToken();
      const response = await apiRequest<VideoChapterListResponse>(`/studio/videos/${videoId}/chapters`, {
        method: "PUT", token, body: { items: items.map((item) => ({ title: item.title, start_seconds: Number(item.start_seconds) })) },
      });
      setItems(response.items.map(toDraft));
      setMessage("Chapters saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to save chapters.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="surface" aria-labelledby="chapters-heading">
      <div className="sectionHeader"><div><p className="eyebrow">Studio</p><h2 id="chapters-heading">Chapters</h2></div></div>
      <form className="chapterForm" onSubmit={save}>
        {items.map((item, index) => (
          <div className="chapterRow" key={`${index}-${item.start_seconds}`}>
            <label><span>Chapter title</span><input value={item.title} onChange={(event) => update(index, "title", event.target.value)} maxLength={160} required disabled={busy} /></label>
            <label><span>Start seconds</span><input type="number" min="0" step="0.001" value={item.start_seconds} onChange={(event) => update(index, "start_seconds", event.target.value)} required disabled={busy} /></label>
            <button type="button" className="secondaryButton" onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))} disabled={busy}>Remove</button>
          </div>
        ))}
        <div className="chapterActions">
          <button type="button" className="secondaryButton" onClick={() => setItems((current) => [...current, { title: "", start_seconds: current.length ? String(Number(current[current.length - 1].start_seconds || 0) + 1) : "0" }])} disabled={busy}>Add chapter</button>
          <button type="submit" disabled={busy}>{busy ? "Saving..." : "Save chapters"}</button>
        </div>
      </form>
      {error ? <p className="errorText" role="alert">{error}</p> : null}
      {message ? <p className="successText" role="status">{message}</p> : null}
    </section>
  );
}

function toDraft(item: VideoChapter): DraftChapter {
  return { title: item.title, start_seconds: item.start_seconds };
}
