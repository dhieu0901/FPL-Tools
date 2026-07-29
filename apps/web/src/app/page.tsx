import type { Metadata } from "next";
import Link from "next/link";
import { FixtureCard } from "@/components/fixture-card";
import { Icon } from "@/components/icons";
import { StandingsTable } from "@/components/standings-table";
import { DataBadge, EmptyState, Pill, SectionHeader } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { formatDateTime, gameweekStateLabel } from "@/lib/format";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("dashboard.title") };
}

export default async function DashboardPage() {
  const locale = await getLocale();
  const t = createTranslator(locale);
  const result = await vmfApi.dashboard();
  const { data } = result;

  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-hero__copy">
          <div className="hero-meta">
            <Pill tone="lime">
              {t("common.season")} {data.season}
            </Pill>
            <DataBadge source={result.source} updatedAt={result.updatedAt} />
          </div>
          <p className="eyebrow">{t("dashboard.eyebrow")}</p>
          <h1>
            {t("dashboard.headline1")}
            <br />
            <span>{t("dashboard.headline2")}</span>
          </h1>
          <p>{t("dashboard.lede")}</p>
          <div className="hero-actions">
            <Link href="/classic" className="primary-button">
              {t("dashboard.viewStandings")} <Icon name="arrow" size={18} />
            </Link>
            <Link href="/h2h/fixtures" className="secondary-button">
              {t("dashboard.fixtures")}
            </Link>
          </div>
        </div>
        <div className="gameweek-card">
          <div className="gameweek-card__topline">
            <span>{data.gameweek.name}</span>
            <Pill tone={data.gameweek.state === "live" ? "coral" : "blue"}>
              {gameweekStateLabel(data.gameweek.state, locale)}
            </Pill>
          </div>
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
          <div className="gameweek-progress">
            <span>
              <small>{t("dashboard.completed")}</small>
              <strong>
                {data.gameweek.fixturesComplete}/{data.gameweek.fixturesTotal}{" "}
                {t("dashboard.matchesShort")}
              </strong>
            </span>
            <span>
              <small>{t("dashboard.deadline")}</small>
              <strong>
                {data.gameweek.deadline
                  ? formatDateTime(data.gameweek.deadline, locale)
                  : t("dashboard.deadlineUnknown")}
              </strong>
            </span>
          </div>
          <div className="gameweek-card__grid" aria-hidden="true" />
        </div>
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

      <section className="dashboard-grid section-space">
        <div>
          <SectionHeader
            eyebrow={t("dashboard.spotlightEyebrow")}
            title={t("dashboard.spotlightTitle")}
            href="/h2h/fixtures"
            linkLabel={t("dashboard.allMatches")}
          />
          {data.featuredFixture ? (
            <FixtureCard fixture={data.featuredFixture} />
          ) : (
            <EmptyState
              icon="calendar"
              title={t("dashboard.noFixtureTitle")}
              description={t("dashboard.noFixtureBody")}
            />
          )}
        </div>
        <aside>
          <SectionHeader eyebrow={t("dashboard.organiser")} title={t("dashboard.notices")} />
          {data.notices.length > 0 ? (
            <div className="notice-stack">
              {data.notices.map((notice) => (
                <article className="notice-card" key={notice.id}>
                  <span className="notice-card__icon" data-priority={notice.priority}>
                    <Icon name={notice.priority === "important" ? "warning" : "info"} size={19} />
                  </span>
                  <div>
                    <strong>{notice.title}</strong>
                    <p>{notice.body}</p>
                    <time>{formatDateTime(notice.publishedAt, locale)}</time>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title={t("dashboard.noNoticeTitle")}
              description={t("dashboard.noNoticeBody")}
            />
          )}
        </aside>
      </section>

      <section className="section-space">
        <SectionHeader
          eyebrow={t("dashboard.classicEyebrow")}
          title={t("dashboard.classicTitle")}
          description={t("dashboard.classicBody")}
          href="/classic"
        />
        <StandingsTable entries={data.standings} compact />
      </section>

      <section className="section-space">
        <SectionHeader
          eyebrow={t("dashboard.momentsEyebrow")}
          title={t("dashboard.momentsTitle")}
          href="/highlights"
        />
        {data.recentHighlights.length > 0 ? (
          <div className="highlight-preview-grid">
            {data.recentHighlights.map((highlight, index) => (
              <article className="highlight-preview" data-featured={index === 0} key={highlight.id}>
                <span className="highlight-preview__number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="eyebrow">{highlight.eyebrow}</p>
                  <h3>{highlight.title}</h3>
                  <p>{highlight.description}</p>
                </div>
                {highlight.value && <strong>{highlight.value}</strong>}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            icon="highlight"
            title={t("dashboard.noHighlightTitle")}
            description={t("dashboard.noHighlightBody")}
          />
        )}
      </section>
    </>
  );
}
