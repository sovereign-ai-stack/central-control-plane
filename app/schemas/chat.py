"""
Chat message & SSE stream schemas.
"""

from typing import List, Optional
from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    conversationId: Optional[str] = None
    message: str
    language: Optional[str] = "fa"
    workflow_id: Optional[str] = None
    workflowId: Optional[str] = None
    file_ids: Optional[List[str]] = None
    fileIds: Optional[List[str]] = None
    use_rag: Optional[bool] = None
    useRag: Optional[bool] = None
    reply_to_message_id: Optional[str] = None
    replyToMessageId: Optional[str] = None
    reply_to_snippet: Optional[str] = None
    replyToSnippet: Optional[str] = None
