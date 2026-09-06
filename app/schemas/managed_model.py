"""
Schemas for Dynamic Model and Node Management.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateModelRequest(BaseModel):
    name: str = Field(..., description="Display name of the model")
    provider: str = Field(..., description="Provider: openai, anthropic, deepseek, gemini, openrouter, custom_vllm")
    model_id: Optional[str] = Field(None, description="Technical model name / identifier (e.g. gpt-4o)")
    modelId: Optional[str] = Field(None, description="CamelCase alias for model_id")
    assigned_role: Optional[str] = Field(None, description="System role: general-model, coding-model, reasoning-model, rag-model")
    assignedRole: Optional[str] = Field(None, description="CamelCase alias for assigned_role")
    api_key: Optional[str] = Field(None, description="Provider API Key")
    apiKey: Optional[str] = Field(None, description="CamelCase alias for api_key")
    api_base: Optional[str] = Field(None, description="Custom API Base URL")
    apiBase: Optional[str] = Field(None, description="CamelCase alias for api_base")
    context_window: Optional[int] = Field(32768, description="Context window tokens")
    contextWindow: Optional[int] = Field(None, description="CamelCase alias for context_window")
    is_enabled: Optional[bool] = Field(True, description="Whether the model is enabled")
    isEnabled: Optional[bool] = Field(None, description="CamelCase alias for is_enabled")


class ToggleModelRequest(BaseModel):
    is_enabled: Optional[bool] = None
    isEnabled: Optional[bool] = None


class ModelDetailResponse(BaseModel):
    id: str
    name: str
    provider: str
    modelId: str
    apiKey: Optional[str] = ""
    hasKey: bool = False
    apiBase: Optional[str] = ""
    assignedRole: str
    isEnabled: bool
    contextWindow: int
    createdAt: str
    updatedAt: str


class ManagedModelsListResponse(BaseModel):
    models: List[Dict[str, Any]]
    activeNodes: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}
