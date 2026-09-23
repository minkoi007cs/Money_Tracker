"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  CreditCard,
  Plus,
  Repeat2,
  TrendingUp,
} from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, money, shortDate, Summary, Transaction } from "@/lib/api";

type Period = "this" | "last" | "all";
function range(period: Period) {
  if (period === "all") return "";
  const now = new Date();
  const year =
    period === "this"
      ? now.getFullYear()
      : now.getMonth()
        ? now.getFullYear()
        : now.getFullYear() - 1;
  const month = period === "this" ? now.getMonth() : (now.getMonth() + 11) % 12;
  const start = `${year}-${String(month + 1).padStart(2, "0")}-01`;
  const end =
    period === "this"
      ? new Date().toISOString().slice(0, 10)
      : new Date(year, month + 1, 0).toISOString().slice(0, 10);
  return `?start=${start}&end=${end}`;
}

export default function Dashboard() {
  const [period, setPeriod] = useState<Period>("all");
  const [summary, setSummary] = useState<Record<string, Summary>>({});
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [comparison, setComparison] = useState<{
    currencies: Record<string, { difference: string; percent: string | null }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setLoading(true);
    Promise.all([
      api<{ currencies: Record<string, Summary> }>(
        `/analytics/summary${range(period)}`,
      ),
      api<{ items: Transaction[] }>("/transactions?page_size=5"),
      api<{
        currencies: Record<
          string,
          { difference: string; percent: string | null }
        >;
      }>("/analytics/comparison"),
    ])
      .then(([a, b, c]) => {
        setSummary(a.currencies);
        setRecent(b.items);
        setComparison(c);
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [period]);
  const currency = Object.keys(summary)[0] || "USD";
  const data = summary[currency];
  const max = Math.max(
    ...(data?.categories.map((x) => Number(x.amount)) || []),
    1,
  );
  const trend = data?.daily.slice(-14) || [];
  const trendMax = Math.max(...trend.map((x) => Number(x.amount)), 1);
  const delta = comparison?.currencies[currency];
  return (
    <AppShell
      title="Overview"
      eyebrow="GOOD TO HAVE YOU HERE"
      action={
        <Link className="button button-primary" href="/import">
          <Plus size={17} /> Import statement
        </Link>
      }
    >
      <div className="intro-row">
        <p>
          Your money at a glance. Every number comes from your imported
          transactions.
        </p>
        <label className="period-select">
          <CalendarDays size={17} />
          <select
            aria-label="Date range"
            value={period}
            onChange={(e) => setPeriod(e.target.value as Period)}
          >
            <option value="all">All time</option>
            <option value="this">This month</option>
            <option value="last">Last month</option>
          </select>
        </label>
      </div>
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : !data ? (
        <EmptyState
          title="Your dashboard starts with a statement"
          text="Upload a CSV to see where your money went, what changed, and what keeps coming back."
          href="/import"
          action="Import your first CSV"
        />
      ) : (
        <>
          <div className="stat-grid">
            <div className="stat-card">
              <span className="stat-icon green">
                <ArrowDownLeft size={20} />
              </span>
              <div>
                <span>Total income</span>
                <strong>{money(data.income, currency)}</strong>
                <small>Money coming in</small>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-icon peach">
                <ArrowUpRight size={20} />
              </span>
              <div>
                <span>Total spending</span>
                <strong>{money(data.spending, currency)}</strong>
                <small>Excludes transfers</small>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-icon blue">
                <TrendingUp size={20} />
              </span>
              <div>
                <span>Net cash flow</span>
                <strong>{money(data.net, currency)}</strong>
                <small>Income minus spending and refunds</small>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-icon lavender">
                <CreditCard size={20} />
              </span>
              <div>
                <span>Transactions</span>
                <strong>{data.count}</strong>
                <small>In selected period</small>
              </div>
            </div>
          </div>
          {Object.keys(summary).length > 1 && (
            <div className="info-banner">
              Multiple currencies are shown separately. Totals are never
              converted or combined.
            </div>
          )}
          <div className="dashboard-grid">
            <section className="panel category-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">BREAKDOWN</span>
                  <h2>Where it went</h2>
                </div>
                <Link href="/transactions" className="panel-link">
                  All transactions <ArrowRight size={16} />
                </Link>
              </div>
              {data.categories.length ? (
                <div className="category-list">
                  {data.categories.slice(0, 6).map((item, index) => (
                    <div className="category-row" key={item.name}>
                      <span className={`category-dot color-${index % 6}`} />
                      <span className="category-name">{item.name}</span>
                      <div className="category-track">
                        <span
                          style={{
                            width: `${Math.max((Number(item.amount) / max) * 100, 2)}%`,
                          }}
                          className={`category-fill fill-${index % 6}`}
                        />
                      </div>
                      <strong>{money(item.amount, currency)}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No spending in this period.</p>
              )}
            </section>
            <section className="panel glance-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">MONTH TO MONTH</span>
                  <h2>What changed</h2>
                </div>
              </div>
              <div className="glance-figure">
                <span>Spending change this month</span>
                <strong>
                  {delta ? money(delta.difference, currency) : "—"}
                </strong>
                <p>
                  {delta?.percent
                    ? `${Number(delta.percent) > 0 ? "+" : ""}${delta.percent}% compared with last month`
                    : "Add a previous month to see a comparison."}
                </p>
              </div>
              <div className="glance-note">
                <Repeat2 size={19} />
                <span>
                  This month is still in progress. Comparisons are descriptive,
                  not predictions.
                </span>
              </div>
            </section>
          </div>
          <section className="panel trend-panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">SPENDING OVER TIME</span>
                <h2>Daily trend</h2>
              </div>
              <span className="chip">{currency}</span>
            </div>
            {trend.length ? (
              <>
                <div
                  className="trend-bars"
                  role="img"
                  aria-label={`Daily spending trend for ${trend.length} active days`}
                >
                  {trend.map((day) => (
                    <div
                      className="trend-column"
                      key={day.date}
                      title={`${shortDate(day.date)}: ${money(day.amount, currency)}`}
                    >
                      <span
                        style={{
                          height: `${Math.max(6, (Number(day.amount) / trendMax) * 100)}%`,
                        }}
                      />
                    </div>
                  ))}
                </div>
                <div className="trend-labels">
                  <span>{shortDate(trend[0].date)}</span>
                  <span>{shortDate(trend[trend.length - 1].date)}</span>
                </div>
                <p className="muted">
                  Showing the last {trend.length} days with recorded spending.
                  Hover over a bar for its amount.
                </p>
              </>
            ) : (
              <p className="muted">No daily spending in this period.</p>
            )}
          </section>
          <div className="dashboard-grid bottom-grid">
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">TOP PLACES</span>
                  <h2>Merchants</h2>
                </div>
              </div>
              {data.merchants.length ? (
                <div className="merchant-list">
                  {data.merchants.slice(0, 5).map((m, i) => (
                    <div key={m.name}>
                      <span className="merchant-rank">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span>{m.name}</span>
                      <strong>{money(m.amount, currency)}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No merchants yet.</p>
              )}
            </section>
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">LATEST ACTIVITY</span>
                  <h2>Recent transactions</h2>
                </div>
                <Link href="/transactions" className="panel-link">
                  View all <ArrowRight size={16} />
                </Link>
              </div>
              {recent.length ? (
                <div className="recent-list">
                  {recent.map((t) => (
                    <div key={t.id}>
                      <span className="recent-avatar">{t.merchant[0]}</span>
                      <div>
                        <strong>{t.merchant}</strong>
                        <small>
                          {shortDate(t.date)} · {t.category}
                        </small>
                      </div>
                      <b className={Number(t.amount) >= 0 ? "positive" : ""}>
                        {money(t.amount, t.currency)}
                      </b>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Nothing here yet.</p>
              )}
            </section>
          </div>
        </>
      )}
    </AppShell>
  );
}
