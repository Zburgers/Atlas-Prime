import { ThumbnailManager } from "./thumbnail-manager";

type ThumbnailPageProps = { params: Promise<{ videoId: string }> };

export default async function StudioThumbnailPage({ params }: ThumbnailPageProps) {
  const { videoId } = await params;
  return <ThumbnailManager videoId={videoId} />;
}
