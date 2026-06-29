import { WatchClient } from "./watch-client";

type WatchPageProps = {
  params: Promise<{ videoId: string }>;
};

export default async function WatchPage({ params }: WatchPageProps) {
  const { videoId } = await params;
  return <WatchClient videoId={videoId} />;
}
