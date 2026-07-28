import type { Metadata } from "next";
import { StandingsTable } from "@/components/standings-table";
import { Callout, DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import type { Division } from "@/lib/types";

export const metadata: Metadata = { title: "Bảng Classic" };

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
        title="Bảng xếp hạng"
        description="Xếp hạng theo tổng điểm FPL net của đúng giai đoạn và division đã chọn."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            {
              href: `/classic?division=high&period=${period}`,
              label: "Division HIGH",
              active: division === "HIGH"
            },
            {
              href: `/classic?division=low&period=${period}`,
              label: "Division LOW",
              active: division === "LOW"
            }
          ]}
        />
        <span className="toolbar-note">{entries.length} đội đang hiển thị</span>
      </div>
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            {
              href: `/classic?division=${divisionSlug}&period=season_1`,
              label: "Season 1 · GW1–19",
              active: period === "season_1"
            },
            {
              href: `/classic?division=${divisionSlug}&period=season_2`,
              label: "Season 2 · GW20–38",
              active: period === "season_2"
            },
            {
              href: `/classic?division=${divisionSlug}&period=full`,
              label: "Cả mùa",
              active: period === "full"
            }
          ]}
        />
      </div>
      <StandingsTable entries={entries} />
      <Callout title="Nguyên tắc xếp hạng" icon="info">
        <p>
          Khi bằng tổng điểm: số lần TotW → điểm GW cao nhất → quyết định có audit log của ban tổ
          chức.
        </p>
      </Callout>
    </>
  );
}
