"use client";

import { useEffect } from "react";
import { EmptyState } from "@/components/ui";
import { t } from "@/lib/i18n";

export default function ErrorPage({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <EmptyState
      icon="warning"
      title={t("error.title")}
      description={t("error.body")}
      action={
        <button className="primary-button" type="button" onClick={reset}>
          {t("common.retry")}
        </button>
      }
    />
  );
}
