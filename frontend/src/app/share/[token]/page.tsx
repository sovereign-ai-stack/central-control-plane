import { SharedConversation } from "@/components/chat/shared-conversation";

export default async function SharedConversationPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <SharedConversation token={token} />;
}
