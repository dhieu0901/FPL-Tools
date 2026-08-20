import type { Metadata } from "next";
import Link from "next/link";
import { DeadlineCountdown } from "@/components/deadline-countdown";
import { FixtureCard } from "@/components/fixture-card";
import { Icon } from "@/components/icons";
import { LiveIndicator, LiveRefresh } from "@/components/live-refresh";
import { StandingsTable } from "@/components/standings-table";
import { TeamPicker } from "@/components/team-picker";
import { DataBadge, EmptyState, Pill, SectionHeader } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { gameweekStateLabel } from "@/lib/format";
import { highlightCopy } from "@/lib/highlight-text";
import { t } from "@/lib/i18n";
import { getMyManagerId } from "@/lib/me";
import type { H2HFixture, StandingEntry } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("dashboard.title") };
}

function findMyFixture(fixtures: H2HFixture[], managerId: string | null): H2HFixture | null {
  if (!managerId) return null;
  return (
    fixtures.find(
      (fixture) => fixture.home.managerId === managerId || fixture.away.managerId === managerId
    ) ?? null
  );
}

function MyStanding({ entry }: { entry: StandingEntry }) {
  return (
    <div className="my-standing">
      <span>
        <small>{t("common.rank")}</small>
        <strong>{entry.rank}</strong>
      </span>
      <span>
        <small>{t("common.total")}</small>
        <strong>{entry.totalPoints}</strong>
      </span>
      <span>
        <small>{t("dashboard.totw")}</small>
        <strong>{entry.totw}</strong>
      </span>
      <Pill tone="blue">{entry.division}</Pill>
    </div>
  );
}

