import { NextRequest, NextResponse } from "next/server";
import { cookieOptions, decodeFlow, encodeSession, exchangeCode, FLOW_COOKIE, hubConfig, HUB_MODE, sameState, SESSION_COOKIE } from "@/lib/hub";

function back(error: string) {
  const url = new URL("/login", hubConfig().appUrl);
  url.searchParams.set("error", error);
  const response = NextResponse.redirect(url, 303);
  response.cookies.delete(FLOW_COOKIE);
  return response;
}

export async function GET(request: NextRequest) {
  if (!HUB_MODE) return NextResponse.redirect(new URL("/login", request.url));
  if (request.nextUrl.searchParams.get("error")) return back("denied");
  const flow = decodeFlow(request.cookies.get(FLOW_COOKIE)?.value);
  const code = request.nextUrl.searchParams.get("code");
  const state = request.nextUrl.searchParams.get("state");
  if (!flow || !code || !state || !sameState(state, flow.state)) return back("state");
  const result = await exchangeCode(code, flow.verifier);
  if (!result.session) return back("exchange");
  const response = NextResponse.redirect(new URL(flow.next, hubConfig().appUrl), 303);
  response.cookies.set(SESSION_COOKIE, encodeSession(result.session), cookieOptions());
  response.cookies.delete(FLOW_COOKIE);
  response.headers.set("Cache-Control", "no-store");
  return response;
}
