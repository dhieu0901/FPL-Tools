"use server";

import { revalidatePath } from "next/cache";
import { type ViolationReviewAction, vmfApi } from "@/lib/api";

const ALLOWED_ACTIONS = new Set<ViolationReviewAction>([
  "request_forgotten_chip_review",
  "approve_exception",
  "reject_exception",
  "confirm",
  "override"
]);

export async function reviewViolation(formData: FormData): Promise<void> {
  const violationId = String(formData.get("violation_id") ?? "").trim();
  const action = String(formData.get("action") ?? "") as ViolationReviewAction;
  const note = String(formData.get("note") ?? "").trim();

  if (!/^\d+$/.test(violationId)) throw new Error("That violation id is not valid.");
  if (!ALLOWED_ACTIONS.has(action)) throw new Error("That review action is not valid.");
  if (!note || note.length > 2000) {
    throw new Error("A review note of 1 to 2000 characters is required.");
  }

  await vmfApi.reviewViolation(violationId, action, note);
  revalidatePath("/admin");
  revalidatePath("/admin/violations");
}
