"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileSpreadsheet, Plus, Trash2 } from "lucide-react";
import AppShell from "@/components/AppShell";
import { EmptyState, ErrorBox, Loading } from "@/components/UI";
import { api, shortDate } from "@/lib/api";

type Batch = {
  id: string;
  filename: string;
  created_at: string;
  row_count: number;
  imported_count: number;
  duplicate_count: number;
  rejected_count: number;
};
type Profile = { id: string; name: string; mapping: Record<string, string> };
export default function History() {
  const [items, setItems] = useState<Batch[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  function refresh() {
    Promise.all([api<Batch[]>("/imports"), api<Profile[]>("/import-profiles")])
      .then(([batches, mappings]) => {
        setItems(batches);
        setProfiles(mappings);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }
  useEffect(refresh, []);
  async function remove(id: string) {
    if (
      !window.confirm(
        "Delete this import and all its transactions? This cannot be undone.",
      )
    )
      return;
    try {
      await api(`/imports/${id}`, { method: "DELETE" });
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function removeProfile(id: string) {
    if (
      !window.confirm(
        "Delete this saved column mapping? Imported transactions will stay.",
      )
    )
      return;
    try {
      await api(`/import-profiles/${id}`, { method: "DELETE" });
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <AppShell
      title="Import history"
      eyebrow="YOUR DATA SOURCES"
      action={
        <Link className="button button-primary" href="/import">
          <Plus size={17} /> New import
        </Link>
      }
    >
      <div className="intro-row">
        <p>
          See every statement you have imported, including duplicates and rows
          that needed review.
        </p>
      </div>
      <ErrorBox message={error} />
      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <EmptyState
          title="No imports yet"
          text="Upload your first CSV statement to start your spending picture."
          href="/import"
          action="Import a CSV"
        />
      ) : (
        <>
          <section className="panel">
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Statement</th>
                    <th>Imported</th>
                    <th>Duplicates</th>
                    <th>Rejected</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <span className="table-name">
                          <FileSpreadsheet size={19} />
                          {b.filename}
                        </span>
                      </td>
                      <td>{b.imported_count}</td>
                      <td>{b.duplicate_count}</td>
                      <td>{b.rejected_count}</td>
                      <td>{shortDate(b.created_at)}</td>
                      <td>
                        <button
                          className="icon-button danger"
                          aria-label={`Delete ${b.filename}`}
                          onClick={() => remove(b.id)}
                        >
                          <Trash2 size={17} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {profiles.length > 0 && (
            <section className="panel profile-panel">
              <div className="panel-heading">
                <div>
                  <span className="section-kicker">SAVED FOR NEXT TIME</span>
                  <h2>Column mappings</h2>
                </div>
              </div>
              {profiles.map((p) => (
                <div className="profile-row" key={p.id}>
                  <div>
                    <strong>{p.name}</strong>
                    <span>
                      Date: {p.mapping.date} · Description:{" "}
                      {p.mapping.description}
                    </span>
                  </div>
                  <button
                    className="icon-button danger"
                    aria-label={`Delete mapping ${p.name}`}
                    onClick={() => removeProfile(p.id)}
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              ))}
            </section>
          )}
        </>
      )}
    </AppShell>
  );
}
