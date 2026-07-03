import { ChannelClient } from "./channel-client";

type ChannelPageProps = {
  params: Promise<{ handle: string }>;
};

export default async function ChannelPage({ params }: ChannelPageProps) {
  const { handle } = await params;
  return <ChannelClient handle={handle} />;
}
