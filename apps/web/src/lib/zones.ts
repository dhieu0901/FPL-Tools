import type { Division, StandingEntry } from "./types";

/**
 * Mark the places that change division at the end of a Season.
 *
 * Six go up from LOW and six come down from HIGH, so those twelve rows are
 * the ones a manager scans for. The marker is a hint, not a verdict: the
 * rulebook sends a tie at the boundary to the tie-break chain, and where the
 * boundary rank is shared this shows nothing at all rather than picking a
 * side. Before anyone has scored, every rank is 1 and the whole table would
 * otherwise light up.
 */

export const PROMOTION_PLACES = 6;
export const RELEGATION_PLACES = 6;

export type Zone = NonNullable<StandingEntry["qualification"]>;

function boundaryIsShared(entries: StandingEntry[], boundaryRank: number): boolean {
  return entries.filter((entry) => entry.rank === boundaryRank).length > 1;
}

export function withZones(entries: StandingEntry[], division: Division): StandingEntry[] {
  if (entries.length <= PROMOTION_PLACES) return entries;

  if (division === "LOW") {
    const boundary = PROMOTION_PLACES;
    if (boundaryIsShared(entries, boundary)) return entries;
    return entries.map((entry) =>
      entry.rank <= boundary ? { ...entry, qualification: "promotion" as Zone } : entry
    );
  }

  const boundary = entries.length - RELEGATION_PLACES;
  if (boundaryIsShared(entries, boundary) || boundaryIsShared(entries, boundary + 1)) {
    return entries;
  }
  return entries.map((entry) =>
    entry.rank > boundary ? { ...entry, qualification: "relegation" as Zone } : entry
  );
}
