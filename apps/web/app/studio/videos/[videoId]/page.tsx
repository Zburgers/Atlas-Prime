import { CaptionManager } from "./caption-manager";
import { ThumbnailManager } from "./thumbnail-manager";

type StudioVideoAssetsPageProps = { params: Promise<{ videoId: string }> };

export default async function StudioVideoAssetsPage({ params }: StudioVideoAssetsPageProps) {
  const { videoId } = await params;
  return (
    <div className="studioStack">
      <ThumbnailManager videoId={videoId} />
      <CaptionManager videoId={videoId} />
    </div>
  );
}
