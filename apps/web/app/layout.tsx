import type { Metadata } from "next";
import PwaClient from "@/components/PwaClient";
import "./globals.css";

export const metadata: Metadata = {
  title: "Where Did My Money Go?",
  description: "A calm, private view of your spending from CSV statements.",
  appleWebApp: { capable: true, title: "Money Tracker", statusBarStyle: "default" },
  icons: { apple: "/icons/apple-touch-icon.png" },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover" as const,
  themeColor: "#235b47",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><PwaClient />{children}</body>
    </html>
  );
}
