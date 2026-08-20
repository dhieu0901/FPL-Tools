import { t } from "@/lib/i18n";
import type { SquadSlot } from "@/lib/types";

/** FPL element types, used only to label a row. */
const POSITION_KEY = {
  1: "squad.gk",
  2: "squad.def",
  3: "squad.mid",
  4: "squad.fwd"
} as const;

function position(slot: SquadSlot): string {
  const key = POSITION_KEY[slot.elementType as 1 | 2 | 3 | 4];
  return key ? t(key) : "-";
}

/**
 * How the row is labelled: the position for the eleven and for the substitute
 * keeper, and the substitution order for the outfield bench. A reader scanning
 * the bench wants to know who comes on first, not what they play.
 */
function slotLabel(slot: SquadSlot): string {
  if (slot.isStarter || slot.isSubstituteGoalkeeper) return position(slot);
  return String(slot.benchOrder ?? 0);
}

function armband(slot: SquadSlot): string {
  if (slot.isCaptain) return "(C)";
  if (slot.isViceCaptain) return "(VC)";
  return "";
}

function SquadRow({ slot }: { slot: SquadSlot }) {
  const badge = armband(slot);
  return (
    <li
      className="squad-row"
      data-state={slot.state}
      data-armband={slot.isCaptain ? "captain" : slot.isViceCaptain ? "vice" : undefined}
      data-benched={slot.multiplier === 0 ? "true" : undefined}
    >
      {/* The state dot is what a reader actually scans for: who is still to
          play, who is on the pitch now, and who is finished for the week. */}
      <span
        className="squad-row__state"
        title={t(`squad.state.${slot.state}`)}
        aria-hidden="true"
      />
      <span className="squad-row__slot">{slotLabel(slot)}</span>
      <span className="squad-row__name">
        {slot.name}
        {slot.club && <span className="squad-row__club">({slot.club})</span>}
        {badge && <em className="squad-row__armband">{badge}</em>}
        {slot.multiplier > 1 && <em className="squad-row__multiplier">×{slot.multiplier}</em>}
        {slot.fixturesTotal > 1 && (
          <em className="squad-row__double" title={t("squad.doubleGameweek")}>
            DGW
          </em>
        )}
      </span>
      <span className="squad-row__points">: {slot.contributionPoints}</span>
    </li>
  );
}

export function SquadList({ squad, title }: { squad: SquadSlot[]; title: string }) {
  if (squad.length === 0) {
    return (
      <div className="squad-list squad-list--empty">
        <h3>{title}</h3>
        <p>{t("squad.unavailable")}</p>
      </div>
    );
  }

  const starters = squad.filter((slot) => slot.isStarter);
  const bench = squad.filter((slot) => !slot.isStarter);
  const yetToPlay = squad.filter((slot) => slot.isStarter && slot.state === "upcoming").length;

  return (
    <div className="squad-list">
      <div className="squad-list__head">
        <h3>{title}</h3>
        <span className="squad-list__count">{t("squad.yetToPlay", { count: yetToPlay })}</span>
      </div>
      <ol className="squad-rows">
        {starters.map((slot) => (
          <SquadRow key={slot.elementId} slot={slot} />
        ))}
      </ol>
      {bench.length > 0 && (
        <>
          <p className="squad-list__divider">{t("squad.benchHeading")}</p>
          <ol className="squad-rows squad-rows--bench">
            {bench.map((slot) => (
              <SquadRow key={slot.elementId} slot={slot} />
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
