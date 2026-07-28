"use client";

import Link from "next/link";
import { Icon } from "./icons";
import { useTranslator } from "./locale-provider";

export function AdminNav({ active }: { active: "overview" | "violations" }) {
  const t = useTranslator();
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
