"use server";

import { revalidatePath } from "next/cache";
import { vmfApi, type ViolationReviewAction } from "@/lib/api";

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

  if (!/^\d+$/.test(violationId)) throw new Error("Violation ID không hợp lệ.");
  if (!ALLOWED_ACTIONS.has(action)) throw new Error("Review action không hợp lệ.");
  if (!note || note.length > 2000) {
    throw new Error("Ghi chú review phải có từ 1 đến 2000 ký tự.");
  }

  await vmfApi.reviewViolation(violationId, action, note);
  revalidatePath("/admin");
  revalidatePath("/admin/violations");
}
