/**
 * The "which manager am I" cookie, shared by the server and the browser.
 *
 * Kept apart from `me.ts` because that module reads `next/headers`, which a
 * client component cannot import. The value is a preference and grants
 * nothing, so the browser is allowed to write it directly.
 */

export const MANAGER_COOKIE = "vmf_manager";

/** One year, so a manager chooses once a season. */
export const MANAGER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export function isManagerId(value: string): boolean {
  return /^\d+$/.test(value);
}

/**
 * Record the choice from the browser, so the next server render sees it.
 *
 * Writing here rather than through the server action is what makes the
 * change feel immediate: the action revalidates the whole layout, which
 * throws away every cached API response and makes the page rebuild itself
 * from scratch. Nothing fetched actually depends on who is reading.
 */
export function rememberManager(managerId: string): void {
  const trimmed = managerId.trim();
  if (!trimmed || !isManagerId(trimmed)) {
    // biome-ignore lint/suspicious/noDocumentCookie: cookieStore is Chromium-only; Safari and Firefox are both in this project's browserslist.
    document.cookie = `${MANAGER_COOKIE}=; path=/; max-age=0; samesite=lax`;
    return;
  }
  // biome-ignore lint/suspicious/noDocumentCookie: cookieStore is Chromium-only; most of this league reads the site on an iPhone.
  document.cookie =
    `${MANAGER_COOKIE}=${encodeURIComponent(trimmed)}` +
    `; path=/; max-age=${MANAGER_COOKIE_MAX_AGE}; samesite=lax`;
}
