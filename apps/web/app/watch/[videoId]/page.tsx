import { WatchClient } from "./watch-client";

type WatchPageProps = {
  params: Promise<{ videoId: string }>;
  searchParams: Promise<{ request_id?: string | string[] }>;
};

export default async function WatchPage({ params, searchParams }: WatchPageProps) {
  const { videoId } = await params;
  const { request_id } = await searchParams;
  const recommendationRequestId = typeof request_id === "string" ? request_id : undefined;
  return <WatchClient videoId={videoId} recommendationRequestId={recommendationRequestId} />;
}
