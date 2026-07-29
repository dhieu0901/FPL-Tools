import type { MessageKey, Translator } from "@/lib/i18n";
import type { Highlight } from "@/lib/types";

/**
 * The API returns a fact and its numbers; the sentence is written here so the
 * same payload reads correctly in either language.
 */
export interface HighlightCopy {
  eyebrow: string;
  title: string;
  body: string;
  value: string;
}

export function highlightCopy(highlight: Highlight, t: Translator): HighlightCopy {
  const variables = {
    manager: highlight.managerName,
    team: highlight.teamName,
    value: highlight.value,
    gameweek: highlight.gameweek ?? 0
  };
  const key = (suffix: string) => `highlight.${highlight.kind}.${suffix}` as MessageKey;

  return {
    eyebrow: t(key("eyebrow")),
    title: t(key("title"), variables),
    body: t(key("body"), variables),
    // TotW awards are a count; every other kind is a points total.
    value: String(highlight.value)
  };
}
