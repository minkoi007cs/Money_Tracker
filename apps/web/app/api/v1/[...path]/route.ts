import { NextRequest, NextResponse } from "next/server";
import { decodeSession, HUB_MODE, revokeSession, SESSION_COOKIE } from "@/lib/hub";

const COOKIE = "money_session";
const API_BASE = process.env.API_BASE_URL || (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000");
const MAX_BODY = 11 * 1024 * 1024;

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  const endpoint = path.join("/");
  const authenticating = !HUB_MODE && request.method === "POST" && (endpoint === "auth/login" || endpoint === "auth/register");

  if (request.method !== "GET" && request.method !== "HEAD") {
    const origin = request.headers.get("origin");
    const host = request.headers.get("host");
    const protocol = request.headers.get("x-forwarded-proto") || request.nextUrl.protocol.replace(":", "");
    if (origin && origin !== `${protocol}://${host}`) return NextResponse.json({ error: { code: "FORBIDDEN", message: "Invalid request origin" } }, { status: 403 });
  }

  const hubSession = HUB_MODE ? decodeSession(request.cookies.get(SESSION_COOKIE)?.value) : null;
  if (request.method === "POST" && endpoint === "auth/logout") {
    if (hubSession) await revokeSession(hubSession.refreshToken);
    const response = NextResponse.json({ signed_out: true });
    response.cookies.delete(HUB_MODE ? SESSION_COOKIE : COOKIE);
    return response;
  }
  if (HUB_MODE && (endpoint === "auth/login" || endpoint === "auth/register")) {
    return NextResponse.json({ error: { code: "HUB_AUTH", message: "Sign in through App System" } }, { status: 410 });
  }

  const session = hubSession;
  const token = HUB_MODE ? session?.accessToken : request.cookies.get(COOKIE)?.value;
  if (!authenticating && !token) return NextResponse.json({ error: { code: "UNAUTHORIZED", message: "Please sign in" } }, { status: 401 });
  if (!API_BASE) return NextResponse.json({ error: { code: "API_UNCONFIGURED", message: "The finance service is not configured" } }, { status: 503 });

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
  if (body && body.byteLength > MAX_BODY) return NextResponse.json({ error: { code: "TOO_LARGE", message: "Request is too large" } }, { status: 413 });

  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (token && !authenticating) headers.set("authorization", `Bearer ${token}`);

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}/api/v1/${endpoint}${request.nextUrl.search}`, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(30000),
    });
  } catch {
    return NextResponse.json({ error: { code: "API_UNAVAILABLE", message: "The finance service is temporarily unavailable" } }, { status: 503 });
  }

  if (authenticating && upstream.ok) {
    const result = await upstream.json();
    const response = NextResponse.json({ user: result.user }, { status: upstream.status });
    response.cookies.set(COOKIE, result.access_token, {
      httpOnly: true,
      secure: request.headers.get("x-forwarded-proto") === "https" || request.nextUrl.protocol === "https:",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 12,
    });
    response.headers.set("Cache-Control", "no-store");
    return response;
  }

  const response = new NextResponse(upstream.body, { status: upstream.status });
  for (const key of ["content-type", "content-disposition"]) {
    const value = upstream.headers.get(key);
    if (value) response.headers.set(key, value);
  }
  response.headers.set("Cache-Control", "no-store");
  if (upstream.status === 401) response.cookies.delete(HUB_MODE ? SESSION_COOKIE : COOKIE);
  if (request.method === "DELETE" && endpoint === "me" && upstream.ok) {
    if (session) await revokeSession(session.refreshToken);
    response.cookies.delete(HUB_MODE ? SESSION_COOKIE : COOKIE);
  }
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
