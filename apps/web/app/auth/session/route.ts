import { NextRequest, NextResponse } from "next/server";
import { cookieOptions, decodeSession, encodeSession, hubConfig, HUB_MODE, refreshSession, SESSION_COOKIE } from "@/lib/hub";

export async function POST(request: NextRequest) {
  if (!HUB_MODE) return NextResponse.json({ active: true });
  const origin = request.headers.get("origin");
  if (origin !== hubConfig().appUrl) return NextResponse.json({ error: { message: "Invalid request origin" } }, { status: 403 });
  const session = decodeSession(request.cookies.get(SESSION_COOKIE)?.value);
  if (!session) return NextResponse.json({ error: { message: "Please sign in" } }, { status: 401 });
  if (session.expiresAt - Date.now() >= 60_000) return NextResponse.json({ active: true }, { headers: { "Cache-Control": "no-store" } });
  const result = await refreshSession(session.refreshToken);
  if (!result.session) {
    const status = result.status === 503 ? 503 : 401;
    const response = NextResponse.json({ error: { message: status === 503 ? "Authentication service unavailable" : "Please sign in again" } }, { status });
    if (status === 401) response.cookies.delete(SESSION_COOKIE);
    return response;
  }
  const response = NextResponse.json({ active: true }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set(SESSION_COOKIE, encodeSession(result.session), cookieOptions());
  return response;
}
