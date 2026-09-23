"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Layers3 } from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, money, Summary } from "@/lib/api";

export default function Categories() {
  const [summary, setSummary] = useState<Record<string, Summary>>({});
  const [reviewCount, setReviewCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([
      api<{ currencies: Record<string, Summary> }>("/analytics/summary"),
      api<{ total: number }>("/transactions?needs_review=true&page_size=1"),
    ])
      .then(([summaryResponse, reviewResponse]) => {
        setSummary(summaryResponse.currencies);
        setReviewCount(reviewResponse.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <AppShell title="Categories" eyebrow="HOW SPENDING ADDS UP">
      <div className="intro-row">
        <p>
          Explore where your spending is grouped. Open a transaction to correct
          a category; your preference will guide future imports.
        </p>
      </div>
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : Object.keys(summary).length === 0 ? (
        <EmptyState
          title="No categories to explore yet"
          text="Import transactions first, then your spending groups will appear here."
          href="/import"
          action="Import CSV"
        />
      ) : (
        <>
          {reviewCount > 0 && (
            <div className="info-banner">
              {reviewCount} transaction{reviewCount === 1 ? " has" : "s have"} a
              low-confidence category. Open Transactions → More filters → Needs
              category review to check them.
            </div>
          )}
          {Object.entries(summary).map(([currency, data]) => (
            <section className="panel categories-panel" key={currency}>
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">{currency} · ALL TIME</span>
                  <h2>Spending by category</h2>
                </div>
                <span className="chip">
                  {money(data.spending, currency)} total
                </span>
              </div>
              {data.categories.length ? (
                <div className="category-cards">
                  {data.categories.map((item, index) => (
                    <div key={item.name} className="category-card">
                      <span className={`category-card-icon fill-${index % 6}`}>
                        <Layers3 size={19} />
                      </span>
                      <div>
                        <strong>{item.name}</strong>
                        <span>
                          {Math.round(
                            (Number(item.amount) / Number(data.spending)) * 100,
                          )}
                          % of spending
                        </span>
                      </div>
                      <b>{money(item.amount, currency)}</b>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No outgoing transactions found.</p>
              )}
              <Link href="/transactions" className="panel-link">
                Review and edit transactions <ArrowRight size={16} />
              </Link>
            </section>
          ))}
        </>
      )}
    </AppShell>
  );
}
