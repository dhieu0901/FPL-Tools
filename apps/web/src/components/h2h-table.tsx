import Link from "next/link";
import { formatNumber } from "@/lib/format";
import type { H2HStanding } from "@/lib/types";
import { Avatar, FormDots, Pill } from "./ui";

export function H2HTable({ entries }: { entries: H2HStanding[] }) {
  return (
    <div className="table-shell">
      <table className="standings-table h2h-table">
        <thead>
          <tr>
            <th>Hạng</th>
            <th>Đội bóng</th>
            <th>Trận</th>
            <th>Thắng</th>
            <th>Hoà</th>
            <th>Thua</th>
            <th>Điểm ghi</th>
            <th>Phong độ</th>
            <th className="number-cell">Điểm</th>
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
                <Link href={`/managers#${entry.managerId}`} className="team-cell">
                  <Avatar name={entry.managerName} size="small" />
                  <span>
                    <strong>{entry.teamName}</strong>
                    <small>{entry.managerName}</small>
                  </span>
                </Link>
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
                {entry.deduction > 0 && <Pill tone="danger">−{entry.deduction}</Pill>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
