import type { Metadata, Viewport } from "next";
import { Archivo, Be_Vietnam_Pro, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/site-header";
import { t } from "@/lib/i18n";
import "./globals.css";

/**
 * The interface is English, but nearly every name in it is Vietnamese.
 *
 * Be Vietnam Pro is drawn for those diacritics, so a team called
 * "CHIẾN THẦN BẤT BẠI" sits on its baseline instead of colliding with the
 * line above. Archivo carries the headings and the scoreboard numerals - it
 * is wide, confident and has the tabular figures a table of scores needs.
 * Both are self-hosted by next/font, so no request leaves the page and
 * nothing reflows once they load.
 */
const bodyFont = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-body-family"
});

const displayFont = Archivo({
  subsets: ["latin", "vietnamese"],
  weight: ["600", "700", "800"],
  display: "swap",
  variable: "--font-display-family"
});

const monoFont = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["500", "700"],
  display: "swap",
  variable: "--font-mono-family"
});

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
    <html lang="en" className={`${bodyFont.variable} ${displayFont.variable} ${monoFont.variable}`}>
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
