import type { Metadata } from "next";
import { FixtureCard } from "@/components/fixture-card";
import { DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Lịch H2H" };

export default async function H2HFixturesPage({
  searchParams
}: {
  searchParams: Promise<{ gameweek?: string }>;
}) {
  const params = await searchParams;
  const parsedGameweek = Number(params.gameweek);
  const gameweek =
    Number.isInteger(parsedGameweek) && parsedGameweek >= 1 && parsedGameweek <= 38
      ? parsedGameweek
      : 1;
  const result = await vmfApi.h2hFixtures(gameweek);
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
        <form method="get" className="compact-select">
          <label htmlFor="gameweek">Vòng đấu</label>
          <select id="gameweek" name="gameweek" defaultValue={String(gameweek)}>
            {Array.from({ length: 38 }, (_, index) => index + 1).map((number) => (
              <option value={number} key={number}>
                GW{number}
              </option>
            ))}
          </select>
          <button type="submit" className="secondary-button">
            Xem
          </button>
        </form>
      </div>
      <div className="fixtures-grid">
        {result.data.map((fixture) => (
          <FixtureCard fixture={fixture} key={fixture.id} />
        ))}
      </div>
      {result.data.length === 0 && (
        <p className="toolbar-note">Chưa có trận H2H nào được xếp cho GW{gameweek}.</p>
      )}
    </>
  );
}
