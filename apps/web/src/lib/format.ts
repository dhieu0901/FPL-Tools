import { t } from "./i18n";
import type { MatchStatus } from "./types";

// The league is played in Vietnam, so every timestamp is rendered in league
// time rather than in the reader's device timezone.
const LEAGUE_TIME_ZONE = "Asia/Bangkok";

const LOCALE_TAG = "en-GB";

const numberFormat = new Intl.NumberFormat(LOCALE_TAG);

const dateFormat = new Intl.DateTimeFormat(LOCALE_TAG, {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: LEAGUE_TIME_ZONE
});

const dateTimeFormat = new Intl.DateTimeFormat(LOCALE_TAG, {
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: LEAGUE_TIME_ZONE
});

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatDate(value: string): string {
  return dateFormat.format(new Date(value));
}

export function formatDateTime(value: string): string {
  return dateTimeFormat.format(new Date(value));
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
  state: "preseason" | "open" | "live" | "provisional" | "final"
): string {
  return t(`state.${state}`);
}

export function matchStatusLabel(status: MatchStatus): string {
  return t(`match.${status}`);
}
