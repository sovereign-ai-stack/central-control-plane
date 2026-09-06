/**
 * Authentication API Client
 */

import { apiFetch, requestJson } from "@/api/client";
import type { AuthResponse, AuthUser } from "@/lib/types";

export interface LoginParams {
  email: string;
  password: string;
}

export interface LoginResult {
  token: string;
  user: AuthUser;
}

export async function loginApi(params: LoginParams): Promise<LoginResult> {
  return requestJson<LoginResult>("auth/login", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export async function getMeApi(): Promise<AuthResponse> {
  return requestJson<AuthResponse>("auth/me");
}

export async function logoutApi(): Promise<{ status: string }> {
  return requestJson<{ status: string }>("auth/logout", {
    method: "POST",
  });
}
