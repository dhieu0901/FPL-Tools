"use server";

import { cookies } from "next/headers";
import { revalidatePath } from "next/cache";
import { isLocale, LOCALE_COOKIE, LOCALE_COOKIE_MAX_AGE } from "@/lib/i18n";

/**
 * Store the reader's language server-side.
 *
 * A server action keeps the switcher working without client JavaScript and
 * lets every page stay server-rendered in the chosen language.
 */
export async function setLocale(formData: FormData): Promise<void> {
  const requested = String(formData.get("locale") ?? "");
  if (!isLocale(requested)) return;

  const store = await cookies();
  store.set(LOCALE_COOKIE, requested, {
    path: "/",
    maxAge: LOCALE_COOKIE_MAX_AGE,
    sameSite: "lax",
    httpOnly: false
  });
  revalidatePath("/", "layout");
}
