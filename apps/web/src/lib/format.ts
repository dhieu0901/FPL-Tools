import { DEFAULT_LOCALE, type Locale, translate } from "./i18n";
import type { MatchStatus } from "./types";

// The league is played in Vietnam, so every timestamp is rendered in league
// time regardless of the reader's language or device timezone.
const LEAGUE_TIME_ZONE = "Asia/Bangkok";

const INTL_TAGS: Record<Locale, string> = { vi: "vi-VN", en: "en-GB" };

const numberFormats = new Map<Locale, Intl.NumberFormat>();
const dateFormats = new Map<Locale, Intl.DateTimeFormat>();
const dateTimeFormats = new Map<Locale, Intl.DateTimeFormat>();

function numberFormat(locale: Locale): Intl.NumberFormat {
  const existing = numberFormats.get(locale);
  if (existing) return existing;
  const created = new Intl.NumberFormat(INTL_TAGS[locale]);
  numberFormats.set(locale, created);
  return created;
}

function dateFormat(locale: Locale): Intl.DateTimeFormat {
  const existing = dateFormats.get(locale);
  if (existing) return existing;
  const created = new Intl.DateTimeFormat(INTL_TAGS[locale], {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: LEAGUE_TIME_ZONE
  });
  dateFormats.set(locale, created);
  return created;
}

function dateTimeFormat(locale: Locale): Intl.DateTimeFormat {
  const existing = dateTimeFormats.get(locale);
  if (existing) return existing;
  const created = new Intl.DateTimeFormat(INTL_TAGS[locale], {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: LEAGUE_TIME_ZONE
  });
  dateTimeFormats.set(locale, created);
  return created;
}

export function formatNumber(value: number, locale: Locale = DEFAULT_LOCALE): string {
  return numberFormat(locale).format(value);
}

export function formatDate(value: string, locale: Locale = DEFAULT_LOCALE): string {
  return dateFormat(locale).format(new Date(value));
}

export function formatDateTime(value: string, locale: Locale = DEFAULT_LOCALE): string {
  return dateTimeFormat(locale).format(new Date(value));
}

export function rankDelta(
  current: number,
  previous: number
): {
  direction: "up" | "down" | "same";
  value: number;
} {
  if (current < previous) return { direction: "up", value: previous - current };
  if (current > previous) return { direction: "down", value: current - previous };
  return { direction: "same", value: 0 };
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return parts
    .slice(-2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function gameweekStateLabel(
  state: "preseason" | "open" | "live" | "provisional" | "final",
  locale: Locale = DEFAULT_LOCALE
): string {
  return translate(locale, `state.${state}`);
}

export function matchStatusLabel(status: MatchStatus, locale: Locale = DEFAULT_LOCALE): string {
  return translate(locale, `match.${status}`);
}
