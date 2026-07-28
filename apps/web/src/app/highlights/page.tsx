import type { Metadata } from "next";
import { Icon } from "@/components/icons";
import { DataBadge, PageHeader, Pill } from "@/components/ui";
import { vmfApi } from "@/lib/api";

export const metadata: Metadata = { title: "Highlights" };

const iconMap = {
  totw: "highlight",
  record: "cup",
  comeback: "pulse",
  notice: "info"
} as const;

export default async function HighlightsPage() {
  const result = await vmfApi.highlights();
  return (
    <>
      <PageHeader
        eyebrow="Season stories"
        title="Highlights"
        description="Những đội hình xuất sắc, cuộc lội ngược dòng và cột mốc đáng nhớ của cộng đồng VMF."
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="highlights-grid">
        {result.data.map((highlight, index) => (
          <article
            className="highlight-card"
            data-category={highlight.category}
            data-large={index === 0}
            key={highlight.id}
          >
            <div className="highlight-card__top">
              <span className="highlight-card__icon">
                <Icon name={iconMap[highlight.category]} size={23} />
              </span>
              <Pill>GW{highlight.gameweek}</Pill>
            </div>
            <div>
              <p className="eyebrow">{highlight.eyebrow}</p>
              <h2>{highlight.title}</h2>
              <p>{highlight.description}</p>
            </div>
            <footer>
              {highlight.managerName && <span>{highlight.managerName}</span>}
              {highlight.value && <strong>{highlight.value}</strong>}
            </footer>
            <span className="highlight-card__ordinal">{String(index + 1).padStart(2, "0")}</span>
          </article>
        ))}
      </div>
    </>
  );
}
