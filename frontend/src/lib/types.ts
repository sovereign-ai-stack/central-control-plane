export type Language = "fa" | "en";
export type Direction = "rtl" | "ltr";

export type CitationSupportStatus = "supported" | "conflict" | "insufficient";

export interface Citation {
  claimIndex?: number;
  title: string;
  section?: string;
  url: string;
  supportStatus: CitationSupportStatus;
  snippet?: string;
  excerpt?: string;
  messageId?: string;
  promptSnippet?: string;
}

export interface ContextFact {
  key: string;
  value: string;
  confidence?: number;
  status?: "confirmed" | "inferred";
  sourceClaimIndex?: number;
}

export interface FileAttachment {
  id: string;
  name: string;
  size: number;
  contentType: "application/pdf";
  pageCount?: number;
}

export type WorkflowState =
  | "detecting"
  | "clarifying"
  | "checking"
  | "fixing"
  | "verifying"
  | "resolved"
  | "blocked";

export interface Workflow {
  id: string;
  type: string;
  goal: string;
  state: WorkflowState;
  stepCount: number;
  nextAction?: string;
}

export type MessageStatus = "pending" | "streaming" | "complete" | "failed" | "interrupted";

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  reasoningContent?: string;
  direction?: Direction;
  status?: MessageStatus;
  citations?: Citation[];
  attachments?: FileAttachment[];
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  titleSource: "model" | "user" | "placeholder" | "fallback";
  language: Language;
  status: "active" | "resolved" | "blocked" | "archived" | "deleted" | "expired";
  createdAt: string;
  updatedAt: string;
  expiresAt: string;
  activeWorkflowId?: string;
  parentConversationId?: string | null;
  parentMessageId?: string | null;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
  context: ContextFact[];
  workflow?: Workflow | null;
}

export type UserRole = "super_admin" | "org_admin" | "team_admin" | "user";

export interface Organization {
  id: string;
  name: string;
  code?: string;
  tokenLimit: number;
  usedTokens: number;
  teamCount: number;
  userCount?: number;
  createdAt: string;
}

export interface Team {
  id: string;
  organizationId: string;
  organizationName?: string;
  litellmTeamId?: string;
  name: string;
  tokenLimit: number;
  usedTokens: number;
  memberCount: number;
  rpmLimit?: number;
  tpmLimit?: number;
  createdAt: string;
}

export interface RagDocument {
  id: string;
  name: string;
  size: number;
  pageCount: number;
  contentType: string;
  organizationId: string;
  organizationName?: string;
  teamId: string;
  teamName?: string;
  chunkCount: number;
  status: "indexed" | "processing" | "failed";
  uploadedBy: string;
  createdAt: string;
}

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role?: UserRole;
  organizationId?: string | null;
  organizationName?: string;
  teamId?: string | null;
  teamName?: string;
  tokenLimit?: number;
  usedTokens?: number;
  isActive?: boolean;
  createdAt: string;
}

export interface AuthResponse {
  user: AuthUser;
}

export interface AdminModelAccess {
  id: string;
  name: string;
  detail: string;
  enabled: boolean;
  isDefault: boolean;
  latencyMs?: number;
  contextWindow?: number;
}

export interface ManagedModel {
  id: string;
  name: string;
  provider: "openai" | "anthropic" | "deepseek" | "gemini" | "openrouter" | "custom_vllm" | "local_node" | string;
  modelId: string;
  apiKey?: string;
  hasKey: boolean;
  apiBase?: string;
  assignedRole: "general-model" | "coding-model" | "reasoning-model" | "rag-model" | string;
  isEnabled: boolean;
  contextWindow: number;
  createdAt: string;
  updatedAt: string;
}

export interface GpuNode {
  node_id: string;
  api_base: string;
  model_name: string;
  served_model_name: string;
  supported_roles: string[];
  hardware?: {
    gpus?: Array<{ name: string; memory_total?: number; memory_free?: number }>;
    total_vram_gb?: number;
    tier_id?: string;
  };
  status: "healthy" | "offline" | "disabled" | string;
  registered_at?: number;
  last_heartbeat?: number;
  seconds_since_last_heartbeat?: number;
}

