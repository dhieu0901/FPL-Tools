"use client";

import Link from "next/link";
import { t } from "@/lib/i18n";
import { Icon } from "./icons";

export function AdminNav({ active }: { active: "overview" | "violations" }) {
  return (
    <nav className="admin-nav" aria-label={t("nav.admin")}>
      <Link href="/admin" data-active={active === "overview"}>
        <Icon name="dashboard" size={17} /> {t("nav.overview")}
      </Link>
      <Link href="/admin/violations" data-active={active === "violations"}>
        <Icon name="warning" size={17} /> {t("nav.violations")}
      </Link>
    </nav>
  );
}
