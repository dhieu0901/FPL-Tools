import type { BracketLayout, BracketWing } from "@/lib/bracket";
import { matchStatusLabel } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { CupMatch, FixtureSide } from "@/lib/types";
import { TeamLink } from "./fpl-link";
import { Pill } from "./ui";

function tone(match: CupMatch) {
  if (match.status === "final") return "lime" as const;
  if (match.status === "live") return "coral" as const;
  if (match.status === "provisional") return "warning" as const;
  return "neutral" as const;
}

function BracketSide({
  side,
  slotLabel,
  gameweek,
  isWinner
}: {
  side: FixtureSide;
  slotLabel: string;
  gameweek: number;
  isWinner: boolean;
}) {
  // Before a place is filled, the bracket still says who will stand here —
  // "HIGH 11", "winner of Q1-3" — which is the whole point of drawing it early.
  const pending = side.managerId === "tbd";
  return (
    <div className="bracket-side" data-winner={isWinner} data-pending={pending}>
      {pending ? (
        <span className="bracket-side__slot">{slotLabel}</span>
      ) : (
        <span className="bracket-side__team">
          <TeamLink side={side} gameweek={gameweek} />
          <small>{side.managerName}</small>
        </span>
      )}
      <b>{side.score ?? "—"}</b>
    </div>
  );
}

export function BracketMatch({ match, gameweek }: { match: CupMatch; gameweek: number }) {
  return (
    <article className="bracket-match" data-status={match.status}>
      <div className="bracket-match__head">
        <span>{match.label}</span>
        <Pill tone={tone(match)}>{matchStatusLabel(match.status)}</Pill>
      </div>
      <BracketSide
        side={match.home}
        slotLabel={match.slotALabel}
        gameweek={gameweek}
        isWinner={Boolean(match.home.isWinner)}
      />
      <BracketSide
        side={match.away}
        slotLabel={match.slotBLabel}
        gameweek={gameweek}
        isWinner={Boolean(match.away.isWinner)}
      />
      {match.decidedBy && <div className="bracket-match__decision">{match.decidedBy}</div>}
    </article>
  );
}

function Wing({ wing, side }: { wing: BracketWing; side: "left" | "right" }) {
  // The right wing reads inwards too, so both sides funnel towards the centre.
  const rounds = side === "right" ? [...wing.rounds].reverse() : wing.rounds;
  return (
    <div className="bracket__wing" data-side={side}>
      {rounds.map((round) => (
        <section className="bracket-column" key={`${side}-${round.id}`}>
          <header className="bracket-column__head">
            <h3>{round.name}</h3>
            <span>GW{round.gameweek}</span>
          </header>
          <div className="bracket-column__ties">
            {round.matches.map((match) => (
              <div className="bracket-slot" key={match.id}>
                <BracketMatch match={match} gameweek={round.gameweek} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

/**
 * The whole Cup on one board: both halves running inwards to the final.
 *
 * On a narrow screen the wings unstack into a single column of rounds, since a
 * five-round-per-side board cannot be read on a phone however it is scaled.
 */
export function CupBracket({ layout }: { layout: BracketLayout }) {
  const finalGameweek = layout.finalRound?.gameweek ?? 0;

  return (
    <div className="bracket-scroll">
      <div className="bracket">
        <Wing wing={layout.left} side="left" />

        <div className="bracket__centre">
          {layout.thirdPlace && (
            <section className="bracket-centre-block bracket-centre-block--third">
              <h3>{t("cup.thirdPlace")}</h3>
              <BracketMatch match={layout.thirdPlace} gameweek={finalGameweek} />
            </section>
          )}
          {layout.final && (
            <section className="bracket-centre-block bracket-centre-block--final">
              <div className="bracket-trophy" aria-hidden="true">
                <svg viewBox="0 0 32 32">
                  <title>Trophy</title>
                  <path
                    d="M9 4h14v6a7 7 0 0 1-14 0V4Zm-4 1h4v3a4 4 0 0 1-4-4V5Zm18 0h4v-1a4 4 0 0 1-4 4V5ZM13 17h6l-1 5h2v3H12v-3h2l-1-5Z"
                    fill="currentColor"
                  />
                </svg>
              </div>
              <h3>{t("cup.final")}</h3>
              <span className="bracket-centre-block__gw">GW{finalGameweek}</span>
              <BracketMatch match={layout.final} gameweek={finalGameweek} />
            </section>
          )}
        </div>

        <Wing wing={layout.right} side="right" />
      </div>
    </div>
  );
}
