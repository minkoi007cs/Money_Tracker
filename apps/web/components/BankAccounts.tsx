"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, BankAccount, money } from "@/lib/api";
import { ErrorBox } from "@/components/UI";

export default function BankAccounts() {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [opening, setOpening] = useState("0");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);

  useEffect(() => { api<BankAccount[]>("/accounts").then(found => setAccounts(found.filter(account => account.source !== "bank"))).catch(err => setError(err.message)); }, []);

  async function add(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(editing ? `/accounts/${editing}` : "/accounts", { method: editing ? "PATCH" : "POST", body: JSON.stringify({ name: name.trim(), currency, opening_balance: opening }) });
      setAccounts((await api<BankAccount[]>("/accounts")).filter(account => account.source !== "bank"));
      setName(""); setOpening("0"); setEditing(null);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  function edit(account: BankAccount) {
    setEditing(account.id); setName(account.name); setCurrency(account.currency); setOpening(account.opening_balance);
  }

  async function remove(account: BankAccount) {
    if (!window.confirm(`Delete ${account.name}? Its transactions will remain in your history without a bank account.`)) return;
    try {
      await api(`/accounts/${account.id}`, { method: "DELETE" });
      setAccounts((await api<BankAccount[]>("/accounts")).filter(account => account.source !== "bank"));
      if (editing === account.id) { setEditing(null); setName(""); setOpening("0"); }
    } catch (err) { setError((err as Error).message); }
  }

  return <section className="panel install-panel">
    <div className="panel-heading"><div><span className="section-kicker">YOUR BANKS</span><h2>Manual accounts</h2></div></div>
    <p className="muted">Set the balance before your first tracked transaction. Each assigned transaction updates that account balance.</p>
    <ErrorBox message={error} />
    <div className="bank-account-list">{accounts.map(account => <div className="bank-account-row" key={account.id}>
      <span><strong>{account.name}</strong><small>Starting balance: {money(account.opening_balance, account.currency)}</small></span>
      <span className="bank-account-controls"><strong>{money(account.balance ?? "0", account.currency)}</strong><span><button type="button" onClick={() => edit(account)}>Edit</button><button type="button" onClick={() => remove(account)}>Delete</button></span></span>
    </div>)}</div>
    <form className="bank-account-form" onSubmit={add}>
      <label>Account name<input required maxLength={100} value={name} onChange={event => setName(event.target.value)} placeholder="e.g. Main checking" /></label>
      <label>Currency<select value={currency} onChange={event => setCurrency(event.target.value)}><option>USD</option><option>EUR</option><option>GBP</option><option>VND</option></select></label>
      <label>Starting balance<input required type="number" inputMode="decimal" step="0.01" value={opening} onChange={event => setOpening(event.target.value)} /></label>
      <button className="button button-primary" disabled={busy}>{busy ? "Saving…" : editing ? "Save account" : "Add account"}</button>
      {editing && <button type="button" className="button button-outline" onClick={() => { setEditing(null); setName(""); setOpening("0"); }}>Cancel</button>}
    </form>
  </section>;
}
