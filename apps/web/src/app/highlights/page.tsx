import type { Metadata } from "next";
import { Icon } from "@/components/icons";
import { DataBadge, EmptyState, PageHeader, Pill } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { highlightCopy } from "@/lib/highlight-text";
import { t } from "@/lib/i18n";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("nav.highlights") };
}

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
        eyebrow={t("highlights.eyebrow")}
        title={t("nav.highlights")}
        description={t("highlights.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      {result.data.length > 0 ? (
        <div className="highlights-grid">
          {result.data.map((highlight, index) => {
            const copy = highlightCopy(highlight, t);
            return (
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
                  {highlight.gameweek !== null && <Pill>GW{highlight.gameweek}</Pill>}
                  {highlight.isProvisional && (
                    <Pill tone="coral">{t("highlight.provisional")}</Pill>
                  )}
                </div>
                <div>
                  <p className="eyebrow">{copy.eyebrow}</p>
                  <h2>{copy.title}</h2>
                  <p>{copy.body}</p>
                </div>
                <footer>
                  <span>{highlight.managerName}</span>
                  <strong>{copy.value}</strong>
                </footer>
                <span className="highlight-card__ordinal">
                  {String(index + 1).padStart(2, "0")}
                </span>
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon="highlight"
          title={t("highlights.emptyTitle")}
          description={t("highlights.emptyBody")}
        />
      )}
    </>
  );
}
