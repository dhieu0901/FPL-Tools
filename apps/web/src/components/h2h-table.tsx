"use client";

import { formatNumber } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { H2HStanding } from "@/lib/types";
import { fplSeasonUrl } from "./fpl-link";
import { Avatar, FormDots, Pill } from "./ui";

export function H2HTable({ entries }: { entries: H2HStanding[] }) {
  return (
    <div className="table-shell">
      <table className="standings-table h2h-table">
        <thead>
          <tr>
            <th>{t("common.rank")}</th>
            <th>{t("common.team")}</th>
            <th>{t("h2h.played")}</th>
            <th>{t("h2h.won")}</th>
            <th>{t("h2h.drawn")}</th>
            <th>{t("h2h.lost")}</th>
            <th>{t("h2h.pointsFor")}</th>
            <th>{t("common.form")}</th>
            <th className="number-cell">{t("common.points")}</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.managerId}>
              <td>
                <span className="h2h-rank" data-top={entry.rank <= 4}>
                  {entry.rank}
                </span>
              </td>
              <td>
                {/* Straight to their season on FPL, which is what a reader
                    clicking a name is after. A side with no known entry id
                    stays plain text rather than becoming a dead link. */}
                {entry.fplEntryId === null ? (
                  <span className="team-cell">
                    <Avatar name={entry.managerName} size="small" />
                    <span>
                      <strong>{entry.teamName}</strong>
                      <small>{entry.managerName}</small>
                    </span>
                  </span>
                ) : (
                  <a
                    className="team-cell fpl-link"
                    href={fplSeasonUrl(entry.fplEntryId)}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={t("fpl.openSeason", { team: entry.teamName })}
                  >
                    <Avatar name={entry.managerName} size="small" />
                    <span>
                      <strong>{entry.teamName}</strong>
                      <small>{entry.managerName}</small>
                    </span>
                  </a>
                )}
              </td>
              <td>{entry.played}</td>
              <td>{entry.won}</td>
              <td>{entry.drawn}</td>
              <td>{entry.lost}</td>
              <td>{formatNumber(entry.pointsFor)}</td>
              <td>
                <FormDots form={entry.form} />
              </td>
              <td className="number-cell total-cell">
                {entry.points}
                {entry.deduction > 0 && <Pill tone="danger">-{entry.deduction}</Pill>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
