import type { Metadata } from "next";
import { StandingsTable } from "@/components/standings-table";
import { Callout, DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import type { Division } from "@/lib/types";

export const metadata: Metadata = { title: "Bảng Classic" };

export default async function ClassicPage({
  searchParams
}: {
  searchParams: Promise<{ division?: string }>;
}) {
  const params = await searchParams;
  const division: Division = params.division === "low" ? "LOW" : "HIGH";
  const result = await vmfApi.classicStandings();
  const entries = result.data.filter((entry) => entry.division === division);

  return (
    <>
      <PageHeader
        eyebrow="Classic League"
        title="Bảng xếp hạng"
        description="Xếp hạng theo tổng điểm FPL net. Màu cạnh thứ hạng thể hiện vùng thành tích, suất Cup và xuống hạng."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            {
              href: "/classic?division=high",
              label: "Division HIGH",
              active: division === "HIGH"
            },
            {
              href: "/classic?division=low",
              label: "Division LOW",
              active: division === "LOW"
            }
          ]}
        />
        <span className="toolbar-note">{entries.length} đội đang hiển thị</span>
      </div>
      <StandingsTable entries={entries} />
      <div className="legend-row">
        <span data-color="lime">Đua vô địch</span>
        <span data-color="blue">Championship</span>
        <span data-color="violet">Suất Cup / Play-off</span>
        <span data-color="danger">Xuống hạng</span>
      </div>
      <Callout title="Nguyên tắc xếp hạng" icon="info">
        <p>
          Khi bằng tổng điểm: số lần TotW → điểm GW cao nhất → quyết định có audit log của ban tổ
          chức.
        </p>
      </Callout>
    </>
  );
}
