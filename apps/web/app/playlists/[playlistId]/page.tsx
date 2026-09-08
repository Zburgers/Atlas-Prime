import { PlaylistClient } from "./playlist-client";
export default async function PlaylistPage({ params }: { params: Promise<{ playlistId: string }> }) { const { playlistId } = await params; return <PlaylistClient playlistId={playlistId} />; }
