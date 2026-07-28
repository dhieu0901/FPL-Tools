import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export default async function Loading() {
  const t = createTranslator(await getLocale());
  return (
    <div className="loading-page" role="status" aria-live="polite">
      <div className="loading-heading" />
      <div className="loading-subheading" />
      <div className="loading-grid">
        {[1, 2, 3, 4].map((item) => (
          <div className="loading-card" key={item} />
        ))}
      </div>
      <span className="sr-only">{t("loading.label")}</span>
    </div>
  );
}
