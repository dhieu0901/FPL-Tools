import type { Metadata } from "next";
import { Icon } from "@/components/icons";
import { DataBadge, EmptyState, PageHeader, Pill } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("nav.highlights") };
}

const iconMap = {
  totw: "highlight",
  record: "cup",
  comeback: "pulse",
  notice: "info"
} as const;

export default async function HighlightsPage() {
  const t = createTranslator(await getLocale());
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
