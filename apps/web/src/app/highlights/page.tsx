import type { Metadata } from "next";
import { Icon } from "@/components/icons";
import { DataBadge, EmptyState, PageHeader, Pill } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { highlightCopy } from "@/lib/highlight-text";
import type { MessageKey } from "@/lib/i18n";
import { t } from "@/lib/i18n";
import type { Highlight, HighlightPeriod } from "@/lib/types";

export async function generateMetadata(): Promise<Metadata> {
  return { title: t("nav.highlights") };
}

const iconMap = {
  totw: "highlight",
  record: "cup",
  comeback: "pulse",
  notice: "info"
} as const;

function HighlightCard({ highlight, ordinal }: { highlight: Highlight; ordinal: number }) {
  const copy = highlightCopy(highlight, t);
  return (
    <article
      className="highlight-card"
      data-category={highlight.category}
      // The lead story of each section spans two columns on a wide screen.
      data-large={ordinal === 1}
    >
      <div className="highlight-card__top">
        <span className="highlight-card__icon">
          <Icon name={iconMap[highlight.category]} size={23} />
        </span>
        {highlight.gameweek !== null && <Pill>GW{highlight.gameweek}</Pill>}
        {highlight.isProvisional && <Pill tone="coral">{t("highlight.provisional")}</Pill>}
      </div>
      <div>
        <p className="eyebrow">{copy.eyebrow}</p>
        <h2>{copy.title}</h2>
        <p>{copy.body}</p>
        {/* Only the kinds that need explaining carry one; the rest say what
            they are. */}
        {copy.note && <p className="highlight-card__note">{copy.note}</p>}
      </div>
      <footer>
        <span>{highlight.managerName}</span>
        <strong>{copy.value}</strong>
      </footer>
      <span className="highlight-card__ordinal">{String(ordinal).padStart(2, "0")}</span>
    </article>
  );
}

/**
 * The season's stories, split by what they are about.
 *
 * A run of cards with no headings leaves a reader unable to tell this week's
 * captain disaster from a record that has stood since August. The two
 * sections answer that before anyone reads a word of the cards.
 */
export default async function HighlightsPage() {
  const result = await vmfApi.highlights();

  const groups: Array<{ period: HighlightPeriod; heading: MessageKey }> = [
    { period: "gameweek", heading: "highlights.thisGameweek" },
    { period: "season", heading: "highlights.seasonRecords" }
  ];
  const sections = groups
    .map((group) => ({
      ...group,
      items: result.data.filter((item) => item.period === group.period)
    }))
    .filter((section) => section.items.length > 0);

  return (
    <>
      <PageHeader
        eyebrow={t("highlights.eyebrow")}
        title={t("nav.highlights")}
        description={t("highlights.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      {sections.length > 0 ? (
        sections.map((section, sectionIndex) => (
          <section className={sectionIndex > 0 ? "section-space" : undefined} key={section.period}>
            <h2 className="highlights-heading">{t(section.heading)}</h2>
            <div className="highlights-grid">
              {section.items.map((highlight, index) => (
                <HighlightCard highlight={highlight} ordinal={index + 1} key={highlight.id} />
              ))}
            </div>
          </section>
        ))
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
