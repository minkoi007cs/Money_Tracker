import { NextRequest, NextResponse } from "next/server";
import { cookieOptions, encodeFlow, hubConfig, HUB_MODE, newFlow, FLOW_COOKIE } from "@/lib/hub";

export async function GET(request: NextRequest) {
  if (!HUB_MODE) return NextResponse.redirect(new URL("/login", request.url));
  const c = hubConfig();
  const { flow, challenge } = newFlow(request.nextUrl.searchParams.get("next"));
  const url = new URL("/authorize", c.url);
  url.searchParams.set("client_id", c.publishableKey);
  url.searchParams.set("redirect_uri", c.callback);
  url.searchParams.set("state", flow.state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  const response = NextResponse.redirect(url, 303);
  response.cookies.set(FLOW_COOKIE, encodeFlow(flow), cookieOptions(600));
  response.headers.set("Cache-Control", "no-store");
  return response;
}
