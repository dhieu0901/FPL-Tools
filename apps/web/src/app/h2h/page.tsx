import type { Metadata } from "next";
import { H2HTable } from "@/components/h2h-table";
import { Callout, DataBadge, PageHeader, SegmentedLinks } from "@/components/ui";
import { vmfApi } from "@/lib/api";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export async function generateMetadata(): Promise<Metadata> {
  return { title: createTranslator(await getLocale())("h2h.title") };
}

export default async function H2HPage() {
  const t = createTranslator(await getLocale());
  const result = await vmfApi.h2hStandings();
  return (
    <>
      <PageHeader
        eyebrow="Head to Head"
        title={t("h2h.heading")}
        description={t("h2h.description")}
        actions={<DataBadge source={result.source} updatedAt={result.updatedAt} />}
      />
      <div className="toolbar-row">
        <SegmentedLinks
          items={[
            { href: "/h2h", label: t("h2h.standings"), active: true },
            { href: "/h2h/fixtures", label: t("h2h.fixtures") }
          ]}
        />
        <span className="toolbar-note">{t("h2h.groupStage")}</span>
      </div>
      <H2HTable entries={result.data} />
      <div className="h2h-summary-grid">
        <article>
          <span>{t("h2h.playoffSlot")}</span>
          <strong>{t("h2h.top8")}</strong>
          <small>{t("h2h.afterGw35")}</small>
        </article>
        <article>
          <span>{t("h2h.quarterFinal")}</span>
          <strong>{t("h2h.quarterFinalGw")}</strong>
          <small>
            {t("h2h.semiFinal")}: {t("h2h.semiFinalGw")}
          </small>
        </article>
        <article>
          <span>{t("h2h.final")}</span>
          <strong>{t("h2h.finalGw")}</strong>
          <small>{t("h2h.noThirdPlace")}</small>
        </article>
      </div>
      <Callout title={t("h2h.immutableTitle")} icon="shield" tone="lime">
        <p>{t("h2h.immutableBody")}</p>
      </Callout>
    </>
  );
}
