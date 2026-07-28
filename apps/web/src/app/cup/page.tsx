import type { Metadata } from "next";
import { DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { matchStatusLabel } from "@/lib/format";
import { vmfApi } from "@/lib/api";
import type { CupMatch } from "@/lib/types";

export const metadata: Metadata = { title: "VMF Cup" };

function BracketMatch({ match }: { match: CupMatch }) {
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
          {matchStatusLabel(match.status)}
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
  const params = await searchParams;
  const season = params.season === "2" ? 2 : 1;
  const result = await vmfApi.cup(season);
  const cup = result.data;

  return (
    <>
      <PageHeader
        eyebrow="Knock-out"
        title={cup.title}
        description={`${cup.qualificationWindow}. Mọi GW vi phạm đóng góp 0 điểm vào bảng xét suất Cup.`}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/cup?season=1", label: "Season 1", active: season === 1 },
            { href: "/cup?season=2", label: "Season 2", active: season === 2 }
          ]}
        />
        <span className="toolbar-note">Cập nhật theo điểm net</span>
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
                  <BracketMatch match={match} key={match.id} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
      {cup.thirdPlace && (
        <section className="third-place">
          <div>
            <p className="eyebrow">Vị trí danh dự</p>
            <h2>Trận tranh hạng ba</h2>
            <p>Cup có trận tranh hạng ba riêng ở vòng đấu cuối.</p>
          </div>
          <div className="third-place__match">
            <BracketMatch match={cup.thirdPlace} />
          </div>
        </section>
      )}
    </>
  );
}
