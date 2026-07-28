import Link from "next/link";
import { EmptyState } from "@/components/ui";
import { createTranslator } from "@/lib/i18n";
import { getLocale } from "@/lib/locale";

export default async function NotFound() {
  const t = createTranslator(await getLocale());
  return (
    <EmptyState
      title={t("notFound.title")}
      description={t("notFound.body")}
      action={
        <Link className="primary-button" href="/">
          {t("notFound.action")}
        </Link>
      }
    />
  );
}
