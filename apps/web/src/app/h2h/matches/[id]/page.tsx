import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChipLine } from "@/components/chip-line";
import { TeamLink } from "@/components/fpl-link";
import { SquadList } from "@/components/squad-list";
import { Avatar, Callout, DataBadge, Pill } from "@/components/ui";
import { ApiRequestError, vmfApi } from "@/lib/api";
import { matchStatusLabel } from "@/lib/format";
import { t } from "@/lib/i18n";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("match.title") };
}

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const result = await vmfApi.h2hMatch(id).catch((error: unknown) => {
    if (error instanceof ApiRequestError && error.status === 404) notFound();
    throw error;
  });
  const match = result.data;

  return (
    <>
      <div className="match-topbar">
        <Link href="/h2h/fixtures" className="back-link">
          <span>←</span> {t("match.back")}
        </Link>
        <DataBadge source={result.source} updatedAt={result.updatedAt} />
      </div>
      <section className="match-hero">
        <div className="match-hero__meta">
          <span>
            GW{match.gameweek} · {match.bracketLabel ?? t("h2h.groupLabel")}
          </span>
          <Pill tone={match.status === "live" ? "coral" : "neutral"}>
            {matchStatusLabel(match.status)}
          </Pill>
        </div>
        <div className="match-scoreboard">
          <div className="match-side match-side--home">
            <Avatar name={match.home.managerName} size="large" />
            <div>
              <h1>
                <TeamLink side={match.home} gameweek={match.gameweek} />
              </h1>
              <p>{match.home.managerName}</p>
            </div>
          </div>
          <div className="match-score">
            <strong>{match.home.score ?? "-"}</strong>
            <span>:</span>
            <strong>{match.away.score ?? "-"}</strong>
          </div>
          <div className="match-side">
            <Avatar name={match.away.managerName} size="large" />
            <div>
              <h1>
                <TeamLink side={match.away} gameweek={match.gameweek} />
              </h1>
              <p>{match.away.managerName}</p>
            </div>
          </div>
        </div>
        <div className="live-context">
          <span>
            <small>{t("match.chip")}</small>
            <strong>{match.homeDetail?.chipUsed ?? "-"}</strong>
          </span>
          <span>
            <small>{t("match.playersLeft")}</small>
            <strong>
              {match.homeDetail && match.awayDetail
                ? `${match.homeDetail.remaining.players} : ${match.awayDetail.remaining.players}`
                : "-"}
            </strong>
          </span>
          <span>
            <small>{t("match.chip")}</small>
            <strong>{match.awayDetail?.chipUsed ?? "-"}</strong>
          </span>
        </div>
      </section>

      {match.homeDetail && match.awayDetail && (
        <section className="squad-grid">
          {[
            { detail: match.homeDetail, side: "home" as const },
            { detail: match.awayDetail, side: "away" as const }
          ].map(({ detail, side }) => (
            <article className="panel-card" key={side}>
              <ChipLine chips={detail.chips} />
              <SquadList
                squad={detail.squad}
                title={t("match.squadOf", { team: detail.teamName })}
              />
              <footer className="squad-footer">
                <span>
                  <small>{t("match.remainingPlayers")}</small>
                  <strong>
                    {t("match.remainingDetail", {
                      players: detail.remaining.players,
                      fixtures: detail.remaining.fixtures,
                      effective: detail.remaining.effectivePlayers
                    })}
                  </strong>
                </span>
                <span>
                  <small>{t("match.benchPoints")}</small>
                  <strong>{detail.benchPoints ?? "-"}</strong>
                </span>
              </footer>
            </article>
          ))}
        </section>
      )}

      {(match.differentials.length > 0 || match.shared.length > 0) && (
        <div className="match-detail-grid">
          <section className="panel-card">
            <h2>{t("match.differentials")}</h2>
            <p className="panel-note">{t("match.differentialsNote")}</p>
            {match.differentials.length === 0 ? (
              <p className="panel-note">{t("match.noDifferentials")}</p>
            ) : (
              <ul className="differential-rows">
                {match.differentials.map((line) => (
                  <li key={line.elementId} data-side={line.netMultiplier > 0 ? "home" : "away"}>
                    <span className="differential-rows__name">
                      {line.name}
                      {(line.isHomeCaptain || line.isAwayCaptain) && (
                        <em className="squad-row__armband">(C)</em>
                      )}
                    </span>
                    <span className="differential-rows__multiplier">
                      {line.homeMultiplier}×:×{line.awayMultiplier}
                    </span>
                    <span className="differential-rows__swing">
                      {line.swingPoints > 0 ? `+${line.swingPoints}` : line.swingPoints}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="panel-card">
            <h2>{t("match.sharedPlayers")}</h2>
            <p className="panel-note">{t("match.sharedNote")}</p>
            <ul className="shared-rows">
              {match.shared.map((line) => (
                <li key={line.elementId}>
                  <span>{line.name}</span>
                  <span>{line.points}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
      <div className="match-detail-grid">
        <section className="panel-card">
          <h2>{t("match.breakdown")}</h2>
          <div className="score-breakdown">
            {match.scoreBreakdown.map((item) => (
              <div key={item.labelKey}>
                <strong>{item.home}</strong>
                <span>{t(item.labelKey)}</span>
                <strong>{item.away}</strong>
              </div>
            ))}
          </div>
        </section>
        <section className="panel-card">
          <h2>{t("match.timeline")}</h2>
          <div className="event-timeline">
            {match.events.map((event) => (
              <article key={`${event.time}-${event.title}`} data-tone={event.tone}>
                <span>{event.time}</span>
                <div>
                  <strong>{event.title}</strong>
                  <p>{event.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
      {match.ruleNote && (
        <Callout title={t("match.resultStatus")} icon="info">
          <p>
            {match.ruleNote.kind === "walkover"
              ? t("match.walkoverNote", { reason: match.ruleNote.reason })
              : match.ruleNote.kind === "settled"
                ? t("match.settledNote")
                : t("match.provisionalNote")}
          </p>
        </Callout>
      )}
    </>
  );
}
