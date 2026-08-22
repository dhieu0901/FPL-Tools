import { clubKit, hasKitImage } from "@/lib/club-kit";

/** The silhouette, used only for the outline drawn over the finished shirt. */
const OUTLINE =
  "M8 5.5 L11 5.5 L14 7.6 L17 5.5 L20 5.5 L25 8 L22 13.2 L20 11.6 L20 25.5 L8 25.5 L8 11.6 L6 13.2 L3 8 Z";

const LEFT_SLEEVE = "M8 5.5 L3 8 L6 13.2 L8 11.6 Z";
const RIGHT_SLEEVE = "M20 5.5 L25 8 L22 13.2 L20 11.6 Z";

/** Where the body sits, so stripes and sashes can be drawn inside it. */
const BODY = { x: 8, y: 5.5, width: 12, height: 20 };

/**
 * A club's home kit, at the height of a squad row.
 *
 * Fifteen names in a column are hard to group by reading; the same fifteen
 * group instantly by colour, which is the whole reason a squad is worth
 * seeing as shirts rather than as text. The club code stays beside it, so
 * nothing here is the only carrier of a fact - a reader who cannot separate
 * United's red from Liverpool's loses nothing, and neither can anyone else.
 *
 * Every shape is drawn inside known geometry rather than clipped, so the
 * component needs no element ids and can be repeated thirty times on a page
 * without two of them colliding.
 */
export function ClubShirt({ club, size = 18 }: { club: string | null; size?: number }) {
  const kit = clubKit(club);

  // The real shirt, where we hold one. It is the same artwork the game
  // prints, so a manager recognises his own side without reading anything.
  // The drawing below stays as the fallback: a club promoted mid-season has
  // no file yet and must still render as something.
  if (club && hasKitImage(club)) {
    return (
      // biome-ignore lint/performance/noImgElement: a 5KB shirt already sized in the markup gains nothing from the image pipeline.
      <img
        className="club-shirt club-shirt--photo"
        src={`/kits/${club.toUpperCase()}.webp`}
        width={size}
        height={size}
        alt={kit.name}
        title={kit.name}
        loading="lazy"
        decoding="async"
      />
    );
  }

  return (
    <svg
      className="club-shirt"
      width={size}
      height={size}
      viewBox="0 0 28 28"
      role="img"
      aria-label={kit.name}
    >
      <title>{kit.name}</title>

      <path d={LEFT_SLEEVE} fill={kit.sleeve} />
      <path d={RIGHT_SLEEVE} fill={kit.sleeve} />
      <rect {...BODY} fill={kit.body} />

      {kit.pattern === "stripes" &&
        // Bands across the body only, so they never spill into a sleeve.
        [9.4, 13.0, 16.6].map((x) => (
          <rect key={x} x={x} y={BODY.y} width="2.2" height={BODY.height} fill={kit.sleeve} />
        ))}

      {kit.pattern === "sash" && (
        <>
          <path d="M20 7 L20 12 L8 21.5 L8 16.5 Z" fill={kit.sleeve} />
          <path d="M20 12 L20 15.5 L8 25 L8 21.5 Z" fill={kit.accent ?? kit.sleeve} />
        </>
      )}

      {/* A collar, and the one piece of shading that stops a flat shape from
          reading as a rectangle with sleeves. */}
      <path d="M11 5.5 L14 7.6 L17 5.5 Z" fill="rgba(0, 0, 0, 0.38)" />

      {/* A white kit on a near-black panel needs an edge to exist at all. */}
      <path
        d={OUTLINE}
        fill="none"
        stroke="rgba(0, 0, 0, 0.5)"
        strokeWidth="1.2"
        strokeLinejoin="round"
      />
    </svg>
  );
}
