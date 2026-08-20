import type { Metadata } from "next";
import { AdminNav } from "@/components/admin-nav";
import { Icon } from "@/components/icons";
import { Avatar, DataBadge, PageHeader, Pill, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { type Translator, t } from "@/lib/i18n";
import type { Violation } from "@/lib/types";
import { reviewViolation } from "./actions";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("violations.title") };
}

function ReviewActions({ violation, t }: { violation: Violation; t: Translator }) {
  if (violation.status !== "pending") {
    return (
      <div className="violation-card__actions">
        <button
          className="secondary-button"
          type="button"
          disabled
          title={t("violations.auditUnavailable")}
        >
          {t("violations.viewAudit")}
        </button>
      </div>
    );
  }

  const actions =
    violation.sourceStatus === "detected"
      ? [
          {
            value: "request_forgotten_chip_review",
            label: t("violations.requestChipReview"),
            className: "secondary-button"
          },
          {
            value: "confirm",
            label: t("violations.confirmViolation"),
            className: "danger-button"
          }
        ]
      : violation.sourceStatus === "pending_review"
        ? [
            {
              value: "approve_exception",
              label: t("violations.approveException"),
              className: "secondary-button"
            },
            {
              value: "reject_exception",
              label: t("violations.rejectException"),
              className: "danger-button"
            }
          ]
        : [];

  // A violation that has already been decided offers nothing to press, so the
  // card ends rather than showing a note field with no way to submit it.
  if (actions.length === 0) return null;

  return (
    <form action={reviewViolation} className="violation-card__actions">
      <input type="hidden" name="violation_id" value={violation.id} />
      <input
        type="text"
        name="note"
        required
        maxLength={2000}
        placeholder={t("violations.notePlaceholder")}
        aria-label={t("violations.noteAria", { id: violation.id })}
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
        eyebrow={t("admin.eyebrow")}
        title={t("violations.heading")}
        description={t("violations.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <AdminNav active="violations" />
      <div className="violation-toolbar">
        <SegmentedLinks
          items={[
            {
              href: "/admin/violations",
              label: t("common.all"),
              active: selected === "all"
            },
            {
              href: "/admin/violations?status=pending",
              label: t("violations.pending"),
              active: selected === "pending"
            },
            {
              href: "/admin/violations?status=confirmed",
              label: t("violations.confirmed"),
              active: selected === "confirmed"
            },
            {
              href: "/admin/violations?status=waived",
              label: t("violations.waived"),
              active: selected === "waived"
            }
          ]}
        />
        <span>{t("common.profileCount", { count: filteredViolations.length })}</span>
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
                  {violation.managerName} ·{" "}
                  {t("managers.division", { division: violation.division })}
                </p>
              </div>
            </div>
            <div className="violation-card__reason">
              <span className="severity" data-level={violation.severity}>
                {(violation.occurrences ?? violation.severity) === 0
                  ? t("violations.noneConfirmed")
                  : t("violations.occurrences", {
                      count: violation.occurrences ?? violation.severity
                    })}
              </span>
              <div>
                <strong>{violation.reason}</strong>
                <p>
                  {violation.transferCost === null
                    ? t("violations.noTransferCost")
                    : t("violations.transferCost", { cost: violation.transferCost })}
                </p>
              </div>
            </div>
            <div className="impact-list">
              {violation.impact.map((impact) => (
                <span key={impact}>
                  <Icon name="chevron" size={13} /> {t(`violations.impact.${impact}`)}
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
                {t(`violations.${violation.status}`)}
              </Pill>
              <time>
                {violation.createdAt
                  ? formatDateTime(violation.createdAt)
                  : t("violations.notReviewed")}
              </time>
            </div>
            <ReviewActions violation={violation} t={t} />
          </article>
        ))}
      </div>
    </>
  );
}
