import Link from "next/link";
import { EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <EmptyState
      title="Không tìm thấy trang"
      description="Đường dẫn này không tồn tại hoặc nội dung đã được di chuyển."
      action={
        <Link className="primary-button" href="/">
          Về tổng quan
        </Link>
      }
    />
  );
}
