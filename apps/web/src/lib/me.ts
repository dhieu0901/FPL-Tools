import { cookies } from "next/headers";

/**
 * Which of the 46 managers is reading.
 *
 * The league is one shared page for everyone, which means every manager has to
 * hunt through 23 fixtures to find the only one they care about. Remembering
 * who they are costs one cookie and turns the site from a league noticeboard
 * into their own scoreboard. It is a preference, not an identity: it grants
 * nothing, so there is nothing to protect.
 */

export const MANAGER_COOKIE = "vmf_manager";

/** One year, so a manager chooses once a season. */
export const MANAGER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export async function getMyManagerId(): Promise<string | null> {
  const store = await cookies();
  const value = store.get(MANAGER_COOKIE)?.value?.trim();
  return value && /^\d+$/.test(value) ? value : null;
}
