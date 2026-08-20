import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/site-header";
import { t } from "@/lib/i18n";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "VMF League · Văn Minh Fantasy",
    template: "%s · VMF League"
  },
  description: "Văn Minh Fantasy League 2026/27 standings, head-to-head and Cup dashboard.",
  applicationName: "VMF League",
  robots: { index: true, follow: true },
  icons: {
    icon: [
      { url: "/favicon.png", sizes: "32x32", type: "image/png" },
      { url: "/vmf-192.png", sizes: "192x192", type: "image/png" }
    ],
    apple: "/apple-icon.png"
  }
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0a1020"
};

// Fetch league data at request-time so Vercel builds never depend on a live API.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          {t("skip.toContent")}
        </a>
        <SiteHeader />
        <main id="main-content" className="main-shell">
          {children}
        </main>
        <footer className="site-footer">
          <div>
            <p>
              <strong>VMF League</strong> · {t("footer.season")}
            </p>
            <p>{t("footer.note")}</p>
          </div>
          <div className="footer-status">
            <span />
            {t("footer.status")}
          </div>
        </footer>
      </body>
    </html>
  );
}
