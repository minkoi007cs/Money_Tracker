"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarClock, Plus, Repeat2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, money, Recurring, shortDate } from "@/lib/api";

const labels: Record<string, string> = {
  subscription: "Subscription",
  recurring_bill: "Recurring bill",
  recurring_income: "Recurring income",
  ignored: "Ignored",
};
export default function Subscriptions() {
  const [items, setItems] = useState<Recurring[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  function refresh() {
    api<Recurring[]>("/recurring")
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, []);
  async function change(key: string, kind: string) {
    try {
      await api(`/recurring/${encodeURIComponent(key)}`, {
        method: "PATCH",
        body: JSON.stringify({ kind }),
      });
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <AppShell
      title="Recurring payments"
      eyebrow="WHAT KEEPS COMING BACK"
      action={
        <Link href="/import" className="button button-primary">
          <Plus size={17} /> Add a statement
        </Link>
      }
    >
      <div className="intro-row">
        <p>
          Patterns found in your transactions. Future charge dates are
          estimates, and you can correct any label.
        </p>
      </div>
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState
          title="No recurring patterns yet"
          text="Recurring payments appear after at least three similar charges. Import more history to help spot them."
          href="/import"
          action="Import another CSV"
        />
      ) : (
        <div className="recurring-grid">
          {items.map((item) => (
            <section
              className="panel recurring-card"
              key={`${item.merchant_key}-${item.currency}`}
            >
              <div className="recurring-top">
                <span className="recurring-icon">
                  <Repeat2 size={21} />
                </span>
                <span className="chip">
                  {Math.round(Number(item.confidence) * 100)}% confidence
                </span>
              </div>
              <h2>{item.merchant}</h2>
              <p>
                {labels[item.kind] || item.kind} · {item.frequency}
              </p>
              <strong>
                {money(item.average_amount, item.currency)}{" "}
                <small>/ {item.frequency.toLowerCase()}</small>
              </strong>
              <div className="recurring-dates">
                <div>
                  <span>Last charged</span>
                  <b>{shortDate(item.last_charged)}</b>
                </div>
                <div>
                  <span>
                    <CalendarClock size={14} /> Next expected (estimate)
                  </span>
                  <b>{shortDate(item.next_expected_date)}</b>
                </div>
              </div>
              <label>
                How should this be labeled?
                <select
                  value={item.kind}
                  onChange={(e) => change(item.merchant_key, e.target.value)}
                >
                  <option value="subscription">Subscription</option>
                  <option value="recurring_bill">Recurring bill</option>
                  <option value="recurring_income">Recurring income</option>
                  <option value="ignored">Ignore this pattern</option>
                </select>
              </label>
            </section>
          ))}
        </div>
      )}
    </AppShell>
  );
}
