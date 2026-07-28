const vietnameseNumber = new Intl.NumberFormat("vi-VN");
const vietnameseDate = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric"
});
const vietnameseDateTime = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "Asia/Bangkok"
});

export function formatNumber(value: number): string {
  return vietnameseNumber.format(value);
}

export function formatDate(value: string): string {
  return vietnameseDate.format(new Date(value));
}

export function formatDateTime(value: string): string {
  return vietnameseDateTime.format(new Date(value));
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
  return {
    preseason: "Chưa bắt đầu",
    open: "Đang mở",
    live: "Đang diễn ra",
    provisional: "Tạm tính",
    final: "Đã chốt",
    walkover: "Xử thắng"
  }[state];
}

export function matchStatusLabel(status: import("./types").MatchStatus): string {
  return {
    scheduled: "Sắp diễn ra",
    live: "Trực tiếp",
    provisional: "Tạm tính",
    final: "Đã chốt",
    walkover: "Xử thắng"
  }[status];
}
