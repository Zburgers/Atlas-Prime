import Link from "next/link";

export default function StudioPage() {
  return (
    <div className="pageGrid">
      <section className="surface" aria-labelledby="studio-heading">
        <p className="eyebrow">Studio</p>
        <h1 id="studio-heading">Creator Studio</h1>
        <p className="muted">Manage videos, privacy, processing state, and upload recovery from one owner-only surface.</p>
        <div className="actionRow">
          <Link className="buttonLink" href="/studio/videos">
            Open videos
          </Link>
          <Link className="buttonLink secondaryButton" href="/upload">
            Upload
          </Link>
        </div>
      </section>

      <aside className="sideStack">
        <section className="surface compactSurface">
          <p className="eyebrow">Owner tools</p>
          <dl className="detailGrid">
            <div>
              <dt>Privacy</dt>
              <dd>private, public, unlisted</dd>
            </div>
            <div>
              <dt>Retry</dt>
              <dd>failed videos only</dd>
            </div>
          </dl>
        </section>
      </aside>
    </div>
  );
}
