import { t } from "@/lib/i18n";
import type { ChipStatus } from "@/lib/types";

/** FPL's codes, as managers abbreviate them. */
const CHIP_ABBREVIATIONS: Record<string, string> = {
  wildcard: "WC",
  freehit: "FH",
  bboost: "BB",
  "3xc": "TC"
};

/** The long name, for a tooltip on a two-letter tag. */
const CHIP_NAMES: Record<string, string> = {
  wildcard: "Wildcard",
  freehit: "Free Hit",
  bboost: "Bench Boost",
  "3xc": "Triple Captain"
};

function abbreviation(code: string): string {
  return CHIP_ABBREVIATIONS[code] ?? code.toUpperCase();
}

function fullName(code: string): string {
  return CHIP_NAMES[code] ?? code;
}

/**
 * What a manager played this Gameweek and what they have left.
 *
 * Chips are written the way managers say them — "BB1" is a Bench Boost played
 * in GW1 — so a season of chip history fits on one line. An unplayed chip has
 * no Gameweek yet, so it carries the letters alone.
 *
 * Both lines always appear, and both say "None" when empty: an absent line
 * reads as missing data, where "None" is an answer. Playing no chip is the
 * normal case and worth stating.
 */
export function ChipLine({ chips }: { chips: ChipStatus }) {
  const played = chips.playedThisGameweek;

  return (
    <dl className="chip-line">
      <div className="chip-line__row">
        <dt>{t("chips.thisGameweek")}</dt>
        <dd>
          {played ? (
            <span className="chip-tag" data-played="true" title={fullName(played.chip)}>
              {played.short}
            </span>
          ) : (
            <span className="chip-none">{t("chips.none")}</span>
          )}
        </dd>
      </div>
      <div className="chip-line__row">
        <dt>{t("chips.remaining")}</dt>
        <dd>
          {chips.remaining.length > 0 ? (
            chips.remaining.map((code) => (
              <span className="chip-tag" title={fullName(code)} key={code}>
                {abbreviation(code)}
              </span>
            ))
          ) : (
            <span className="chip-none">{t("chips.none")}</span>
          )}
        </dd>
      </div>
      {chips.used.length > 0 && (
        <div className="chip-line__row">
          <dt>{t("chips.usedThisHalf")}</dt>
          <dd>
            {chips.used.map((play) => (
              <span
                className="chip-tag"
                data-spent="true"
                title={fullName(play.chip)}
                key={play.short}
              >
                {play.short}
              </span>
            ))}
          </dd>
        </div>
      )}
    </dl>
  );
}
