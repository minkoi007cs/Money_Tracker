"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ChartNoAxesCombined,
  LockKeyhole,
  Wallet,
} from "lucide-react";
import { api, setToken } from "@/lib/api";
import { ErrorBox } from "@/components/UI";

export default function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await api<{ access_token: string }>(
        `/auth/${mode === "login" ? "login" : "register"}`,
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      setToken(result.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-layout">
      <div className="auth-aside">
        <Link className="brand" href="/">
          <span className="brand-mark">
            <Wallet size={20} />
          </span>
          <span>
            where<span className="brand-light">money</span>
          </span>
        </Link>
        <div className="auth-aside-copy">
          <span className="hero-pill">A calmer way to see your spending</span>
          <h2>Clarity looks good on your money.</h2>
          <p>From a messy statement to a picture that finally makes sense.</p>
          <div className="auth-aside-card">
            <ChartNoAxesCombined size={22} />
            <span>
              Spending insights that start with your data, not assumptions.
            </span>
          </div>
        </div>
        <small>Private by design · Built for everyday decisions</small>
      </div>
      <main className="auth-main">
        <div className="auth-card">
          <span className="auth-icon">
            <LockKeyhole size={23} />
          </span>
          <h1>{mode === "login" ? "Welcome back" : "Create your workspace"}</h1>
          <p>
            {mode === "login"
              ? "Pick up where you left off with your spending."
              : "Start with a simple, private view of your money."}
          </p>
          <form onSubmit={submit}>
            <label>
              Email address
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                minLength={10}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 10 characters"
                required
              />
            </label>
            <ErrorBox message={error} />
            <button
              className="button button-primary button-full"
              disabled={busy}
            >
              {busy
                ? "Please wait…"
                : mode === "login"
                  ? "Log in"
                  : "Create account"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="auth-switch">
            {mode === "login" ? "New here?" : "Already have an account?"}{" "}
            <Link href={mode === "login" ? "/signup" : "/login"}>
              {mode === "login" ? "Create an account" : "Log in"}
            </Link>
          </div>
          <div className="auth-privacy">
            <LockKeyhole size={15} /> Your statements are never used for
            advertising.
          </div>
        </div>
      </main>
    </div>
  );
}
