import type { Metadata } from "next";
import { Avatar, DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { formatNumber } from "@/lib/format";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Managers" };

const statusPresentation = {
  active: { label: "Active", tone: "lime" },
  locked: { label: "Locked", tone: "warning" },
  suspended: { label: "Suspended", tone: "warning" },
  pending_review: { label: "Pending", tone: "warning" },
  removed: { label: "Removed", tone: "danger" },
  deleted: { label: "Deleted", tone: "danger" }
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
        eyebrow="Cộng đồng"
        title={`${result.data.length} managers. Một mùa giải.`}
        description="Hồ sơ thi đấu công khai chỉ hiển thị dữ liệu giải; thông tin cá nhân được giới hạn cho ban tổ chức."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="manager-toolbar">
        <SegmentedLinks
          items={[
            { href: "/managers", label: "Tất cả", active: selected === "all" },
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
        <span>{filteredManagers.length} hồ sơ</span>
      </div>
      <div className="managers-grid">
        {filteredManagers.map((manager) => (
          <article className="manager-card" id={manager.id} key={manager.id}>
            <header>
              <Avatar name={manager.name} division={manager.division} size="large" />
              <div>
                <span className="manager-card__division">Division {manager.division}</span>
                <h2>{manager.teamName}</h2>
                <p>{manager.name}</p>
              </div>
              <Pill tone={statusPresentation[manager.status].tone}>
                {statusPresentation[manager.status].label}
              </Pill>
            </header>
            <div className="manager-card__stats">
              <span>
                <small>Hạng</small>
                <strong>{manager.rank === null ? "—" : `#${manager.rank}`}</strong>
              </span>
              <span>
                <small>Tổng điểm</small>
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
                GW gần nhất <strong>{manager.gameweekPoints ?? "—"}</strong>
              </span>
              <span>
                Violation <strong>{manager.violations ?? "—"}</strong>
              </span>
            </footer>
          </article>
        ))}
      </div>
    </>
  );
}
