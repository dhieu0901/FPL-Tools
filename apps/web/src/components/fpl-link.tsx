import { t } from "@/lib/i18n";
import type { FixtureSide } from "@/lib/types";

/** A manager's own Gameweek page on FPL, which is where these points come from. */
export function fplEntryUrl(entryId: number, gameweek: number): string {
  return `https://fantasy.premierleague.com/entry/${entryId}/event/${gameweek}`;
}

/**
 * A team name that opens the same Gameweek on FPL.
 *
 * Managers cross-check against FPL constantly, so the team name is the link
 * rather than a separate icon: it is the thing they already want to click.
 * A side with no known entry id renders as plain text, never a dead link.
 */
export function TeamLink({
  side,
  gameweek,
  className
}: {
  side: FixtureSide;
  gameweek: number;
  className?: string;
}) {
  if (side.fplEntryId === null) {
    return <span className={className}>{side.teamName}</span>;
  }
  return (
    <a
      className={className ? `${className} fpl-link` : "fpl-link"}
      href={fplEntryUrl(side.fplEntryId, gameweek)}
      target="_blank"
      rel="noopener noreferrer"
      title={t("fpl.openOnFpl", { team: side.teamName })}
    >
      {side.teamName}
    </a>
  );
}
