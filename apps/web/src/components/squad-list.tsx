import { ClubShirt } from "@/components/club-shirt";
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

/**
 * What is still to come, by position.
 *
 * The count alone does not say much: three defenders left and three forwards
 * left are very different positions to be in with a tie in the balance. Only
 * the eleven counts, because a bench player scores nothing unless a starter
 * fails to appear.
 */
function stillToPlay(squad: SquadSlot[]): { total: number; parts: string[] } {
  const waiting = squad.filter((slot) => slot.isStarter && slot.state === "upcoming");
  const byPosition = new Map<number, number>();
  for (const slot of waiting) {
    byPosition.set(slot.elementType, (byPosition.get(slot.elementType) ?? 0) + 1);
  }
  // Back to front, the way a squad is read.
  const parts = [1, 2, 3, 4]
    .filter((type) => byPosition.has(type))
    .map((type) => `${byPosition.get(type)} ${t(POSITION_KEY[type as 1 | 2 | 3 | 4])}`);
  return { total: waiting.length, parts };
}

function SquadRow({ slot }: { slot: SquadSlot }) {
  const badge = armband(slot);
  // Every row shows what the player actually scored, the way FPL prints it.
  // Multiplying first would report a benched player as zero, hiding the one
  // thing a manager most wants to see, and would double a captain's line so
  // that it no longer matched the number on FPL's own page. The armband and
  // the dimmed bench already say which of these count.
  const benched = slot.multiplier === 0;
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
        <span className="squad-row__player">{slot.name}</span>
        {badge && <em className="squad-row__armband">{badge}</em>}
        {slot.multiplier > 1 && <em className="squad-row__multiplier">×{slot.multiplier}</em>}
        {slot.fixturesTotal > 1 && (
          <em className="squad-row__double" title={t("squad.doubleGameweek")}>
            DGW
          </em>
        )}
      </span>
      {/* The shirt groups a squad by club at a glance; the code beside it is
          what separates the three clubs that play in plain red. */}
      <span className="squad-row__kit">
        <ClubShirt club={slot.club} size={17} />
        <span className="squad-row__club">{slot.club}</span>
      </span>
      <span
        className="squad-row__points"
        title={benched ? t("squad.benchNote", { points: slot.points }) : undefined}
      >
        {slot.points}
      </span>
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
  const played = starters.filter((slot) => slot.state !== "upcoming").length;
  const waiting = stillToPlay(squad);

  return (
    <div className="squad-list">
      <div className="squad-list__head">
        <h3>{title}</h3>
        {/* How far through the eleven this side is, as a bar rather than a
            second number to read. */}
        <span
          className="squad-list__progress"
          role="img"
          aria-label={t("squad.played", { played, total: starters.length })}
        >
          <span style={{ width: `${(played / Math.max(starters.length, 1)) * 100}%` }} />
        </span>
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

      <p className="squad-list__remaining" data-done={waiting.total === 0}>
        {waiting.total === 0 ? (
          t("squad.allPlayed")
        ) : (
          <>
            <strong>{t("squad.stillToPlay", { count: waiting.total })}</strong>
            <span>{waiting.parts.join(" + ")}</span>
          </>
        )}
      </p>
    </div>
  );
}
