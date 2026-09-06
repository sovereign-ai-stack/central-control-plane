import { NextRequest, NextResponse } from "next/server";

const configuredPath = (process.env.APP_SECRET_PATH || process.env.NEXT_PUBLIC_APP_SECRET_PATH || "").trim();
const secretSegments = configuredPath.split("/").filter(Boolean);
const hasSecretPath = secretSegments.length > 0;
const secretPrefix = hasSecretPath ? `/${secretSegments.join("/")}` : "";

const assetPattern = /\.(?:css|js|map|ico|png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf)$/i;

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  if (hasSecretPath && (pathname === secretPrefix || pathname.startsWith(`${secretPrefix}/`))) {
    const rewrittenUrl = request.nextUrl.clone();
    rewrittenUrl.pathname = pathname.slice(secretPrefix.length) || "/";
    return NextResponse.rewrite(rewrittenUrl);
  }

  if (!hasSecretPath || pathname.startsWith("/_next/") || assetPattern.test(pathname) || pathname === "/api" || pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  return new NextResponse(null, { status: 404 });
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
