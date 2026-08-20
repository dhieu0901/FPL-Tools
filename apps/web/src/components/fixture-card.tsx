"use client";

import Link from "next/link";
import { useState } from "react";
import { formatDateTime, matchStatusLabel } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { H2HFixture, MatchDetail } from "@/lib/types";
import { ChipLine } from "./chip-line";
import { TeamLink } from "./fpl-link";
import { Icon } from "./icons";
import { SquadList } from "./squad-list";
import { Pill } from "./ui";

type LoadState = "idle" | "loading" | "ready" | "failed";

function Score({ fixture }: { fixture: H2HFixture }) {
  if (fixture.home.score === null || fixture.away.score === null) {
    return <span className="fixture-card__versus">VS</span>;
  }
  return (
    <span className="fixture-card__score">
      <strong data-leading={fixture.home.score > fixture.away.score}>{fixture.home.score}</strong>
      <span>–</span>
      <strong data-leading={fixture.away.score > fixture.home.score}>{fixture.away.score}</strong>
    </span>
  );
}

/**
 * One head-to-head tie, with both squads a click away.
 *
 * The panel is fetched on the first expand rather than with the fixture list:
 * a Gameweek is twenty-three ties, and loading forty-six squads to render a
 * list nobody has opened yet would make the page slow for everyone.
 */
export function FixtureCard({
  fixture,
  highlighted = false
}: {
  fixture: H2HFixture;
  highlighted?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [state, setState] = useState<LoadState>("idle");
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const panelId = `fixture-squads-${fixture.id}`;

  const tone =
    fixture.status === "live" ? "coral" : fixture.status === "final" ? "lime" : "neutral";

  async function toggle() {
    const next = !expanded;
    setExpanded(next);
    if (!next || state === "loading" || state === "ready") return;

    setState("loading");
    try {
      const response = await fetch(`/api/matches/${fixture.id}`);
      if (!response.ok) throw new Error(String(response.status));
      const body = (await response.json()) as { data: MatchDetail };
      setDetail(body.data);
      setState("ready");
    } catch {
      setState("failed");
    }
  }

  return (
    <article className="fixture-card" data-expanded={expanded} data-mine={highlighted}>
      <div className="fixture-card__meta">
        <span>
          GW{fixture.gameweek} · {fixture.bracketLabel ?? t("h2h.groupLabel")}
        </span>
        <Pill tone={tone}>{matchStatusLabel(fixture.status)}</Pill>
      </div>

      <div className="fixture-card__teams">
        <div className="fixture-team fixture-team--home" data-winner={fixture.home.isWinner}>
          <TeamLink
            side={fixture.home}
            gameweek={fixture.gameweek}
            className="fixture-team__name"
          />
          <small>{fixture.home.managerName}</small>
        </div>
        <Score fixture={fixture} />
        <div className="fixture-team" data-winner={fixture.away.isWinner}>
          <TeamLink
            side={fixture.away}
            gameweek={fixture.gameweek}
            className="fixture-team__name"
          />
          <small>{fixture.away.managerName}</small>
        </div>
      </div>

      <div className="fixture-card__footer">
        <button
          type="button"
          className="fixture-card__toggle"
          onClick={toggle}
          aria-expanded={expanded}
          aria-controls={panelId}
        >
          <Icon name="chevron" size={16} />
          {expanded ? t("fixtures.hideSquads") : t("fixtures.showSquads")}
        </button>
        <Link href={`/h2h/matches/${fixture.id}`} className="fixture-card__open">
          {t("common.details")} <Icon name="arrow" size={15} />
        </Link>
      </div>

      {expanded && (
        <div className="fixture-card__panel" id={panelId}>
          {state === "loading" && <p className="panel-note">{t("fixtures.loadingSquads")}</p>}
          {state === "failed" && (
            <p className="panel-note" role="status">
              {t("fixtures.squadsUnavailable")}
            </p>
          )}
          {state === "ready" && detail && (
            <>
              <div className="fixture-card__squads">
                {[
                  { side: detail.homeDetail, fallback: fixture.home.teamName, key: "home" },
                  { side: detail.awayDetail, fallback: fixture.away.teamName, key: "away" }
                ].map(({ side, fallback, key }) => (
                  <div className="fixture-card__side" key={key}>
                    {side && <ChipLine chips={side.chips} />}
                    <SquadList squad={side?.squad ?? []} title={side?.teamName ?? fallback} />
                  </div>
                ))}
              </div>
              <p className="fixture-card__legend">
                <span data-state="upcoming" /> {t("squad.state.upcoming")}
                <span data-state="playing" /> {t("squad.state.playing")}
                <span data-state="finished" /> {t("squad.state.finished")}
              </p>
            </>
          )}
        </div>
      )}

      {fixture.kickoff && (
        <div className="fixture-card__kickoff">
          <Icon name="clock" size={15} />
          {formatDateTime(fixture.kickoff)}
        </div>
      )}
    </article>
  );
}