export interface AdminUserQuota {
  id: string;
  initials: string;
  name: string;
  email: string;
  role?: UserRole;
  organizationId?: string | null;
  organizationName?: string;
  teamId?: string | null;
  teamName?: string;
  isActive?: boolean;
  usedTokens: number;
  tokenLimit: number;
  usedPercent: number;
  conversationCount: number;
  status: "healthy" | "near-limit" | "suspended";
}

export interface AdminDashboard {
  requestsToday: number;
  tokensThisMonth: number;
  activeUsers: number;
  totalUsers: number;
  totalOrganizations?: number;
  totalTeams?: number;
  averageResponseMs: number | null;
  requestsLastHour: number[];
  maxRps: number;
  defaultRps: number;
  inferenceConcurrency: number;
  maxInputChars: number;
  maxOutputTokens: number;
  maxPdfPages: number;
  perAccountTokenLimit: number;
  workspaceTokenLimit: number;
  tokenUsagePercent: number;
  messagesPerHour: number;
  messagesUsedLastHour: number;
  litellm?: {
    status: string;
    url: string;
    masterKeyPrefix?: string;
    activeVirtualTeams?: number;
  };
  models: AdminModelAccess[];
  users: AdminUserQuota[];
  activeNodes?: Array<Record<string, any>>;
}

export interface McpApiKey {
  id: string;
  name: string;
  prefix: string;
  rpm: number;
  rps: number;
  createdAt: string;
  lastUsedAt?: string | null;
  revokedAt?: string | null;
}

export interface McpApiKeyCreated extends McpApiKey {
  token: string;
}

export interface UsageLimits {
  maxConversations: number;
  requestsPerWindow: number;
  requestWindowMinutes: number;
  maxInputChars: number;
  maxOutputTokens: number;
  maxHistoryMessages: number;
  maxConcurrentStreams: number;
  conversationRetentionDays: number;
  maxPdfAttachments: number;
  maxPdfSizeBytes: number;
  maxPdfPages: number;
  mcpDefaultRpm: number;
  mcpDefaultRps: number;
  mcpMaxRpm: number;
  mcpMaxRps: number;
  maxRps?: number;
  defaultRps?: number;
  inferenceConcurrency?: number;
  totalTokensUsed: number;
  totalTokenLimit: number;
  userTokensUsed?: number;
  userTokenLimit?: number;
  teamTokensUsed?: number;
  teamTokenLimit?: number;
  teamName?: string;
  orgTokensUsed?: number;
  orgTokenLimit?: number;
  orgName?: string;
  clusterTokensUsed?: number;
  clusterTokenLimit?: number;
  messagesUsedThisHour: number;
  messagesPerHour: number;
}

export type ProgressStage =
  | "understanding"
  | "searching"
  | "verifying"
  | "reasoning"
  | "answering";

export interface StreamProgressEvent {
  type: "progress";
  requestId: string;
  stage: ProgressStage;
  label: string;
}

export interface StreamDeltaEvent {
  type: "delta";
  requestId: string;
  text: string;
}

export interface StreamThinkingEvent {
  type: "thinking";
  requestId: string;
  text: string;
}

export interface ToolCall {
  requestId: string;
  name: string;
  status: "started" | "completed" | "failed";
  label: string;
  summary?: string;
}

export interface StreamToolCallEvent extends ToolCall {
  type: "tool";
}

export interface StreamCompleteEvent {
  type: "complete";
  userMessageId?: string;
  message: Message;
  workflow?: Workflow;
}

export interface StreamErrorEvent {
  type: "error";
  code: string;
  message: string;
  retryable?: boolean;
}

export type StreamEvent =
  | StreamProgressEvent
  | StreamDeltaEvent
  | StreamThinkingEvent
  | StreamToolCallEvent
  | StreamCompleteEvent
  | StreamErrorEvent;

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  requestId: string;
}
