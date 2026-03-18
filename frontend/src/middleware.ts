import { NextRequest, NextResponse } from "next/server";

const PYTHON_API = process.env.PYTHON_API_URL || "http://python-api:8088";

// Paths that should be proxied to the Python API
const PROXY_PREFIXES = ["/api/projects", "/api/chat", "/api/ws-token"];

// Paths handled by Next.js API routes (not proxied)
const NEXTJS_PREFIXES = ["/api/auth", "/api/orgs"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip Next.js API routes
  if (NEXTJS_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Proxy matching paths to Python API
  if (PROXY_PREFIXES.some((p) => pathname.startsWith(p))) {
    const url = new URL(pathname + request.nextUrl.search, PYTHON_API);
    return NextResponse.rewrite(url);
  }

  if (pathname === "/health") {
    return NextResponse.rewrite(new URL("/health", PYTHON_API));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*", "/health"],
};
