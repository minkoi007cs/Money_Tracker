"use client";

import { useEffect, useState } from "react";
import { Download, Smartphone } from "lucide-react";

export default function InstallApp() {
  const [ready, setReady] = useState(false);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const update = () => {
      setReady(Boolean(window.moneyTrackerInstallPrompt));
      setInstalled(window.matchMedia("(display-mode: standalone)").matches ||
        ("standalone" in navigator && Boolean((navigator as Navigator & { standalone?: boolean }).standalone)));
    };
    update();
    window.addEventListener("moneytracker:install-ready", update);
    window.addEventListener("appinstalled", update);
    return () => {
      window.removeEventListener("moneytracker:install-ready", update);
      window.removeEventListener("appinstalled", update);
    };
  }, []);

  async function install() {
    const prompt = window.moneyTrackerInstallPrompt;
    if (!prompt) return;
    await prompt.prompt();
    await prompt.userChoice;
    window.moneyTrackerInstallPrompt = undefined;
    setReady(false);
  }

  return (
    <section className="panel install-panel">
      <div className="panel-heading">
        <div>
          <span className="section-kicker">PHONE ACCESS</span>
          <h2>Install on your phone</h2>
        </div>
        <Smartphone size={23} />
      </div>
      {installed ? <p>Money Tracker is already open as an installed app.</p> : <>
        <p>Open the published HTTPS site on your phone. The app icon will appear on your home screen.</p>
        {ready && <button className="button button-primary" onClick={install}><Download size={16} /> Install app</button>}
        <div className="install-steps">
          <p><strong>iPhone:</strong> In Safari, tap Share, then <strong>Add to Home Screen</strong>.</p>
          <p><strong>Android:</strong> In Chrome, tap the menu, then <strong>Install app</strong> or <strong>Add to Home screen</strong>.</p>
        </div>
      </>}
      <p className="hint">A connection is needed to sign in and load your financial data. Your CSV files are only sent to the app API when you choose to import them.</p>
    </section>
  );
}
