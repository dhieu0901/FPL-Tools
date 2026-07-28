import type { Metadata } from "next";
import Link from "next/link";
import { FixtureCard } from "@/components/fixture-card";
import { Icon } from "@/components/icons";
import { StandingsTable } from "@/components/standings-table";
import { DataBadge, EmptyState, Pill, SectionHeader } from "@/components/ui";
import { formatDateTime, gameweekStateLabel } from "@/lib/format";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = {
  title: "Tổng quan"
};

export default async function DashboardPage() {
  const result = await vmfApi.dashboard();
  const { data } = result;

  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-hero__copy">
          <div className="hero-meta">
            <Pill tone="lime">Mùa {data.season}</Pill>
            <DataBadge source={result.source} updatedAt={result.updatedAt} />
          </div>
          <p className="eyebrow">Văn Minh Fantasy League</p>
          <h1>
            Mỗi điểm số.
            <br />
            <span>Đều có câu chuyện.</span>
          </h1>
          <p>
            Theo dõi Classic, đối đầu H2H và hành trình Cup trên một bảng điều hành minh bạch, cập
            nhật xuyên suốt mùa giải.
          </p>
          <div className="hero-actions">
            <Link href="/classic" className="primary-button">
              Xem bảng xếp hạng <Icon name="arrow" size={18} />
            </Link>
            <Link href="/h2h/fixtures" className="secondary-button">
              Lịch đối đầu
            </Link>
          </div>
        </div>
        <div className="gameweek-card">
          <div className="gameweek-card__topline">
            <span>{data.gameweek.name}</span>
            <Pill tone={data.gameweek.state === "live" ? "coral" : "blue"}>
              {gameweekStateLabel(data.gameweek.state)}
            </Pill>
          </div>
          <div className="gameweek-orbit" aria-hidden="true">
            <svg viewBox="0 0 180 180">
              <title>Tiến độ Gameweek</title>
              <circle cx="90" cy="90" r="76" className="orbit-track" />
              <circle
                cx="90"
                cy="90"
                r="76"
                className="orbit-value"
                pathLength="100"
                strokeDasharray={`${data.gameweek.progress} 100`}
              />
            </svg>
            <span>
              <strong>{data.gameweek.number}</strong>
              <small>GW</small>
            </span>
          </div>
          <div className="gameweek-progress">
            <span>
              <small>Hoàn thành</small>
              <strong>
                {data.gameweek.fixturesComplete}/{data.gameweek.fixturesTotal} trận
              </strong>
            </span>
            <span>
              <small>Deadline</small>
              <strong>
                {data.gameweek.deadline ? formatDateTime(data.gameweek.deadline) : "Chưa công bố"}
              </strong>
            </span>
          </div>
          <div className="gameweek-card__grid" aria-hidden="true" />
        </div>
      </section>

      <section className="metrics-grid" aria-label="Chỉ số nhanh">
        {data.metrics.map((metric) => (
          <article className="metric-card" data-tone={metric.tone} key={metric.label}>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>{metric.detail}</small>
          </article>
        ))}
      </section>

      <section className="dashboard-grid section-space">
        <div>
          <SectionHeader
            eyebrow="Tâm điểm vòng đấu"
            title="Đối đầu nổi bật"
            href="/h2h/fixtures"
            linkLabel="Mọi trận đấu"
          />
          {data.featuredFixture ? (
            <FixtureCard fixture={data.featuredFixture} />
          ) : (
            <EmptyState
              icon="calendar"
              title="Chưa có lịch H2H"
              description="Lịch thi đấu sẽ xuất hiện sau khi admin tạo schedule."
            />
          )}
        </div>
        <aside>
          <SectionHeader eyebrow="Ban tổ chức" title="Thông báo" />
          {data.notices.length > 0 ? (
            <div className="notice-stack">
              {data.notices.map((notice) => (
                <article className="notice-card" key={notice.id}>
                  <span className="notice-card__icon" data-priority={notice.priority}>
                    <Icon name={notice.priority === "important" ? "warning" : "info"} size={19} />
                  </span>
                  <div>
                    <strong>{notice.title}</strong>
                    <p>{notice.body}</p>
                    <time>{formatDateTime(notice.publishedAt)}</time>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="Chưa có thông báo" description="Admin chưa đăng thông báo mới." />
          )}
        </aside>
      </section>

      <section className="section-space">
        <SectionHeader
          eyebrow="Division HIGH"
          title="Cuộc đua Classic"
          description="Bảng điểm tạm tính sau các trận đã hoàn tất."
          href="/classic"
        />
        <StandingsTable entries={data.standings} compact />
      </section>

      <section className="section-space">
        <SectionHeader eyebrow="Khoảnh khắc VMF" title="Highlights mới nhất" href="/highlights" />
        {data.recentHighlights.length > 0 ? (
          <div className="highlight-preview-grid">
            {data.recentHighlights.map((highlight, index) => (
              <article className="highlight-preview" data-featured={index === 0} key={highlight.id}>
                <span className="highlight-preview__number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="eyebrow">{highlight.eyebrow}</p>
                  <h3>{highlight.title}</h3>
                  <p>{highlight.description}</p>
                </div>
                {highlight.value && <strong>{highlight.value}</strong>}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState
            icon="highlight"
            title="Highlights đang được hoàn thiện"
            description="Backend hiện chưa cung cấp nguồn highlights."
          />
        )}
      </section>
    </>
  );
}
