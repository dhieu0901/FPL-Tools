import type { Metadata } from "next";
import { AdminNav } from "@/components/admin-nav";
import { Icon } from "@/components/icons";
import { Avatar, DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Quản lý vi phạm" };

const statusLabel = {
  pending: "Chờ xử lý",
  confirmed: "Đã xác nhận",
  waived: "Được miễn"
};

export default async function AdminViolationsPage({
  searchParams
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const params = await searchParams;
  const selected =
    params.status === "pending" || params.status === "confirmed" || params.status === "waived"
      ? params.status
      : "all";
  const result = await vmfApi.adminViolations();
  const filteredViolations =
    selected === "all"
      ? result.data
      : result.data.filter((violation) => violation.status === selected);
  return (
    <>
      <PageHeader
        eyebrow="Khu vực điều hành"
        title="Violation review"
        description="Xác minh vi phạm, phạm vi ảnh hưởng và lịch sử quyết định theo từng gameweek."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <AdminNav active="violations" />
      <div className="violation-toolbar">
        <SegmentedLinks
          items={[
            {
              href: "/admin/violations",
              label: "Tất cả",
              active: selected === "all"
            },
            {
              href: "/admin/violations?status=pending",
              label: "Chờ xử lý",
              active: selected === "pending"
            },
            {
              href: "/admin/violations?status=confirmed",
              label: "Đã xác nhận",
              active: selected === "confirmed"
            },
            {
              href: "/admin/violations?status=waived",
              label: "Được miễn",
              active: selected === "waived"
            }
          ]}
        />
        <span>{filteredViolations.length} hồ sơ</span>
      </div>
      <div className="violation-list">
        {filteredViolations.map((violation) => (
          <article className="violation-card" key={violation.id}>
            <div className="violation-card__identity">
              <Avatar name={violation.managerName} division={violation.division} />
              <div>
                <span>
                  {violation.id.toUpperCase()} · GW{violation.gameweek}
                </span>
                <h2>{violation.teamName}</h2>
                <p>
                  {violation.managerName} · Division {violation.division}
                </p>
              </div>
            </div>
            <div className="violation-card__reason">
              <span className="severity" data-level={violation.severity}>
                Cấp {violation.severity}
              </span>
              <div>
                <strong>{violation.reason}</strong>
                <p>Transfer cost ghi nhận: −{violation.transferCost}</p>
              </div>
            </div>
            <div className="impact-list">
              {violation.impact.map((impact) => (
                <span key={impact}>
                  <Icon name="chevron" size={13} /> {impact}
                </span>
              ))}
            </div>
            <div className="violation-card__status">
              <Pill
                tone={
                  violation.status === "pending"
                    ? "warning"
                    : violation.status === "confirmed"
                      ? "danger"
                      : "lime"
                }
              >
                {statusLabel[violation.status]}
              </Pill>
              <time>{formatDateTime(violation.createdAt)}</time>
            </div>
            <div className="violation-card__actions">
              {violation.status === "pending" ? (
                <>
                  <button className="secondary-button" type="button">
                    Yêu cầu bổ sung
                  </button>
                  <button className="danger-button" type="button">
                    Xác nhận vi phạm
                  </button>
                </>
              ) : (
                <button className="secondary-button" type="button">
                  Xem audit log
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
