"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "./brand-mark";
import { Icon, type IconName } from "./icons";

const primaryNav: Array<{ href: string; label: string; icon: IconName }> = [
  { href: "/", label: "Tổng quan", icon: "dashboard" },
  { href: "/classic", label: "Classic", icon: "standings" },
  { href: "/h2h", label: "H2H", icon: "fixture" },
  { href: "/cup", label: "Cup", icon: "cup" },
  { href: "/highlights", label: "Highlights", icon: "highlight" },
  { href: "/managers", label: "Managers", icon: "manager" }
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
        <nav className="desktop-nav" aria-label="Điều hướng chính">
          {primaryNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="nav-link"
              data-active={isActive(pathname, item.href)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="header-actions">
          <span className="season-pill">2026/27</span>
          <Link href="/admin" className="admin-link">
            <Icon name="shield" size={17} />
            <span>Điều hành</span>
          </Link>
        </div>
      </div>
      <nav className="mobile-nav" aria-label="Điều hướng di động">
        {primaryNav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="mobile-nav__link"
            data-active={isActive(pathname, item.href)}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </header>
  );
}
