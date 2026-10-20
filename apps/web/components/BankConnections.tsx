"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Script from "next/script";
import { Landmark, RefreshCw } from "lucide-react";
import { api, BankStatus, fetchedAt } from "@/lib/api";
import { openLink, startLink } from "@/lib/plaid";
import { ErrorBox } from "@/components/UI";

export default function BankConnections({ onUpdated, autoSync = false, compact = false }: { onUpdated?: () => void; autoSync?: boolean; compact?: boolean }) {
  const [data, setData] = useState<BankStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const updating = useRef(false);
  const linking = useRef(false);
  const updated = useRef(onUpdated);
  useEffect(() => { updated.current = onUpdated; }, [onUpdated]);

  const refresh = useCallback(async (sync: boolean) => {
    if (updating.current || linking.current) return;
    updating.current = true;
    setBusy(true);
    try {
      let status = await api<BankStatus>("/banks");
      let changed = false;
      let syncError: string | null = null;
      if (sync && status.configured) {
        const results = await Promise.allSettled(status.connections.filter(c => c.status === "connected").map(c =>
          api<{ skipped?: boolean; error?: string }>(`/banks/${c.id}/sync`, { method: "POST" }),
        ));
        for (const result of results) {
          if (result.status === "rejected") { syncError = result.reason.message; continue; }
          if (result.value.error) syncError = result.value.error;
          if (!result.value.skipped) changed = true;
        }
        status = await api<BankStatus>("/banks");
      }
      setData(status);
      setError(syncError);
      if (changed) updated.current?.();
    } catch (error) { setError((error as Error).message); }
    finally { updating.current = false; setBusy(false); }
  }, []);

  useEffect(() => {
    void refresh(autoSync);
    if (!autoSync) return;
    const update = () => { if (document.visibilityState === "visible") void refresh(true); };
    const timer = window.setInterval(update, 60000);
    window.addEventListener("focus", update);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", update); };
  }, [autoSync, refresh]);

  async function connect(connectionId?: string) {
    if (linking.current) return;
    linking.current = true;
    setBusy(true); setError(null); setNotice("");
    try {
      openLink(await startLink(connectionId), () => {
        linking.current = false;
        setNotice("Bank connected. Your transaction history may take a few minutes to arrive.");
        updated.current?.();
        void refresh(true);
      }, message => { linking.current = false; setError(message); setBusy(false); });
    } catch (error) { linking.current = false; setError((error as Error).message); setBusy(false); }
  }

  async function disconnect(id: string, name: string) {
    if (!window.confirm(`Disconnect ${name} and delete its synced accounts and transactions? Your bank accounts themselves will stay open.`)) return;
    setBusy(true); setError(null);
    try {
      await api(`/banks/${id}`, { method: "DELETE" });
      updated.current?.();
      await refresh(false);
    } catch (error) { setError((error as Error).message); }
    finally { setBusy(false); }
  }

  return <section className="panel bank-connections">
    {data?.configured && <Script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js" onReady={() => setReady(true)} onError={() => setError("Bank sign-in could not load. Check your connection and reload.")} />}
    <div className="panel-heading">
      <div><span className="section-kicker">CHASE · PNC</span><h2>Connected banks</h2></div>
      <Landmark size={23} />
    </div>
    {!compact && <p className="muted">Connect your banks to see balances and transactions together. Updates are checked when you open Overview; your bank may provide data with a delay.</p>}
    {data?.environment === "sandbox" && <div className="info-banner">Sandbox · Test accounts and balances only. This does not connect to your real Chase or PNC account.</div>}
    {data && !data.configured && <div className="info-banner">Bank connections are awaiting setup. Your saved transactions are still available.</div>}
    <ErrorBox message={error} />
    {notice && <p role="status">{notice}</p>}
    <div className="bank-account-list">{data?.connections.map(c => <div className="bank-account-row" key={c.id}>
      <span><strong>{c.institution_name}</strong><small>{c.status === "needs_login" ? "Sign in again to resume updates" : c.error_code ? "Update failed · showing saved data" : !c.history_ready ? "Fetching transaction history…" : "Connected"}</small><small>Last successful fetch: {fetchedAt(c.last_synced_at)}</small></span>
      <div className="button-row">
        {c.status === "needs_login" && <button disabled={!ready || busy} className="button button-outline" onClick={() => connect(c.id)}>Reconnect</button>}
        {!compact && <button disabled={busy} className="button button-outline" onClick={() => disconnect(c.id, c.institution_name)}>Disconnect</button>}
      </div>
    </div>)}</div>
    <div className="button-row bank-actions">
      <button className="button button-primary" disabled={!data?.configured || !ready || busy} onClick={() => connect()}><Landmark size={17} /> Connect bank</button>
      {!!data?.connections.length && <button disabled={busy || !data?.configured} className="button button-outline" onClick={() => { setError(null); void refresh(true); }}><RefreshCw size={16} /> {busy ? "Updating…" : "Check for updates"}</button>}
    </div>
    {!!data?.connections.length && !compact && <p className="hint">Current and available balances are bank-reported snapshots, which may be cached. Posted transactions count toward statistics; pending transactions stay separate.</p>}
  </section>;
}
