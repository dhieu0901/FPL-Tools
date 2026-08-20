import type { Metadata } from "next";
import { Callout, PageHeader, Pill } from "@/components/ui";
import { t } from "@/lib/i18n";
import {
  FORMAT_BLOCKS,
  formatDong,
  MANAGER_OBLIGATIONS,
  PRIZE_FUND_TOTAL,
  PRIZE_SECTIONS,
  TIE_BREAK_STEPS,
  VIOLATION_CONSEQUENCES,
  VIOLATION_COUNTING
} from "@/lib/rulebook";

export const metadata: Metadata = { title: "Rules and prizes" };

export default function RulesPage() {
  return (
    <>
      <PageHeader
        eyebrow={t("rules.eyebrow")}
        title={t("rules.title")}
        description={t("rules.description")}
        actions={<Pill tone="lime">{formatDong(PRIZE_FUND_TOTAL)}</Pill>}
      />

      <section className="section-space">
        <div className="section-heading">
          <p className="eyebrow">{t("rules.formatEyebrow")}</p>
          <h2>{t("rules.formatTitle")}</h2>
        </div>
        <div className="rule-grid">
          {FORMAT_BLOCKS.map((block) => (
            <article className="rule-card" key={block.title}>
              <h3>{block.title}</h3>
              <p>{block.body}</p>
              {block.points && (
                <ul>
                  {block.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="section-space">
        <div className="section-heading">
          <p className="eyebrow">{t("rules.tieBreakEyebrow")}</p>
          <h2>{t("rules.tieBreakTitle")}</h2>
          <p>{t("rules.tieBreakBody")}</p>
        </div>
        <ol className="tie-break-chain">
          {TIE_BREAK_STEPS.map((step, index) => (
            <li key={step}>
              <span className="tie-break-chain__step">{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
      </section>

      <section className="section-space">
        <div className="section-heading">
          <p className="eyebrow">{t("rules.disciplineEyebrow")}</p>
          <h2>{t("rules.disciplineTitle")}</h2>
        </div>
        <div className="discipline-grid">
          <article className="rule-card">
            <h3>{t("rules.obligations")}</h3>
            <ul>
              {MANAGER_OBLIGATIONS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
          <article className="rule-card">
            <h3>{t("rules.counting")}</h3>
            <table className="data-table counting-table">
              <thead>
                <tr>
                  <th scope="col">{t("rules.gameweekTotal")}</th>
                  <th scope="col">{t("rules.counts")}</th>
                </tr>
              </thead>
              <tbody>
                {VIOLATION_COUNTING.map((row) => (
                  <tr key={row.range}>
                    <td>{row.range}</td>
                    <td>{row.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="panel-note">{t("rules.countingNote")}</p>
          </article>
        </div>
        <div className="sanction-grid">
          {VIOLATION_CONSEQUENCES.map((level, index) => (
            <article className="sanction-card" data-level={index + 1} key={level.level}>
              <header>
                <span>{index + 1}</span>
                <h3>{t("rules.offence", { level: level.level })}</h3>
              </header>
              <ul>
                {level.points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
        <Callout title={t("rules.forgottenChip")} icon="info">
          <p>{t("rules.forgottenChipBody")}</p>
        </Callout>
      </section>

      <section className="section-space">
        <div className="section-heading">
          <p className="eyebrow">{t("rules.prizeEyebrow")}</p>
          <h2>{t("rules.prizeTitle")}</h2>
          <p>{t("rules.prizeBody", { total: formatDong(PRIZE_FUND_TOTAL) })}</p>
        </div>
        <div className="prize-grid">
          {PRIZE_SECTIONS.map((section) => (
            <article className="prize-card" data-section={section.id} key={section.id}>
              <header className="prize-card__head">
                <h3>{section.title}</h3>
                <strong>{formatDong(section.total)}</strong>
              </header>
              {section.note && <p className="prize-card__note">{section.note}</p>}
              {section.groups.map((group) => (
                <div className="prize-group" key={`${section.id}-${group.title}`}>
                  {section.groups.length > 1 && (
                    <p className="prize-group__title">
                      {group.title}
                      {group.subtitle && <small>{group.subtitle}</small>}
                    </p>
                  )}
                  <ul className="prize-lines">
                    {group.lines.map((line) => (
                      <li key={line.place}>
                        <span>
                          {line.place}
                          {line.note && <em>{line.note}</em>}
                        </span>
                        <b>
                          {formatDong(line.amount)}
                          {line.perManager && <small>{t("rules.perManager")}</small>}
                        </b>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </article>
          ))}
        </div>
        <Callout title={t("rules.minigameFund")} icon="info">
          <p>{t("rules.minigameFundBody")}</p>
        </Callout>
      </section>
    </>
  );
}
