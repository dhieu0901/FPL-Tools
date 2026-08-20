"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { MessageKey } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import { BrandMark } from "./brand-mark";
import { Icon, type IconName } from "./icons";

const primaryNav: Array<{ href: string; label: MessageKey; icon: IconName }> = [
  { href: "/", label: "nav.overview", icon: "dashboard" },
  { href: "/classic", label: "nav.classic", icon: "standings" },
  { href: "/h2h", label: "nav.h2h", icon: "fixture" },
  { href: "/cup", label: "nav.cup", icon: "cup" },
  { href: "/highlights", label: "nav.highlights", icon: "highlight" },
  { href: "/managers", label: "nav.managers", icon: "manager" },
  { href: "/rules", label: "nav.rules", icon: "info" }
];

function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="site-header">
      <div className="site-header__inner">
        <Link href="/" className="brand-link">
          <BrandMark />
        </Link>
        <nav className="desktop-nav" aria-label={t("nav.main")}>
          {primaryNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="nav-link"
              data-active={isActive(pathname, item.href)}
            >
              {t(item.label)}
            </Link>
          ))}
        </nav>
        <div className="header-actions">
          <span className="season-pill">2026/27</span>
          {/* Prefetching would fetch a protected route in the background, and
              the 401 it returns makes the browser raise a sign-in dialog over
              the public site. The admin area is reached by clicking. */}
          <Link href="/admin" className="admin-link" prefetch={false}>
            <Icon name="shield" size={17} />
            <span>{t("nav.control")}</span>
          </Link>
        </div>
      </div>
      <nav className="mobile-nav" aria-label={t("nav.mobile")}>
        {primaryNav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="mobile-nav__link"
            data-active={isActive(pathname, item.href)}
          >
            <Icon name={item.icon} size={18} />
            <span>{t(item.label)}</span>
          </Link>
        ))}
      </nav>
    </header>
  );
}
