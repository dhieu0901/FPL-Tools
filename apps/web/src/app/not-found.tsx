import Link from "next/link";
import { EmptyState } from "@/components/ui";
import { t } from "@/lib/i18n";

export default async function NotFound() {
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
