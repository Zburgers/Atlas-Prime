import { AuthApiStatus } from "./components/api-status";
import { VideoList } from "./components/video-list";

export default function Home() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return (
    <div className="homeStack">
      <VideoList />
      <section className="surface compactSurface">
        <p className="eyebrow">Local API</p>
        <p>
          Health endpoint: <code>{apiBaseUrl}/healthz</code>
        </p>
        <AuthApiStatus apiBaseUrl={apiBaseUrl} />
      </section>
    </div>
  );
}
