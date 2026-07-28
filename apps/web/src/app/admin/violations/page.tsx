import type { Metadata } from "next";
import { AdminNav } from "@/components/admin-nav";
import { Icon } from "@/components/icons";
import { Avatar, DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { vmfApi } from "@/lib/api";
import type { Violation } from "@/lib/types";
import { reviewViolation } from "./actions";

export const metadata: Metadata = { title: "Quản lý vi phạm" };

const statusLabel = {
  pending: "Chờ xử lý",
  confirmed: "Đã xác nhận",
  waived: "Được miễn"
};

function ReviewActions({ violation }: { violation: Violation }) {
  if (violation.status !== "pending") {
    return (
      <div className="violation-card__actions">
        <button
          className="secondary-button"
          type="button"
          disabled
          title="Audit-log detail chưa có endpoint cho giao diện."
        >
          Xem audit log
        </button>
      </div>
    );
  }

  const actions =
    violation.sourceStatus === "detected"
      ? [
          {
            value: "request_forgotten_chip_review",
            label: "Yêu cầu kiểm tra chip",
            className: "secondary-button"
          },
          {
            value: "confirm",
            label: "Xác nhận vi phạm",
            className: "danger-button"
          }
        ]
      : violation.sourceStatus === "pending_review"
        ? [
            {
              value: "approve_exception",
              label: "Duyệt ngoại lệ",
              className: "secondary-button"
            },
            {
              value: "reject_exception",
              label: "Bác ngoại lệ",
              className: "danger-button"
            }
          ]
        : [];

  if (actions.length === 0) {
    return (
      <div className="violation-card__actions">
        <button className="secondary-button" type="button" disabled>
          Dữ liệu minh hoạ · không thể review
        </button>
      </div>
    );
  }

  return (
    <form action={reviewViolation} className="violation-card__actions">
      <input type="hidden" name="violation_id" value={violation.id} />
      <input
        type="text"
        name="note"
        required
        maxLength={2000}
        placeholder="Ghi chú bắt buộc"
        aria-label={`Ghi chú review violation ${violation.id}`}
      />
      {actions.map((action) => (
        <button
          className={action.className}
          type="submit"
          name="action"
          value={action.value}
          key={action.value}
        >
          {action.label}
        </button>
      ))}
    </form>
  );
}

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
                {(violation.occurrences ?? violation.severity) === 0
                  ? "Không xác nhận"
                  : `${violation.occurrences ?? violation.severity} lần trong bản ghi`}
              </span>
              <div>
                <strong>{violation.reason}</strong>
                <p>
                  {violation.transferCost === null
                    ? "Backend chưa trả transfer cost"
                    : `Transfer cost ghi nhận: −${violation.transferCost}`}
                </p>
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
              <time>
                {violation.createdAt ? formatDateTime(violation.createdAt) : "Chưa review"}
              </time>
            </div>
            <ReviewActions violation={violation} />
          </article>
        ))}
      </div>
    </>
  );
}
