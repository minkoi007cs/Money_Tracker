import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

export const HUB_MODE = process.env.NEXT_PUBLIC_AUTH_MODE === "hub";
export const SESSION_COOKIE = "money_hub_session";
export const FLOW_COOKIE = "money_hub_flow";
const SESSION_AGE = 60 * 60 * 24 * 30;

export type HubSession = { accessToken: string; refreshToken: string; expiresAt: number };
type HubFlow = { state: string; verifier: string; next: string };

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required for App System authentication`);
  return value;
}

export function hubConfig() {
  const url = required("INFRA_URL").replace(/\/+$/, "");
  const secretKey = required("INFRA_SECRET_KEY");
  const publishableKey = required("INFRA_PUBLISHABLE_KEY");
  const appUrl = required("APP_URL").replace(/\/+$/, "");
  if (!secretKey.startsWith("sk_") || !publishableKey.startsWith("pk_")) throw new Error("Invalid App System key type");
  return { url, secretKey, publishableKey, appUrl, callback: `${appUrl}/auth/callback` };
}

export function cookieOptions(maxAge = SESSION_AGE) {
  return { httpOnly: true, secure: hubConfig().appUrl.startsWith("https://"), sameSite: "lax" as const, path: "/", maxAge };
}

export function safeNext(value: string | null): string {
  return value?.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\") ? value : "/dashboard";
}

export function newFlow(next: string | null) {
  const verifier = randomBytes(32).toString("base64url");
  const state = randomBytes(24).toString("base64url");
  const challenge = createHash("sha256").update(verifier).digest("base64url");
  return { flow: { state, verifier, next: safeNext(next) }, challenge };
}

export function sameState(a: string, b: string): boolean {
  const x = Buffer.from(a);
  const y = Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x, y);
}

function encode(value: object): string {
  return Buffer.from(JSON.stringify(value)).toString("base64url");
}

function decode(value: string | undefined): unknown {
  if (!value) return null;
  try { return JSON.parse(Buffer.from(value, "base64url").toString("utf8")); } catch { return null; }
}

export function encodeFlow(value: HubFlow): string { return encode(value); }
export function decodeFlow(value: string | undefined): HubFlow | null {
  const parsed = decode(value) as Partial<HubFlow> | null;
  return parsed && typeof parsed.state === "string" && typeof parsed.verifier === "string" && parsed.verifier.length >= 43
    ? { state: parsed.state, verifier: parsed.verifier, next: safeNext(parsed.next ?? null) } : null;
}
export function encodeSession(value: HubSession): string { return encode(value); }
export function decodeSession(value: string | undefined): HubSession | null {
  const parsed = decode(value) as Partial<HubSession> | null;
  return parsed && typeof parsed.accessToken === "string" && typeof parsed.refreshToken === "string" && typeof parsed.expiresAt === "number"
    ? { accessToken: parsed.accessToken, refreshToken: parsed.refreshToken, expiresAt: parsed.expiresAt } : null;
}

function pair(body: unknown): HubSession | null {
  if (!body || typeof body !== "object") return null;
  const wrapper = body as { data?: unknown };
  const data = (wrapper.data ?? body) as Record<string, unknown>;
  const accessToken = data.accessToken ?? data.access_token;
  const refreshToken = data.refreshToken ?? data.refresh_token;
  const expiresIn = data.expiresIn ?? data.expires_in ?? 600;
  return typeof accessToken === "string" && typeof refreshToken === "string" && typeof expiresIn === "number"
    ? { accessToken, refreshToken, expiresAt: Date.now() + expiresIn * 1000 } : null;
}

async function authPost(path: string, body: object): Promise<{ session: HubSession | null; status: number }> {
  const c = hubConfig();
  try {
    const response = await fetch(`${c.url}/api/v1/auth/${path}`, {
      method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${c.secretKey}` },
      body: JSON.stringify(body), cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    return { session: response.ok ? pair(await response.json()) : null, status: response.status };
  } catch { return { session: null, status: 503 }; }
}

export function exchangeCode(code: string, verifier: string) {
  return authPost("token", { grant_type: "authorization_code", code, code_verifier: verifier, redirect_uri: hubConfig().callback });
}

const pendingRefresh = new Map<string, Promise<{ session: HubSession | null; status: number }>>();
export function refreshSession(refreshToken: string) {
  const existing = pendingRefresh.get(refreshToken);
  if (existing) return existing;
  const request = authPost("refresh", { refresh_token: refreshToken }).finally(() => pendingRefresh.delete(refreshToken));
  pendingRefresh.set(refreshToken, request);
  return request;
}

export async function revokeSession(refreshToken: string): Promise<void> {
  const c = hubConfig();
  try {
    await fetch(`${c.url}/api/v1/auth/revoke`, {
      method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${c.secretKey}` },
      body: JSON.stringify({ refresh_token: refreshToken }), cache: "no-store", signal: AbortSignal.timeout(5000),
    });
  } catch { /* Local cookie is cleared even if App System is temporarily unavailable. */ }
}
