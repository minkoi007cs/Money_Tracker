"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Plus,
  Search,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, money, shortDate, Transaction } from "@/lib/api";

const categories = [
  "Food & Dining",
  "Groceries",
  "Transportation",
  "Shopping",
  "Entertainment",
  "Housing",
  "Utilities",
  "Subscriptions",
  "Education",
  "Health",
  "Travel",
  "Personal Care",
  "Income",
  "Transfers",
  "Fees",
  "Cash",
  "Gifts & Donations",
  "Other",
];
export default function TransactionsPage() {
  const [items, setItems] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [direction, setDirection] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [minAmount, setMinAmount] = useState("");
  const [maxAmount, setMaxAmount] = useState("");
  const [subscriptionOnly, setSubscriptionOnly] = useState(false);
  const [reviewOnly, setReviewOnly] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [draft, setDraft] = useState<Partial<Transaction>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    if (direction) params.set("direction", direction);
    if (start) params.set("start", start);
    if (end) params.set("end", end);
    if (minAmount) params.set("min_amount", minAmount);
    if (maxAmount) params.set("max_amount", maxAmount);
    if (subscriptionOnly) params.set("is_subscription", "true");
    if (reviewOnly) params.set("needs_review", "true");
    setLoading(true);
    api<{ items: Transaction[]; total: number }>(`/transactions?${params}`)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [
    page,
    search,
    category,
    direction,
    start,
    end,
    minAmount,
    maxAmount,
    subscriptionOnly,
    reviewOnly,
    refreshKey,
  ]);
  function open(item: Transaction) {
    setSelected(item);
    setDraft({
      category: item.category,
      merchant: item.merchant,
      notes: item.notes,
      is_transfer: item.is_transfer,
      is_refund: item.is_refund,
      is_subscription: item.is_subscription,
    });
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    setError(null);
    try {
      await api(`/transactions/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          category: draft.category,
          merchant_name: draft.merchant,
          notes: draft.notes,
          is_transfer: draft.is_transfer,
          is_refund: draft.is_refund,
          is_subscription: draft.is_subscription,
        }),
      });
      setSelected(null);
      setRefreshKey((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function remove() {
    if (
      !selected ||
      !window.confirm("Delete this transaction? This cannot be undone.")
    )
      return;
    try {
      await api(`/transactions/${selected.id}`, { method: "DELETE" });
      setSelected(null);
      setRefreshKey((v) => v + 1);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <AppShell
      title="Transactions"
      eyebrow="EVERY DETAIL, YOUR WAY"
      action={
        <Link className="button button-primary" href="/import">
          <Plus size={17} /> Import statement
        </Link>
      }
    >
      <div className="intro-row">
        <p>
          Find a purchase, correct a category, or mark a transfer. Your
          corrections guide future imports.
        </p>
        <span className="chip">{total} transactions</span>
      </div>
      <div className="filters">
        <label className="search-field">
          <Search size={18} />
          <input
            aria-label="Search transactions"
            placeholder="Search merchant or description…"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </label>
        <label>
          <SlidersHorizontal size={17} />
          <select
            aria-label="Category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          <select
            aria-label="Direction"
            value={direction}
            onChange={(e) => {
              setDirection(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All activity</option>
            <option value="expense">Money out</option>
            <option value="income">Money in</option>
          </select>
        </label>
        <button
          className="button button-outline"
          onClick={() => setAdvanced(!advanced)}
        >
          More filters
        </button>
      </div>
      {advanced && (
        <div className="advanced-filters">
          <label>
            From
            <input
              type="date"
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            To
            <input
              type="date"
              value={end}
              onChange={(e) => {
                setEnd(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Min. amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={minAmount}
              onChange={(e) => {
                setMinAmount(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label>
            Max. amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={maxAmount}
              onChange={(e) => {
                setMaxAmount(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={subscriptionOnly}
              onChange={(e) => {
                setSubscriptionOnly(e.target.checked);
                setPage(1);
              }}
            />{" "}
            Subscriptions only
          </label>
          <label className="filter-checkbox">
            <input
              type="checkbox"
              checked={reviewOnly}
              onChange={(e) => {
                setReviewOnly(e.target.checked);
                setPage(1);
              }}
            />{" "}
            Needs category review
          </label>
        </div>
      )}
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState
          title="No transactions found"
          text={
            total
              ? "Try a different search or filter."
              : "Import a CSV to populate your transaction history."
          }
          href={total ? undefined : "/import"}
          action="Import CSV"
        />
      ) : (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table className="data-table transaction-table">
              <thead>
                <tr>
                  <th>Transaction</th>
                  <th>Category</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => open(t)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") open(t);
                    }}
                  >
                    <td>
                      <div className="transaction-name">
                        <span className="recent-avatar">{t.merchant[0]}</span>
                        <span>
                          <strong>{t.merchant}</strong>
                          <small>{t.description_raw}</small>
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className="category-chip">{t.category}</span>
                      {t.is_transfer && <span className="tag">Transfer</span>}
                    </td>
                    <td>{shortDate(t.date)}</td>
                    <td
                      className={`amount-cell ${Number(t.amount) > 0 ? "positive" : ""}`}
                    >
                      {money(t.amount, t.currency)}
                    </td>
                    <td>
                      <ArrowRight size={16} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              Showing {(page - 1) * 25 + 1}–{Math.min(page * 25, total)} of{" "}
              {total}
            </span>
            <div>
              <button
                className="button button-outline"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                <ArrowLeft size={15} /> Previous
              </button>
              <button
                className="button button-outline"
                disabled={page * 25 >= total}
                onClick={() => setPage(page + 1)}
              >
                Next <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </section>
      )}
      {selected && (
        <div className="drawer-backdrop" onClick={() => setSelected(null)}>
          <aside
            className="drawer"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Transaction details"
          >
            <div className="drawer-heading">
              <div>
                <span className="section-kicker">TRANSACTION DETAILS</span>
                <h2>{selected.merchant}</h2>
              </div>
              <button
                className="icon-button"
                onClick={() => setSelected(null)}
                aria-label="Close"
              >
                <X size={21} />
              </button>
            </div>
            <div className="drawer-amount">
              {money(selected.amount, selected.currency)}
              <small>{shortDate(selected.date)}</small>
            </div>
            <form onSubmit={save}>
              <label>
                Merchant
                <input
                  value={draft.merchant || ""}
                  onChange={(e) =>
                    setDraft({ ...draft, merchant: e.target.value })
                  }
                />
              </label>
              <label>
                Category
                <select
                  value={draft.category || "Other"}
                  onChange={(e) =>
                    setDraft({ ...draft, category: e.target.value })
                  }
                >
                  {categories.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label>
                Notes
                <textarea
                  rows={3}
                  value={draft.notes || ""}
                  onChange={(e) =>
                    setDraft({ ...draft, notes: e.target.value })
                  }
                  placeholder="Add a note for yourself"
                />
              </label>
              <div className="checkbox-list">
                <label>
                  <input
                    type="checkbox"
                    checked={!!draft.is_transfer}
                    onChange={(e) =>
                      setDraft({ ...draft, is_transfer: e.target.checked })
                    }
                  />{" "}
                  Mark as transfer
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={!!draft.is_refund}
                    onChange={(e) =>
                      setDraft({ ...draft, is_refund: e.target.checked })
                    }
                  />{" "}
                  Mark as refund
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={!!draft.is_subscription}
                    onChange={(e) =>
                      setDraft({ ...draft, is_subscription: e.target.checked })
                    }
                  />{" "}
                  Mark as subscription
                </label>
              </div>
              <p className="detail-note">
                Original description: {selected.description_raw}
                <br />
                Category source: {selected.category_source} · Confidence:{" "}
                {Math.round(Number(selected.confidence) * 100)}%
              </p>
              <div className="drawer-actions">
                <button
                  className="button button-primary button-full"
                  disabled={saving}
                >
                  {saving ? "Saving…" : "Save changes"}
                </button>
                <button
                  type="button"
                  className="button button-danger"
                  onClick={remove}
                >
                  <Trash2 size={16} /> Delete transaction
                </button>
              </div>
            </form>
          </aside>
        </div>
      )}
    </AppShell>
  );
}
