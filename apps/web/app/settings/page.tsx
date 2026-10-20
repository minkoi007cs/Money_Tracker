"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, ShieldCheck, Trash2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import InstallApp from "@/components/InstallApp";
import BankConnections from "@/components/BankConnections";
import BankAccounts from "@/components/BankAccounts";
import { ErrorBox, Loading } from "@/components/UI";
import { api, ensureHubSession } from "@/lib/api";

export default function Settings() {
  const router = useRouter();
  const [currency, setCurrency] = useState("USD");
  const [timezone, setTimezone] = useState("America/New_York");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    api<{ currency: string; timezone: string }>("/settings")
      .then((v) => {
        setCurrency(v.currency);
        setTimezone(v.timezone);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  async function save() {
    try {
      await api("/settings", {
        method: "PATCH",
        body: JSON.stringify({ currency, timezone }),
      });
      setNotice("Preferences saved.");
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function exportCsv(path = "/export/transactions", filename = "transactions.csv") {
    try {
      await ensureHubSession();
      const response = await fetch(`/api/v1${path}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Could not export transactions");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function erase(path: string, prompt: string) {
    if (!window.confirm(prompt)) return;
    try {
      await api(path, { method: "DELETE" });
      if (path === "/me") {
        router.push("/");
      } else setNotice("Bank connections and financial data have been deleted.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <AppShell title="Settings & privacy" eyebrow="YOUR SPACE, YOUR RULES">
      <div className="intro-row">
        <p>
          Choose how your workspace behaves, and stay in control of every
          transaction you upload.
        </p>
      </div>
      <ErrorBox message={error} />
      {notice && (
        <div className="success-box" role="status">
          {notice}
        </div>
      )}
      {loading ? (
        <Loading />
      ) : (
        <div className="settings-grid">
          <BankConnections />
          <BankAccounts />
          <InstallApp />
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">PREFERENCES</span>
                <h2>Your defaults</h2>
              </div>
            </div>
            <div className="settings-form">
              <label>
                Default currency
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                >
                  <option>USD</option>
                  <option>EUR</option>
                  <option>GBP</option>
                  <option>VND</option>
                </select>
              </label>
              <label>
                Timezone
                <input
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="America/New_York"
                />
              </label>
              <p className="hint">
                Currencies are kept separate. We never convert transaction
                amounts automatically.
              </p>
              <button className="button button-primary" onClick={save}>
                Save preferences
              </button>
            </div>
          </section>
          <section className="panel privacy-panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">YOUR DATA</span>
                <h2>Privacy controls</h2>
              </div>
              <ShieldCheck size={23} />
            </div>
            <p>
              Your original CSV is processed for import and not stored.
              Normalized transactions remain until you delete them.
            </p>
            <div className="privacy-action">
              <div>
                <strong>Export your transactions</strong>
                <span>Download a CSV with the data in your workspace.</span>
              </div>
              <button className="button button-outline" onClick={() => exportCsv()}>
                <Download size={16} /> Export CSV
              </button>
            </div>
            <div className="privacy-action">
              <div><strong>Export bank accounts</strong><span>Download names, currencies, and starting/current balances.</span></div>
              <button className="button button-outline" onClick={() => exportCsv("/export/accounts", "accounts.csv")}><Download size={16} /> Export accounts</button>
            </div>
            <div className="privacy-action">
              <div>
                <strong>Disconnect banks and delete data</strong>
                <span>
                  Disconnects banks and removes financial data. Your profile stays
                  active.
                </span>
              </div>
              <button
                className="button button-danger"
                onClick={() =>
                  erase(
                    "/data",
                    "Disconnect all banks and delete all financial data? This cannot be undone.",
                  )
                }
              >
                <Trash2 size={16} /> Delete data
              </button>
            </div>
            <div className="privacy-action">
              <div>
                <strong>Delete your account</strong>
                <span>{process.env.NEXT_PUBLIC_AUTH_MODE === "hub" ? "Removes your Money Tracker profile and financial data. Your App System sign-in remains active." : "Removes your account and all its financial data."}</span>
              </div>
              <button
                className="button button-danger"
                onClick={() =>
                  erase(
                    "/me",
                    process.env.NEXT_PUBLIC_AUTH_MODE === "hub" ? "Permanently delete your Money Tracker profile and every transaction? Your App System sign-in will remain. This cannot be undone." : "Permanently delete your account and every transaction? This cannot be undone.",
                  )
                }
              >
                <Trash2 size={16} /> Delete account
              </button>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
