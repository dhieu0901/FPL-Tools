import type { CupMatch, CupRound } from "./types";

/**
 * Split a Cup into the two halves that meet in the final.
 *
 * The shape is read from the bracket itself rather than hardcoded: each tie
 * names the earlier ties feeding it, as "W(QF-1)", so following those names
 * back from the final produces the two wings. When the organisers reseed a
 * Cup, the page follows without anyone editing a layout table.
 */

export interface BracketWing {
  /** Rounds from the outermost qualifier inwards, ending at the semi-final. */
  rounds: CupRound[];
}

export interface BracketLayout {
  left: BracketWing;
  right: BracketWing;
  final: CupMatch | null;
  finalRound: CupRound | null;
  thirdPlace: CupMatch | null;
}

const WINNER_OF = /^W\((.+)\)$/;

/** The ties whose winners play in this one. */
export function feederTies(match: CupMatch): string[] {
  return [match.slotALabel, match.slotBLabel]
    .map((label) => WINNER_OF.exec(label)?.[1])
    .filter((id): id is string => Boolean(id));
}

/** Every tie that leads into `tieId`, including itself. */
function ancestry(tieId: string, byTie: Map<string, CupMatch>, seen = new Set<string>()): void {
  if (seen.has(tieId)) return;
  seen.add(tieId);
  const match = byTie.get(tieId);
  if (!match) return;
  for (const feeder of feederTies(match)) ancestry(feeder, byTie, seen);
}

function subtree(tieId: string, byTie: Map<string, CupMatch>): Set<string> {
  const seen = new Set<string>();
  ancestry(tieId, byTie, seen);
  return seen;
}

function wing(rounds: CupRound[], ties: Set<string>): BracketWing {
  return {
    rounds: rounds
      .map((round) => ({
        ...round,
        matches: round.matches.filter((match) => ties.has(match.label))
      }))
      .filter((round) => round.matches.length > 0)
  };
}

export function layoutBracket(rounds: CupRound[], thirdPlace: CupMatch | null): BracketLayout {
  const ordered = [...rounds].sort((a, b) => a.roundOrder - b.roundOrder);
  const byTie = new Map<string, CupMatch>();
  for (const round of ordered) {
    for (const match of round.matches) byTie.set(match.label, match);
  }

  const finalRound = ordered.at(-1) ?? null;
  const final = finalRound?.matches[0] ?? null;
  const earlier = ordered.slice(0, -1);

  if (!final) {
    return { left: { rounds: [] }, right: { rounds: [] }, final: null, finalRound, thirdPlace };
  }

  const [leftFeeder, rightFeeder] = feederTies(final);
  // A final drawn straight from qualification places has no wings to build.
  if (!leftFeeder || !rightFeeder) {
    return {
      left: wing(earlier, new Set(earlier.flatMap((r) => r.matches.map((m) => m.label)))),
      right: { rounds: [] },
      final,
      finalRound,
      thirdPlace
    };
  }

  return {
    left: wing(earlier, subtree(leftFeeder, byTie)),
    right: wing(earlier, subtree(rightFeeder, byTie)),
    final,
    finalRound,
    thirdPlace
  };
}

/** True once both sides of a tie are known. */
export function isDrawnTie(match: CupMatch): boolean {
  return match.home.managerId !== "tbd" && match.away.managerId !== "tbd";
}
