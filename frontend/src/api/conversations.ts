/**
 * Conversations API Client
 */

import { requestJson } from "@/api/client";
import type { Conversation, ConversationDetail } from "@/lib/types";

export async function fetchConversationsApi(): Promise<{ conversations: Conversation[] }> {
  return requestJson<{ conversations: Conversation[] }>("conversations");
}

export async function fetchConversationDetailApi(convId: string): Promise<ConversationDetail> {
  return requestJson<ConversationDetail>(`conversations/${convId}`);
}

export async function createConversationApi(params?: {
  title?: string;
  language?: string;
}): Promise<Conversation> {
  return requestJson<Conversation>("conversations", {
    method: "POST",
    body: JSON.stringify(params || {}),
  });
}

export async function updateConversationApi(
  convId: string,
  params: { title?: string; language?: string }
): Promise<Conversation> {
  return requestJson<Conversation>(`conversations/${convId}`, {
    method: "PATCH",
    body: JSON.stringify(params),
  });
}

export async function deleteConversationApi(convId: string): Promise<{ deleted: boolean; id: string }> {
  return requestJson<{ deleted: boolean; id: string }>(`conversations/${convId}`, {
    method: "DELETE",
  });
}

export async function shareConversationApi(
  convId: string
): Promise<{ token: string; conversationId: string }> {
  return requestJson<{ token: string; conversationId: string }>(`conversations/${convId}/share`, {
    method: "POST",
  });
}
