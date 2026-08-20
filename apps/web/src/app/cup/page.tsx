import type { Metadata } from "next";
import { CupBracket } from "@/components/bracket";
import { DataBadge, EmptyState, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { layoutBracket } from "@/lib/bracket";
import { t } from "@/lib/i18n";
import type { CupQualificationEntry } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("cup.title") };
}

const ENTRY_ROUND_KEY = {
  1: "cup.entersQualifying1",
  2: "cup.entersQualifying2",
  3: "cup.entersRoundOf16"
} as const;

function QualificationTable({
  title,
  entries
}: {
  title: string;
  entries: CupQualificationEntry[];
}) {
  return (
    <div className="qualification-block">
      <h3>{title}</h3>
      <div className="table-scroll">
        <table className="data-table qualification-table">
          <thead>
            <tr>
              <th scope="col">{t("common.rank")}</th>
              <th scope="col">{t("common.team")}</th>
              <th scope="col">{t("cup.qualificationPoints")}</th>
              <th scope="col">{t("cup.entryRound")}</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.managerId} data-eliminated={entry.entersAtRound === null}>
                <td>{entry.rank}</td>
                <td>
                  <strong>{entry.teamName}</strong>
                  <small>{entry.managerName}</small>
                </td>
                <td>
                  {entry.points}
                  {entry.gameweeksExcluded.length > 0 && (
                    <em
                      className="qualification-table__excluded"
                      title={t("cup.excludedDetail", {
                        gameweeks: entry.gameweeksExcluded.join(", ")
                      })}
                    >
                      {t("cup.excludedCount", { count: entry.gameweeksExcluded.length })}
                    </em>
                  )}
                </td>
                <td>
                  {entry.entersAtRound === null
                    ? t("cup.notQualified")
                    : t(ENTRY_ROUND_KEY[entry.entersAtRound as 1 | 2 | 3])}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default async function CupPage({
  searchParams
}: {
  searchParams: Promise<{ season?: string }>;
}) {
  const params = await searchParams;
  const season = params.season === "2" ? 2 : 1;

  const [cupResult, qualificationResult] = await Promise.all([
    vmfApi.cup(season),
    // The table is the interesting half of the Cup until it is drawn, so a
    // failure there empties one panel rather than the page.
    vmfApi.cupQualification(season).catch(() => null)
  ]);
  const cup = cupResult.data;
  const qualification = qualificationResult?.data ?? null;
  const layout = layoutBracket(cup.rounds, cup.thirdPlace);

  return (
    <>
      <PageHeader
        eyebrow={t("cup.eyebrow")}
        title={cup.title}
        description={t("cup.description", { window: cup.qualificationWindow })}
        actions={<DataBadge source={cupResult.source} updatedAt={cupResult.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/cup?season=1", label: t("cup.season1"), active: season === 1 },
            { href: "/cup?season=2", label: t("cup.season2"), active: season === 2 }
          ]}
        />
        <span className="toolbar-note">{t("cup.netNote")}</span>
      </div>

      {cup.isDrawn ? (
        <section className="section-space">
          <p className="panel-note bracket-hint">{t("cup.bracketHint")}</p>
          <CupBracket layout={layout} />
        </section>
      ) : (
        <EmptyState
          icon="cup"
          title={t("cup.notDrawnTitle")}
          description={t("cup.notDrawnBody", { window: cup.qualificationWindow })}
        />
      )}

      {qualification && (
        <section className="section-space">
          <div className="section-heading">
            <p className="eyebrow">{t("cup.qualificationEyebrow")}</p>
            <h2>{t("cup.qualificationTitle")}</h2>
            <p>
              {qualification.isSettled
                ? t("cup.qualificationSettled", { gameweek: qualification.endGameweek })
                : t("cup.qualificationLive", { gameweek: qualification.endGameweek })}
            </p>
          </div>
          <div className="qualification-grid">
            <QualificationTable title={t("classic.divisionHigh")} entries={qualification.high} />
            <QualificationTable title={t("classic.divisionLow")} entries={qualification.low} />
          </div>
        </section>
      )}
    </>
  );
}
