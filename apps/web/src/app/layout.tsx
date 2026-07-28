import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "VMF League · Văn Minh Fantasy",
    template: "%s · VMF League"
  },
  description: "Bảng điều hành và theo dõi giải Văn Minh Fantasy League mùa 2026/27.",
  applicationName: "VMF League",
  robots: { index: true, follow: true }
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0a1020"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <a className="skip-link" href="#main-content">
          Đi tới nội dung chính
        </a>
        <SiteHeader />
        <main id="main-content" className="main-shell">
          {children}
        </main>
        <footer className="site-footer">
          <div>
            <p>
              <strong>VMF League</strong> · Mùa giải 2026/27
            </p>
            <p>Dữ liệu điểm số được đồng bộ và kiểm toán theo luật giải.</p>
          </div>
          <div className="footer-status">
            <span />
            Hệ thống vận hành
          </div>
        </footer>
      </body>
    </html>
  );
}
