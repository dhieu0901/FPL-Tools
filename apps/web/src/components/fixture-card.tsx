import Link from "next/link";
import { formatDateTime, matchStatusLabel } from "@/lib/format";
import type { H2HFixture } from "@/lib/types";
import { Icon } from "./icons";
import { Pill } from "./ui";

function Score({ fixture }: { fixture: H2HFixture }) {
  if (fixture.home.score === null || fixture.away.score === null) {
    return <span className="fixture-card__versus">VS</span>;
  }
  return (
    <span className="fixture-card__score">
      <strong>{fixture.home.score}</strong>
      <span>–</span>
      <strong>{fixture.away.score}</strong>
    </span>
  );
}

export function FixtureCard({ fixture }: { fixture: H2HFixture }) {
  const tone =
    fixture.status === "live" ? "coral" : fixture.status === "final" ? "lime" : "neutral";

  return (
    <Link href={`/h2h/matches/${fixture.id}`} className="fixture-card">
      <div className="fixture-card__meta">
        <span>
          GW{fixture.gameweek} · {fixture.group}
        </span>
        <Pill tone={tone}>{matchStatusLabel(fixture.status)}</Pill>
      </div>
      <div className="fixture-card__teams">
        <div className="fixture-team fixture-team--home">
          <strong>{fixture.home.teamName}</strong>
          <small>{fixture.home.managerName}</small>
        </div>
        <Score fixture={fixture} />
        <div className="fixture-team">
          <strong>{fixture.away.teamName}</strong>
          <small>{fixture.away.managerName}</small>
        </div>
      </div>
      <div className="fixture-card__footer">
        <span>
          <Icon name="clock" size={15} />
          {formatDateTime(fixture.kickoff)}
        </span>
        <span className="fixture-card__open">
          Chi tiết <Icon name="chevron" size={15} />
        </span>
      </div>
    </Link>
  );
}
