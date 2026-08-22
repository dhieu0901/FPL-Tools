import type { Metadata } from "next";
import { CaptainDonut } from "@/components/captain-donut";
import { DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { chipAbbreviation, chipName } from "@/lib/chips";
import { t } from "@/lib/i18n";
import type { StatsScope } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("nav.stats") };
}

const SCOPES: Array<{ scope: StatsScope; label: string }> = [
  { scope: "ALL", label: "stats.scopeAll" },
  { scope: "HIGH", label: "stats.scopeHigh" },
  { scope: "LOW", label: "stats.scopeLow" }
].map((item) => ({ scope: item.scope as StatsScope, label: t(item.label as never) }));

function readScope(value: string | undefined): StatsScope {
  return value === "HIGH" || value === "LOW" ? value : "ALL";
}

export default async function StatsPage({
  searchParams
}: {
  searchParams: Promise<{ division?: string }>;
}) {
  const params = await searchParams;
  const scope = readScope(params.division?.toUpperCase());
  const result = await vmfApi.stats(scope);
  const stats = result.data;

  // Chips are counted out of the managers in scope, not out of the squads
  // published: a chip is recorded with the score, and every manager has one.
  const chipBase = Math.max(stats.managers, 1);

  return (
    <>
      <PageHeader
        eyebrow={t("stats.eyebrow")}
        title={t("nav.stats")}
        description={t("stats.description", { gameweek: stats.gameweek })}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />

      <div className="toolbar-row">
        <SegmentedLinks
          items={SCOPES.map((item) => ({
            href: item.scope === "ALL" ? "/stats" : `/stats?division=${item.scope}`,
            label: item.label,
            active: item.scope === scope
          }))}
        />
        <p className="toolbar-note">
          {t("stats.pool", { managers: stats.managers, squads: stats.squadsKnown })}
        </p>
      </div>

      <div className="stats-grid">
        <section className="panel-card">
          <h2>{t("stats.captains")}</h2>
          <p className="panel-note">{t("stats.captainsNote")}</p>
          <CaptainDonut picks={stats.captains} total={stats.squadsKnown} />
        </section>

        <section className="panel-card">
          <h2>{t("stats.chips")}</h2>
          <p className="panel-note">{t("stats.chipsNote")}</p>
          <ul className="chip-bars">
            {stats.chips.map((chip) => {
              const share = chip.thisSeason / chipBase;
              return (
                <li key={chip.chip}>
                  <span className="chip-bars__name">
                    <em>{chipAbbreviation(chip.chip)}</em>
                    {chipName(chip.chip)}
                  </span>
                  <span className="chip-bars__track" aria-hidden="true">
                    <span style={{ width: `${Math.max(share * 100, share > 0 ? 2 : 0)}%` }} />
                  </span>
                  <span className="chip-bars__value">
                    {chip.thisSeason}
                    <small>{Math.round(share * 100)}%</small>
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </>
  );
}
