import { setMyManager } from "@/app/me-action";
import { t } from "@/lib/i18n";
import type { Manager } from "@/lib/types";

/**
 * Choose which manager you are, once.
 *
 * Rendered as a plain form so it works before hydration; the select submits
 * itself when JavaScript is available, and the button covers when it is not.
 */
export function TeamPicker({
  managers,
  selectedId
}: {
  managers: Manager[];
  selectedId: string | null;
}) {
  const sorted = [...managers].sort((a, b) => a.teamName.localeCompare(b.teamName));

  return (
    <form action={setMyManager} className="team-picker">
      <label htmlFor="vmf-manager">{t("me.label")}</label>
      <div className="team-picker__controls">
        <select id="vmf-manager" name="manager_id" defaultValue={selectedId ?? ""}>
          <option value="">{t("me.placeholder")}</option>
          {sorted.map((manager) => (
            <option value={manager.id} key={manager.id}>
              {manager.teamName} · {manager.name}
            </option>
          ))}
        </select>
        <button type="submit" className="secondary-button">
          {selectedId ? t("me.change") : t("me.save")}
        </button>
      </div>
    </form>
  );
}
