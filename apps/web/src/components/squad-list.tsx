import type { SquadSlot } from "@/lib/types";
import type { Translator } from "@/lib/i18n";

/** FPL element types, used only to label a row. */
const POSITION_KEY = {
  1: "squad.gk",
  2: "squad.def",
  3: "squad.mid",
  4: "squad.fwd"
} as const;

function positionLabel(slot: SquadSlot, t: Translator): string {
  const key = POSITION_KEY[slot.elementType as 1 | 2 | 3 | 4];
  return key ? t(key) : "—";
}

/**
 * The bench is named rather than numbered by squad position, because a manager
 * thinks in "second keeper, first sub" and not in "position 12".
 */
function benchLabel(slot: SquadSlot, t: Translator): string {
  if (slot.isSubstituteGoalkeeper) return t("squad.gkSub");
  return t("squad.bench", { order: slot.benchOrder ?? 0 });
}

function armband(slot: SquadSlot): string {
  if (slot.isCaptain) return "(C)";
  if (slot.isViceCaptain) return "(VC)";
  return "";
}

function SquadRow({ slot, t }: { slot: SquadSlot; t: Translator }) {
  const badge = armband(slot);
  return (
    <li
      className="squad-row"
      data-state={slot.state}
      data-armband={slot.isCaptain ? "captain" : slot.isViceCaptain ? "vice" : undefined}
      data-benched={slot.multiplier === 0 ? "true" : undefined}
    >
      <span className="squad-row__slot">
        {slot.isStarter ? positionLabel(slot, t) : benchLabel(slot, t)}
      </span>
      <span className="squad-row__name">
        {slot.name}
        {badge && <em className="squad-row__armband">{badge}</em>}
        {slot.multiplier > 1 && <em className="squad-row__multiplier">×{slot.multiplier}</em>}
        {slot.fixturesTotal > 1 && (
          <em className="squad-row__double" title={t("squad.doubleGameweek")}>
            DGW
          </em>
        )}
      </span>
      <span className="squad-row__points">{slot.contributionPoints}</span>
    </li>
  );
}

export function SquadList({
  squad,
  t,
  title
}: {
  squad: SquadSlot[];
  t: Translator;
  title: string;
}) {
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

  return (
    <div className="squad-list">
      <h3>{title}</h3>
      <ol className="squad-rows">
        {starters.map((slot) => (
          <SquadRow key={slot.elementId} slot={slot} t={t} />
        ))}
      </ol>
      {bench.length > 0 && (
        <>
          <p className="squad-list__divider">{t("squad.benchHeading")}</p>
          <ol className="squad-rows squad-rows--bench">
            {bench.map((slot) => (
              <SquadRow key={slot.elementId} slot={slot} t={t} />
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
