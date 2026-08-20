import { chipName } from "@/lib/chips";
import type { MessageKey, Translator } from "@/lib/i18n";
import type { Highlight, HighlightKind } from "@/lib/types";

/**
 * The API returns a fact and its numbers; the sentence is written here.
 *
 * Keeping the prose out of the API means a card can be reworded without a
 * deploy on both sides, and the numbers can never disagree with the words
 * because they come from the same payload.
 */
export interface HighlightCopy {
  eyebrow: string;
  title: string;
  body: string;
  value: string;
  /** A line explaining the card, for kinds that are not self-evident. */
  note: string | null;
}

/**
 * Kinds that need explaining.
 *
 * Most cards say what they are: a captain returned two points, a bench was
 * left with fifteen. These three do not. "Lone wolf" means nothing until you
 * know ownership is counted inside this league, and a burned chip only reads
 * as a disaster once you know there are four of them in half a season.
 */
const EXPLAINED: ReadonlySet<HighlightKind> = new Set<HighlightKind>([
  "team_of_the_week",
  "lone_wolf",
  "chip_misfire"
]);

export function highlightCopy(highlight: Highlight, t: Translator): HighlightCopy {
  const variables = {
    manager: highlight.managerName,
    team: highlight.teamName,
    value: highlight.value,
    gameweek: highlight.gameweek ?? 0,
    subject: highlight.subject ?? "",
    detail: highlight.detail ?? "",
    chip: highlight.detail ? chipName(highlight.detail) : ""
  };
  const key = (suffix: string) => `highlight.${highlight.kind}.${suffix}` as MessageKey;

  return {
    eyebrow: t(key("eyebrow")),
    title: t(key("title"), variables),
    body: t(key("body"), variables),
    // TotW awards are a count; every other kind is a points total.
    value: String(highlight.value),
    note: EXPLAINED.has(highlight.kind) ? t(key("note"), variables) : null
  };
}
