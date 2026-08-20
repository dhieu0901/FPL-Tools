"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { formatDateTime, initials } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { DataSource, Division } from "@/lib/types";
import { Icon, type IconName } from "./icons";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function SectionHeader({
  eyebrow,
  title,
  description,
  href,
  linkLabel
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <div className="section-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {href && (
        <Link href={href} className="text-link">
          {linkLabel ?? t("common.viewAll")} <Icon name="arrow" size={17} />
        </Link>
      )}
    </div>
  );
}

export function DataBadge({ source, updatedAt }: { source: DataSource; updatedAt: string }) {
  const isUnavailable = source === "unavailable";
  return (
    <div className="data-badge" data-unavailable={isUnavailable}>
      <span className="data-badge__dot" />
      <span>{isUnavailable ? t("data.unavailable") : t("data.live")}</span>
      <span className="data-badge__time">
        {t("data.respondedAt", { time: formatDateTime(updatedAt) })}
      </span>
    </div>
  );
}

export function Pill({
  children,
  tone = "neutral"
}: {
  children: ReactNode;
  tone?: "neutral" | "lime" | "coral" | "blue" | "danger" | "warning";
}) {
  return (
    <span className="pill" data-tone={tone}>
      {children}
    </span>
  );
}

export function Avatar({
  name,
  division,
  size = "medium"
}: {
  name: string;
  division?: Division;
  size?: "small" | "medium" | "large";
}) {
  return (
    <span
      className="avatar"
      data-division={division?.toLowerCase()}
      data-size={size}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

export function FormDots({ form }: { form: Array<"W" | "D" | "L"> }) {
  return (
    <span
      className="form-dots"
      role="img"
      aria-label={t("common.formAria", { form: form.join(", ") })}
    >
      {form.map((item, index) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: form slots have fixed positional identity.
        <span key={`${item}-${index}`} data-result={item}>
          {item}
        </span>
      ))}
    </span>
  );
}

export function EmptyState({
  icon = "info",
  title,
  description,
  action
}: {
  icon?: IconName;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon">
        <Icon name={icon} size={28} />
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function Callout({
  icon = "info",
  title,
  children,
  tone = "blue"
}: {
  icon?: IconName;
  title: string;
  children: ReactNode;
  tone?: "blue" | "warning" | "danger" | "lime";
}) {
  return (
    <aside className="callout" data-tone={tone}>
      <Icon name={icon} size={20} />
      <div>
        <strong>{title}</strong>
        <div>{children}</div>
      </div>
    </aside>
  );
}

export function SegmentedLinks({
  items
}: {
  items: Array<{ href: string; label: string; active?: boolean }>;
}) {
  return (
    <nav className="segmented-links" aria-label={t("common.contentOptions")}>
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          data-active={item.active}
          aria-current={item.active ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
