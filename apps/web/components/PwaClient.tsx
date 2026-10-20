"use client";

import { useEffect } from "react";

export type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

declare global {
  interface Window {
    moneyTrackerInstallPrompt?: InstallPromptEvent;
  }
}

export default function PwaClient() {
  useEffect(() => {
    if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // The app still works in browsers that decline service workers.
      });
    }
    const onPrompt = (event: Event) => {
      event.preventDefault();
      window.moneyTrackerInstallPrompt = event as InstallPromptEvent;
      window.dispatchEvent(new Event("moneytracker:install-ready"));
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  return null;
}
