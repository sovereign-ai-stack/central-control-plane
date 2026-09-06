import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const configuredBackendPath = (
  process.env.BACKEND_APP_SECRET_PATH ||
  process.env.APP_SECRET_PATH ||
  process.env.NEXT_PUBLIC_APP_SECRET_PATH ||
  ""
).trim();
const secretSegments = configuredBackendPath.split("/").filter(Boolean);
const BACKEND_APP_SECRET_PATH = secretSegments.length > 0 ? `/${secretSegments.join("/")}` : "";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

export const dynamic = "force-dynamic";
export const maxDuration = 300;

async function handleProxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const pathStr = path.join("/");
  const url = new URL(req.url);
  const targetUrl = `${BACKEND_URL}${BACKEND_APP_SECRET_PATH}/api/${pathStr}${url.search}`;

  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      forwardHeaders.set(key, value);
    }
  });

  const clientIp = req.headers.get("x-forwarded-for") || req.headers.get("x-real-ip");
  if (clientIp) {
    forwardHeaders.set("X-Forwarded-For", clientIp);
  }

  let body: BodyInit | undefined = undefined;
  if (["POST", "PUT", "PATCH"].includes(req.method)) {
    if (req.body) {
      body = req.body;
    } else {
      try {
        const buffer = await req.arrayBuffer();
        if (buffer.byteLength > 0) {
          body = buffer;
        }
      } catch {
        // Body may be empty
      }
    }
  }

  try {
    const fetchOptions: RequestInit & { duplex?: string } = {
      method: req.method,
      headers: forwardHeaders,
      body,
      signal: req.signal,
      cache: "no-store",
    };
    if (body) {
      fetchOptions.duplex = "half";
    }

    const upstreamRes = await fetch(targetUrl, fetchOptions);

    const contentType = upstreamRes.headers.get("content-type")?.toLowerCase() || "";
    const isStreamingResponse =
      contentType.includes("text/event-stream") ||
      contentType.includes("application/x-sovereign-voice-stream") ||
      contentType.includes("application/x-sovereign-voice-stream") ||
      contentType.startsWith("audio/");

    if (isStreamingResponse && upstreamRes.body) {
      const streamHeaders = new Headers();
      copyResponseHeaders(upstreamRes.headers, streamHeaders, "set");
      streamHeaders.set("Cache-Control", "no-cache, no-transform");
      if (contentType.includes("text/event-stream")) {
        streamHeaders.set("Content-Type", "text/event-stream");
      }

      return new Response(upstreamRes.body, {
        status: upstreamRes.status,
        statusText: upstreamRes.statusText,
        headers: streamHeaders,
      });
    }

    const responseHeaders = new Headers();
    copyResponseHeaders(upstreamRes.headers, responseHeaders, "append");

    const resBuffer = await upstreamRes.arrayBuffer();
    return new Response(resBuffer, {
      status: upstreamRes.status,
      statusText: upstreamRes.statusText,
      headers: responseHeaders,
    });
  } catch {
    if (req.signal.aborted) {
      return new Response(null, { status: 499 });
    }

    const errorDetails = {
      type: "urn:sovereign:service-unavailable",
      title: "Service Unavailable",
      status: 503,
      detail: "Backend service is currently unreachable. Please try again in a few moments.",
      requestId: crypto.randomUUID(),
    };

    return NextResponse.json(errorDetails, {
      status: 503,
      headers: {
        "Content-Type": "application/problem+json",
      },
    });
  }
}

function copyResponseHeaders(source: Headers, target: Headers, mode: "append" | "set") {
  const headersWithCookies = source as Headers & { getSetCookie?: () => string[] };
  const setCookies = headersWithCookies.getSetCookie?.() ?? [];

  source.forEach((value, key) => {
    if (key === "set-cookie" && setCookies.length > 0) return;
    if (HOP_BY_HOP_HEADERS.has(key.toLowerCase())) return;
    if (mode === "set") target.set(key, value);
    else target.append(key, value);
  });

  for (const cookie of setCookies) target.append("set-cookie", cookie);
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function PUT(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function HEAD(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}

export async function OPTIONS(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return handleProxy(req, ctx);
}
