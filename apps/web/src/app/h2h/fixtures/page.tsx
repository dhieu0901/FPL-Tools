import type { Metadata } from "next";
import { FixtureCard } from "@/components/fixture-card";
import { DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("fixtures.title") };
}

export default async function H2HFixturesPage({
  searchParams
}: {
  searchParams: Promise<{ gameweek?: string }>;
}) {
  const t = createTranslator(await getLocale());
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
      <div className="fixtures-grid">
        {result.data.map((fixture) => (
          <FixtureCard fixture={fixture} key={fixture.id} />
        ))}
      </div>
      {result.data.length === 0 && (
        <p className="toolbar-note">{t("fixtures.empty", { gameweek })}</p>
      )}
    </>
  );
}
