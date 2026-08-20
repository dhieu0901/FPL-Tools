"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { MANAGER_COOKIE, MANAGER_COOKIE_MAX_AGE } from "@/lib/me";

/**
 * Remember, or forget, which manager is reading.
 *
 * A server action keeps this working without client JavaScript and lets every
 * page stay server-rendered, which matters on a phone on stadium wifi.
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
