import type { Metadata } from "next";
import { DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { matchStatusLabel } from "@/lib/format";
import { createTranslator, type Locale } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";
import type { CupMatch } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("cup.title") };
}

function BracketMatch({ match, locale }: { match: CupMatch; locale: Locale }) {
  return (
    <article className="bracket-match">
      <div className="bracket-match__head">
        <span>{match.label}</span>
        <Pill
          tone={
            match.status === "final"
              ? "lime"
              : match.status === "provisional"
                ? "warning"
                : "neutral"
          }
        >
          {matchStatusLabel(match.status, locale)}
        </Pill>
      </div>
      {[
        { slot: "home", side: match.home },
        { slot: "away", side: match.away }
      ].map(({ slot, side }) => (
        <div
          className="bracket-side"
          data-winner={side.isWinner}
          key={`${match.id}-${slot}-${side.managerId}`}
        >
          <span>
            <strong>{side.teamName}</strong>
            <small>{side.managerName}</small>
          </span>
          <b>{side.score ?? "—"}</b>
        </div>
      ))}
      {match.decidedBy && <div className="bracket-match__decision">{match.decidedBy}</div>}
    </article>
  );
}

export default async function CupPage({
  searchParams
}: {
  searchParams: Promise<{ season?: string }>;
}) {
  const locale = await getLocale();
  const t = createTranslator(locale);
  const params = await searchParams;
  const season = params.season === "2" ? 2 : 1;
  const result = await vmfApi.cup(season);
  const cup = result.data;

  return (
    <>
      <PageHeader
        eyebrow={t("cup.eyebrow")}
        title={cup.title}
        description={t("cup.description", {
          window: season === 2 ? t("cup.window2") : t("cup.window1")
        })}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
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
      <div className="bracket-shell">
        <div className="bracket">
          {cup.rounds.map((round) => (
            <section className="bracket-round" key={round.id}>
              <header>
                <span>{round.gameweek}</span>
                <h2>{round.name}</h2>
              </header>
              <div className="bracket-round__matches">
                {round.matches.map((match) => (
                  <BracketMatch match={match} locale={locale} key={match.id} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
      {cup.thirdPlace && (
        <section className="third-place">
          <div>
            <p className="eyebrow">{t("cup.honours")}</p>
            <h2>{t("cup.thirdPlace")}</h2>
            <p>{t("cup.thirdPlaceBody")}</p>
          </div>
          <div className="third-place__match">
            <BracketMatch match={cup.thirdPlace} locale={locale} />
          </div>
        </section>
      )}
    </>
  );
}
