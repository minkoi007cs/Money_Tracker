"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Lightbulb, TrendingUp } from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, money } from "@/lib/api";

type Insight = { text: string; kind: string; evidence: Record<string, string> };
type Comparison = {
  current_period: string;
  previous_period: string;
  currencies: Record<
    string,
    {
      current: string;
      previous: string;
      difference: string;
      percent: string | null;
      categories: {
        name: string;
        current: string;
        previous: string;
        difference: string;
      }[];
    }
  >;
  note: string;
};
export default function Insights() {
  const [items, setItems] = useState<Insight[]>([]);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    Promise.all([
      api<Insight[]>("/insights"),
      api<Comparison>("/analytics/comparison"),
    ])
      .then(([a, b]) => {
        setItems(a);
        setComparison(b);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <AppShell title="Insights" eyebrow="THE STORY BEHIND THE NUMBERS">
      <div className="intro-row">
        <p>
          Plain-language facts calculated from your own transactions. No
          judgment, just a clearer view.
        </p>
      </div>
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState
          title="Insights need a little history"
          text="Import a statement to see the categories and merchants behind your spending."
          href="/import"
          action="Import a CSV"
        />
      ) : (
        <>
          <div className="insight-grid">
            {items.map((item, index) => (
              <section className="panel insight-card" key={index}>
                <span className="insight-icon">
                  <Lightbulb size={21} />
                </span>
                <span className="section-kicker">BASED ON YOUR DATA</span>
                <h2>{item.text}</h2>
                <p>
                  Evidence:{" "}
                  {Object.entries(item.evidence)
                    .map(([k, v]) => `${k.replaceAll("_", " ")} ${v}`)
                    .join(" · ")}
                </p>
              </section>
            ))}
          </div>
          {comparison && Object.entries(comparison.currencies).length > 0 && (
            <section className="panel comparison-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">THIS MONTH VS LAST</span>
                  <h2>How spending changed</h2>
                </div>
                <TrendingUp size={21} />
              </div>
              <div className="comparison-grid">
                {Object.entries(comparison.currencies).map(
                  ([currency, row]) => (
                    <div key={currency}>
                      <span>{currency}</span>
                      <strong>{money(row.current, currency)}</strong>
                      <p>
                        Last month {money(row.previous, currency)} · Change{" "}
                        {money(row.difference, currency)}
                        {row.percent && ` (${row.percent}%)`}
                      </p>
                      <div className="comparison-categories">
                        {row.categories
                          .filter(
                            (c) => Number(c.current) || Number(c.previous),
                          )
                          .slice(0, 5)
                          .map((c) => (
                            <div key={c.name}>
                              <span>{c.name}</span>
                              <b>{money(c.difference, currency)}</b>
                            </div>
                          ))}
                      </div>
                    </div>
                  ),
                )}
              </div>
              <small className="muted">
                This month is still in progress. Comparisons describe recorded
                transactions.
              </small>
            </section>
          )}
          <Link className="panel-link" href="/transactions">
            Explore your transactions <ArrowRight size={17} />
          </Link>
        </>
      )}
    </AppShell>
  );
}
