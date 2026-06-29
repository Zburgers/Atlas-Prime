"use client";

import { Show, SignInButton, useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, apiRequest, type UploadResponse, type Video } from "../components/video-api";
import { StatusPanel } from "../components/status-ui";

export function UploadForm() {
  const { getToken } = useAuth();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<"idle" | "creating" | "uploading" | "done">("idle");
  const [createdVideo, setCreatedVideo] = useState<Video | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setUploadResult(null);

    if (!file) {
      setError("Choose a local video file before uploading.");
      return;
    }

    const token = await getToken();
    if (!token) {
      setError("Sign in before uploading a video.");
      return;
    }

    try {
      setPhase("creating");
      const video = await apiRequest<Video>("/videos", {
        method: "POST",
        token,
        body: { title, description: description || null },
      });
      setCreatedVideo(video);

      setPhase("uploading");
      const formData = new FormData();
      formData.set("file", file);
      const result = await apiRequest<UploadResponse>(`/videos/${video.id}/upload`, {
        method: "POST",
        token,
        body: formData,
      });
      setUploadResult(result);
      setCreatedVideo(result.video);
      setPhase("done");
    } catch (err) {
      setPhase("idle");
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    }
  }

  const busy = phase === "creating" || phase === "uploading";

  return (
    <div className="pageGrid">
      <section className="surface" aria-labelledby="upload-heading">
        <p className="eyebrow">Upload</p>
        <h1 id="upload-heading">Create a private video</h1>
        <p className="muted">
          The MVP path sends the selected file through FastAPI, which owns validation and MinIO storage.
        </p>

        <Show when="signed-out">
          <div className="notice">
            <p>Sign in to create private uploads.</p>
            <SignInButton mode="modal">
              <button type="button">Sign in</button>
            </SignInButton>
          </div>
        </Show>

        <Show when="signed-in">
          <form className="uploadForm" onSubmit={submitUpload}>
            <label>
              <span>Title</span>
              <input
                required
                maxLength={180}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Lecture 01: Introduction"
              />
            </label>
            <label>
              <span>Description</span>
              <textarea
                maxLength={5000}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional context for the video."
              />
            </label>
            <label>
              <span>Video file</span>
              <input
                required
                accept="video/mp4,video/x-m4v,video/quicktime,video/webm,.mp4,.m4v,.mov,.webm"
                type="file"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <p className="fieldHint">New videos stay private by default. Direct browser-to-MinIO upload is not used.</p>
            {error ? <p className="errorText">{error}</p> : null}
            <button type="submit" disabled={busy}>
              {phase === "creating" ? "Creating..." : phase === "uploading" ? "Uploading..." : "Upload"}
            </button>
          </form>
        </Show>
      </section>

      <aside className="sideStack">
        <section className="surface compactSurface">
          <p className="eyebrow">Flow</p>
          <ol className="plainList">
            <li>Create video metadata.</li>
            <li>Post file to FastAPI upload endpoint.</li>
            <li>Show queued status after upload succeeds.</li>
          </ol>
        </section>
        {createdVideo ? <StatusPanel video={createdVideo} /> : null}
        {uploadResult ? (
          <section className="surface compactSurface">
            <p className="eyebrow">Upload result</p>
            <dl className="detailGrid">
              <div>
                <dt>Bytes</dt>
                <dd>{uploadResult.size_bytes.toLocaleString()}</dd>
              </div>
              <div>
                <dt>Content type</dt>
                <dd>{uploadResult.content_type}</dd>
              </div>
            </dl>
            <Link className="buttonLink fullWidth" href={`/watch/${uploadResult.video.id}`}>
              Watch status
            </Link>
          </section>
        ) : null}
      </aside>
    </div>
  );
}
