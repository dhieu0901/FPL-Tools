import { ClubShirt } from "@/components/club-shirt";
import { formatKickoff } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { PlayerFixture, SquadSlot } from "@/lib/types";

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

function armband(slot: SquadSlot): string {
  if (slot.isCaptain) return "C";
  if (slot.isViceCaptain) return "V";
  return "";
}

/** "HUL (A)" - the club faced, and whether at home or away. */
function opponentLabel(fixture: PlayerFixture): string {
  const venue = fixture.isHome ? t("squad.home") : t("squad.away");
  return `${fixture.opponent ?? "?"} (${venue})`;
}

/**
 * Where a match has got to, in the fewest words that are still true.
 *
 * Before kick-off the only useful answer is when, so it gives the time. Once
 * it is running the minute is what a reader is watching. Once the whistle has
 * gone there is nothing left to wait for and it says so.
 */
function statusLabel(fixture: PlayerFixture): string {
  if (fixture.playedOut) return t("squad.statusDone", { minutes: fixture.minutes });
  if (fixture.started) return t("squad.statusLive", { minutes: fixture.minutes });
  return fixture.kickoff ? formatKickoff(fixture.kickoff) : t("squad.statusUnscheduled");
}

function fixtureState(fixture: PlayerFixture): "done" | "live" | "upcoming" {
  if (fixture.playedOut) return "done";
  return fixture.started ? "live" : "upcoming";
}

function SquadRow({ slot, benched }: { slot: SquadSlot; benched: boolean }) {
  const badge = armband(slot);
  const label = benched ? String(slot.benchOrder ?? t("squad.gk")) : position(slot);

  return (
    <tr
      className="squad-row"
      data-state={slot.state}
      data-benched={benched || undefined}
      data-armband={slot.isCaptain ? "captain" : slot.isViceCaptain ? "vice" : undefined}
    >
      <td className="squad-row__slot-cell">
        <span className="squad-row__slot">{label}</span>
      </td>
      <td className="squad-row__player-cell">
        {/* A keeper's kit is a different shirt, and putting him in the
            outfield one is the sort of thing a manager spots instantly. */}
        <ClubShirt club={slot.club} size={20} keeper={slot.elementType === 1} />
        <span className="squad-row__name">{slot.name}</span>
        {badge && (
          <em className="squad-row__armband" data-role={slot.isCaptain ? "captain" : "vice"}>
            {badge}
          </em>
        )}
        {slot.multiplier > 1 && <em className="squad-row__multiplier">×{slot.multiplier}</em>}
      </td>
      <td className="squad-row__fixtures">
        {/* A Double Gameweek is two matches, and hiding one of them would
            hide half the reason a player was picked. */}
        {slot.fixtures.length === 0 ? (
          slot.knowsFixtures ? (
            <span className="squad-chip" data-state="idle">
              {t("squad.noFixture")}
            </span>
          ) : null
        ) : (
          slot.fixtures.map((fixture) => (
            <span
              className="squad-chip"
              data-state={fixtureState(fixture)}
              key={`${fixture.opponent}-${fixture.kickoff}`}
            >
              {opponentLabel(fixture)}
            </span>
          ))
        )}
      </td>
      <td className="squad-row__status">
        {slot.fixtures.map((fixture) => (
          <span key={`${fixture.opponent}-${fixture.kickoff}`}>{statusLabel(fixture)}</span>
        ))}
      </td>
      <td className="squad-row__points">{slot.points}</td>
    </tr>
  );
}

/**
 * A manager's fifteen, with what each player still has to come.
 *
 * The two questions during a Gameweek are "who has played" and "who is left",
 * and neither is answerable from a name and a score alone: a zero means
 * nothing until you know whether it is final. So every row carries the club
 * faced and where the match has got to, and the reader never has to open FPL
 * in another tab to find out.
 */
export function SquadTable({ squad, title }: { squad: SquadSlot[]; title: string }) {
  if (squad.length === 0) {
    return (
      <div className="squad-table squad-table--empty">
        <h3>{title}</h3>
        <p>{t("squad.unavailable")}</p>
      </div>
    );
  }

  const starters = squad.filter((slot) => slot.isStarter);
  const bench = squad.filter((slot) => !slot.isStarter);
  const played = starters.filter((slot) => slot.state !== "upcoming").length;

  return (
    <div className="squad-table">
      <div className="squad-table__head">
        <h3>{title}</h3>
        <span
          className="squad-table__progress"
          role="img"
          aria-label={t("squad.played", { played, total: starters.length })}
        >
          <span style={{ width: `${(played / Math.max(starters.length, 1)) * 100}%` }} />
        </span>
      </div>

      <div className="squad-table__shell">
        <table>
          <thead>
            <tr>
              <th />
              <th>{t("squad.colPlayer")}</th>
              <th>{t("squad.colOpponent")}</th>
              <th>{t("squad.colStatus")}</th>
              <th className="squad-row__points">{t("squad.colPoints")}</th>
            </tr>
          </thead>
          <tbody>
            {starters.map((slot) => (
              <SquadRow slot={slot} benched={false} key={slot.elementId} />
            ))}
            {bench.length > 0 && (
              <tr className="squad-table__divider">
                <td colSpan={5}>{t("squad.benchHeading")}</td>
              </tr>
            )}
            {bench.map((slot) => (
              <SquadRow slot={slot} benched key={slot.elementId} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
