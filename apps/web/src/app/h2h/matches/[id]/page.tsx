import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Avatar, Callout, DataBadge, Pill } from "@/components/ui";
import { ApiRequestError, vmfApi } from "@/lib/api";
import { matchStatusLabel } from "@/lib/format";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("match.title") };
}

export default async function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const locale = await getLocale();
  const t = createTranslator(locale);
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
            {matchStatusLabel(match.status, locale)}
          </Pill>
        </div>
        <div className="match-scoreboard">
          <div className="match-side match-side--home">
            <Avatar name={match.home.managerName} size="large" />
            <div>
              <h1>{match.home.teamName}</h1>
              <p>{match.home.managerName}</p>
            </div>
          </div>
          <div className="match-score">
            <strong>{match.home.score ?? "–"}</strong>
            <span>:</span>
            <strong>{match.away.score ?? "–"}</strong>
          </div>
          <div className="match-side">
            <Avatar name={match.away.managerName} size="large" />
            <div>
              <h1>{match.away.teamName}</h1>
              <p>{match.away.managerName}</p>
            </div>
          </div>
        </div>
        <div className="live-context">
          <span>
            <small>{t("match.captain")}</small>
            <strong>{match.home.captain ?? "—"}</strong>
          </span>
          <span>
            <small>{t("match.playersLeft")}</small>
            <strong>
              {match.home.activePlayers === undefined || match.away.activePlayers === undefined
                ? "—"
                : `${match.home.activePlayers} : ${match.away.activePlayers}`}
            </strong>
          </span>
          <span>
            <small>{t("match.captain")}</small>
            <strong>{match.away.captain ?? "—"}</strong>
          </span>
        </div>
      </section>
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
