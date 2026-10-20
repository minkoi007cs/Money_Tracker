import { api } from "@/lib/api";

const FLOW_KEY = "money-bank-link";
type LinkFlow = { token: string; connectionId?: string; started: number };
type Handler = { open: () => void; destroy: () => void };
type PlaidError = { display_message?: string | null; error_code?: string } | null;

declare global {
  interface Window {
    Plaid?: { create: (config: {
      token: string;
      receivedRedirectUri?: string;
      onSuccess: (publicToken: string | null) => void;
      onExit: (error: PlaidError) => void;
    }) => Handler };
  }
}

export async function finishLink(flow: LinkFlow, publicToken: string | null) {
  if (flow.connectionId) {
    await api(`/banks/${flow.connectionId}/reconnected`, { method: "POST" });
  } else {
    if (!publicToken) throw new Error("Bank sign-in did not finish. Try connecting again.");
    await api("/banks/exchange", { method: "POST", body: JSON.stringify({ public_token: publicToken }) });
  }
  sessionStorage.removeItem(FLOW_KEY);
}

export function resumeFlow(): LinkFlow | null {
  try {
    const flow = JSON.parse(sessionStorage.getItem(FLOW_KEY) || "null");
    return flow && typeof flow.token === "string" && typeof flow.started === "number" && Date.now() - flow.started < 30 * 60 * 1000 ? flow : null;
  } catch { return null; }
}

export function openLink(flow: LinkFlow, onDone: () => void, onError: (message: string | null) => void, redirect?: string) {
  if (!window.Plaid) throw new Error("Bank sign-in is still loading. Try again shortly.");
  const handler = window.Plaid.create({
    token: flow.token,
    ...(redirect ? { receivedRedirectUri: redirect } : {}),
    onSuccess: (publicToken) => {
      finishLink(flow, publicToken).then(onDone).catch(error => onError(error.message)).finally(() => handler.destroy());
    },
    onExit: (error) => {
      sessionStorage.removeItem(FLOW_KEY);
      onError(error ? "Bank sign-in could not finish. Please try again." : null);
      handler.destroy();
    },
  });
  handler.open();
  return handler;
}

export async function startLink(connectionId?: string) {
  const result = await api<{ link_token: string }>("/banks/link-token", {
    method: "POST", body: JSON.stringify({ connection_id: connectionId || null }),
  });
  const flow = { token: result.link_token, connectionId, started: Date.now() };
  sessionStorage.setItem(FLOW_KEY, JSON.stringify(flow));
  return flow;
}
