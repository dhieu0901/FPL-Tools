"use client";

import Link from "next/link";
import { formatNumber, rankDelta } from "@/lib/format";
import type { StandingEntry } from "@/lib/types";
import { useLocale, useTranslator } from "./locale-provider";
import { Avatar, FormDots, Pill } from "./ui";

function QualificationMarker({ value }: { value: StandingEntry["qualification"] }) {
  const t = useTranslator();
  if (!value) return null;
  return <span className="qualification-marker" data-zone={value} title={t(`zone.${value}`)} />;
}

export function StandingsTable({
  entries,
  compact = false
}: {
  entries: StandingEntry[];
  compact?: boolean;
}) {
  const locale = useLocale();
  const t = useTranslator();
  const showForm = !compact && entries.some((entry) => entry.form.length > 0);
  const showGameweek = entries.some((entry) => entry.gameweekPoints !== null);

  return (
    <div className="table-shell">
      <table className="standings-table">
        <thead>
          <tr>
            <th scope="col">{t("common.rank")}</th>
            <th scope="col">{t("common.team")}</th>
            {showForm && <th scope="col">{t("common.form")}</th>}
            {showGameweek && (
              <th scope="col" className="number-cell">
                GW
              </th>
            )}
            <th scope="col" className="number-cell">
              {t("common.total")}
            </th>
            {!compact && (
              <th scope="col" className="number-cell">
                TotW
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const delta =
              entry.previousRank === null ? null : rankDelta(entry.rank, entry.previousRank);
            return (
              <tr key={`${entry.division}-${entry.managerId}`}>
                <td>
                  <div className="rank-cell">
                    <QualificationMarker value={entry.qualification} />
                    <strong>{entry.rank}</strong>
                    {delta && (
                      <span className="rank-delta" data-direction={delta.direction}>
                        {delta.direction === "up"
                          ? `↑${delta.value}`
                          : delta.direction === "down"
                            ? `↓${delta.value}`
                            : "—"}
                      </span>
                    )}
                  </div>
                </td>
                <td>
                  <Link href={`/managers#${entry.managerId}`} className="team-cell">
                    <Avatar name={entry.managerName} division={entry.division} size="small" />
                    <span>
                      <strong>{entry.teamName}</strong>
                      <small>{entry.managerName}</small>
                    </span>
                    {entry.violations !== null && entry.violations > 0 && (
                      <Pill tone="danger">V{entry.violations}</Pill>
                    )}
                  </Link>
                </td>
                {showForm && (
                  <td>
                    <FormDots form={entry.form} />
                  </td>
                )}
                {showGameweek && <td className="number-cell">{entry.gameweekPoints}</td>}
                <td className="number-cell total-cell">
                  {formatNumber(entry.totalPoints, locale)}
                </td>
                {!compact && <td className="number-cell">{entry.totw}</td>}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
