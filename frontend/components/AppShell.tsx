"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowDownToLine,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  CreditCard,
  FileClock,
  Layers3,
  Lightbulb,
  LogOut,
  Menu,
  Repeat2,
  Settings2,
  Wallet,
  X,
} from "lucide-react";
import { api, setToken, token } from "@/lib/api";

const nav = [
  { href: "/dashboard", label: "Overview", icon: ChartNoAxesCombined },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/import", label: "Import CSV", icon: ArrowDownToLine },
  { href: "/history", label: "Import history", icon: FileClock },
  { href: "/subscriptions", label: "Recurring", icon: Repeat2 },
  { href: "/categories", label: "Categories", icon: Layers3 },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/settings", label: "Settings & privacy", icon: Settings2 },
];

export default function AppShell({
  children,
  title,
  eyebrow,
  action,
}: {
  children: React.ReactNode;
  title: string;
  eyebrow?: string;
  action?: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ email: string } | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token()) {
      router.replace("/login");
      return;
    }
    api<{ email: string }>("/me")
      .then(setUser)
      .catch(() => {
        setToken(null);
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading)
    return (
      <div className="center-screen">
        <div className="loading-ring" />
        <p>Opening your workspace…</p>
      </div>
    );

  return (
    <div className="app-frame">
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="sidebar-top">
          <Link
            href="/dashboard"
            className="brand"
            onClick={() => setOpen(false)}
          >
            <span className="brand-mark">
              <Wallet size={21} />
            </span>
            <span>
              where<span className="brand-light">money</span>
              <small>Personal finance, made clear.</small>
            </span>
          </Link>
          <button
            className="mobile-only icon-button"
            onClick={() => setOpen(false)}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>
        <div className="workspace-switch">
          <span className="workspace-avatar">P</span>
          <span>
            <strong>Personal workspace</strong>
            <small>My spending dashboard</small>
          </span>
          <ChevronDown size={15} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <Link
              key={item.href}
              className={`nav-item ${pathname === item.href ? "active" : ""}`}
              href={item.href}
              onClick={() => setOpen(false)}
            >
              <item.icon size={19} strokeWidth={1.9} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-note">
            <CircleHelp size={18} />
            <div>
              <strong>Your data, your view.</strong>
              <span>
                Your statements stay private. You can export or delete your data
                anytime.
              </span>
            </div>
          </div>
          <button
            className="nav-item logout"
            onClick={() => {
              setToken(null);
              router.push("/");
            }}
          >
            <LogOut size={19} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      {open && (
        <button
          className="mobile-overlay"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="main-area">
        <header className="topbar">
          <button
            className="mobile-only icon-button"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>
          <div className="topbar-path">
            Your workspace <span>/</span> {title}
          </div>
          <div className="topbar-right">
            <span className="secure-badge">● Private workspace</span>
            <span className="user-avatar" title={user?.email || "Account"}>
              {user?.email?.slice(0, 1).toUpperCase() || "U"}
            </span>
          </div>
        </header>
        <main className="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{eyebrow || "YOUR FINANCIAL PICTURE"}</p>
              <h1>{title}</h1>
            </div>
            {action}
          </div>
          {children}
        </main>
        <footer className="app-footer">
          Where Did My Money Go? · A clearer view of your money, on your terms.
        </footer>
      </div>
    </div>
  );
}
