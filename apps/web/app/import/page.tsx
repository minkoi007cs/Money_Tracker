"use client";

import { ChangeEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  CloudUpload,
  FileSpreadsheet,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";
import AppShell from "@/components/AppShell";
import { ErrorBox } from "@/components/UI";
import { api } from "@/lib/api";

type Preview = {
  headers: string[];
  sample: Record<string, string>[];
  row_count: number;
  suggested_mapping: Record<string, string>;
  saved_profile: string | null;
};
type Result = {
  imported_count: number;
  duplicate_count: number;
  rejected_count: number;
  row_count: number;
  errors: { row: number; reason: string }[];
};
const fields = [
  "date",
  "description",
  "amount",
  "debit",
  "credit",
  "merchant",
  "currency",
];

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [format, setFormat] = useState("%Y-%m-%d");
  const [signMode, setSignMode] = useState("negative_spend");
  const [saveProfile, setSaveProfile] = useState(false);
  const [profileName, setProfileName] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function choose(event: ChangeEvent<HTMLInputElement>) {
    const chosen = event.target.files?.[0];
    if (!chosen) return;
    setFile(chosen);
    setPreview(null);
    setResult(null);
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", chosen);
      const next = await api<Preview>("/imports/preview", {
        method: "POST",
        body: form,
      });
      setPreview(next);
      setMapping(next.suggested_mapping);
      const dateSample = next.sample[0]?.[next.suggested_mapping.date];
      setFormat(
        next.suggested_mapping.date_format ||
          (dateSample?.includes("/") ? "" : "%Y-%m-%d"),
      );
      setSignMode(next.suggested_mapping.sign_mode || "negative_spend");
      setProfileName(next.saved_profile || "");
      setSaveProfile(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!file) return;
    if (
      !mapping.date ||
      !mapping.description ||
      (!mapping.amount && !mapping.debit && !mapping.credit) ||
      !format
    ) {
      setError(
        "Map date, description and amount, then choose the date format.",
      );
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append(
        "mapping_json",
        JSON.stringify({
          ...mapping,
          date_format: format,
          sign_mode: signMode,
        }),
      );
      if (saveProfile && profileName.trim())
        form.append("profile_name", profileName.trim());
      setResult(
        await api<Result>("/imports/confirm", { method: "POST", body: form }),
      );
      setPreview(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell title="Import a statement" eyebrow="START WITH YOUR DATA">
      <div className="intro-row">
        <p>
          Bring a CSV from your bank. You will review the columns before
          anything is added.
        </p>
      </div>
      <div className="steps">
        <span className="step active">
          1 <b>Upload</b>
        </span>
        <span className={preview ? "step active" : "step"}>
          2 <b>Review columns</b>
        </span>
        <span className={result ? "step active" : "step"}>
          3 <b>Complete</b>
        </span>
      </div>
      <ErrorBox message={error} />
      {result ? (
        <section className="panel result-panel">
          <span className="success-icon">
            <CheckCircle2 size={31} />
          </span>
          <h2>Your statement is ready</h2>
          <p>Here is what happened during this import.</p>
          <div className="result-stats">
            <div>
              <strong>{result.imported_count}</strong>
              <span>Imported</span>
            </div>
            <div>
              <strong>{result.duplicate_count}</strong>
              <span>Duplicates skipped</span>
            </div>
            <div>
              <strong>{result.rejected_count}</strong>
              <span>Rows needing review</span>
            </div>
          </div>
          {result.errors.length > 0 && (
            <div className="row-errors">
              <h3>Rows to review</h3>
              {result.errors.map((e) => (
                <p key={e.row}>
                  Row {e.row}: {e.reason}
                </p>
              ))}
            </div>
          )}
          <div className="button-row">
            <Link href="/dashboard" className="button button-primary">
              Go to overview <ArrowRight size={16} />
            </Link>
            <button
              className="button button-outline"
              onClick={() => {
                setResult(null);
                setFile(null);
              }}
            >
              <RotateCcw size={16} /> Import another
            </button>
          </div>
        </section>
      ) : !preview ? (
        <>
          <label className="upload-zone">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={choose}
              hidden
            />
            <span className="upload-icon">
              <CloudUpload size={32} />
            </span>
            <strong>
              {busy ? "Reading your file…" : "Choose a CSV statement"}
            </strong>
            <span>Click here to select a file from your computer</span>
            <small>CSV only · Up to 10 MB · Original file is not kept</small>
          </label>
          <div className="import-info">
            <div>
              <FileSpreadsheet size={21} />
              <span>
                <strong>Many bank formats work</strong>
                <small>
                  Map date, description, and amount columns before import.
                </small>
              </span>
            </div>
            <div>
              <ShieldCheck size={21} />
              <span>
                <strong>You stay in control</strong>
                <small>
                  Preview 10 rows and review anything that could not be read.
                </small>
              </span>
            </div>
          </div>
        </>
      ) : (
        <div className="import-review">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">FILE PREVIEW</span>
                <h2>{file?.name}</h2>
              </div>
              <span className="chip">{preview.row_count} rows found</span>
            </div>
            <p className="muted">
              The first 10 rows are shown below. Confirm that the data looks
              right.
            </p>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    {preview.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.sample.map((row, index) => (
                    <tr key={index}>
                      {preview.headers.map((h) => (
                        <td key={h}>{row[h] || "—"}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="panel mapping-panel">
            <div className="panel-heading">
              <div>
                <span className="section-kicker">COLUMN MAPPING</span>
                <h2>Match the columns</h2>
              </div>
            </div>
            {preview.saved_profile && (
              <div className="info-banner">
                Using your saved mapping “{preview.saved_profile}”. Review it
                before importing.
              </div>
            )}
            <div className="mapping-grid">
              {fields.map((field) => (
                <label key={field}>
                  {field[0].toUpperCase() + field.slice(1)}
                  {["date", "description"].includes(field) && " *"}
                  <select
                    value={mapping[field] || ""}
                    onChange={(e) =>
                      setMapping({ ...mapping, [field]: e.target.value })
                    }
                  >
                    <option value="">Not used</option>
                    {preview.headers.map((h) => (
                      <option key={h} value={h}>
                        {h}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              <label>
                Date format *
                <select
                  value={format}
                  onChange={(e) => setFormat(e.target.value)}
                >
                  <option value="">Choose a format</option>
                  <option value="%Y-%m-%d">YYYY-MM-DD</option>
                  <option value="%m/%d/%Y">MM/DD/YYYY</option>
                  <option value="%d/%m/%Y">DD/MM/YYYY</option>
                </select>
              </label>
              <label>
                Amount sign
                <select
                  value={signMode}
                  onChange={(e) => setSignMode(e.target.value)}
                >
                  <option value="negative_spend">
                    Negative means spending
                  </option>
                  <option value="positive_spend">
                    Positive means spending
                  </option>
                </select>
              </label>
            </div>
            <p className="hint">
              For separate Debit and Credit columns, leave Amount unused. Money
              coming in is stored as positive; spending is negative.
            </p>
            <div className="save-profile">
              <label>
                <input
                  type="checkbox"
                  checked={saveProfile}
                  onChange={(e) => setSaveProfile(e.target.checked)}
                />{" "}
                Save this mapping for future statements
              </label>
              {saveProfile && (
                <input
                  aria-label="Mapping name"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  placeholder="For example, checking account"
                  maxLength={100}
                />
              )}
            </div>
            <div className="button-row">
              <button
                className="button button-primary"
                onClick={confirm}
                disabled={busy || (saveProfile && !profileName.trim())}
              >
                {busy ? "Importing…" : "Confirm import"}
                <ArrowRight size={16} />
              </button>
              <button
                className="button button-outline"
                onClick={() => {
                  setPreview(null);
                  setFile(null);
                }}
              >
                Cancel
              </button>
            </div>
          </section>
        </div>
      )}
    </AppShell>
  );
}
