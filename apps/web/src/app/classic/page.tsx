import type { Metadata } from "next";
import { StandingsTable } from "@/components/standings-table";
import { Callout, DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { Division } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("classic.title") };
}

export default async function ClassicPage({
  searchParams
}: {
  searchParams: Promise<{ division?: string; period?: string }>;
}) {
  const params = await searchParams;
  const division: Division = params.division === "low" ? "LOW" : "HIGH";
  const period =
    params.period === "season_2" || params.period === "full" ? params.period : "season_1";
  const divisionSlug = division.toLowerCase();
  const result = await vmfApi.classicStandings(division, period);
  const entries = result.data;

  return (
    <>
      <PageHeader
        eyebrow="Classic League"
        title={t("classic.heading")}
        description={t("classic.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            {
              href: `/classic?division=high&period=${period}`,
              label: t("classic.divisionHigh"),
              active: division === "HIGH"
            },
            {
              href: `/classic?division=low&period=${period}`,
              label: t("classic.divisionLow"),
              active: division === "LOW"
            }
          ]}
        />
        <span className="toolbar-note">{t("classic.teamsShown", { count: entries.length })}</span>
      </div>
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            {
              href: `/classic?division=${divisionSlug}&period=season_1`,
              label: t("classic.season1"),
              active: period === "season_1"
            },
            {
              href: `/classic?division=${divisionSlug}&period=season_2`,
              label: t("classic.season2"),
              active: period === "season_2"
            },
            {
              href: `/classic?division=${divisionSlug}&period=full`,
              label: t("classic.fullSeason"),
              active: period === "full"
            }
          ]}
        />
      </div>
      <StandingsTable entries={entries} />
      <Callout title={t("classic.tieBreakTitle")} icon="info">
        <p>{t("classic.tieBreakBody")}</p>
      </Callout>
    </>
  );
}
