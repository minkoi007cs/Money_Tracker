"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { openLink, resumeFlow } from "@/lib/plaid";
import { ErrorBox } from "@/components/UI";

export default function BankCallback() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  useEffect(() => {
    if (!ready || started.current) return;
    started.current = true;
    const flow = resumeFlow();
    if (!flow || !new URLSearchParams(window.location.search).has("oauth_state_id")) {
      setError("This bank sign-in has expired. Return to Overview and connect again.");
      return;
    }
    try {
      openLink(flow, () => router.replace("/dashboard"), message => setError(message || "Bank sign-in was cancelled."), window.location.href);
    } catch (error) { setError((error as Error).message); }
  }, [ready, router]);
  return <main className="center-screen">
    <Script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js" onReady={() => setReady(true)} onError={() => setError("Bank sign-in could not load. Please return to Overview and try again.")} />
    <h1>Finishing bank sign-in</h1>
    <p>Your bank connection will appear in Overview.</p>
    <ErrorBox message={error} />
    {error && <Link className="button button-primary" href="/dashboard">Back to Overview</Link>}
  </main>;
}
