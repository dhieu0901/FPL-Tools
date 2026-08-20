import type { Metadata } from "next";
import { AdminNav } from "@/components/admin-nav";
import { Icon } from "@/components/icons";
import { DataBadge, EmptyState, PageHeader, Pill } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { t } from "@/lib/i18n";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("admin.title") };
}

export default async function AdminPage() {
  const result = await vmfApi.adminOverview();
  const data = result.data;
  return (
    <>
      <PageHeader
        eyebrow={t("admin.eyebrow")}
        title={t("admin.heading")}
        description={t("admin.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <AdminNav active="overview" />
      <section className="admin-health">
        <div className="admin-health__icon">
          <Icon name="pulse" size={28} />
        </div>
        <div>
          <span>{t("admin.syncState")}</span>
          <h2>{data.sync ? t("admin.syncHealthy") : t("admin.syncUnknown")}</h2>
          <p>
            {data.sync
              ? t("admin.syncDetail", {
                  time: formatDateTime(data.sync.lastSuccessfulAt),
                  latency: data.sync.latencySeconds
                })
              : t("admin.syncMissing")}
          </p>
        </div>
        <Pill tone={data.sync ? "lime" : "warning"}>
          {data.sync ? t("admin.healthy") : t("admin.unknown")}
        </Pill>
      </section>
      <section className="admin-stat-grid">
        <article>
          <span>{t("nav.managers")}</span>
          <strong>{data.counts.managers}</strong>
          <small>{t("admin.managersConfirmed")}</small>
        </article>
        <article>
          <span>{t("admin.provisionalScores")}</span>
          <strong>{data.counts.provisionalScores ?? "-"}</strong>
          <small>
            {data.counts.provisionalScores === null
              ? t("admin.noEndpoint")
              : t("admin.awaitingFinalize")}
          </small>
        </article>
        <article data-tone="warning">
          <span>{t("admin.pendingViolations")}</span>
          <strong>{data.counts.pendingViolations}</strong>
          <small>{t("admin.needsDecision")}</small>
        </article>
        <article>
          <span>{t("admin.lockedTeams")}</span>
          <strong>{data.counts.lockedTeams}</strong>
          <small>{t("admin.lockedTeamsNote")}</small>
        </article>
      </section>
      <div className="admin-grid">
        <section className="panel-card">
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">{t("admin.byGameweek")}</p>
              <h2>{t("admin.divisionAverage")}</h2>
            </div>
            <Icon name="standings" size={22} />
          </div>
          {data.divisionAverages.length > 0 ? (
            <div className="average-list">
              {data.divisionAverages.map((item) => (
                <article key={item.division}>
                  <span>{t("managers.division", { division: item.division })}</span>
                  <strong>{item.average}</strong>
                  <small>{t("admin.eligibleManagers", { count: item.eligibleManagers })}</small>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title={t("admin.noAverageTitle")} description={t("admin.noAverageBody")} />
          )}
          <p className="panel-note">{t("admin.averageNote")}</p>
        </section>
        <section className="panel-card">
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">{t("admin.workerLog")}</p>
              <h2>{t("admin.recentJobs")}</h2>
            </div>
            <Pill tone="warning">{t("admin.syncCadence")}</Pill>
          </div>
          {data.recentJobs.length > 0 ? (
            <div className="job-list">
              {data.recentJobs.map((job) => (
                <article key={job.id}>
                  <span className="job-status" data-status={job.status}>
                    <Icon name={job.status === "success" ? "check" : "clock"} size={15} />
                  </span>
                  <div>
                    <strong>{job.name}</strong>
                    <small>{formatDateTime(job.startedAt)}</small>
                  </div>
                  <span>{job.duration}</span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title={t("admin.noJobTitle")} description={t("admin.noJobBody")} />
          )}
        </section>
      </div>
    </>
  );
}
