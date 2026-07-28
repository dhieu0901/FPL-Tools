"use client";

import { setLocale } from "@/app/locale-action";
import { useLocale, useTranslator } from "./locale-provider";

function VietnamFlag() {
  return (
    <svg viewBox="0 0 60 40" className="flag-icon" aria-hidden="true">
      <rect width="60" height="40" fill="#da251d" />
      <polygon
        fill="#ff0"
        points="30,8 32.82,16.12 41.41,16.29 34.57,21.48 37.05,29.71 30,24.8 22.95,29.71 25.43,21.48 18.59,16.29 27.18,16.12"
      />
    </svg>
  );
}

function UnitedKingdomFlag() {
  return (
    <svg viewBox="0 0 60 40" className="flag-icon" aria-hidden="true">
      <clipPath id="vmf-uk-flag-quadrants">
        <path d="M30,20 h30 v20 z v-20 h-30 z h-30 v-20 z v20 h30 z" />
      </clipPath>
      <rect width="60" height="40" fill="#012169" />
      <path d="M0,0 L60,40 M60,0 L0,40" stroke="#fff" strokeWidth="8" />
      <path
        d="M0,0 L60,40 M60,0 L0,40"
        clipPath="url(#vmf-uk-flag-quadrants)"
        stroke="#c8102e"
        strokeWidth="5"
      />
      <path d="M30,0 v40 M0,20 h60" stroke="#fff" strokeWidth="13" />
      <path d="M30,0 v40 M0,20 h60" stroke="#c8102e" strokeWidth="8" />
    </svg>
  );
}

export function LocaleSwitcher() {
  const locale = useLocale();
  const t = useTranslator();

  return (
    // A server action stores the choice, so the switcher also works before
    // hydration and every page keeps rendering on the server.
    <form action={setLocale} className="locale-switcher" aria-label={t("locale.switch")}>
      <button
        type="submit"
        name="locale"
        value="vi"
        data-active={locale === "vi"}
        aria-pressed={locale === "vi"}
        title={t("locale.vi")}
      >
        <VietnamFlag />
        <span className="sr-only">{t("locale.vi")}</span>
      </button>
      <button
        type="submit"
        name="locale"
        value="en"
        data-active={locale === "en"}
        aria-pressed={locale === "en"}
        title={t("locale.en")}
      >
        <UnitedKingdomFlag />
        <span className="sr-only">{t("locale.en")}</span>
      </button>
    </form>
  );
}
