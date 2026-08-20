import { t } from "@/lib/i18n";
import type { ChipStatus } from "@/lib/types";

/** FPL's codes, written the way the game writes them. */
const CHIP_NAMES: Record<string, string> = {
  wildcard: "Wildcard",
  freehit: "Free Hit",
  bboost: "Bench Boost",
  "3xc": "Triple Captain"
};

function name(code: string): string {
  return CHIP_NAMES[code] ?? code;
}

/**
 * What a manager played this Gameweek and what they have left.
 *
 * Both lines always appear, and both say "None" when they are empty: an
 * absent line reads as missing data, where "None" is an answer. Playing no
 * chip is the normal case, and it is worth stating.
 */
export function ChipLine({ chips }: { chips: ChipStatus }) {
  const played = chips.playedThisGameweek;

  return (
    <dl className="chip-line">
      <div className="chip-line__row" data-active={played !== null}>
        <dt>{t("chips.thisGameweek")}</dt>
        <dd>
          {played ? (
            <span className="chip-tag" data-played="true">
              {name(played)}
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
              <span className="chip-tag" key={code}>
                {name(code)}
              </span>
            ))
          ) : (
            <span className="chip-none">{t("chips.none")}</span>
          )}
        </dd>
      </div>
    </dl>
  );
}
