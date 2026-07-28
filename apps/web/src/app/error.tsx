"use client";

import { useEffect } from "react";
import { useTranslator } from "@/components/locale-provider";
import { EmptyState } from "@/components/ui";

export default function ErrorPage({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslator();

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
