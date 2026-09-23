"use client";

import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";

export function EmptyState({
  title,
  text,
  href,
  action,
}: {
  title: string;
  text: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Inbox size={28} />
      </span>
      <h3>{title}</h3>
      <p>{text}</p>
      {href && (
        <Link href={href} className="button button-primary">
          {action || "Get started"}
          <ArrowRight size={16} />
        </Link>
      )}
    </div>
  );
}

export function ErrorBox({ message }: { message: string | null }) {
  return message ? (
    <div className="error-box" role="alert">
      {message}
    </div>
  ) : null;
}

export function Loading() {
  return (
    <div className="loading-state">
      <div className="loading-ring" />
      Loading your data…
    </div>
  );
}
