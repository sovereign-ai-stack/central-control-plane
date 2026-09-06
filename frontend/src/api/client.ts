/**
 * Standardized Frontend API Client
 * Wraps apiFetch with response parsing, headers handling, and error localization.
 */

import { apiFetch, apiPath } from "@/lib/api";

export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && "detail" in errData) {
        errorDetail = String(errData.detail);
      }
      throw new ApiError(errorDetail, res.status, errData);
    } catch (e) {
      if (e instanceof ApiError) throw e;
      throw new ApiError(errorDetail, res.status);
    }
  }
  return res.json() as Promise<T>;
}

export { apiFetch, apiPath };
