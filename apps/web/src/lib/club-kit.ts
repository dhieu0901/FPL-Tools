/**
 * The twenty home kits of the 2026/27 season.
 *
 * Every colour here was sampled from FPL's own shirt artwork rather than
 * recalled, because recalling them got four of the twenty wrong: Arsenal and
 * United are plain red this season and not white-sleeved, Coventry is striped
 * and not solid, and Palace is a white shirt with a sash rather than the
 * red-and-blue stripes they are remembered for.
 *
 * Colour alone cannot carry a club. Six clubs play in red and three in white,
 * so what separates them here is what separates them on a pitch: stripes,
 * contrasting sleeves, a sash. Liverpool, United and Forest are all plain red
 * and no drawing can split them - that is what the club code beside the shirt
 * is for.
 *
 * A club with no entry renders neutral grey, so a promoted side works the day
 * it arrives and can be given a kit whenever someone gets round to it.
 */

export type KitPattern = "solid" | "stripes" | "sash";

export interface ClubKit {
  /** The dominant colour of the front of the shirt. */
  body: string;
  /** Sleeves, and the second colour of a striped shirt. */
  sleeve: string;
  /** The second band of a sash. */
  accent?: string;
  pattern: KitPattern;
  name: string;
}

export const NEUTRAL_KIT: ClubKit = {
  body: "#8B93A7",
  sleeve: "#5C6478",
  pattern: "solid",
  name: "Unknown club"
};

const KITS: Record<string, ClubKit> = {
  ARS: { body: "#E11B27", sleeve: "#D5212E", pattern: "solid", name: "Arsenal" },
  AVL: { body: "#491829", sleeve: "#95BFE5", pattern: "solid", name: "Aston Villa" },
  BHA: { body: "#1A61B4", sleeve: "#FFFFFF", pattern: "stripes", name: "Brighton" },
  BOU: { body: "#C82928", sleeve: "#2C2626", pattern: "stripes", name: "Bournemouth" },
  BRE: { body: "#CA0926", sleeve: "#FFFFFF", pattern: "stripes", name: "Brentford" },
  CHE: { body: "#1F439D", sleeve: "#1F439D", pattern: "solid", name: "Chelsea" },
  COV: { body: "#6FC5EC", sleeve: "#FFFFFF", pattern: "stripes", name: "Coventry City" },
  CRY: {
    body: "#FCFBFC",
    sleeve: "#C4122E",
    accent: "#1B458F",
    pattern: "sash",
    name: "Crystal Palace"
  },
  EVE: { body: "#1B4297", sleeve: "#1B4297", pattern: "solid", name: "Everton" },
  FUL: { body: "#F3F3F3", sleeve: "#1A1A1A", pattern: "solid", name: "Fulham" },
  HUL: { body: "#F09607", sleeve: "#28251F", pattern: "stripes", name: "Hull City" },
  IPS: { body: "#103B83", sleeve: "#8EB0DE", pattern: "solid", name: "Ipswich Town" },
  LEE: { body: "#FDFFFF", sleeve: "#1D428A", pattern: "solid", name: "Leeds United" },
  LIV: { body: "#A41432", sleeve: "#A41432", pattern: "solid", name: "Liverpool" },
  MCI: { body: "#96C5E3", sleeve: "#96C5E3", pattern: "solid", name: "Manchester City" },
  MUN: { body: "#BD0A24", sleeve: "#BD0B29", pattern: "solid", name: "Manchester United" },
  NEW: { body: "#212121", sleeve: "#FFFFFF", pattern: "stripes", name: "Newcastle United" },
  NFO: { body: "#C72830", sleeve: "#C72830", pattern: "solid", name: "Nottingham Forest" },
  SUN: { body: "#E11F23", sleeve: "#FFF4F0", pattern: "stripes", name: "Sunderland" },
  TOT: { body: "#F7F7F7", sleeve: "#132257", pattern: "solid", name: "Tottenham Hotspur" }
};

export function clubKit(code: string | null): ClubKit {
  if (!code) return NEUTRAL_KIT;
  return KITS[code.toUpperCase()] ?? { ...NEUTRAL_KIT, name: code };
}
