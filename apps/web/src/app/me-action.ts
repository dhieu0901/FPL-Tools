"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { MANAGER_COOKIE, MANAGER_COOKIE_MAX_AGE } from "@/lib/me";

/**
 * Remember, or forget, which manager is reading.
 *
 * This is the fallback path, taken when the form is submitted before the
 * picker has hydrated. Once it has, the picker writes the cookie itself and
 * refreshes the router, which is far quicker.
 *
 * The revalidate below is heavier than the change deserves: it throws away
 * the cached upstream responses for every page under the layout, so the next
 * render rebuilds the dashboard from six API calls. That is the price of a
 * full page POST with no client to update, and it is only paid on this path.
 */
export async function setMyManager(formData: FormData): Promise<void> {
  const requested = String(formData.get("manager_id") ?? "").trim();
  const store = await cookies();

  if (!requested || !/^\d+$/.test(requested)) {
    store.delete(MANAGER_COOKIE);
  } else {
    store.set(MANAGER_COOKIE, requested, {
      path: "/",
      maxAge: MANAGER_COOKIE_MAX_AGE,
      sameSite: "lax",
      httpOnly: false
    });
  }

  revalidatePath("/", "layout");
}
