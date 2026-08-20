"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";
import { setMyManager } from "@/app/me-action";
import { t } from "@/lib/i18n";
import { rememberManager } from "@/lib/me-cookie";
import type { Manager } from "@/lib/types";

/**
 * Choose which manager you are, once.
 *
 * Rendered as a plain form with a submit button, so a choice made in the
 * second before hydration still posts to the server action rather than
 * silently doing nothing. (That window is the real case. A page this app
 * streams does not render usefully with JavaScript off at all, so the form
 * is a bridge, not a no-JS guarantee.)
 *
 * Once mounted it takes over. Choosing writes the cookie in the browser and
 * asks the router to re-render, which re-reads the page with the new reader
 * but keeps every cached API response. Going through the server action
 * instead would revalidate the whole layout and rebuild the dashboard from
 * six upstream calls, several seconds of waiting to highlight a different
 * row. Nothing the page fetches depends on who is reading.
 */
export function TeamPicker({
  managers,
  selectedId
}: {
  managers: Manager[];
  selectedId: string | null;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [choice, setChoice] = useState(selectedId ?? "");
  const [enhanced, setEnhanced] = useState(false);

  useEffect(() => setEnhanced(true), []);

  // A choice made in another tab, or a refresh, wins over stale local state.
  useEffect(() => setChoice(selectedId ?? ""), [selectedId]);

  const sorted = [...managers].sort((a, b) => a.teamName.localeCompare(b.teamName));

  function choose(next: string) {
    // The select shows the new value immediately; the page catches up behind.
    setChoice(next);
    rememberManager(next);
    startTransition(() => router.refresh());
  }

  return (
    <form action={setMyManager} className="team-picker" data-pending={pending || undefined}>
      <label htmlFor="vmf-manager">{t("me.label")}</label>
      <div className="team-picker__controls">
        <select
          id="vmf-manager"
          name="manager_id"
          value={enhanced ? choice : undefined}
          defaultValue={enhanced ? undefined : (selectedId ?? "")}
          onChange={(event) => choose(event.target.value)}
        >
          <option value="">{t("me.placeholder")}</option>
          {sorted.map((manager) => (
            <option value={manager.id} key={manager.id}>
              {manager.teamName} · {manager.name}
            </option>
          ))}
        </select>

        {enhanced ? (
          <span className="team-picker__status" role="status" aria-live="polite">
            {pending ? t("me.applying") : choice ? t("me.applied") : ""}
          </span>
        ) : (
          <button type="submit" className="secondary-button">
            {selectedId ? t("me.change") : t("me.save")}
          </button>
        )}
      </div>
    </form>
  );
}
