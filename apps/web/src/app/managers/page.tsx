import type { Metadata } from "next";
import { fplSeasonUrl } from "@/components/fpl-link";
import { Avatar, DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("nav.managers") };
}

const statusTone = {
  active: "lime",
  locked: "warning",
  suspended: "warning",
  pending_review: "warning",
  removed: "danger",
  deleted: "danger"
} as const;

export default async function ManagersPage({
  searchParams
}: {
  searchParams: Promise<{ division?: string }>;
}) {
  const params = await searchParams;
  const selected =
    params.division === "high" || params.division === "low" ? params.division : "all";
  const result = await vmfApi.managers();
  const filteredManagers =
    selected === "all"
      ? result.data
      : result.data.filter((manager) => manager.division.toLowerCase() === selected);
  return (
    <>
      <PageHeader
        eyebrow={t("managers.eyebrow")}
        title={t("managers.heading", { count: result.data.length })}
        description={t("managers.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="manager-toolbar">
        <SegmentedLinks
          items={[
            { href: "/managers", label: t("common.all"), active: selected === "all" },
            {
              href: "/managers?division=high",
              label: "HIGH",
              active: selected === "high"
            },
            {
              href: "/managers?division=low",
              label: "LOW",
              active: selected === "low"
            }
          ]}
        />
        <span>{t("common.profileCount", { count: filteredManagers.length })}</span>
      </div>
      <div className="managers-grid">
        {filteredManagers.map((manager) => (
          <article className="manager-card" id={manager.id} key={manager.id}>
            <header>
              <Avatar name={manager.name} division={manager.division} size="large" />
              <div>
                <span className="manager-card__division">
                  {t("managers.division", { division: manager.division })}
                </span>
                <h2>
                  <a
                    className="fpl-link"
                    href={fplSeasonUrl(manager.fplEntryId)}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={t("fpl.openSeason", { team: manager.teamName })}
                  >
                    {manager.teamName}
                  </a>
                </h2>
                <p>{manager.name}</p>
              </div>
              <Pill tone={statusTone[manager.status]}>
                {t(`managers.status.${manager.status}`)}
              </Pill>
            </header>
            <div className="manager-card__stats">
              <span>
                <small>{t("common.rank")}</small>
                <strong>{manager.rank === null ? "—" : `#${manager.rank}`}</strong>
              </span>
              <span>
                <small>{t("managers.totalPoints")}</small>
                <strong>
                  {manager.totalPoints === null ? "—" : formatNumber(manager.totalPoints)}
                </strong>
              </span>
              <span>
                <small>TotW</small>
                <strong>{manager.totw ?? "—"}</strong>
              </span>
            </div>
            <footer>
              <span>
                {t("managers.lastGameweek")} <strong>{manager.gameweekPoints ?? "—"}</strong>
              </span>
              <span>
                {t("managers.violations")} <strong>{manager.violations ?? "—"}</strong>
              </span>
            </footer>
          </article>
        ))}
      </div>
    </>
  );
}
