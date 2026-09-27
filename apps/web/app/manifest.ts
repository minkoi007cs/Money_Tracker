import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Where Did My Money Go?",
    short_name: "Money Tracker",
    description: "Track your bank statement spending and recurring payments.",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    background_color: "#f8f9f6",
    theme_color: "#235b47",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
