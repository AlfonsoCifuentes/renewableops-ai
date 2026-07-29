import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";
import Script from "next/script";

import "./globals.css";

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "RenewableOps AI · Control Room",
    template: "%s · RenewableOps AI",
  },
  description:
    "Plataforma reproducible de forecasting, salud de activos, MLOps y gobierno para una cartera renovable de demostración.",
  applicationName: "RenewableOps AI",
  authors: [{ name: "Alfonso Cifuentes" }],
  keywords: [
    "renewable energy",
    "forecasting",
    "MLOps",
    "Databricks",
    "scikit-learn",
    "operations",
  ],
  robots: { index: true, follow: true },
  openGraph: {
    title: "RenewableOps AI",
    description: "Renewable operations, forecasting and MLOps control room.",
    type: "website",
    locale: "es_ES",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f1ec" },
    { media: "(prefers-color-scheme: dark)", color: "#121a17" },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="es"
      className={`${sans.variable} ${mono.variable}`}
      data-scroll-behavior="smooth"
      suppressHydrationWarning
    >
      <body>
        <Script id="renewableops-theme" strategy="beforeInteractive">
          {`try{var t=localStorage.getItem("renewableops-theme");if(t){document.documentElement.dataset.theme=t}}catch(e){}`}
        </Script>
        {children}
      </body>
    </html>
  );
}
