import { chipAbbreviation as abbreviation, chipName as fullName } from "@/lib/chips";
import { t } from "@/lib/i18n";
import type { ChipStatus } from "@/lib/types";

/**
 * What a manager has spent, and what they still hold.
 *
 * Chips are written the way managers say them - "BB1" is a Bench Boost played
 * in GW1 - so the Gameweek a chip went on is part of its name and no separate
 * line is needed to say what was played this week. An unplayed chip has no
 * Gameweek yet, so it carries the letters alone.
 *
 * Both lines always appear, and both say "None" when empty: an absent line
 * reads as missing data, where "None" is an answer. Holding every chip and
 * having spent none are both normal, and both worth stating.
 */
export function ChipLine({ chips }: { chips: ChipStatus }) {
  const playedNow = chips.playedThisGameweek?.short ?? null;

  return (
    <dl className="chip-line">
      <div className="chip-line__row">
        <dt>{t("chips.used")}</dt>
        <dd>
          {chips.used.length > 0 ? (
            chips.used.map((play) => (
              <span
                className="chip-tag"
                // The chip played in the Gameweek being viewed is the reason
                // a score looks unusual, so it keeps the colour.
                data-played={play.short === playedNow}
                data-spent={play.short !== playedNow}
                title={fullName(play.chip)}
                key={play.short}
              >
                {play.short}
              </span>
            ))
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
    </dl>
  );
}
