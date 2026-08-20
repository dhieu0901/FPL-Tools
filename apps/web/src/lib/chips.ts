/**
 * FPL's chip codes, in the two forms managers use.
 *
 * Shared rather than kept beside the chip line, because a chip is also named
 * in the highlights, and one league writing "TC" in one place and "3xc" in
 * another would read as two different things.
 */

const ABBREVIATIONS: Record<string, string> = {
  wildcard: "WC",
  freehit: "FH",
  bboost: "BB",
  "3xc": "TC"
};

const NAMES: Record<string, string> = {
  wildcard: "Wildcard",
  freehit: "Free Hit",
  bboost: "Bench Boost",
  "3xc": "Triple Captain"
};

/** "TC" - what a manager writes. */
export function chipAbbreviation(code: string): string {
  return ABBREVIATIONS[code] ?? code.toUpperCase();
}

/** "Triple Captain" - what a manager says. */
export function chipName(code: string): string {
  return NAMES[code] ?? code;
}
