import type { Metadata } from "next";
import { AdminNav } from "@/components/admin-nav";
import { Icon } from "@/components/icons";
import { DataBadge, EmptyState, PageHeader, Pill } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Điều hành" };

export default async function AdminPage() {
  const result = await vmfApi.adminOverview();
  const data = result.data;
  return (
    <>
      <PageHeader
        eyebrow="Khu vực điều hành"
        title="Trung tâm vận hành"
        description="Theo dõi đồng bộ, trạng thái tính điểm và các ngoại lệ cần xử lý."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <AdminNav active="overview" />
      <section className="admin-health">
        <div className="admin-health__icon">
          <Icon name="pulse" size={28} />
        </div>
        <div>
          <span>Tình trạng đồng bộ</span>
          <h2>{data.sync ? "Hệ thống hoạt động bình thường" : "Chưa có telemetry worker"}</h2>
          <p>
            {data.sync
              ? `Thành công lúc ${formatDateTime(data.sync.lastSuccessfulAt)} · Độ trễ ${data.sync.latencySeconds} giây`
              : "Backend hiện chưa cung cấp endpoint trạng thái đồng bộ."}
          </p>
        </div>
        <Pill tone={data.sync ? "lime" : "warning"}>{data.sync ? "Healthy" : "Unknown"}</Pill>
      </section>
      <section className="admin-stat-grid">
        <article>
          <span>Managers</span>
          <strong>{data.counts.managers}</strong>
          <small>Đã xác nhận tham gia</small>
        </article>
        <article>
          <span>Điểm tạm tính</span>
          <strong>{data.counts.provisionalScores ?? "—"}</strong>
          <small>
            {data.counts.provisionalScores === null ? "Chưa có endpoint" : "Chờ finalize"}
          </small>
        </article>
        <article data-tone="warning">
          <span>Violation chờ xử lý</span>
          <strong>{data.counts.pendingViolations}</strong>
          <small>Cần quyết định admin</small>
        </article>
        <article>
          <span>Team bị khóa</span>
          <strong>{data.counts.lockedTeams}</strong>
          <small>Dùng điểm trung bình division</small>
        </article>
      </section>
      <div className="admin-grid">
        <section className="panel-card">
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">Theo gameweek</p>
              <h2>Điểm trung bình division</h2>
            </div>
            <Icon name="standings" size={22} />
          </div>
          {data.divisionAverages.length > 0 ? (
            <div className="average-list">
              {data.divisionAverages.map((item) => (
                <article key={item.division}>
                  <span>Division {item.division}</span>
                  <strong>{item.average}</strong>
                  <small>{item.eligibleManagers} managers hợp lệ</small>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Chưa có dữ liệu trung bình"
              description="Backend chưa cung cấp endpoint division average."
            />
          )}
          <p className="panel-note">
            Team locked/removed và điểm replacement không được đưa vào mẫu tính.
          </p>
        </section>
        <section className="panel-card">
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">Worker log</p>
              <h2>Tác vụ gần đây</h2>
            </div>
            <Pill tone="warning">Probe 15 phút</Pill>
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
            <EmptyState
              title="Chưa có worker log"
              description="Backend chưa cung cấp endpoint lịch sử tác vụ."
            />
          )}
        </section>
      </div>
    </>
  );
}
