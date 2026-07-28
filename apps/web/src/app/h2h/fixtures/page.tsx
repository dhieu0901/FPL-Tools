import type { Metadata } from "next";
import { FixtureCard } from "@/components/fixture-card";
import { DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Lịch H2H" };

export default async function H2HFixturesPage() {
  const result = await vmfApi.h2hFixtures();
  return (
    <>
      <PageHeader
        eyebrow="Head to Head"
        title="Lịch & kết quả"
        description="Điểm live có thể thay đổi cho tới khi gameweek được finalize."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/h2h", label: "Bảng xếp hạng" },
            { href: "/h2h/fixtures", label: "Lịch & kết quả", active: true }
          ]}
        />
        <label className="compact-select">
          <span>Vòng đấu</span>
          <select defaultValue="13" aria-label="Chọn vòng đấu">
            <option value="12">GW12</option>
            <option value="13">GW13</option>
            <option value="14">GW14</option>
          </select>
        </label>
      </div>
      <div className="fixtures-grid">
        {result.data.map((fixture) => (
          <FixtureCard fixture={fixture} key={fixture.id} />
        ))}
      </div>
    </>
  );
}
