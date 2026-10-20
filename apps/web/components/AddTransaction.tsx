"use client";

import { FormEvent, useEffect, useState } from "react";
import { X } from "lucide-react";
import { api, BankAccount } from "@/lib/api";
import { ErrorBox } from "@/components/UI";

const categories = ["Food & Dining", "Groceries", "Transportation", "Shopping", "Entertainment", "Housing", "Utilities", "Subscriptions", "Education", "Health", "Travel", "Personal Care", "Income", "Transfers", "Fees", "Cash", "Gifts & Donations", "Other"];
const localDate = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};

export default function AddTransaction({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [currency, setCurrency] = useState("USD");
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [accountId, setAccountId] = useState("");
  const [direction, setDirection] = useState("expense");
  const [date, setDate] = useState(localDate);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("Other");
  const [transfer, setTransfer] = useState(false);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<{ currency: string }>("/settings"), api<BankAccount[]>("/accounts")])
      .then(([settings, found]) => { setCurrency(settings.currency); setAccounts(found.filter(account => account.source !== "bank")); })
      .catch(() => {});
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!Number.isFinite(Number(amount)) || Number(amount) <= 0) {
      setError("Enter an amount greater than zero.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api("/transactions", {
        method: "POST",
        body: JSON.stringify({ date, description: description.trim(), amount: `${direction === "expense" ? "-" : ""}${amount}`, currency, account_id: accountId || null, category, is_transfer: transfer, notes }),
      });
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return <div className="drawer-backdrop" onClick={onClose}>
    <aside className="drawer" role="dialog" aria-modal="true" aria-label="Add transaction" onClick={event => event.stopPropagation()}>
      <div className="drawer-heading"><div><span className="section-kicker">MANUAL ENTRY</span><h2>Add transaction</h2></div><button className="icon-button" onClick={onClose} aria-label="Close"><X size={21} /></button></div>
      <p className="muted">Record money in or out when you do not have a CSV statement.</p>
      <ErrorBox message={error} />
      <form onSubmit={save}>
        <label>Money direction<select value={direction} onChange={event => { setDirection(event.target.value); setCategory(event.target.value === "income" ? "Income" : "Other"); }}><option value="expense">Money out</option><option value="income">Money in</option></select></label>
        <label>Amount<input type="number" inputMode="decimal" min="0.01" step="0.01" required value={amount} onChange={event => setAmount(event.target.value)} /></label>
        <label>Currency<select value={currency} onChange={event => setCurrency(event.target.value)}><option>USD</option><option>EUR</option><option>GBP</option><option>VND</option></select></label>
        <label>Bank account<select value={accountId} onChange={event => { const id = event.target.value; setAccountId(id); const account = accounts.find(item => item.id === id); if (account) setCurrency(account.currency); }}><option value="">Unassigned</option>{accounts.map(item => <option key={item.id} value={item.id}>{item.name} · {item.currency}</option>)}</select></label>
        <label>Date<input type="date" required value={date} onChange={event => setDate(event.target.value)} /></label>
        <label>Description<input required maxLength={500} value={description} onChange={event => setDescription(event.target.value)} placeholder="e.g. Groceries" /></label>
        <label>Category<select value={category} onChange={event => setCategory(event.target.value)}>{categories.map(item => <option key={item}>{item}</option>)}</select></label>
        <label>Notes<textarea rows={2} maxLength={2000} value={notes} onChange={event => setNotes(event.target.value)} /></label>
        <label className="manual-checkbox"><input type="checkbox" checked={transfer} onChange={event => setTransfer(event.target.checked)} /> Mark as transfer (excluded from income and spending)</label>
        <button className="button button-primary button-full" disabled={saving}>{saving ? "Saving…" : "Save transaction"}</button>
      </form>
    </aside>
  </div>;
}
