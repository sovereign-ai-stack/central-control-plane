/**
 * Admin Panel API Client
 * Provides typed methods for all administrative operations.
 */

import { apiFetch, requestJson } from "@/api/client";
import type {
  AdminDashboard,
  AdminModelAccess,
  AdminUserQuota,
  Organization,
  RagDocument,
  Team,
  UsageLimits,
  UserRole,
} from "@/lib/types";

// ================= Dashboard, Models & Limits =================
export async function fetchAdminDashboard(): Promise<AdminDashboard> {
  return requestJson<AdminDashboard>("admin/dashboard");
}

export async function fetchAdminModels(): Promise<{ models: AdminModelAccess[] }> {
  return requestJson<{ models: AdminModelAccess[] }>("admin/models");
}

export async function fetchUsageLimits(): Promise<UsageLimits> {
  return requestJson<UsageLimits>("usage-limits");
}

// ================= Organizations =================
export async function fetchOrganizations(): Promise<{ organizations: Organization[] }> {
  return requestJson<{ organizations: Organization[] }>("admin/organizations");
}

export async function fetchOrganizationDetail(
  orgId: string
): Promise<{ organization: Organization; teams: Team[]; users: AdminUserQuota[] }> {
  return requestJson<{ organization: Organization; teams: Team[]; users: AdminUserQuota[] }>(
    `admin/organizations/${orgId}`
  );
}

export async function createOrganization(params: {
  name: string;
  code?: string;
  tokenLimit?: number;
}): Promise<Organization> {
  return requestJson<Organization>("admin/organizations", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function updateOrganization(
  orgId: string,
  params: { name?: string; code?: string; tokenLimit?: number }
): Promise<Organization> {
  return requestJson<Organization>(`admin/organizations/${orgId}`, {
    method: "PUT",
    body: JSON.stringify(params),
  });
}

export async function deleteOrganization(orgId: string): Promise<{ deleted: boolean; id: string }> {
  return requestJson<{ deleted: boolean; id: string }>(`admin/organizations/${orgId}`, {
    method: "DELETE",
  });
}

// ================= Teams =================
export async function fetchTeams(organizationId?: string): Promise<{ teams: Team[] }> {
  const query = organizationId ? `?organizationId=${encodeURIComponent(organizationId)}` : "";
  return requestJson<{ teams: Team[] }>(`admin/teams${query}`);
}

export async function fetchTeamDetail(
  teamId: string
): Promise<{ team: Team; members: AdminUserQuota[]; documents: RagDocument[] }> {
  return requestJson<{ team: Team; members: AdminUserQuota[]; documents: RagDocument[] }>(
    `admin/teams/${teamId}`
  );
}

export async function createTeam(params: {
  name: string;
  organizationId: string;
  tokenLimit?: number;
  rpmLimit?: number;
  tpmLimit?: number;
}): Promise<Team> {
  return requestJson<Team>("admin/teams", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function updateTeam(
  teamId: string,
  params: { name?: string; tokenLimit?: number; rpmLimit?: number; tpmLimit?: number }
): Promise<Team> {
  return requestJson<Team>(`admin/teams/${teamId}`, {
    method: "PUT",
    body: JSON.stringify(params),
  });
}

export async function deleteTeam(teamId: string): Promise<{ deleted: boolean; id: string }> {
  return requestJson<{ deleted: boolean; id: string }>(`admin/teams/${teamId}`, {
    method: "DELETE",
  });
}

// ================= Users =================
export async function fetchUsers(params?: {
  organizationId?: string;
  teamId?: string;
  roleFilter?: string;
}): Promise<{ users: AdminUserQuota[] }> {
  const queryParams = new URLSearchParams();
  if (params?.organizationId && params.organizationId !== "all") queryParams.set("organizationId", params.organizationId);
  if (params?.teamId && params.teamId !== "all") queryParams.set("teamId", params.teamId);
  if (params?.roleFilter && params.roleFilter !== "all") queryParams.set("roleFilter", params.roleFilter);
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestJson<{ users: AdminUserQuota[] }>(`admin/users${query}`);
}

export async function createUser(params: {
  email: string;
  name: string;
  password: string;
  role: UserRole;
  organizationId?: string;
  teamId?: string;
  tokenLimit?: number;
}): Promise<AdminUserQuota> {
  return requestJson<AdminUserQuota>("admin/users", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function updateUser(
  userId: string,
  params: {
    name?: string;
    password?: string;
    role?: UserRole;
    organizationId?: string;
    teamId?: string;
    tokenLimit?: number;
    isActive?: boolean;
  }
): Promise<AdminUserQuota> {
  return requestJson<AdminUserQuota>(`admin/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(params),
  });
}

export async function deleteUser(userId: string): Promise<{ deleted: boolean; id: string }> {
  return requestJson<{ deleted: boolean; id: string }>(`admin/users/${userId}`, {
    method: "DELETE",
  });
}

// ================= Documents (RAG) =================
export async function fetchDocuments(params?: {
  organizationId?: string;
  teamId?: string;
}): Promise<{ documents: RagDocument[] }> {
  const queryParams = new URLSearchParams();
  if (params?.organizationId) queryParams.set("organizationId", params.organizationId);
  if (params?.teamId) queryParams.set("teamId", params.teamId);
  const query = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return requestJson<{ documents: RagDocument[] }>(`admin/documents${query}`);
}

export async function uploadDocumentApi(
  formData: FormData
): Promise<RagDocument> {
  const res = await apiFetch("admin/documents/upload", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    throw new Error(`Upload failed with status ${res.status}`);
  }
  return res.json() as Promise<RagDocument>;
}

export async function createTextDocumentApi(params: {
  title: string;
  content: string;
  organizationId?: string;
  teamId?: string;
}): Promise<RagDocument> {
  return requestJson<RagDocument>("admin/documents/text", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function deleteDocumentApi(docId: string): Promise<{ deleted: boolean; id: string }> {
  return requestJson<{ deleted: boolean; id: string }>(`admin/documents/${docId}`, {
    method: "DELETE",
  });
}
