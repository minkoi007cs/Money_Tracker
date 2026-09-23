import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Where Did My Money Go?",
  description: "A calm, private view of your spending from CSV statements.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
