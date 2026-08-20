/**
 * The 2026/27 competition rules and prize fund, as published by the organisers.
 *
 * This is reference data for the rules page, kept beside the copy rather than
 * fetched: it is decided once before the season and never derived from play.
 * The API stays the source of truth for anything that changes with results.
 */

export interface PrizeLine {
  place: string;
  amount: number;
  /** Set when one line pays several managers, e.g. both losing semi-finalists. */
  perManager?: boolean;
  note?: string;
}

export interface PrizeGroup {
  title: string;
  subtitle?: string;
  total: number;
  lines: PrizeLine[];
}

export interface PrizeSection {
  id: string;
  title: string;
  total: number;
  note?: string;
  groups: PrizeGroup[];
}

export const PRIZE_FUND_TOTAL = 9_200_000;

export const PRIZE_SECTIONS: PrizeSection[] = [
  {
    id: "classic",
    title: "Classic",
    total: 5_600_000,
    note: "2,800,000₫ per Season, paid in both halves of the year.",
    groups: [
      {
        title: "HIGH",
        subtitle: "1,450,000₫ per Season",
        total: 1_450_000,
        lines: [
          { place: "Champion", amount: 600_000 },
          { place: "Runner-up", amount: 400_000 },
          { place: "Third", amount: 250_000 },
          { place: "Fourth", amount: 200_000 }
        ]
      },
      {
        title: "LOW",
        subtitle: "1,350,000₫ per Season",
        total: 1_350_000,
        lines: [
          { place: "Champion", amount: 550_000 },
          { place: "Runner-up", amount: 350_000 },
          { place: "Third", amount: 200_000 },
          { place: "Fourth", amount: 150_000 },
          { place: "Fifth and sixth", amount: 50_000, perManager: true }
        ]
      }
    ]
  },
  {
    id: "h2h",
    title: "Head to head",
    total: 1_200_000,
    note: "One competition across all 46 managers.",
    groups: [
      {
        title: "H2H",
        total: 1_200_000,
        lines: [
          { place: "Champion", amount: 500_000 },
          { place: "Runner-up", amount: 300_000 },
          {
            place: "Third",
            amount: 150_000,
            perManager: true,
            note: "Both losing semi-finalists share third; there is no play-off for it."
          },
          { place: "Group-stage winner", amount: 100_000 }
        ]
      }
    ]
  },
  {
    id: "cup",
    title: "VMF Cup",
    total: 1_700_000,
    note: "850,000₫ per Season.",
    groups: [
      {
        title: "Cup",
        subtitle: "850,000₫ per Season",
        total: 850_000,
        lines: [
          { place: "Champion", amount: 400_000 },
          { place: "Runner-up", amount: 200_000 },
          { place: "Third", amount: 150_000, note: "Decided by a third-place match." },
          { place: "Fourth", amount: 100_000 }
        ]
      }
    ]
  },
  {
    id: "special",
    title: "Special awards",
    total: 700_000,
    groups: [
      {
        title: "Special",
        total: 700_000,
        lines: [
          { place: "Monthly Classic winner", amount: 50_000, note: "Ten months." },
          { place: "Classic number one across the full season", amount: 100_000 },
          { place: "Highest score in a single Gameweek", amount: 100_000 }
        ]
      }
    ]
  }
];

export interface RuleBlock {
  title: string;
  body: string;
  points?: string[];
}

export const FORMAT_BLOCKS: RuleBlock[] = [
  {
    title: "Classic",
    body: "46 managers in two divisions, played over two Seasons.",
    points: [
      "HIGH 20 managers · LOW 26 managers.",
      "Season 1 is GW1-GW19; Season 2 is GW20-GW38 and starts from zero.",
      "After each Season the top 6 of LOW go up and the bottom 6 of HIGH come down."
    ]
  },
  {
    title: "Head to head",
    body: "All 46 managers in one competition.",
    points: [
      "Group stage GW1-GW35.",
      "The top 8 reach the play-offs: quarter-finals GW36, semi-finals GW37, final GW38.",
      "Both losing semi-finalists share third place."
    ]
  },
  {
    title: "VMF Cup",
    body: "A knockout Cup in each half of the season.",
    points: [
      "Classic places are read after GW13 and GW32.",
      "HIGH 19-20 and LOW 23-26 do not enter; the other 40 do.",
      "Qualifying 1 · Qualifying 2 · Round of 16 · Quarter-finals · Semi-finals · Final.",
      "Season 1 runs GW14-GW19, Season 2 runs GW33-GW38, and both play a third-place match."
    ]
  }
];

export const TIE_BREAK_STEPS: string[] = [
  "More Team of the Week awards",
  "Higher captain points",
  "More goals scored",
  "Fewer cards",
  "Higher Classic points up to that Gameweek",
  "A draw made by the organisers"
];

export const VIOLATION_COUNTING: Array<{ range: string; count: string }> = [
  { range: "−12 to −16", count: "1 violation" },
  { range: "−20 to −24", count: "2 violations" },
  { range: "−28 or worse", count: "3 or more violations" }
];

export const VIOLATION_CONSEQUENCES: Array<{
  level: string;
  points: string[];
}> = [
  {
    level: "First",
    points: [
      "The whole entry fee is forfeited into the minigame and running fund.",
      "Cup: the Gameweek does not count towards qualification, and a violation in a knockout tie loses it.",
      "H2H: 6 points deducted, and a violation in a play-off loses that tie."
    ]
  },
  {
    level: "Second",
    points: ["Removed from the Cup and from H2H.", "Only 50% of any prize otherwise earned."]
  },
  { level: "Third", points: ["Removed from VMF 2026/27 entirely."] }
];

export const MANAGER_OBLIGATIONS: string[] = [
  "No transfers that take a Gameweek more than −8 in total.",
  "Join the new league on time after each Season.",
  "Follow the rulebook and the organisers' announcements."
];

export function formatDong(amount: number): string {
  return `${new Intl.NumberFormat("en-GB").format(amount)}₫`;
}
