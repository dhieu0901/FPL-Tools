"use client";

import { createContext, type ReactNode, useContext, useMemo } from "react";
import { createTranslator, DEFAULT_LOCALE, type Locale, type Translator } from "@/lib/i18n";

const LocaleContext = createContext<Locale>(DEFAULT_LOCALE);

export function LocaleProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

export function useLocale(): Locale {
  return useContext(LocaleContext);
}

export function useTranslator(): Translator {
  const locale = useLocale();
  return useMemo(() => createTranslator(locale), [locale]);
}
