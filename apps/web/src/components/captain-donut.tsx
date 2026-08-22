import { ClubShirt } from "@/components/club-shirt";
import { t } from "@/lib/i18n";
import type { CaptainPick } from "@/lib/types";

/**
 * One blue hue, brightest for the most-picked captain and stepping down by
 * rank.
 *
 * A ramp rather than one colour per player, because a categorical palette
 * runs out: eight hues is the ceiling and a ninth would be indistinguishable
 * from one already on screen. Identity here is carried by the label beside
 * each slice and by the shirt in the list below, so the colour is free to do
 * the one job it is good at - saying which share is the big one.
 *
 * The floor is set where the darkest step still clears 3:1 against the panel
 * behind it; below that a slice stops being visible at all.
 */
const RAMP_TOP = 0.78;
const RAMP_BOTTOM = 0.44;

function lightnessFor(rank: number, total: number): number {
  if (total < 2) return RAMP_TOP;
  return RAMP_TOP - (rank / (total - 1)) * (RAMP_TOP - RAMP_BOTTOM);
}

function sliceColour(rank: number, total: number): string {
  return `hsl(212 62% ${(lightnessFor(rank, total) * 100).toFixed(1)}%)`;
}

/** Ink that stays legible on the step it sits on. */
function labelColour(rank: number, total: number): string {
  return lightnessFor(rank, total) > 0.6 ? "#0b1220" : "#ffffff";
}

/**
 * Below this a slice is too thin to hold its own label, and the number is
 * read from the list instead.
 */
const LABEL_FLOOR = 0.08;

/** A point on the ring, measured clockwise from twelve o'clock. */
function point(fraction: number, radius: number): [number, number] {
  const angle = fraction * 2 * Math.PI - Math.PI / 2;
  return [50 + radius * Math.cos(angle), 50 + radius * Math.sin(angle)];
}

function arc(from: number, to: number, outer: number, inner: number): string {
  const [x1, y1] = point(from, outer);
  const [x2, y2] = point(to, outer);
  const [x3, y3] = point(to, inner);
  const [x4, y4] = point(from, inner);
  const wide = to - from > 0.5 ? 1 : 0;
  return [
    `M ${x1} ${y1}`,
    `A ${outer} ${outer} 0 ${wide} 1 ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${inner} ${inner} 0 ${wide} 0 ${x4} ${y4}`,
    "Z"
  ].join(" ");
}

/**
 * Who the league trusted with the armband.
 *
 * Every captain is shown, however few picked him: a differential captain is
 * exactly the pick worth seeing, and folding the tail into "Other" would hide
 * the only interesting decision on the page.
 *
 * The ring answers "was this a consensus or a split" at a glance. The list
 * under it is the real reading, and doubles as the table view that keeps the
 * figures available to a reader who cannot separate the shades.
 */
export function CaptainDonut({ picks, total }: { picks: CaptainPick[]; total: number }) {
  if (picks.length === 0 || total === 0) {
    return <p className="panel-note">{t("stats.noCaptains")}</p>;
  }

  let cursor = 0;
  const slices = picks.map((pick, index) => {
    const from = cursor;
    const share = pick.count / total;
    cursor += share;
    return { pick, index, from, to: cursor, share };
  });

  return (
    <div className="captain-donut">
      <svg viewBox="0 0 100 100" className="captain-donut__ring" role="img" aria-hidden="true">
        {slices.map(({ pick, index, from, to }) => (
          <path
            key={pick.elementId}
            d={arc(from, to, 46, 30)}
            fill={sliceColour(index, slices.length)}
            // A surface-coloured edge keeps neighbouring shades apart without
            // a second colour doing it.
            stroke="var(--panel)"
            strokeWidth="1.4"
          />
        ))}
        {/* One hue cannot separate four adjacent slices - measured, not
            assumed - so the number is written on the slice and the colour is
            left to do the one thing it is good at: showing the order. */}
        {slices.map(({ pick, index, from, to, share }) => {
          if (share < LABEL_FLOOR) return null;
          const [x, y] = point((from + to) / 2, 38);
          return (
            <text
              key={pick.elementId}
              x={x}
              y={y}
              className="captain-donut__slice-label"
              fill={labelColour(index, slices.length)}
            >
              {Math.round(share * 100)}%
            </text>
          );
        })}
        <text x="50" y="47" className="captain-donut__total">
          {total}
        </text>
        <text x="50" y="59" className="captain-donut__caption">
          {t("stats.squads")}
        </text>
      </svg>

      <ol className="captain-list">
        {slices.map(({ pick, index, share }) => (
          <li key={pick.elementId}>
            <span
              className="captain-list__swatch"
              style={{ background: sliceColour(index, slices.length) }}
              aria-hidden="true"
            />
            <ClubShirt club={pick.club} size={18} />
            <span className="captain-list__name">{pick.name}</span>
            <span className="captain-list__club">{pick.club}</span>
            <span className="captain-list__count">{pick.count}</span>
            <span className="captain-list__share">{Math.round(share * 100)}%</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
