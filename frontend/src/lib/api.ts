// Same-origin API URL helpers for the configured secret path.

const configuredPath = (process.env.NEXT_PUBLIC_APP_SECRET_PATH || "").trim();
const secretSegments = configuredPath.split("/").filter(Boolean);
const secretPath = secretSegments.length > 0 ? `/${secretSegments.join("/")}` : "";

export const appSecretPath = secretPath;

export function appPath(path = ""): string {
  const runtimePath = getRuntimeSecretPath();
  const cleanPath = path.replace(/^\/+/, "");
  if (!cleanPath) return runtimePath || "/";
  return runtimePath ? `${runtimePath}/${cleanPath}` : `/${cleanPath}`;
}

export function apiPath(path = ""): string {
  const base = getRuntimeSecretPath();
  const cleanPath = path.replace(/^\/+/, "");
  return base ? `${base}/api/${cleanPath}` : `/api/${cleanPath}`;
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return fetch(apiPath(path), {
    credentials: "include",
    ...init,
    headers,
  });
}

function getRuntimeSecretPath(): string {
  if (appSecretPath) return appSecretPath;
  return "";
}
