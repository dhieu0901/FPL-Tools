import { cookies } from "next/headers";
import { isManagerId, MANAGER_COOKIE, MANAGER_COOKIE_MAX_AGE } from "./me-cookie";

/**
 * Which of the 46 managers is reading.
 *
 * The league is one shared page for everyone, which means every manager has to
 * hunt through 23 fixtures to find the only one they care about. Remembering
 * who they are costs one cookie and turns the site from a league noticeboard
 * into their own scoreboard. It is a preference, not an identity: it grants
 * nothing, so there is nothing to protect.
 */

export { MANAGER_COOKIE, MANAGER_COOKIE_MAX_AGE };

export async function getMyManagerId(): Promise<string | null> {
  const store = await cookies();
  const value = store.get(MANAGER_COOKIE)?.value?.trim();
  return value && isManagerId(value) ? value : null;
}
