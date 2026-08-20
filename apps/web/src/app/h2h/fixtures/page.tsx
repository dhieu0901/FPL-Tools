import type { Metadata } from "next";
import { FixtureCard } from "@/components/fixture-card";
import { DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { t } from "@/lib/i18n";
import { getMyManagerId } from "@/lib/me";
import type { H2HFixture } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("fixtures.title") };
}

function isMine(fixture: H2HFixture, managerId: string): boolean {
  return fixture.home.managerId === managerId || fixture.away.managerId === managerId;
}

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

  const [result, myManagerId] = await Promise.all([vmfApi.h2hFixtures(gameweek), getMyManagerId()]);

  // Twenty-three ties is a long scroll to find the one you are in, so yours
  // comes first and the rest keep the order the schedule gave them.
  const mine = myManagerId ? result.data.filter((fixture) => isMine(fixture, myManagerId)) : [];
  const others = myManagerId
    ? result.data.filter((fixture) => !isMine(fixture, myManagerId))
    : result.data;

  return (
    <>
      <PageHeader
        eyebrow="Head to Head"
        title={t("fixtures.heading")}
        description={t("fixtures.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/h2h", label: t("h2h.standings") },
            { href: "/h2h/fixtures", label: t("h2h.fixtures"), active: true }
          ]}
        />
        <form method="get" className="compact-select">
          <label htmlFor="gameweek">{t("fixtures.gameweek")}</label>
          <select id="gameweek" name="gameweek" defaultValue={String(gameweek)}>
            {Array.from({ length: 38 }, (_, index) => index + 1).map((number) => (
              <option value={number} key={number}>
                GW{number}
              </option>
            ))}
          </select>
          <button type="submit" className="secondary-button">
            {t("fixtures.apply")}
          </button>
        </form>
      </div>

      {mine.length > 0 && (
        <section className="fixtures-mine">
          <h2 className="fixtures-mine__heading">{t("fixtures.yours")}</h2>
          <div className="fixtures-grid">
            {mine.map((fixture) => (
              <FixtureCard fixture={fixture} highlighted key={fixture.id} />
            ))}
          </div>
        </section>
      )}

      {others.length > 0 && (
        <section className={mine.length > 0 ? "section-space" : undefined}>
          {mine.length > 0 && (
            <h2 className="fixtures-mine__heading">{t("fixtures.everyoneElse")}</h2>
          )}
          <div className="fixtures-grid">
            {others.map((fixture) => (
              <FixtureCard fixture={fixture} key={fixture.id} />
            ))}
          </div>
        </section>
      )}

      {result.data.length === 0 && (
        <p className="toolbar-note">{t("fixtures.empty", { gameweek })}</p>
      )}
    </>
  );
}
