export type Transaction = {
  id: string;
  date: string;
  merchant: string;
  description_raw: string;
  description_normalized: string;
  amount: string;
  currency: string;
  category: string;
  category_source: string;
  confidence: string;
  is_transfer: boolean;
  is_refund: boolean;
  is_subscription: boolean;
  notes: string;
  import_id: string;
  account_id: string | null;
};

export type BankAccount = {
  id: string;
  name: string;
  currency: string;
  opening_balance: string;
  balance: string;
};
export type Summary = {
  income: string;
  spending: string;
  refunds: string;
  net: string;
  count: number;
  categories: { name: string; amount: string }[];
  merchants: { name: string; amount: string }[];
  daily: { date: string; amount: string }[];
};
export type Recurring = {
  merchant_key: string;
  merchant: string;
  currency: string;
  average_amount: string;
  frequency: string;
  kind: string;
  last_charged: string;
  next_expected_date: string;
  confidence: string;
  occurrences: number;
};

let sessionCheck: Promise<void> | null = null;

export async function ensureHubSession(): Promise<void> {
  if (process.env.NEXT_PUBLIC_AUTH_MODE !== "hub") return;
  if (!sessionCheck) {
    const check = async () => {
      const response = await fetch("/auth/session", { method: "POST", cache: "no-store" });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body?.error?.message || "Please sign in again");
      }
    };
    const run = (async () => {
      if (typeof navigator !== "undefined" && navigator.locks) {
        await navigator.locks.request("money-hub-session-refresh", check);
      } else {
        await check();
      }
    })();
    sessionCheck = run.finally(() => { sessionCheck = null; });
  }
  return sessionCheck!;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  if (path !== "/auth/logout") await ensureHubSession();
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error?.error?.message || `Request failed (${response.status})`,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function money(value: string | number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    Number(value),
  );
}

export function shortDate(value: string) {
  return new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(
    "en-US",
    { month: "short", day: "numeric", year: "numeric" },
  );
}
