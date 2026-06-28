export default function Home() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  return (
    <main>
      <section className="panel">
        <p className="label">Atlas Prime MVP</p>
        <h1>Local stack is ready for sector work.</h1>
        <p>
          Sector H provides Docker Compose, repeatable test commands, MinIO buckets,
          Redis, PostgreSQL, a FastAPI health surface, and a Celery media worker.
        </p>
        <p>
          API health: <code>{apiBaseUrl}/healthz</code>
        </p>
      </section>
    </main>
  );
}
