"use client";

import { useEffect } from "react";
import { EmptyState } from "@/components/ui";

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
      title="Không thể tải nội dung"
      description="Dữ liệu đang tạm thời gián đoạn. Bạn có thể thử tải lại mà không làm mất trạng thái."
      action={
        <button className="primary-button" type="button" onClick={reset}>
          Thử lại
        </button>
      }
    />
  );
}