export default async function DashboardPage() {
  const [result, myManagerId] = await Promise.all([vmfApi.dashboard(), getMyManagerId()]);
  const { data } = result;

  const myFixture = findMyFixture(data.fixtures, myManagerId);
  const myManager = data.managers.find((manager) => manager.id === myManagerId) ?? null;
  const myStanding = data.standings.find((entry) => entry.managerId === myManagerId) ?? null;
  const hasStarted = data.gameweek.state !== "preseason" && data.gameweek.number > 0;

  // Before anyone has played, a table of zeros reads as a broken page rather
  // than as a season that has not begun, so the dashboard says so instead.
  const anyPointsScored = data.standings.some((entry) => entry.totalPoints !== 0);

  return (
    <LiveRefresh live={data.gameweek.state === "live"}>
      <section className="dashboard-hero">
        <div className="dashboard-hero__copy">
          <div className="hero-meta">
            <Pill tone="lime">
              {t("common.season")} {data.season}
            </Pill>
            <Pill tone={data.gameweek.state === "live" ? "coral" : "blue"}>
              {data.gameweek.name} · {gameweekStateLabel(data.gameweek.state)}
            </Pill>
            <DataBadge source={result.source} updatedAt={result.updatedAt} />
            <LiveIndicator />
          </div>

          {myManager ? (
            <>
              <p className="eyebrow">{t("dashboard.welcome")}</p>
              <h1>{myManager.teamName}</h1>
              {myStanding ? (
                <MyStanding entry={myStanding} />
              ) : (
                <p>{t("dashboard.noStandingYet")}</p>
              )}
            </>
          ) : (
            <>
              <p className="eyebrow">{t("dashboard.eyebrow")}</p>
              <h1>
                {t("dashboard.headline1")}
                <br />
                <span>{t("dashboard.headline2")}</span>
              </h1>
              <p>{t("dashboard.pickPrompt")}</p>
            </>
          )}

          <TeamPicker managers={data.managers} selectedId={myManagerId} />

          <div className="hero-actions">
            <Link href="/h2h/fixtures" className="primary-button">
              {t("dashboard.fixtures")} <Icon name="arrow" size={18} />
            </Link>
            <Link href="/classic" className="secondary-button">
              {t("dashboard.viewStandings")}
            </Link>
          </div>
        </div>

        <div className="gameweek-card">
          <div className="gameweek-card__topline">
            <span>{data.gameweek.name}</span>
            <Pill tone={data.gameweek.state === "live" ? "coral" : "blue"}>
              {gameweekStateLabel(data.gameweek.state)}
            </Pill>
          </div>

          {data.gameweek.deadline && !hasStarted ? (
            <DeadlineCountdown deadline={data.gameweek.deadline} />
          ) : (
            <div className="gameweek-orbit" aria-hidden="true">
              <svg viewBox="0 0 180 180">
                <title>{t("dashboard.gameweekProgress")}</title>
                <circle cx="90" cy="90" r="76" className="orbit-track" />
                <circle
                  cx="90"
                  cy="90"
                  r="76"
                  className="orbit-value"
                  pathLength="100"
                  strokeDasharray={`${data.gameweek.progress} 100`}
                />
              </svg>
              <span>
                <strong>{data.gameweek.number}</strong>
                <small>GW</small>
              </span>
            </div>
          )}

          <div className="gameweek-progress">
            <span>
              <small>{t("dashboard.completed")}</small>
              <strong>
                {data.gameweek.fixturesComplete}/{data.gameweek.fixturesTotal}{" "}
                {t("dashboard.matchesShort")}
              </strong>
            </span>
            <span>
              <small>{t("dashboard.h2hThisWeek")}</small>
              <strong>{data.fixtures.length}</strong>
            </span>
          </div>
          <div className="gameweek-card__grid" aria-hidden="true" />
        </div>
      </section>

      <section className="section-space">
        <SectionHeader
          eyebrow={myFixture ? t("dashboard.yourMatchEyebrow") : t("dashboard.spotlightEyebrow")}
          title={myFixture ? t("dashboard.yourMatchTitle") : t("dashboard.spotlightTitle")}
          href="/h2h/fixtures"
          linkLabel={t("dashboard.allMatches")}
        />
        {myFixture ? (
          <FixtureCard fixture={myFixture} highlighted />
        ) : data.fixtures.length > 0 ? (
          <>
            {!myManagerId && <p className="panel-note">{t("dashboard.pickToSeeYours")}</p>}
            <FixtureCard fixture={data.fixtures[0]} />
          </>
        ) : (
          <EmptyState
            icon="calendar"
            title={t("dashboard.noFixtureTitle")}
            description={t("dashboard.noFixtureBody")}
          />
        )}
      </section>

      <section className="metrics-grid" aria-label={t("dashboard.quickMetrics")}>
        {data.metrics.map((metric) => (
          <article className="metric-card" data-tone={metric.tone} key={metric.labelKey}>
            <span>{t(metric.labelKey)}</span>
            <strong>{metric.value}</strong>
            <small>{t(metric.detailKey, metric.detailVars)}</small>
          </article>
        ))}
      </section>

      <section className="section-space">
        <SectionHeader
          eyebrow={t("dashboard.classicEyebrow")}
          title={t("dashboard.classicTitle")}
          description={
            anyPointsScored ? t("dashboard.classicBody") : t("dashboard.classicNotStarted")
          }
          href="/classic"
        />
        <StandingsTable entries={data.standings} compact />
      </section>

      {data.recentHighlights.length > 0 && (
        <section className="section-space">
          <SectionHeader
            eyebrow={t("dashboard.momentsEyebrow")}
            title={t("dashboard.momentsTitle")}
            href="/highlights"
          />
          <div className="highlight-preview-grid">
            {data.recentHighlights.map((highlight, index) => {
              const copy = highlightCopy(highlight, t);
              return (
                <article
                  className="highlight-preview"
                  data-featured={index === 0}
                  key={highlight.id}
                >
                  <span className="highlight-preview__number">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p className="eyebrow">{copy.eyebrow}</p>
                    <h3>{copy.title}</h3>
                    <p>{copy.body}</p>
                  </div>
                  <strong>{copy.value}</strong>
                </article>
              );
            })}
          </div>
        </section>
      )}
    </LiveRefresh>
  );
}
